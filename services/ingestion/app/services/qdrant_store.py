"""Qdrant store for child vectors — collection `rag_children` per CONTRACTS.md.

Payload per point: {parent_id, doc_id, filename, text, heading_path, page_no,
pages, child_index}. Payload indexes: doc_id (KEYWORD), parent_id (KEYWORD).

API verified against qdrant-client 1.18.0 (AsyncQdrantClient: collection_exists,
create_collection, create_payload_index, upsert, delete).
"""

from functools import lru_cache
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client import models as qmodels

from app.config import get_settings


@lru_cache
def get_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(url=get_settings().qdrant_url)


async def ensure_collection() -> None:
    """Idempotently create rag_children (size=1024 per CONTRACTS.md, cosine)
    with KEYWORD payload indexes on doc_id and parent_id."""
    settings = get_settings()
    client = get_client()
    if not await client.collection_exists(settings.qdrant_collection):
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qmodels.VectorParams(
                size=settings.embedding_dim,  # size=1024 (frozen contract)
                distance=qmodels.Distance.COSINE,
            ),
        )
    # create_payload_index is idempotent (re-creating an identical index is a no-op).
    for field in ("doc_id", "parent_id"):
        await client.create_payload_index(
            collection_name=settings.qdrant_collection,
            field_name=field,
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )


async def upsert_children(points: list[dict[str, Any]]) -> None:
    """Upsert child points. Each dict: {id, vector, payload} where payload holds
    parent_id, doc_id, filename, text, heading_path, page_no, pages, child_index."""
    if not points:
        return
    settings = get_settings()
    await get_client().upsert(
        collection_name=settings.qdrant_collection,
        points=[
            qmodels.PointStruct(
                id=p["id"], vector=p["vector"], payload=p["payload"]
            )
            for p in points
        ],
        wait=True,
    )


async def delete_by_doc(doc_id: str) -> None:
    """Delete all points belonging to a document (filter on doc_id payload index)."""
    settings = get_settings()
    client = get_client()
    if not await client.collection_exists(settings.qdrant_collection):
        return
    await client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="doc_id", match=qmodels.MatchValue(value=doc_id)
                    )
                ]
            )
        ),
        wait=True,
    )


async def close_client() -> None:
    await get_client().close()
    get_client.cache_clear()
