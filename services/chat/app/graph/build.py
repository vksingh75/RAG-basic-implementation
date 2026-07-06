"""Graph assembly: START -> retrieve -> generate -> END.

Compiled with the AsyncPostgresSaver checkpointer so conversation state
survives restarts. thread_id is passed per-invocation via
config={"configurable": {"thread_id": session_id}} — chat_sessions.id IS the
thread_id.

build_graph is an async factory called from the FastAPI lifespan AFTER
`await checkpointer.setup()` has created the checkpoint tables.
"""

from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph

from app.config import Settings
from app.graph.nodes import make_generate_node, make_retrieve_node
from app.graph.state import RAGState
from app.services.retrieval_client import RetrievalClient


async def build_graph(
    checkpointer: AsyncPostgresSaver,
    retrieval_client: RetrievalClient,
    llm: BaseChatModel,
    settings: Settings,
):
    workflow = StateGraph(RAGState)
    workflow.add_node("retrieve", make_retrieve_node(retrieval_client, settings))
    workflow.add_node("generate", make_generate_node(llm, settings))
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "generate")
    workflow.add_edge("generate", END)
    return workflow.compile(checkpointer=checkpointer)
