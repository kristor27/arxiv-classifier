"""Postgres: one row per judged paper. The authors' category is the ground truth; judge outputs are JSONB."""

import json
from datetime import datetime

import asyncpg

from arxiv_classifier.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id                text PRIMARY KEY,          -- arXiv id, e.g. 2610.06851
    url               text NOT NULL,
    title             text NOT NULL,
    abstract          text NOT NULL,
    authors           text NOT NULL,
    primary_category  text NOT NULL,             -- ground truth: the category the authors chose
    categories        text[] NOT NULL,           -- primary + cross-lists: the lenient ground truth
    published         timestamptz NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now(),
    jev               jsonb NOT NULL,
    llm               jsonb                      -- the comparison LLM's answer
);
CREATE INDEX IF NOT EXISTS papers_created_at ON papers (created_at DESC);
"""

COLUMNS = ("id", "url", "title", "abstract", "authors", "primary_category", "categories", "published", "jev", "llm")


async def connect() -> asyncpg.Pool:
    async def init(conn):  # read/write JSONB as Python dicts
        await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")

    pool = await asyncpg.create_pool(settings.database_url, init=init, min_size=1, max_size=10)
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(4242)")  # several replicas start at once
        await conn.execute(SCHEMA)
    return pool


def to_json(row) -> dict:
    d = dict(row)
    d["published"], d["created_at"] = d["published"].isoformat(), d["created_at"].isoformat()
    return d


async def insert_paper(pool, paper: dict) -> dict | None:
    values = {**paper, "published": datetime.fromisoformat(paper["published"])}
    row = await pool.fetchrow(
        f"INSERT INTO papers ({', '.join(COLUMNS)}) VALUES ({', '.join(f'${i + 1}' for i in range(len(COLUMNS)))}) "
        "ON CONFLICT (id) DO NOTHING RETURNING *",
        *(values.get(c) for c in COLUMNS))
    return to_json(row) if row else None


# Filters for the feed. Each is a fixed SQL fragment, never built from user input.
FILTERS = {
    "jev_wrong": "jev->>'category' <> primary_category",
    "llm_wrong": "llm IS NOT NULL AND llm->>'category' <> primary_category",
    "disagree": "llm IS NOT NULL AND jev->>'category' <> llm->>'category'",
}


async def recent(pool, limit: int, category: str | None, only: str | None) -> list[dict]:
    where = FILTERS.get(only, "TRUE")
    rows = await pool.fetch(
        f"SELECT * FROM papers WHERE ($2::text IS NULL OR primary_category = $2) AND {where} "
        "ORDER BY created_at DESC LIMIT $1", limit, category)
    return [to_json(r) for r in rows]


async def get(pool, paper_id: str) -> dict | None:
    row = await pool.fetchrow("SELECT * FROM papers WHERE id = $1", paper_id)
    return to_json(row) if row else None


# Every number is computed on the papers BOTH judges answered, so the comparison is like for like.
HEAD_TO_HEAD = """
SELECT
    count(*)                                                                    AS n,
    avg((jev->>'category' = primary_category)::int)                             AS jev_accuracy,
    avg((llm->>'category' = primary_category)::int)                             AS llm_accuracy,
    avg((jev->>'category' = ANY(categories))::int)                              AS jev_lenient,
    avg((llm->>'category' = ANY(categories))::int)                              AS llm_lenient,
    avg((jev->>'category' = llm->>'category')::int)                             AS agreement,
    percentile_cont(0.5)  WITHIN GROUP (ORDER BY (jev->>'ms')::float8)          AS jev_p50_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY (jev->>'ms')::float8)          AS jev_p95_ms,
    percentile_cont(0.5)  WITHIN GROUP (ORDER BY (llm->>'ms')::float8)          AS llm_p50_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY (llm->>'ms')::float8)          AS llm_p95_ms,
    avg((jev->>'cost')::float8)                                                 AS jev_cost_per_paper,
    avg((llm->>'cost')::float8)                                                 AS llm_cost_per_paper,
    avg((jev->>'tokens_in')::float8)                                            AS jev_tokens_in,
    avg((llm->>'tokens_in')::float8)                                            AS llm_tokens_in,
    avg((llm->>'tokens_out')::float8)                                           AS llm_tokens_out
FROM papers WHERE llm IS NOT NULL
"""

TOTALS = """
SELECT count(*) AS total, count(llm) AS with_llm,
       coalesce(sum((jev->>'cost')::float8), 0) AS jev_spent, coalesce(sum((llm->>'cost')::float8), 0) AS llm_spent
FROM papers
"""

PER_CATEGORY = """
SELECT primary_category AS category, count(*) AS n,
       avg((jev->>'category' = primary_category)::int) AS jev,
       avg((llm->>'category' = primary_category)::int) AS llm
FROM papers WHERE llm IS NOT NULL GROUP BY 1 ORDER BY 2 DESC
"""

CONFUSIONS = """
SELECT 'jev' AS engine, primary_category AS truth, jev->>'category' AS predicted, count(*) AS n
FROM papers WHERE llm IS NOT NULL AND jev->>'category' <> primary_category GROUP BY 2, 3
UNION ALL
SELECT 'llm', primary_category, llm->>'category', count(*)
FROM papers WHERE llm IS NOT NULL AND llm->>'category' <> primary_category GROUP BY 2, 3
ORDER BY n DESC
"""

ANSWERS = """
SELECT (jev->>'confidence')::float8 AS jev_conf, jev->>'category' = primary_category AS jev_ok,
       (llm->>'confidence')::float8 AS llm_conf, llm->>'category' = primary_category AS llm_ok,
       (jev->>'ms')::int AS jev_ms, (llm->>'ms')::int AS llm_ms
FROM papers WHERE llm IS NOT NULL ORDER BY created_at DESC LIMIT 2000
"""

THRESHOLDS = [i / 20 for i in range(20)]  # 0.00, 0.05 … 0.95


def coverage_curve(answers: list[tuple[float, bool]]) -> list[dict]:
    """If you only act on answers at or above a confidence threshold: how many do you keep, and how many are right?"""
    out = []
    for t in THRESHOLDS:
        kept = [ok for conf, ok in answers if conf >= t]
        out.append({"threshold": t, "coverage": len(kept) / len(answers), "accuracy": sum(kept) / len(kept) if kept else None})
    return out


def calibration(answers: list[tuple[float, bool]]) -> list[dict]:
    """Confidence in 10 bins vs how often answers in that bin were right. Perfect calibration is the diagonal."""
    bins = [[] for _ in range(10)]
    for conf, ok in answers:
        bins[min(int(conf * 10), 9)].append((conf, ok))
    return [{"confidence": sum(c for c, _ in b) / len(b), "accuracy": sum(ok for _, ok in b) / len(b), "n": len(b)}
            for b in bins if b]


async def stats(pool) -> dict:
    s = dict(await pool.fetchrow(HEAD_TO_HEAD)) | dict(await pool.fetchrow(TOTALS))
    s["per_category"] = [dict(r) for r in await pool.fetch(PER_CATEGORY)]
    confusions = [dict(r) for r in await pool.fetch(CONFUSIONS)]
    s["confusions"] = {e: [c for c in confusions if c["engine"] == e][:6] for e in ("jev", "llm")}
    rows = await pool.fetch(ANSWERS)
    for e in ("jev", "llm"):
        answers = [(r[f"{e}_conf"], r[f"{e}_ok"]) for r in rows]
        s[f"{e}_coverage"] = coverage_curve(answers) if answers else []
        s[f"{e}_calibration"] = calibration(answers) if answers else []
    s["latency"] = {"jev": [r["jev_ms"] for r in rows[:300]], "llm": [r["llm_ms"] for r in rows[:300]]}
    return s


if __name__ == "__main__":  # self-check for the curve maths
    a = [(0.95, True), (0.9, True), (0.6, False), (0.3, False)]
    c = coverage_curve(a)
    assert c[0] == {"threshold": 0.0, "coverage": 1.0, "accuracy": 0.5}, c[0]
    assert c[18] == {"threshold": 0.9, "coverage": 0.5, "accuracy": 1.0}, c[18]
    cal = calibration(a)
    assert [round(b["confidence"], 3) for b in cal] == [0.3, 0.6, 0.925] and [b["accuracy"] for b in cal] == [0, 0, 1], cal
    print("db.py ok")
