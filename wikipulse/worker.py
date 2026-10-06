"""Worker: takes edits off the Redis Stream, fetches the diff, asks the judges, stores and broadcasts the result.

Scale it horizontally: every replica joins the same consumer group, so each edit goes to exactly one worker.
"""

import asyncio
import json
import logging
import random
import socket

import redis.asyncio as redis
from redis.exceptions import ResponseError

from wikipulse import db, wiki
from wikipulse.config import settings
from wikipulse.judges import JevJudge, llm_judge
from wikipulse.ingestor import STREAM

log = logging.getLogger("worker")
GROUP = "judges"
CONSUMER = socket.gethostname()  # the pod name in Kubernetes


async def process(fields: dict, http, pool, r, jev: JevJudge, llm):
    diff = await wiki.fetch_diff(http, fields["server_url"], int(fields["old"]), int(fields["rev"]))
    edit = {
        "rev": int(fields["rev"]), "wiki": fields["wiki"], "title": fields["title"], "url": fields["url"],
        "editor": fields["editor"], "anonymous": wiki.is_anonymous(fields["editor"]),
        "comment": fields["comment"], "byte_delta": int(fields["byte_delta"]), **diff,
    }
    sampled = llm is not None and random.random() < settings.llm_sample_rate
    # Both judges run at the same time on the same input: a fair race.
    results = await asyncio.gather(jev.judge(edit), *([llm.judge(edit)] if sampled else []), return_exceptions=True)
    if isinstance(results[0], BaseException):
        raise results[0]
    edit["jev"] = results[0]
    if sampled:
        if isinstance(results[1], BaseException):
            log.warning("%s failed: %s", llm.label, str(results[1])[:120])
        else:
            edit["llm"] = results[1]
    row = await db.insert_edit(pool, edit)
    if row:
        await r.publish("verdicts", json.dumps(row))
        g = edit.get("llm")
        log.info("%-16s %5dms  %-30.30s%s", row["jev"]["verdict"], row["jev"]["ms"], row["title"],
                 f"  | {g['label']} {g['verdict']} {g['ms']}ms" if g else "")


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
            await process(fields, http, pool, r, jev, llm)
        except Exception as e:
            # ponytail: failed edits are dropped, not retried; add a dead-letter stream if every edit matters
            log.warning("edit %s skipped: %s", fields.get("rev"), e)
        finally:
            await r.xack(STREAM, GROUP, msg_id)
            sem.release()

    async with wiki.client() as http:
        log.info("worker %s ready (comparison LLM: %s)", CONSUMER, llm.label if llm else "off")
        while True:
            # Take over messages a crashed worker never acknowledged (e.g. a pod killed mid-edit).
            _, claimed, *_ = await r.xautoclaim(STREAM, GROUP, CONSUMER, min_idle_time=60_000, count=10)
            # block must stay under redis-py's 5 s default socket timeout, or the wait itself raises TimeoutError.
            batches = await r.xreadgroup(GROUP, CONSUMER, {STREAM: ">"}, count=settings.worker_concurrency, block=2000)
            for msg_id, fields in claimed + [m for _, msgs in batches for m in msgs]:
                if not fields:
                    continue
                await sem.acquire()  # at most WORKER_CONCURRENCY edits in flight; a slow one never blocks the rest
                task = asyncio.create_task(handle(msg_id, fields))
                running.add(task)
                task.add_done_callback(running.discard)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    for noisy in ("httpx", "httpx2", "typesafe_sdk", "anthropic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    asyncio.run(main())
