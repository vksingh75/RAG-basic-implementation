"""Ingestion service — FastAPI app on :8002 (nginx proxies /api/ingest/ -> /).

Startup order (lifespan):
1. open the psycopg pool
2. load the embedding model
3. FAIL FAST if EMBEDDING_DIM != model.get_sentence_embedding_dimension()
4. ensure the Qdrant collection (idempotent)
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.dao.base import close_pool, create_pool
from app.routers import documents, health
from app.services import qdrant_store
from app.services.embedder import get_embedder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # 1. Postgres pool
    pool = create_pool()
    await pool.open(wait=True)
    logger.info("Postgres pool opened")

    # 2. Embedding model (heavy — load off the event loop)
    embedder = await asyncio.to_thread(get_embedder)

    # 3. Fail-fast dimension check (CONTRACTS.md Embedding Convention)
    model_dim = embedder.model.get_sentence_embedding_dimension()
    if settings.embedding_dim != model_dim:
        raise RuntimeError(
            f"EMBEDDING_DIM mismatch: configured EMBEDDING_DIM={settings.embedding_dim} "
            f"but model '{settings.embedding_model}' produces {model_dim}-dim vectors. "
            "Fix EMBEDDING_DIM / EMBEDDING_MODEL in the environment."
        )
    logger.info("Embedding model '%s' loaded (%s-dim)", settings.embedding_model, model_dim)

    # 4. Qdrant collection (idempotent)
    await qdrant_store.ensure_collection()
    logger.info("Qdrant collection '%s' ready", settings.qdrant_collection)

    try:
        yield
    finally:
        await qdrant_store.close_client()
        await close_pool()


app = FastAPI(title="RAG-basic-implementation Ingestion Service", lifespan=lifespan)

# Mounted at root — nginx adds the /api/ingest/ prefix.
app.include_router(health.router)
app.include_router(documents.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8002)
