# One image for every Python service; Compose / Kubernetes pick the command.
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH=/app/.venv/bin:$PATH PYTHONUNBUFFERED=1

# Dependencies first: this layer stays cached until pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY arxiv_classifier ./arxiv_classifier
# Run as "nobody". Numeric, so Kubernetes can verify runAsNonRoot.
USER 65534
EXPOSE 8000
CMD ["uvicorn", "arxiv_classifier.api:app", "--host", "0.0.0.0", "--port", "8000"]
