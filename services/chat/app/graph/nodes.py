"""Graph nodes: retrieve -> generate.

Node factories close over the retrieval client / llm singletons built in the
FastAPI lifespan. Per-invocation values (thread_id, top_k) travel in the
runnable config under "configurable". The retrieve node delegates to the
Retrieval service over HTTP.
"""

from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, trim_messages
from langchain_core.runnables import RunnableConfig

from app.config import Settings
from app.graph.state import RAGState
from app.services.llm import build_numbered_context
from app.services.retrieval_client import RetrievalClient

SYSTEM_PROMPT = """\
You are a precise assistant that answers questions using ONLY the numbered \
context blocks below. Rules:
- Base every claim on the context; if the context does not contain the answer, \
say you don't know — do not invent information.
- Cite sources inline using the bracketed numbers of the blocks you used, \
e.g. [1] or [2][3], matching the numbering of the context blocks exactly.
- You may use the prior conversation for follow-up questions, but factual \
claims must still be grounded in the context blocks.

Context blocks:
{context}
"""


def make_retrieve_node(retrieval_client: RetrievalClient, settings: Settings):
    async def retrieve(state: RAGState, config: RunnableConfig) -> dict[str, Any]:
        # The latest human message is the current query.
        query = ""
        for message in reversed(state["messages"]):
            if isinstance(message, HumanMessage):
                query = str(message.content)
                break

        top_k = int(
            (config.get("configurable") or {}).get("top_k") or settings.top_k
        )
        parents = await retrieval_client.retrieve(query, top_k=top_k)
        _, citations = build_numbered_context(parents)
        return {
            "retrieved": parents,
            "citations": [c.model_dump() for c in citations],
        }

    return retrieve


def make_generate_node(llm: BaseChatModel, settings: Settings):
    async def generate(state: RAGState, config: RunnableConfig) -> dict[str, Any]:
        context, _ = build_numbered_context(state.get("retrieved", []))
        system = SystemMessage(
            content=SYSTEM_PROMPT.format(context=context or "(no context retrieved)")
        )

        # Bound history before invoking; system prompt is prepended separately.
        trimmed = trim_messages(
            state["messages"],
            max_tokens=settings.max_history_tokens,
            token_counter="approximate",
            strategy="last",
            start_on="human",
            include_system=False,
        )
        if not trimmed:
            # Degenerate case: latest turn alone exceeded the budget — never
            # invoke with an empty history.
            trimmed = state["messages"][-1:]

        response = await llm.ainvoke([system, *trimmed])
        # add_messages reducer appends the AIMessage; citations stay in state
        # for the chat router to persist/return.
        return {"messages": [response]}

    return generate
