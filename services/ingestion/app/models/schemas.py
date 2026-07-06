"""Pydantic response models — field names/types frozen in docs/CONTRACTS.md."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

DocumentStatus = Literal["pending", "processing", "completed", "failed"]


class DocumentOut(BaseModel):
    """Matches CONTRACTS.md `DocumentOut` exactly.

    `id` serializes to a uuid str; `created_at`/`updated_at` serialize to iso strings.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: Optional[str] = None
    status: DocumentStatus
    error: Optional[str] = None
    num_pages: Optional[int] = None
    num_parents: Optional[int] = None
    num_children: Optional[int] = None
    created_at: datetime
    updated_at: datetime
