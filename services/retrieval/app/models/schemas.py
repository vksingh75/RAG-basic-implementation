"""Pydantic v2 schemas — shapes frozen in docs/CONTRACTS.md (Retrieval Endpoints)."""

from pydantic import BaseModel


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 8


class ParentContext(BaseModel):
    parent_id: str
    doc_id: str
    filename: str
    heading_path: list[str]
    content: str
    page_start: int | None = None
    page_end: int | None = None
    score: float


class RetrieveResponse(BaseModel):
    parents: list[ParentContext]
