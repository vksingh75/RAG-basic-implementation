"""READ-ONLY helpers for parent_chunks (owned by the ingestion service).

Rows are enriched with documents.filename + doc_id for citation building.
"""

from typing import Any

from psycopg_pool import AsyncConnectionPool


class ParentChunkDAO:
    def __init__(self, pool: AsyncConnectionPool) -> None:
        self._pool = pool

    async def get_by_ids(self, parent_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Fetch parent chunks by id, joined with documents for citation fields.

        Returns a mapping parent_id (str) -> row dict with keys:
        id, document_id (== doc_id), heading_path, content, page_start,
        page_end, filename.
        """
        if not parent_ids:
            return {}
        async with self._pool.connection() as conn:
            cur = await conn.execute(
                """
                SELECT pc.id,
                       pc.document_id,
                       pc.heading_path,
                       pc.content,
                       pc.page_start,
                       pc.page_end,
                       d.filename
                FROM parent_chunks pc
                JOIN documents d ON d.id = pc.document_id
                WHERE pc.id = ANY(%s::uuid[])
                """,
                (parent_ids,),
            )
            rows = await cur.fetchall()
        return {str(row["id"]): dict(row) for row in rows}
