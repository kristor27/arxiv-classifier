# Can a decision model sort arXiv as well as an LLM?

A live, head-to-head evaluation of **[Jev](https://typesafe.ai)**, TypeSafe AI's *System One* decision model,
against a generative LLM (**Claude Sonnet 5.5** by default, or Gemini 3.8 Flash with `LLM_PROVIDER=gemini`).

Both models read new arXiv papers (title and abstract only) and pick the paper's primary category out of 12
computer-science categories. The right answer is known for every paper: the category its authors chose. So every
paper scores both models on **accuracy, latency and cost**, on exactly the same input, at the same instant.

## Results so far (240 papers)

| | Jev 1.13 | Claude Sonnet 5.5 |
|---|---|---|
| Accuracy (exact primary category) | 73.3% | **75.8%** |
| Lenient accuracy (any listed category) | 80.8% | **85.0%** |
| Median response | **252 ms** | 1.4 s |
| 95th percentile response | **401 ms** | 2.0 s |
| Cost per 1,000 papers | **$0.046** | $3.33 |

Sonnet is about 2.5 points more accurate; Jev is 5.6× faster and 73× cheaper. Sonnet ran with thinking off and low
effort (its fastest setting), both models got the same category definitions, and costs come from each response's
real token counts at list prices. The dashboard also shows accuracy per category, accuracy when acting only on
confident answers, calibration, and each model's most common mistakes.

```
 arXiv API (polled every 15 min, or `make benchmark N=…`)
          │
   ┌──────▼──────┐   Redis Stream    ┌──────────────┐  Jev + LLM on every paper,
   │  ingestor   │ ───────────────►  │ worker  × N  │  same input, same instant
   └─────────────┘  consumer group   └──────┬───────┘
                                            │ INSERT + PUBLISH
                                     ┌──────▼──────┐        ┌─────────────────────┐
                                     │  Postgres   │ ◄───── │  FastAPI  /api /ws  │ ◄── SvelteKit dashboard
                                     └─────────────┘        └─────────────────────┘     (served by nginx)
```

## Run it

You need Docker (OrbStack works well on a Mac), `uv`, and Node ≥ 22.12. Put your keys in `.env`
(see `.env.example`).

| Mode | Command | Open |
|---|---|---|
| **Docker Compose** | `make up`, then `make benchmark N=200` | http://localhost:8080 |
| **Kubernetes** | `make k8s-deploy`, `make k8s-open`, then `make k8s-benchmark N=200` | http://localhost:8081 |
| **Develop** (hot reload) | `make dev-infra`, then `make dev-ingestor`, `make dev-worker`, `make dev-api`, `make dev-web` | http://localhost:5173 |

`make help` lists every command. API docs are at `/api/docs`.

**Costs.** A 200-paper benchmark costs about $0.70 with Sonnet 5.5 and about $0.01 with Jev. Papers are never judged
twice, so running the benchmark again extends it. **■ Stop judging** in the dashboard stops the ingestor polling
arXiv; `make down` or `make k8s-stop` stops everything.

## Code

| File | What it does |
|---|---|
| `arxiv_classifier/judges.py` | **The judges.** Start here: the same questions, as typed Jev questions and as an LLM prompt with a JSON schema. |
| `arxiv_classifier/arxiv.py` | the arXiv API client, the parser, the 12 category definitions |
| `arxiv_classifier/ingestor.py` | arXiv → Redis, polling for new papers |
| `arxiv_classifier/benchmark.py` | queue the N latest papers for a head-to-head run |
| `arxiv_classifier/worker.py` | Redis → both judges at once → Postgres → live broadcast |
| `arxiv_classifier/db.py` | storage and every metric (accuracy, coverage curve, calibration, confusions) |
| `arxiv_classifier/api.py` | FastAPI routes + WebSocket |
| `web/` | SvelteKit dashboard |
| `deploy/k8s/` | Kubernetes manifests (Kustomize) |

`docs/` explains the infrastructure (queues, Docker, Kubernetes). It was written for the first version of this
project, which judged live Wikipedia edits; that version is in the git history.
