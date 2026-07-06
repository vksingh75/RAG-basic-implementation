"""Graph state — MessagesState extended with retrieval artifacts.

RAGState inherits the `messages` key with the add_messages reducer from
langgraph's MessagesState (langgraph 1.x: langgraph.graph.MessagesState),
which gives in-context memory across turns when combined with the
AsyncPostgresSaver checkpointer (thread_id = session_id).
"""

from typing import Any

from langgraph.graph import MessagesState


class RAGState(MessagesState):
    # Parents returned by the retriever for the current turn
    # (parent_id, doc_id, filename, heading_path, content, page_start/end, score).
    retrieved: list[dict[str, Any]]
    # Citation dicts (per docs/CONTRACTS.md Citation shape) for the current turn.
    citations: list[dict[str, Any]]
