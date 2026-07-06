"""Async ingestion pipeline — document status lifecycle:

pending -> processing -> completed | failed (error text recorded on failure;
failure cleanup deletes the document's Qdrant points).
"""

import asyncio
import logging
import os
from typing import Any
from uuid import UUID

from app.dao import documents as documents_dao
from app.dao import parent_chunks as parent_chunks_dao
from app.services import qdrant_store
from app.services.chunking import chunk_file
from app.services.embedder import get_embedder

logger = logging.getLogger(__name__)


def _build_points(
    doc_id: UUID, filename: str, children: list[dict[str, Any]], vectors: list[list[float]]
) -> list[dict[str, Any]]:
    """Qdrant points with the payload shape frozen in CONTRACTS.md."""
    return [
        {
            "id": child["id"],
            "vector": vector,
            "payload": {
                "parent_id": child["parent_id"],
                "doc_id": str(doc_id),
                "filename": filename,
                "text": child["text"],
                "heading_path": child["heading_path"],
                "page_no": child["page_no"],
                "pages": child["pages"],
                "child_index": child["child_index"],
            },
        }
        for child, vector in zip(children, vectors)
    ]


async def process_document(document_id: UUID, file_path: str, filename: str) -> None:
    """Background task: convert -> chunk -> persist parents -> embed + upsert children."""
    try:
        await documents_dao.set_status(document_id, "processing")

        # CPU-heavy docling conversion/chunking off the event loop.
        num_pages, parents, children = await asyncio.to_thread(chunk_file, file_path)

        # Parents to Postgres (uuids generated in chunking; children already mapped).
        await parent_chunks_dao.bulk_insert(document_id, parents)

        # Embed children ("passage: " prefix + normalization inside embedder).
        embedder = get_embedder()
        texts = [c["text"] for c in children]
        vectors = await asyncio.to_thread(embedder.embed_passages, texts) if texts else []

        # ensure_collection is idempotent — always invoked before upsert.
        await qdrant_store.ensure_collection()
        await qdrant_store.upsert_children(_build_points(document_id, filename, children, vectors))

        await documents_dao.update_counts(
            document_id,
            num_pages=num_pages,
            num_parents=len(parents),
            num_children=len(children),
        )
        await documents_dao.set_status(document_id, "completed")
        logger.info(
            "Ingested %s (%s): %s parents, %s children, %s pages",
            filename, document_id, len(parents), len(children), num_pages,
        )
    except Exception as exc:
        logger.exception("Ingestion failed for %s (%s)", filename, document_id)
        # Cleanup: remove any points already upserted for this doc.
        try:
            await qdrant_store.delete_by_doc(str(document_id))
        except Exception:
            logger.exception("Qdrant cleanup failed for %s", document_id)
        await documents_dao.set_status(document_id, "failed", error=str(exc))
    finally:
        try:
            os.unlink(file_path)
        except OSError:
            pass
