"""Revert checker: the ground truth. Did Wikipedia's human editors undo the edits Jev judged?

Runs once and exits — a Kubernetes CronJob schedules it every 5 minutes.
"""

import asyncio
import logging

from wikipulse import db, wiki
from wikipulse.config import settings

log = logging.getLogger("reverts")


async def main():
    pool = await db.connect()
    async with wiki.client() as http:
        for name in settings.wikis.split(","):
            server = f"https://{name.removesuffix('wiki')}.wikipedia.org"  # enwiki -> en.wikipedia.org
            # ponytail: one check 30 min after the edit; reverts that come later are missed
            while revs := await db.unchecked(pool, server):
                reverted = await wiki.reverted_revisions(http, server, revs)
                await db.mark_checked(pool, revs, reverted)
                log.info("%s: checked %d edits, %d reverted", name, len(revs), len(reverted))
    await pool.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    asyncio.run(main())
