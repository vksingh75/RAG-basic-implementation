"""DAO for the `documents` table (see infra/postgres/init.sql)."""

from typing import Any, Optional
from uuid import UUID

from app.dao.base import execute, fetch_all, fetch_one

_COLUMNS = (
    "id, filename, content_type, status, error, "
    "num_pages, num_parents, num_children, created_at, updated_at"
)


async def insert_document(filename: str, content_type: Optional[str]) -> dict[str, Any]:
    """Insert with status 'pending'; returns the full row."""
    row = await fetch_one(
        f"""
        INSERT INTO documents (filename, content_type, status)
        VALUES (%s, %s, 'pending')
        RETURNING {_COLUMNS}
        """,
        (filename, content_type),
    )
    assert row is not None
    return row


async def set_status(document_id: UUID, status: str, error: Optional[str] = None) -> None:
    await execute(
        """
        UPDATE documents
        SET status = %s, error = %s, updated_at = now()
        WHERE id = %s
        """,
        (status, error, document_id),
    )


async def update_counts(
    document_id: UUID,
    num_pages: Optional[int],
    num_parents: int,
    num_children: int,
) -> None:
    await execute(
        """
        UPDATE documents
        SET num_pages = %s, num_parents = %s, num_children = %s, updated_at = now()
        WHERE id = %s
        """,
        (num_pages, num_parents, num_children, document_id),
    )


async def list_documents() -> list[dict[str, Any]]:
    return await fetch_all(
        f"SELECT {_COLUMNS} FROM documents ORDER BY created_at DESC"
    )


async def get_document(document_id: UUID) -> Optional[dict[str, Any]]:
    return await fetch_one(
        f"SELECT {_COLUMNS} FROM documents WHERE id = %s", (document_id,)
    )


async def delete_document(document_id: UUID) -> int:
    """Delete the document row; parent_chunks cascade via FK. Returns rows deleted."""
    return await execute("DELETE FROM documents WHERE id = %s", (document_id,))
