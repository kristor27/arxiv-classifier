"""Benchmark: queue the N most recent arXiv papers so both judges race on all of them.

    python -m arxiv_classifier.benchmark 300

Papers already judged are skipped, so running it twice extends the benchmark instead of repeating it.
"""

import asyncio
import sys

import redis.asyncio as redis

from arxiv_classifier import arxiv
from arxiv_classifier.config import settings
from arxiv_classifier.ingestor import enqueue

PAGE = 100


async def main(n: int):
    r = redis.from_url(settings.redis_url, decode_responses=True)
    queued, start = 0, 0
    async with arxiv.client() as http:
        while queued < n and start < 20 * n:  # stop eventually if arXiv has fewer matching papers
            papers = await arxiv.recent(http, start=start, count=PAGE)
            queued += await enqueue(r, papers[: n - queued])
            start += PAGE
            print(f"queued {queued}/{n}", flush=True)
            await asyncio.sleep(3)  # arXiv's rate limit: one request every 3 seconds
    print(f"done: {queued} papers queued for judging")


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 100))
