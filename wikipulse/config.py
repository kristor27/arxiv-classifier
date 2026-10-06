"""All settings come from environment variables (12-factor). Same code runs in dev, Docker and Kubernetes."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    typesafe_api_key: str = ""
    jev_model: str = "jev-1.13.0"  # pinned: thresholds depend on model behaviour

    # The generative LLM Jev is compared against: "claude" (Sonnet 5.5) or "gemini" (3.8 Flash).
    llm_provider: str = "claude"
    llm_sample_rate: float = 0.25  # share of edits also sent to the LLM, for the comparison
    anthropic_api_key: str = ""
    gemini_api_key: str = ""

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql://wikipulse:wikipulse@localhost:5433/wikipulse"

    wikis: str = "enwiki"  # comma-separated, e.g. "enwiki,frwiki"
    worker_concurrency: int = 8
    user_agent: str = "WikiPulse/0.1 (educational Jev demo; https://github.com/kristor27/wikipulse)"


# Prices in USD per million tokens (checked 2026-10-01).
# Jev: output is free. Gemini 3.8 Flash: thinking tokens are billed as output.
JEV_PRICE_IN = 0.042
CLAUDE_PRICE_IN = 2.00   # Claude Sonnet 5.5
CLAUDE_PRICE_OUT = 10.00
GEMINI_PRICE_IN = 0.75
GEMINI_PRICE_OUT = 3.75

settings = Settings()
