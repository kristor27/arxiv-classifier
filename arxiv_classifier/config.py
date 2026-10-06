"""All settings come from environment variables (12-factor). Same code runs in dev, Docker and Kubernetes."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    typesafe_api_key: str = ""
    jev_model: str = "jev-1.13.0"  # pinned: thresholds depend on model behaviour

    # The generative LLM Jev is compared against: "claude" (Sonnet 5.5) or "gemini" (3.8 Flash).
    llm_provider: str = "claude"
    llm_sample_rate: float = 1.0  # share of papers also sent to the LLM; 1.0 = a full head-to-head on every paper
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://arxiv:arxiv@localhost:5433/arxiv"

    poll_minutes: int = 15  # how often the ingestor asks arXiv for new papers (arXiv announces once a day)
    worker_concurrency: int = 8
    user_agent: str = "arxiv-classifier/0.2 (educational Jev demo; https://github.com/kristor27/arxiv-classifier)"


# Prices in USD per million tokens (checked 2026-10-01).
# Jev: output is free. Gemini 3.8 Flash: thinking tokens are billed as output.
JEV_PRICE_IN = 0.042
CLAUDE_PRICE_IN = 2.00   # Claude Sonnet 5.5
CLAUDE_PRICE_OUT = 10.00
GEMINI_PRICE_IN = 0.75
GEMINI_PRICE_OUT = 3.75

settings = Settings()
