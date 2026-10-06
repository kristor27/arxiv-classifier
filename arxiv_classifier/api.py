"""HTTP API for the dashboard. Interactive docs at /api/docs."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Literal

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from arxiv_classifier import db
from arxiv_classifier.arxiv import CATEGORIES
from arxiv_classifier.config import settings
from arxiv_classifier.ingestor import PAUSED
from arxiv_classifier.judges import JevJudge, llm_judge

log = logging.getLogger("api")
clients: set[WebSocket] = set()


async def broadcast(r: redis.Redis):
    """One Redis subscription per API replica, fanned out to every open WebSocket."""
    async with r.pubsub() as ps:
        await ps.subscribe("verdicts")
        async for msg in ps.listen():
            if msg["type"] == "message":
                for ws in list(clients):
                    try:
                        await ws.send_text(msg["data"])
                    except Exception:
                        clients.discard(ws)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await db.connect()
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    llm = llm_judge()
    app.state.judges = {"jev": JevJudge()} | ({"llm": llm} if llm else {})
    task = asyncio.create_task(broadcast(app.state.redis))
    yield
    task.cancel()
    await app.state.pool.close()


app = FastAPI(title="arXiv Classifier", description="Jev vs a generative LLM, sorting new arXiv papers.",
              lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.get("/api/health")
async def health():
    await app.state.pool.fetchval("SELECT 1")
    await app.state.redis.ping()
    return {"ok": True}


@app.get("/api/papers")
async def papers(limit: int = Query(40, le=200),
                 category: Literal[tuple(CATEGORIES)] | None = None,
                 only: Literal["jev_wrong", "llm_wrong", "disagree"] | None = None):
    return await db.recent(app.state.pool, limit, category, only)


@app.get("/api/papers/{paper_id}")
async def paper(paper_id: str):
    if row := await db.get(app.state.pool, paper_id):
        return row
    raise HTTPException(404, "paper not found")


@app.get("/api/stats")
async def stats():
    s = await db.stats(app.state.pool)
    s["paused"] = bool(await app.state.redis.exists(PAUSED))
    s["categories"] = CATEGORIES
    llm = app.state.judges.get("llm")
    s["engines"] = {"jev": settings.jev_model, "llm": llm.label if llm else None}
    return s


class PipelineIn(BaseModel):
    paused: bool


@app.post("/api/pipeline")
async def pipeline(body: PipelineIn):
    """Stop or resume judging: the ingestor stops polling, so nothing new reaches the judges."""
    # ponytail: no auth — anyone who can open the dashboard can toggle this; add auth before exposing it publicly
    if body.paused:
        await app.state.redis.set(PAUSED, 1)
    else:
        await app.state.redis.delete(PAUSED)
    return {"paused": body.paused}


class PaperIn(BaseModel):
    title: str = Field(min_length=3, max_length=400)
    abstract: str = Field(min_length=20, max_length=4000)


@app.post("/api/judge/{engine}")
async def judge(engine: Literal["jev", "llm"], body: PaperIn):
    """The playground: classify any title + abstract. The dashboard calls both engines at once to race them."""
    judge = app.state.judges.get(engine)
    if not judge:
        raise HTTPException(503, f"{engine} is not configured")
    try:
        return await judge.judge(body.model_dump())
    except Exception as e:
        log.warning("%s judge failed: %s", engine, e)
        raise HTTPException(502, f"{engine} failed: {str(e)[:200]}")


@app.websocket("/ws/live")
async def live(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()  # we only push; this just waits for the client to leave
    except WebSocketDisconnect:
        clients.discard(ws)
