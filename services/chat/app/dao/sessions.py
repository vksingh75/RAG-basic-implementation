"""Read-write DAO for chat_sessions. chat_sessions.id IS the langgraph thread_id."""

from typing import Any

from psycopg_pool import AsyncConnectionPool

from app.models.schemas import SessionOut


def _to_session_out(row: dict[str, Any]) -> SessionOut:
    return SessionOut(
        id=str(row["id"]),
        title=row["title"],
        created_at=row["created_at"].isoformat(),
        updated_at=row["updated_at"].isoformat(),
    )


class SessionDAO:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def create_session(self, title: str | None = None) -> SessionOut:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                INSERT INTO chat_sessions (title)
                VALUES (%s)
                RETURNING id, title, created_at, updated_at
                """,
                (title,),
            )
            row = await cur.fetchone()
        return _to_session_out(row)

    async def list_sessions(self) -> list[SessionOut]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chat_sessions
                ORDER BY updated_at DESC
                """
            )
            rows = await cur.fetchall()
        return [_to_session_out(row) for row in rows]

    async def get_session(self, session_id: str) -> SessionOut | None:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT id, title, created_at, updated_at
                FROM chat_sessions
                WHERE id = %s
                """,
                (session_id,),
            )
            row = await cur.fetchone()
        return _to_session_out(row) if row else None

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session. chat_messages are removed via ON DELETE CASCADE."""
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                "DELETE FROM chat_sessions WHERE id = %s RETURNING id",
                (session_id,),
            )
            row = await cur.fetchone()
        return row is not None

    async def touch_session(self, session_id: str) -> None:
        """Bump updated_at so sessions sort by recent activity."""
        async with self._pool.connection() as conn:
            await conn.execute(
                "UPDATE chat_sessions SET updated_at = now() WHERE id = %s",
                (session_id,),
            )
