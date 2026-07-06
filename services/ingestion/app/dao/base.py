"""psycopg3 async connection pool + query helpers.

The pool is created here but opened/closed by the FastAPI lifespan (app/main.py).
"""

from typing import Any, Optional, Sequence

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import get_settings

_pool: Optional[AsyncConnectionPool] = None


def create_pool() -> AsyncConnectionPool:
    """Create (but do not open) the global pool. Called once from the app lifespan."""
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=get_settings().database_url,
            min_size=1,
            max_size=10,
            open=False,
            kwargs={"row_factory": dict_row, "autocommit": True},
        )
    return _pool


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("Connection pool not initialized — app lifespan not started")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def fetch_all(query: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
    async with get_pool().connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            return await cur.fetchall()


async def fetch_one(query: str, params: Sequence[Any] = ()) -> Optional[dict[str, Any]]:
    async with get_pool().connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            return await cur.fetchone()


async def execute(query: str, params: Sequence[Any] = ()) -> int:
    """Run a statement; returns affected row count."""
    async with get_pool().connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(query, params)
            return cur.rowcount


async def execute_many(query: str, params_seq: Sequence[Sequence[Any]]) -> None:
    async with get_pool().connection() as conn:
        async with conn.cursor() as cur:
            await cur.executemany(query, params_seq)
