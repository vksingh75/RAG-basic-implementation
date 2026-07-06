"""Pydantic v2 models — field names and types are FROZEN per docs/CONTRACTS.md."""

from typing import Literal

from pydantic import BaseModel


class Citation(BaseModel):
    index: int  # 1-based
    doc_id: str  # uuid str
    filename: str
    parent_id: str  # uuid str
    heading_path: list[str]
    page_start: int | None = None
    page_end: int | None = None


class ChatRequest(BaseModel):
    session_id: str  # uuid str
    message: str
    top_k: int = 8


class ChatResponse(BaseModel):
    session_id: str  # uuid str
    answer: str
    citations: list[Citation]


class SessionCreate(BaseModel):
    title: str | None = None


class SessionOut(BaseModel):
    id: str  # uuid str
    title: str | None = None
    created_at: str  # iso str
    updated_at: str  # iso str


class MessageOut(BaseModel):
    id: str  # uuid str
    session_id: str  # uuid str
    role: Literal["user", "assistant"]
    content: str
    citations: list[Citation] | None = None
    created_at: str  # iso str
