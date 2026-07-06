"""Document endpoints — shapes frozen in docs/CONTRACTS.md (proxied at /api/ingest/)."""

import os
import tempfile
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, status

from app.dao import documents as documents_dao
from app.models.schemas import DocumentOut
from app.services import qdrant_store
from app.services.pipeline import process_document

router = APIRouter()

_UPLOAD_CHUNK_SIZE = 1024 * 1024


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(file: UploadFile, background_tasks: BackgroundTasks) -> DocumentOut:
    """Accept a document, persist it to a temp path, process asynchronously. 202."""
    filename = file.filename or "upload"
    suffix = os.path.splitext(filename)[1] or ".pdf"

    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="ingest-")
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await file.read(_UPLOAD_CHUNK_SIZE):
                out.write(chunk)
    except Exception:
        os.unlink(tmp_path)
        raise

    row = await documents_dao.insert_document(filename, file.content_type)
    background_tasks.add_task(process_document, row["id"], tmp_path, filename)
    return DocumentOut(**row)


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents() -> list[DocumentOut]:
    rows = await documents_dao.list_documents()
    return [DocumentOut(**row) for row in rows]


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(document_id: UUID) -> DocumentOut:
    row = await documents_dao.get_document(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentOut(**row)


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: UUID) -> None:
    """Delete Qdrant points + Postgres rows (parent_chunks cascade). 204."""
    row = await documents_dao.get_document(document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    await qdrant_store.delete_by_doc(str(document_id))
    await documents_dao.delete_document(document_id)
