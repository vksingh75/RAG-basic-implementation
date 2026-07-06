"""Retrieval service — FastAPI on :8003 (internal, no nginx route).

Lifespan order:
  1. Open the shared psycopg AsyncConnectionPool.
  2. Load the sentence-transformers embedder and FAIL FAST if
     EMBEDDING_DIM != model.get_sentence_embedding_dimension().
  3. Create the AsyncQdrantClient.
  4. Wire ParentChunkDAO + Retriever and stash everything on app.state.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient

from app.config import get_settings
from app.dao.base import create_pool
from app.dao.parent_chunks import ParentChunkDAO
from app.routers import health, retrieve
from app.services.embedder import Embedder
from app.services.retriever import Retriever

logger = logging.getLogger("retrieval")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # 1. Shared psycopg pool (parent-chunk DAO).
    pool = create_pool(settings.database_url)
    await pool.open(wait=True, timeout=60)
    logger.info("Postgres pool opened")

    # 2. Embedder + fail-fast dimension check.
    logger.info("Loading embedding model %s ...", settings.embedding_model)
    embedder = await asyncio.to_thread(Embedder, settings.embedding_model)
    actual_dim = embedder.get_sentence_embedding_dimension()
    if actual_dim != settings.embedding_dim:
        raise RuntimeError(
            f"EMBEDDING_DIM mismatch: configured {settings.embedding_dim}, "
            f"model {settings.embedding_model} reports "
            f"{actual_dim} (get_sentence_embedding_dimension)"
        )
    logger.info("Embedding model ready (dim=%s)", actual_dim)

    # 3. Qdrant client.
    qdrant = AsyncQdrantClient(url=settings.qdrant_url)

    # 4. Wiring: DAO + retriever.
    parent_chunks = ParentChunkDAO(pool)
    retriever = Retriever(
        embedder=embedder,
        qdrant=qdrant,
        parent_chunks=parent_chunks,
        collection=settings.qdrant_collection,
        top_parents=settings.top_parents,
    )

    app.state.settings = settings
    app.state.pool = pool
    app.state.retriever = retriever
    logger.info("Retrieval service ready (collection=%s)", settings.qdrant_collection)

    try:
        yield
    finally:
        await qdrant.close()
        await pool.close()


app = FastAPI(title="Retrieval Service", lifespan=lifespan)

app.include_router(health.router)
app.include_router(retrieve.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=get_settings().retrieval_port)
