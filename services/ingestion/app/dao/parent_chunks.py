"""DAO for the `parent_chunks` table (see infra/postgres/init.sql)."""

from typing import Any
from uuid import UUID

from app.dao.base import execute_many, fetch_all


async def bulk_insert(document_id: UUID, parents: list[dict[str, Any]]) -> None:
    """Insert parent chunks with pre-generated uuids.

    Each parent dict: id, parent_index, heading_path (list[str]), content,
    page_start, page_end, token_count.
    """
    if not parents:
        return
    await execute_many(
        """
        INSERT INTO parent_chunks
            (id, document_id, parent_index, heading_path, content,
             page_start, page_end, token_count)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            (
                p["id"],
                document_id,
                p["parent_index"],
                p["heading_path"],
                p["content"],
                p["page_start"],
                p["page_end"],
                p["token_count"],
            )
            for p in parents
        ],
    )


async def get_by_document(document_id: UUID) -> list[dict[str, Any]]:
    return await fetch_all(
        """
        SELECT id, document_id, parent_index, heading_path, content,
               page_start, page_end, token_count
        FROM parent_chunks
        WHERE document_id = %s
        ORDER BY parent_index
        """,
        (document_id,),
    )
