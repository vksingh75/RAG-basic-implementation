"""Parent-child retrieval.

Flow (per docs/CONTRACTS.md + GOAL.md):
  "query: "-prefixed normalized embedding
    -> Qdrant query_points on rag_children (top_k child points)
    -> dedupe children by parent_id keeping the best (max) child score
    -> keep top `top_parents` parents ranked by best child score
    -> fetch full parent rows from Postgres (joined with documents.filename)
    -> return ordered parents with citation fields.
"""

import asyncio
from typing import Any

from qdrant_client import AsyncQdrantClient

from app.dao.parent_chunks import ParentChunkDAO
from app.services.embedder import Embedder


class Retriever:
    def __init__(
        self,
        embedder: Embedder,
        qdrant: AsyncQdrantClient,
        parent_chunks: ParentChunkDAO,
        collection: str,
        top_parents: int = 4,
    ) -> None:
        self._embedder = embedder
        self._qdrant = qdrant
        self._parent_chunks = parent_chunks
        self._collection = collection
        self._top_parents = top_parents

    async def retrieve(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        """Return up to `top_parents` parent chunks ordered by best child score.

        Each returned dict has: parent_id, doc_id, filename, heading_path,
        content, page_start, page_end, score.
        """
        # SentenceTransformer.encode is blocking — keep the event loop free.
        vector = await asyncio.to_thread(self._embedder.embed_query, query)

        response = await self._qdrant.query_points(
            collection_name=self._collection,
            query=vector,
            limit=top_k,
            with_payload=True,
        )

        # Dedupe children by parent_id, keeping the best (max) child score.
        best_by_parent: dict[str, float] = {}
        for point in response.points:
            payload = point.payload or {}
            parent_id = payload.get("parent_id")
            if parent_id is None:
                continue
            score = float(point.score)
            if parent_id not in best_by_parent or score > best_by_parent[parent_id]:
                best_by_parent[parent_id] = score

        ranked = sorted(best_by_parent.items(), key=lambda kv: kv[1], reverse=True)
        top = ranked[: self._top_parents]
        if not top:
            return []

        rows = await self._parent_chunks.get_by_ids([pid for pid, _ in top])

        parents: list[dict[str, Any]] = []
        for parent_id, score in top:
            row = rows.get(parent_id)
            if row is None:
                # Child point references a parent no longer in Postgres
                # (e.g. document deleted mid-flight) — skip it.
                continue
            parents.append(
                {
                    "parent_id": parent_id,
                    "doc_id": str(row["document_id"]),
                    "filename": row["filename"],
                    "heading_path": list(row["heading_path"] or []),
                    "content": row["content"],
                    "page_start": row["page_start"],
                    "page_end": row["page_end"],
                    "score": score,
                }
            )
        return parents
