"""POST /chat — grounded, cited, memory-persistent chat.

Dual-write pattern:
  1. Persist the user message to chat_messages (read model) BEFORE invoking.
  2. Invoke the compiled graph with thread_id = session_id (checkpointer
     restores prior turns via add_messages).
  3. Persist the assistant message WITH citations JSONB after invoking.
"""

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import HumanMessage

from app.models.schemas import ChatRequest, ChatResponse, Citation

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    sessions = request.app.state.sessions
    messages = request.app.state.messages
    graph = request.app.state.graph

    if await sessions.get_session(payload.session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # 1. Dual-write: user message before graph invocation.
    await messages.insert_message(
        session_id=payload.session_id,
        role="user",
        content=payload.message,
    )

    # 2. Invoke the graph; thread_id = session_id (str(UUID)).
    config = {
        "configurable": {
            "thread_id": str(payload.session_id),
            "top_k": payload.top_k,
        }
    }
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=payload.message)]},
        config=config,
    )

    answer = str(result["messages"][-1].content)
    citation_dicts = result.get("citations") or []
    citations = [Citation.model_validate(c) for c in citation_dicts]

    # 3. Dual-write: assistant message with citations JSONB.
    await messages.insert_message(
        session_id=payload.session_id,
        role="assistant",
        content=answer,
        citations=citation_dicts,
    )
    await sessions.touch_session(payload.session_id)

    return ChatResponse(
        session_id=payload.session_id,
        answer=answer,
        citations=citations,
    )
