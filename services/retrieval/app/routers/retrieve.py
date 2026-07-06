"""POST /retrieve per docs/CONTRACTS.md (Retrieval Endpoints).

The retriever returns dicts whose keys match ParentContext exactly.
"""

from fastapi import APIRouter, Request

from app.models.schemas import ParentContext, RetrieveRequest, RetrieveResponse

router = APIRouter()


@router.post("/retrieve")
async def retrieve(req: RetrieveRequest, request: Request) -> RetrieveResponse:
    retriever = request.app.state.retriever
    parents = await retriever.retrieve(req.query, top_k=req.top_k)
    return RetrieveResponse(parents=[ParentContext(**p) for p in parents])
