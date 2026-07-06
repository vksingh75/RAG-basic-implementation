"""Service configuration — env var names are frozen in docs/CONTRACTS.md."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Reads DATABASE_URL, QDRANT_URL, QDRANT_COLLECTION, EMBEDDING_MODEL, EMBEDDING_DIM."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://postgres:postgres@postgres:5432/rag"
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "rag_children"
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dim: int = 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
