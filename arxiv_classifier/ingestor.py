"""Ingestor: polls arXiv for new papers and pushes them onto a Redis Stream.

Run exactly ONE replica: two ingestors would queue every paper twice.
"""

import asyncio
import json
import logging

import redis.asyncio as redis

from arxiv_classifier import arxiv
from arxiv_classifier.config import settings

log = logging.getLogger("ingestor")
STREAM = "papers"
SEEN = "papers:seen"        # every paper id ever queued, so polls and benchmarks never judge one twice
PAUSED = "pipeline:paused"  # set from the dashboard: stop sending papers to the judges (and stop paying)


async def enqueue(r: redis.Redis, papers: list[dict]) -> int:
    """Queue the papers we haven't seen yet. Returns how many were new."""
    new = 0
    for p in papers:
        if await r.sadd(SEEN, p["id"]):  # SADD returns 1 only the first time an id is added
            await r.xadd(STREAM, {"paper": json.dumps(p)}, maxlen=10_000, approximate=True)
            new += 1
    return new


async def main():
    r = redis.from_url(settings.redis_url, decode_responses=True)
    async with arxiv.client() as http:
        while True:
            if await r.exists(PAUSED):
                log.info("paused, not polling")
            else:
                try:
                    new = await enqueue(r, await arxiv.recent(http))
                    log.info("polled arXiv: %d new papers queued", new)
                except Exception as e:
                    log.warning("poll failed: %s", e)
            await asyncio.sleep(settings.poll_minutes * 60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    asyncio.run(main())
