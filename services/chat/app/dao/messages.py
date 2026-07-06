"""Read-write DAO for chat_messages (dual-write read model, citations JSONB)."""

from typing import Any

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from app.models.schemas import Citation, MessageOut


def _to_message_out(row: dict[str, Any]) -> MessageOut:
    citations_raw = row["citations"]
    citations = (
        [Citation.model_validate(c) for c in citations_raw]
        if citations_raw is not None
        else None
    )
    return MessageOut(
        id=str(row["id"]),
        session_id=str(row["session_id"]),
        role=row["role"],
        content=row["content"],
        citations=citations,
        created_at=row["created_at"].isoformat(),
    )


class MessageDAO:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def insert_message(
        self,
        session_id: str,
        role: str,
        content: str,
        citations: list[dict[str, Any]] | None = None,
    ) -> MessageOut:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                INSERT INTO chat_messages (session_id, role, content, citations)
                VALUES (%s, %s, %s, %s)
                RETURNING id, session_id, role, content, citations, created_at
                """,
                (
                    session_id,
                    role,
                    content,
                    Jsonb(citations) if citations is not None else None,
                ),
            )
            row = await cur.fetchone()
        return _to_message_out(row)

    async def list_messages(self, session_id: str) -> list[MessageOut]:
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT id, session_id, role, content, citations, created_at
                FROM chat_messages
                WHERE session_id = %s
                ORDER BY created_at ASC, id ASC
                """,
                (session_id,),
            )
            rows = await cur.fetchall()
        return [_to_message_out(row) for row in rows]
