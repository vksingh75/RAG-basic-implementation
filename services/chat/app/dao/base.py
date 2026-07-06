"""Shared psycopg3 async connection pool.

One pool serves both the DAO layer and the LangGraph AsyncPostgresSaver.
AsyncPostgresSaver requires connections with autocommit=True,
prepare_threshold=0 and dict_row row factory (verified against
langgraph-checkpoint-postgres 3.1.0 source), which also suits the DAOs.
"""

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


def create_pool(database_url: str, min_size: int = 1, max_size: int = 10) -> AsyncConnectionPool:
    """Create (but do not open) the shared async connection pool.

    Caller must ``await pool.open()`` inside the FastAPI lifespan and
    ``await pool.close()`` on shutdown.
    """
    return AsyncConnectionPool(
        conninfo=database_url,
        min_size=min_size,
        max_size=max_size,
        open=False,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
    )
