"""Application settings — env var names match docs/CONTRACTS.md / .env.example."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Postgres (host = compose service `postgres`)
    database_url: str = "postgresql://postgres:postgres@postgres:5432/ragdb"

    # Qdrant
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "rag_children"

    # Embeddings — intfloat/multilingual-e5-large, 1024-dim, cosine, L2-normalized
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dim: int = 1024

    # Retrieval — deduped parents kept for context
    top_parents: int = 4

    # Service
    retrieval_port: int = 8003


@lru_cache
def get_settings() -> Settings:
    return Settings()
