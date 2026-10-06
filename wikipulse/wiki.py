"""Everything that talks to Wikipedia: the live edit stream, diffs, and revert tags."""

import html
import json
import logging
import re
from collections.abc import AsyncIterator

import httpx

from wikipulse.config import settings

log = logging.getLogger(__name__)

STREAM_URL = "https://stream.wikimedia.org/v2/stream/recentchange"
MAX_TEXT = 1500  # chars per field sent to the judges

_ROW = re.compile(r"<tr>(.*?)</tr>", re.S)
_DELETED = re.compile(r'class="diff-deletedline[^"]*"><div>(.*?)</div></td>', re.S)
_ADDED = re.compile(r'class="diff-addedline[^"]*"><div>(.*?)</div></td>', re.S)
_DEL = re.compile(r'<del class="diffchange[^"]*">(.*?)</del>', re.S)
_INS = re.compile(r'<ins class="diffchange[^"]*">(.*?)</ins>', re.S)
_TAG = re.compile(r"<[^>]+>")
_IP = re.compile(r"^(\d{1,3}(\.\d{1,3}){3}|[0-9a-fA-F:]+:[0-9a-fA-F:]*)$")


def client() -> httpx.AsyncClient:
    # Wikimedia asks every client to send a descriptive User-Agent.
    return httpx.AsyncClient(headers={"User-Agent": settings.user_agent}, timeout=20)


def _text(fragment: str) -> str:
    return html.unescape(_TAG.sub("", fragment)).strip()


def is_anonymous(user: str) -> bool:
    return bool(_IP.match(user)) or user.startswith("~")  # "~2026-…" = temporary accounts


async def recent_changes(http: httpx.AsyncClient) -> AsyncIterator[dict]:
    """Yield article edits forever, reconnecting where we left off (Server-Sent Events + Last-Event-ID)."""
    wikis = set(settings.wikis.split(","))
    last_id = None
    while True:
        headers = {"Last-Event-ID": last_id} if last_id else {}
        try:
            async with http.stream("GET", STREAM_URL, headers=headers, timeout=None) as r:
                async for line in r.aiter_lines():
                    if line.startswith("id:"):
                        last_id = line[3:].strip()
                    elif line.startswith("data:"):
                        ev = json.loads(line[5:])
                        yield ev | {"_matched": ev.get("wiki") in wikis and ev.get("type") == "edit"
                                    and ev.get("namespace") == 0 and not ev.get("bot")}
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            log.warning("stream dropped (%s), reconnecting", e)


def parse_diff(body: str) -> dict:
    """Turn MediaWiki's HTML diff table into plain removed / added / context text."""
    removed, added, context = [], [], []
    for row in _ROW.findall(body):
        d, a = _DELETED.search(row), _ADDED.search(row)
        if d and a:  # changed line: keep only the changed words, plus the new line as context
            removed += [_text(x) for x in _DEL.findall(d.group(1))] or [_text(d.group(1))]
            added += [_text(x) for x in _INS.findall(a.group(1))] or [_text(a.group(1))]
            context.append(_text(a.group(1))[:300])
        elif d:
            removed.append(_text(d.group(1)))
        elif a:
            added.append(_text(a.group(1)))
    join = lambda parts: "\n".join(p for p in parts if p)[:MAX_TEXT]
    return {"removed": join(removed), "added": join(added), "context": join(context)}


async def fetch_diff(http: httpx.AsyncClient, server_url: str, old: int, new: int) -> dict:
    r = await http.get(f"{server_url}/w/api.php", params={
        "action": "compare", "fromrev": old, "torev": new, "prop": "diff",
        "format": "json", "formatversion": 2})
    r.raise_for_status()
    return parse_diff(r.json().get("compare", {}).get("body", ""))


async def reverted_revisions(http: httpx.AsyncClient, server_url: str, revids: list[int]) -> set[int]:
    """Which of these revisions Wikipedia's own editors later reverted (MediaWiki tags them `mw-reverted`)."""
    r = await http.get(f"{server_url}/w/api.php", params={
        "action": "query", "prop": "revisions", "revids": "|".join(map(str, revids)),
        "rvprop": "ids|tags", "format": "json", "formatversion": 2})
    r.raise_for_status()
    return {rev["revid"] for page in r.json().get("query", {}).get("pages", [])
            for rev in page.get("revisions", []) if "mw-reverted" in rev.get("tags", [])}


if __name__ == "__main__":  # self-check for the diff parser
    sample = """<tr><td class="diff-deletedline diff-side-deleted"><div>Paris is the <del class="diffchange diffchange-inline">capital</del> of France.</div></td>
    <td class="diff-addedline diff-side-added"><div>Paris is the <ins class="diffchange diffchange-inline">worst city</ins> of France.</div></td></tr>
    <tr><td class="diff-addedline diff-side-added"><div>lol &amp; bye</div></td></tr>"""
    out = parse_diff(sample)
    assert out == {"removed": "capital", "added": "worst city\nlol & bye", "context": "Paris is the worst city of France."}, out
    assert is_anonymous("192.168.0.1") and is_anonymous("2a01:cb00::1") and not is_anonymous("Cloptonson")
    print("wiki.py ok")
