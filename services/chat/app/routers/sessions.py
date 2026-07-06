"""Session endpoints per docs/CONTRACTS.md.

POST   /sessions                -> SessionOut
GET    /sessions                -> list[SessionOut]
GET    /sessions/{id}/messages  -> list[MessageOut]
DELETE /sessions/{id}           -> 204; deletes session rows AND the langgraph
                                   checkpoint thread (adelete_thread).
"""

from fastapi import APIRouter, HTTPException, Request, Response

from app.models.schemas import MessageOut, SessionCreate, SessionOut

router = APIRouter()


@router.post("/sessions", response_model=SessionOut)
async def create_session(
    request: Request, payload: SessionCreate | None = None
) -> SessionOut:
    dao = request.app.state.sessions
    title = payload.title if payload is not None else None
    return await dao.create_session(title=title)


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(request: Request) -> list[SessionOut]:
    dao = request.app.state.sessions
    return await dao.list_sessions()


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
async def list_session_messages(request: Request, session_id: str) -> list[MessageOut]:
    sessions = request.app.state.sessions
    if await sessions.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = request.app.state.messages
    return await messages.list_messages(session_id)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(request: Request, session_id: str) -> Response:
    sessions = request.app.state.sessions
    deleted = await sessions.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    # Also delete the langgraph checkpoint thread (thread_id == session_id).
    # Method name verified against langgraph-checkpoint-postgres 3.1.0:
    # AsyncPostgresSaver.adelete_thread(thread_id).
    checkpointer = request.app.state.checkpointer
    await checkpointer.adelete_thread(session_id)
    return Response(status_code=204)
