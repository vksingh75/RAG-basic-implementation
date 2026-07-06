"""LLM factory + numbered [n] citation context builder.

LLM is created via langchain's init_chat_model (langchain 1.x:
`from langchain.chat_models import init_chat_model`). Default model string is
"groq:llama-3.3-70b-versatile" (GROQ_API_KEY); swappable by env only
(LLM_MODEL) — no code change needed for openai/anthropic.
"""

from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from app.models.schemas import Citation


def get_llm(model: str) -> BaseChatModel:
    """Instantiate the chat model from an init_chat_model string, e.g.
    "groq:llama-3.3-70b-versatile"."""
    return init_chat_model(model)


def _format_pages(page_start: int | None, page_end: int | None) -> str:
    if page_start is None and page_end is None:
        return ""
    if page_end is None or page_end == page_start:
        return f", p. {page_start}"
    if page_start is None:
        return f", p. {page_end}"
    return f", pp. {page_start}-{page_end}"


def build_numbered_context(
    parents: list[dict[str, Any]],
) -> tuple[str, list[Citation]]:
    """Build the numbered [n] context blocks and matching Citation objects.

    Each retrieved parent becomes a block:
        [n] (filename — heading_path, pp. X-Y)
        <content>
    and a Citation {index=n, doc_id, filename, parent_id, heading_path,
    page_start, page_end}.
    """
    blocks: list[str] = []
    citations: list[Citation] = []
    for n, parent in enumerate(parents, start=1):
        heading = " > ".join(parent["heading_path"]) if parent["heading_path"] else ""
        heading_part = f" — {heading}" if heading else ""
        pages_part = _format_pages(parent["page_start"], parent["page_end"])
        blocks.append(
            f"[{n}] ({parent['filename']}{heading_part}{pages_part})\n"
            f"{parent['content']}"
        )
        citations.append(
            Citation(
                index=n,
                doc_id=parent["doc_id"],
                filename=parent["filename"],
                parent_id=parent["parent_id"],
                heading_path=parent["heading_path"],
                page_start=parent["page_start"],
                page_end=parent["page_end"],
            )
        )
    return "\n\n".join(blocks), citations
