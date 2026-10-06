"""HTTP API for the dashboard. Interactive docs at /api/docs."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Literal

import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from wikipulse import db
from wikipulse.config import settings
from wikipulse.ingestor import PAUSED
from wikipulse.judges import TOPICS, JevJudge, llm_judge

log = logging.getLogger("api")
SECONDS_PER_YEAR = 365 * 24 * 3600
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


app = FastAPI(title="WikiPulse", description="An immune system for Wikipedia, powered by Jev.",
              lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json")


@app.get("/api/health")
async def health():
    await app.state.pool.fetchval("SELECT 1")
    await app.state.redis.ping()
    return {"ok": True}


@app.get("/api/edits")
async def edits(limit: int = Query(50, le=200),
                verdict: Literal["disruptive", "good_faith_error", "improvement"] | None = None,
                topic: str | None = Query(None, max_length=30)):
    return await db.recent(app.state.pool, limit, verdict, topic)


@app.get("/api/edits/{rev}")
async def edit(rev: int):
    if row := await db.get(app.state.pool, rev):
        return row
    raise HTTPException(404, "edit not found")


@app.get("/api/stats")
async def stats():
    s = await db.stats(app.state.pool)
    rate = float(await app.state.redis.get("rate:all_edits_per_s") or 0)
    llm_per_edit = s["llm_cost_per_edit"]
    s["all_wikimedia_edits_per_s"] = rate
    # What it would cost to judge every edit we judged — and every edit on all of Wikimedia for a year.
    s["llm_cost_if_all"] = llm_per_edit * s["total"] if llm_per_edit else None
    s["jev_cost_per_year_all_wikimedia"] = s["jev_cost_per_edit"] * rate * SECONDS_PER_YEAR
    s["llm_cost_per_year_all_wikimedia"] = llm_per_edit * rate * SECONDS_PER_YEAR if llm_per_edit else None
    s["paused"] = bool(await app.state.redis.exists(PAUSED))
    s["topic_names"] = list(TOPICS)
    llm = app.state.judges.get("llm")
    s["engines"] = {"jev": settings.jev_model, "llm": llm.label if llm else None}
    return s


class PipelineIn(BaseModel):
    paused: bool


@app.post("/api/pipeline")
async def pipeline(body: PipelineIn):
    """Stop or resume judging. The stream keeps being read; edits are just not sent to the judges."""
    # ponytail: no auth — anyone who can open the dashboard can toggle this; add auth before exposing it publicly
    if body.paused:
        await app.state.redis.set(PAUSED, 1)
    else:
        await app.state.redis.delete(PAUSED)
    return {"paused": body.paused}


class EditIn(BaseModel):
    title: str = Field(max_length=300)
    comment: str = Field("", max_length=500)
    removed: str = Field("", max_length=1500)
    added: str = Field("", max_length=1500)
    anonymous: bool = True


@app.post("/api/judge/{engine}")
async def judge(engine: Literal["jev", "llm"], body: EditIn):
    """The playground: judge a made-up edit. The dashboard calls both engines at once to race them."""
    judge = app.state.judges.get(engine)
    if not judge:
        raise HTTPException(503, f"{engine} is not configured")
    edit = body.model_dump() | {"context": "", "byte_delta": len(body.added) - len(body.removed)}
    try:
        return await judge.judge(edit)
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
