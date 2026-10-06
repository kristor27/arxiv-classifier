"""Ingestor: reads Wikipedia's live edit stream and pushes article edits onto a Redis Stream.

Run exactly ONE replica: two ingestors would push every edit twice.
"""

import asyncio
import logging
import time

import redis.asyncio as redis

from wikipulse import wiki
from wikipulse.config import settings

log = logging.getLogger("ingestor")
STREAM = "edits"
PAUSED = "pipeline:paused"  # set from the dashboard: stop sending edits to the judges (and stop paying)


async def main():
    r = redis.from_url(settings.redis_url, decode_responses=True)
    seen, window_start = 0, time.monotonic()
    async with wiki.client() as http:
        async for ev in wiki.recent_changes(http):
            if ev.get("type") == "edit":
                seen += 1
            if ev["_matched"] and not await r.exists(PAUSED):
                edit = {
                    "rev": ev["revision"]["new"], "old": ev["revision"].get("old") or 0,
                    "wiki": ev["wiki"], "server_url": ev["server_url"], "title": ev["title"],
                    "url": ev["notify_url"], "editor": ev["user"], "comment": ev.get("comment", ""),
                    "byte_delta": ev["length"]["new"] - (ev["length"].get("old") or 0),
                }
                # MAXLEN keeps Redis memory bounded if the workers fall behind.
                await r.xadd(STREAM, {k: str(v) for k, v in edit.items()}, maxlen=10_000, approximate=True)
            elapsed = time.monotonic() - window_start
            if elapsed >= 10:  # the whole of Wikimedia's edit rate, used for the cost projection
                await r.set("rate:all_edits_per_s", seen / elapsed)
                log.info("all Wikimedia: %.1f edits/s", seen / elapsed)
                seen, window_start = 0, time.monotonic()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    asyncio.run(main())
