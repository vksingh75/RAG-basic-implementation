"""HTTP client for the Retrieval service (see docs/CONTRACTS.md).

The chat agent no longer embeds queries or talks to Qdrant/Postgres for
parent chunks — the retrieve graph node delegates to the Retrieval service
via POST {RETRIEVAL_URL}/retrieve. A non-200 response raises
httpx.HTTPStatusError, which surfaces as a 500 from /chat (per CONTRACTS).
"""

from typing import Any

import httpx


class RetrievalClient:
    """Thin async wrapper around the Retrieval service's /retrieve endpoint."""

    def __init__(self, base_url: str, client: httpx.AsyncClient):
        self.base_url = base_url.rstrip("/")
        self.client = client

    async def retrieve(self, query: str, top_k: int = 8) -> list[dict[str, Any]]:
        """POST /retrieve and return the parents list.

        Each parent dict matches the frozen ParentContext shape
        (parent_id, doc_id, filename, heading_path, content, page_start,
        page_end, score) that build_numbered_context expects.
        """
        resp = await self.client.post(
            f"{self.base_url}/retrieve",
            json={"query": query, "top_k": top_k},
            timeout=30.0,
        )
        resp.raise_for_status()
        return resp.json()["parents"]
