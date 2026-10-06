# 2. The pipeline

## Server-Sent Events in (`wiki.py`)

Wikimedia publishes every change to every wiki at `stream.wikimedia.org/v2/stream/recentchange`.
It's a plain HTTP response that never ends: one `data: {json}` line per event, plus an `id:` line.
If the connection drops, we reconnect and send `Last-Event-ID`, and the stream resumes where we
left off. Wikimedia asks every client to send a descriptive `User-Agent`.

## Why a queue between ingestor and workers?

Edits arrive in bursts, and judging one takes a network round trip to Wikipedia (for the diff) and
another to Jev. The ingestor only reads and enqueues, which is fast, so it never falls behind the
stream. The workers do the slow part, and you can run as many as you need.

**Redis Streams** fit well here:

- `XADD edits * …` appends an edit, with `MAXLEN ~10000` so memory stays bounded.
- `XREADGROUP GROUP judges <worker>` gives each message to exactly **one** worker in the
  consumer group, so adding replicas splits the work instead of duplicating it.
- `XACK` marks it done. If a worker dies before acking (for example a pod killed mid-edit),
  `XAUTOCLAIM` lets another worker take the message over after 60 seconds.

Inside a worker, a semaphore caps the number of edits in flight (`WORKER_CONCURRENCY`), and every
edit runs as its own task, so one slow LLM call never blocks the others.

## Fan-out to browsers

After the `INSERT`, the worker runs `PUBLISH verdicts <json>`. Each API replica holds **one**
Redis subscription and forwards every message to all of its WebSocket clients (`api.py`,
`broadcast`). With 2 API pods and 100 viewers, that's still only 2 Redis subscriptions.

## Routes

| Route | Purpose |
|---|---|
| `GET /api/edits?verdict=…` | latest judged edits |
| `GET /api/edits/{rev}` | one edit |
| `GET /api/stats` | counters, latency samples, costs, projections, accuracy |
| `POST /api/judge/{jev\|llm}` | the race playground: judge a made-up edit |
| `WS /ws/live` | push of every new verdict |
| `GET /api/health` | checks Postgres + Redis; used by the Kubernetes probes |
