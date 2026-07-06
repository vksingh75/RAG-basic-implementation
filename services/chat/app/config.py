"""Application settings — env var names match docs/CONTRACTS.md / .env.example."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres (host = compose service `postgres`)
    database_url: str = "postgresql://postgres:postgres@postgres:5432/ragdb"

    # Retrieval service (HTTP) — the chat agent delegates retrieval here
    retrieval_url: str = "http://retrieval:8003"

    # LLM — init_chat_model model string; provider swappable by env only
    llm_model: str = "groq:llama-3.3-70b-versatile"
    groq_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    # Retrieval
    top_k: int = 8            # default top_k forwarded to the retrieval service

    # History bounding (approximate tokens) for trim_messages
    max_history_tokens: int = 3000

    # Service
    chat_port: int = 8001


@lru_cache
def get_settings() -> Settings:
    return Settings()
