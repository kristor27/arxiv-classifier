"""Worker: takes papers off the Redis Stream, asks both judges at the same instant, stores and broadcasts the result.

Scale it horizontally: every replica joins the same consumer group, so each paper goes to exactly one worker.
"""

import asyncio
import json
import logging
import random
import socket

import redis.asyncio as redis
from redis.exceptions import ResponseError

from arxiv_classifier import db
from arxiv_classifier.config import settings
from arxiv_classifier.ingestor import STREAM
from arxiv_classifier.judges import JevJudge, llm_judge

log = logging.getLogger("worker")
GROUP = "judges"
CONSUMER = socket.gethostname()  # the pod name in Kubernetes


async def process(paper: dict, pool, r, jev: JevJudge, llm):
    sampled = llm is not None and random.random() < settings.llm_sample_rate
    # Both judges run at the same time on the same input: a fair race.
    results = await asyncio.gather(jev.judge(paper), *([llm.judge(paper)] if sampled else []), return_exceptions=True)
    if isinstance(results[0], BaseException):
        raise results[0]
    paper["jev"] = results[0]
    if sampled:
        if isinstance(results[1], BaseException):
            log.warning("%s failed: %s", llm.label, str(results[1])[:120])
        else:
            paper["llm"] = results[1]
    row = await db.insert_paper(pool, paper)
    if row:
        await r.publish("verdicts", json.dumps(row))
        mark = lambda j: f"{j['category']:6} {'✓' if j['category'] == paper['primary_category'] else '✗'} {j['ms']:5}ms"
        g = paper.get("llm")
        log.info("truth %-6s | jev %s%s | %.40s", paper["primary_category"], mark(paper["jev"]),
                 f" | llm {mark(g)}" if g else "", paper["title"])


async def main():
    r = redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await r.xgroup_create(STREAM, GROUP, id="$", mkstream=True)
    except ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise
    pool = await db.connect()
    jev = JevJudge()
    llm = llm_judge()
    sem = asyncio.Semaphore(settings.worker_concurrency)
    running = set()

    async def handle(msg_id, fields):
        try:
            await process(json.loads(fields["paper"]), pool, r, jev, llm)
        except Exception as e:
            # ponytail: failed papers are dropped, not retried; add a dead-letter stream if every paper matters
            log.warning("paper skipped: %s", e)
        finally:
            await r.xack(STREAM, GROUP, msg_id)
            sem.release()

    log.info("worker %s ready (comparison LLM: %s)", CONSUMER, llm.label if llm else "off")
    while True:
        # Take over messages a crashed worker never acknowledged (e.g. a pod killed mid-paper).
        _, claimed, *_ = await r.xautoclaim(STREAM, GROUP, CONSUMER, min_idle_time=60_000, count=10)
        # block must stay under redis-py's 5 s default socket timeout, or the wait itself raises TimeoutError.
        batches = await r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=settings.worker_concurrency, block=2000)
        for msg_id, fields in claimed + [m for _, msgs in batches for m in msgs]:
            if not fields:
                continue
            await sem.acquire()  # at most WORKER_CONCURRENCY papers in flight; a slow one never blocks the rest
            task = asyncio.create_task(handle(msg_id, fields))
            running.add(task)
            task.add_done_callback(running.discard)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    for noisy in ("httpx", "httpx2", "typesafe_sdk", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    asyncio.run(main())
