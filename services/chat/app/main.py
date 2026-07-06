"""Chat Agent service — FastAPI + LangGraph on :8001 (proxied at /api/rag/).

The retrieve step no longer embeds queries or talks to Qdrant — it calls the
Retrieval service over HTTP (POST {RETRIEVAL_URL}/retrieve).

Lifespan order:
  1. Open the shared psycopg AsyncConnectionPool.
  2. Create AsyncPostgresSaver on the pool and `await checkpointer.setup()`
     (creates the langgraph checkpoint tables — NOT in init.sql).
  3. Create the httpx client + RetrievalClient (non-fatal /health ping).
  4. Build the compiled graph and stash everything on app.state.

Routers are mounted at root; nginx adds the /api/rag/ prefix.
"""

import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import get_settings
from app.dao.base import create_pool
from app.dao.messages import MessageDAO
from app.dao.sessions import SessionDAO
from app.graph.build import build_graph
from app.routers import chat, health, sessions
from app.services.llm import get_llm
from app.services.retrieval_client import RetrievalClient

logger = logging.getLogger("chat")
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # init_chat_model providers read API keys from the environment; mirror
    # settings values there in case they were loaded from a .env file only.
    for env_name, value in (
        ("GROQ_API_KEY", settings.groq_api_key),
        ("OPENAI_API_KEY", settings.openai_api_key),
        ("ANTHROPIC_API_KEY", settings.anthropic_api_key),
    ):
        if value and not os.environ.get(env_name):
            os.environ[env_name] = value

    # 1. Shared psycopg pool (DAOs + checkpointer).
    pool = create_pool(settings.database_url)
    await pool.open(wait=True, timeout=60)
    logger.info("Postgres pool opened")

    # 2. Checkpointer — creates checkpoint tables (NOT in init.sql).
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    logger.info("LangGraph checkpoint tables ready (checkpointer.setup)")

    # 3. HTTP retrieval client + optional, non-fatal startup ping.
    http_client = httpx.AsyncClient()
    retrieval_client = RetrievalClient(settings.retrieval_url, http_client)
    try:
        resp = await http_client.get(
            f"{settings.retrieval_url}/health", timeout=5
        )
        resp.raise_for_status()
        logger.info("Retrieval service reachable at %s", settings.retrieval_url)
    except Exception as exc:  # noqa: BLE001 — startup ping is best-effort
        logger.warning("retrieval /health not reachable yet: %s", exc)

    # 4. Wiring: LLM, compiled graph, DAOs.
    llm = get_llm(settings.llm_model)
    graph = await build_graph(checkpointer, retrieval_client, llm, settings)

    app.state.settings = settings
    app.state.pool = pool
    app.state.checkpointer = checkpointer
    app.state.retrieval_client = retrieval_client
    app.state.graph = graph
    app.state.sessions = SessionDAO(pool)
    app.state.messages = MessageDAO(pool)
    logger.info("Chat Agent service ready (llm=%s)", settings.llm_model)

    try:
        yield
    finally:
        await http_client.aclose()
        await pool.close()


app = FastAPI(title="Chat Agent Service", lifespan=lifespan)

app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(chat.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=get_settings().chat_port)
