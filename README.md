# WikiPulse

**An immune system for Wikipedia.** Every edit to English Wikipedia is judged live by
[Jev](https://typesafe.ai), TypeSafe AI's *System One* decision model: is it **disruptive**, a
**good-faith error**, or an **improvement**? A sample of the same edits goes to a generative LLM
(Claude Sonnet 5.5 by default, or Gemini 3.8 Flash with `LLM_PROVIDER=gemini`) at the same moment, so the dashboard shows the speed and cost difference live.

```
 Wikimedia EventStreams (SSE, ~15-25 edits/s worldwide)
          │
   ┌──────▼──────┐   Redis Stream    ┌──────────────┐  Jev on 100% of edits
   │  ingestor   │ ───────────────►  │ worker  × N  │  LLM on a 25% sample (same input, same instant)
   └─────────────┘  consumer group   └──────┬───────┘
                                            │ INSERT + PUBLISH
                         ┌──────────────────▼──┐        ┌─────────────────────┐
   CronJob every 5 min → │      Postgres       │ ◄───── │  FastAPI  /api /ws  │ ◄── SvelteKit dashboard
   "did humans revert?"  └─────────────────────┘        └─────────────────────┘     (served by nginx)
```

## Why Jev here?

A generative LLM writes its answer token by token, and you then parse that text. Jev is given
the state and a fixed set of typed questions, and returns **calibrated probabilities over the
allowed answers in one forward pass**. It never writes free text, so there is no JSON to parse
and it can't answer with a label you didn't offer.

| measured on this project | Jev 1.13 | Claude Sonnet 5.5 (thinking off, low effort) |
|---|---|---|
| median response | ~240 ms | see the dashboard |
| price | $0.042 / M input, output free | $2 / M input, $10 / M output |
| answers | 4 typed answers + probabilities, one call | one generated JSON object |

## Run it

You need Docker (OrbStack works well on a Mac), `uv`, and Node ≥ 22.12. Put your keys in `.env`
(see `.env.example`).

| Mode | Command | Open |
|---|---|---|
| **Develop** (hot reload) | `make dev-infra`, then `make dev-ingestor`, `make dev-worker`, `make dev-api`, `make dev-web`, each in its own terminal | http://localhost:5173 |
| **Docker Compose** | `make up` | http://localhost:8080 |
| **Kubernetes** | `make k8s-deploy` then `make k8s-open` | http://localhost:8081 |

`make help` lists every command. API docs are at `/api/docs`.

**Stopping (and stopping the bill):** press **■ Stop judging** in the dashboard header. The
stream is still read, but no edits go to Jev or the LLM until you press *Resume*. To stop
everything: `make down` (Compose) or `make k8s-stop` (scales ingestor and workers to 0;
`make k8s-start` brings them back).

## Learn from it

The code is small on purpose. Read the docs in this order:

1. [docs/01-jev.md](docs/01-jev.md): how a Jev call works and how the questions were designed
2. [docs/02-pipeline.md](docs/02-pipeline.md): SSE, Redis Streams, consumer groups, WebSockets
3. [docs/03-docker.md](docs/03-docker.md): one image for many services, multi-stage builds, Compose
4. [docs/04-kubernetes.md](docs/04-kubernetes.md): Deployments, StatefulSets, CronJobs, probes, scaling, and deploying on a real server with k3s

| File | What it does |
|---|---|
| `wikipulse/judges.py` | **The two judges.** Start here. |
| `wikipulse/wiki.py` | Wikipedia stream, diffs, revert tags |
| `wikipulse/ingestor.py` | stream → Redis |
| `wikipulse/worker.py` | Redis → diff → judges → Postgres → live broadcast |
| `wikipulse/reverts.py` | ground truth: did Wikipedia's editors undo it? |
| `wikipulse/api.py` | FastAPI routes + WebSocket |
| `web/` | SvelteKit dashboard |
| `deploy/k8s/` | Kubernetes manifests (Kustomize) |
