# 3. Docker

## One image, many services

`ingestor`, `worker`, `reverts` and `api` are the same Python code started with different
commands, so they share **one image** (`wikipulse:latest`) and Compose or Kubernetes picks the
command. That means one build, one thing to scan, and one version running everywhere.

Things to notice in `Dockerfile`:

- **Layer order.** `pyproject.toml` and `uv.lock` are copied and installed *before* the code. When
  you change Python code, the dependency layer comes from cache and the build takes seconds.
- `uv sync --frozen` installs exactly what the lockfile says, with no surprise upgrades.
- `USER 65534` runs as a non-root user. It's numeric so Kubernetes can verify it. (A `#` comment
  after an instruction is *not* a comment in a Dockerfile; that mistake cost us one failed deploy.)
- **Secrets never go in the image.** `.dockerignore` excludes `.env`, and keys are injected at
  run time.

## Multi-stage build for the web

`web/Dockerfile` builds the SvelteKit site with Node, then copies only the static files into
`nginx:alpine`. The final image is ~60 MB and contains no Node. nginx also proxies `/api` and
`/ws` to the `api` hostname, which works unchanged in Compose (container name) and in
Kubernetes (Service name).

## Compose

`compose.yaml` runs the full stack: Postgres with a named volume and a healthcheck, Redis, and the
app services, which wait for `service_healthy` before starting. `deploy.replicas: 2` on the worker
already shows horizontal scaling. Postgres is exposed on host port **5433** so it doesn't clash
with a Postgres already installed on your machine.
