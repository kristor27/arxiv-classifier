"""Postgres: one table, one row per judged edit. Judge outputs are stored as JSONB."""

import json

import asyncpg

from wikipulse.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS edits (
    rev         bigint PRIMARY KEY,
    wiki        text NOT NULL,
    title       text NOT NULL,
    url         text NOT NULL,
    editor      text NOT NULL,
    anonymous   boolean NOT NULL,
    comment     text NOT NULL,
    byte_delta  integer NOT NULL,
    removed     text NOT NULL,
    added       text NOT NULL,
    context     text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    jev         jsonb NOT NULL,
    llm         jsonb,        -- the comparison LLM's answer, on a sample of edits
    reverted    boolean,      -- filled later by the revert checker: did Wikipedia's humans undo it?
    checked_at  timestamptz
);
CREATE INDEX IF NOT EXISTS edits_created_at ON edits (created_at DESC);
-- One-time migration: the comparison column used to be called "gemini".
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'edits' AND column_name = 'gemini') THEN
        ALTER TABLE edits RENAME COLUMN gemini TO llm;
    END IF;
END $$;
"""

COLUMNS = ("rev", "wiki", "title", "url", "editor", "anonymous", "comment", "byte_delta",
           "removed", "added", "context", "jev", "llm")


async def connect() -> asyncpg.Pool:
    async def init(conn):  # read/write JSONB as Python dicts
        await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")

    pool = await asyncpg.create_pool(settings.database_url, init=init, min_size=1, max_size=10)
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(4242)")  # several replicas start at once
        await conn.execute(SCHEMA)
    return pool


async def insert_edit(pool: asyncpg.Pool, edit: dict) -> dict:
    row = await pool.fetchrow(
        f"INSERT INTO edits ({', '.join(COLUMNS)}) VALUES ({', '.join(f'${i + 1}' for i in range(len(COLUMNS)))}) "
        "ON CONFLICT (rev) DO NOTHING RETURNING *",
        *(edit.get(c) for c in COLUMNS))
    return to_json(row) if row else None


def to_json(row) -> dict:
    d = dict(row)
    for k in ("created_at", "checked_at"):
        d[k] = d[k].isoformat() if d[k] else None
    return d


async def recent(pool, limit: int, verdict: str | None, topic: str | None) -> list[dict]:
    rows = await pool.fetch(
        "SELECT * FROM edits WHERE ($2::text IS NULL OR jev->>'verdict' = $2) AND ($3::text IS NULL OR jev->>'topic' = $3) "
        "ORDER BY created_at DESC LIMIT $1",
        limit, verdict, topic)
    return [to_json(r) for r in rows]


async def get(pool, rev: int) -> dict | None:
    row = await pool.fetchrow("SELECT * FROM edits WHERE rev = $1", rev)
    return to_json(row) if row else None


STATS = """
SELECT
    count(*)                                                        AS total,
    count(*) FILTER (WHERE jev->>'verdict' = 'disruptive')          AS disruptive,
    count(*) FILTER (WHERE jev->>'verdict' = 'good_faith_error')    AS good_faith_error,
    count(*) FILTER (WHERE jev->>'verdict' = 'improvement')         AS improvement,
    coalesce(sum((jev->>'cost')::float8), 0)                        AS jev_cost,
    coalesce(avg((jev->>'cost')::float8), 0)                        AS jev_cost_per_edit,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY (jev->>'ms')::float8)    AS jev_p50_ms,
    count(llm)                                                      AS llm_n,
    coalesce(sum((llm->>'cost')::float8), 0)                        AS llm_cost,
    avg((llm->>'cost')::float8)                                     AS llm_cost_per_edit,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY (llm->>'ms')::float8)    AS llm_p50_ms,
    avg((jev->>'verdict' = llm->>'verdict')::int)                   AS agreement,
    count(*) FILTER (WHERE checked_at IS NOT NULL)                  AS checked,
    count(*) FILTER (WHERE reverted)                                AS reverted,
    count(*) FILTER (WHERE reverted AND jev->>'verdict' <> 'improvement')                         AS caught,
    count(*) FILTER (WHERE checked_at IS NOT NULL AND jev->>'verdict' = 'disruptive')             AS flagged_checked,
    count(*) FILTER (WHERE reverted AND jev->>'verdict' = 'disruptive')                           AS flagged_reverted
FROM edits
"""

PULSE = """
SELECT extract(epoch FROM date_trunc('minute', created_at))::bigint AS t, jev->>'verdict' AS verdict, count(*) AS n
FROM edits WHERE created_at > now() - interval '30 minutes' GROUP BY 1, 2 ORDER BY 1
"""

TOPICS = """
SELECT jev->>'topic' AS topic, count(*) AS n, count(*) FILTER (WHERE jev->>'verdict' = 'disruptive') AS disruptive
FROM edits WHERE jev ? 'topic' GROUP BY 1 ORDER BY 2 DESC
"""

LATENCY = """
(SELECT 'jev' AS engine, (jev->>'ms')::int AS ms FROM edits ORDER BY created_at DESC LIMIT 300)
UNION ALL
(SELECT 'llm', (llm->>'ms')::int FROM edits WHERE llm IS NOT NULL ORDER BY created_at DESC LIMIT 300)
"""


async def stats(pool) -> dict:
    s = dict(await pool.fetchrow(STATS))
    s["pulse"] = [dict(r) for r in await pool.fetch(PULSE)]
    s["topics"] = [dict(r) for r in await pool.fetch(TOPICS)]
    lat = {"jev": [], "llm": []}
    for r in await pool.fetch(LATENCY):
        lat[r["engine"]].append(r["ms"])
    s["latency"] = lat
    return s


async def unchecked(pool, wiki_server: str, older_than_min: int = 30, limit: int = 50) -> list[int]:
    rows = await pool.fetch(
        "SELECT rev FROM edits WHERE url LIKE $1 || '%' AND checked_at IS NULL "
        "AND created_at < now() - make_interval(mins => $2) ORDER BY created_at LIMIT $3",
        wiki_server, older_than_min, limit)
    return [r["rev"] for r in rows]


async def mark_checked(pool, revs: list[int], reverted: set[int]):
    await pool.execute(
        "UPDATE edits SET checked_at = now(), reverted = rev = ANY($2::bigint[]) WHERE rev = ANY($1::bigint[])",
        revs, list(reverted))
