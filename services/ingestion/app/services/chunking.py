"""docling hierarchical parent-child chunking.

Children: HybridChunker ~256-token chunks (HuggingFaceTokenizer bound to the
embedding model), contextualized text, heading_path, per-page info from
chunk.meta.doc_items[].prov[].page_no.

Parents: consecutive children sharing the same heading_path, split when the
accumulated token count would exceed ~2000.

API verified against docling 2.109.0 / docling-core 2.86.0:
- HuggingFaceTokenizer at docling_core.transforms.chunker.tokenizer.huggingface
  with from_pretrained(model_name, max_tokens=...) and count_tokens(text)
  (current wrapper API — the older plain-string tokenizer arg is deprecated).
- HybridChunker(tokenizer=<BaseTokenizer>); chunker.contextualize(chunk);
  chunk.meta.headings (list[str] | None); chunk.meta.doc_items[].prov[].page_no.
"""

import uuid
from functools import lru_cache
from typing import Any, Optional

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer

from app.config import get_settings

CHILD_MAX_TOKENS = 256
PARENT_MAX_TOKENS = 2000


@lru_cache
def get_converter() -> DocumentConverter:
    """DocumentConverter with OCR disabled by default (speed)."""
    pdf_options = PdfPipelineOptions(do_ocr=False)
    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options)}
    )


@lru_cache
def get_tokenizer() -> HuggingFaceTokenizer:
    return HuggingFaceTokenizer.from_pretrained(
        get_settings().embedding_model, max_tokens=CHILD_MAX_TOKENS
    )


@lru_cache
def get_chunker() -> HybridChunker:
    return HybridChunker(tokenizer=get_tokenizer())


def _chunk_pages(chunk: Any) -> list[int]:
    """Sorted unique page numbers from chunk.meta.doc_items[].prov[].page_no."""
    pages: set[int] = set()
    for item in getattr(chunk.meta, "doc_items", None) or []:
        for prov in getattr(item, "prov", None) or []:
            page_no = getattr(prov, "page_no", None)
            if page_no is not None:
                pages.add(int(page_no))
    return sorted(pages)


def chunk_file(
    file_path: str,
) -> tuple[Optional[int], list[dict[str, Any]], list[dict[str, Any]]]:
    """Convert + chunk a document. Synchronous and CPU-heavy — run in a thread.

    Returns (num_pages, parents, children):
    - parent: {id, parent_index, heading_path, content, page_start, page_end, token_count}
    - child:  {id, parent_id, child_index, text, heading_path, page_no, pages}
      (text is the contextualized text that gets embedded and stored in Qdrant)
    """
    tokenizer = get_tokenizer()
    chunker = get_chunker()

    result = get_converter().convert(file_path)
    dl_doc = result.document
    num_pages = len(dl_doc.pages) or None

    # --- children ---------------------------------------------------------
    raw_children: list[dict[str, Any]] = []
    for chunk in chunker.chunk(dl_doc):
        text = chunker.contextualize(chunk)
        if not text.strip():
            continue
        heading_path = list(chunk.meta.headings or [])
        pages = _chunk_pages(chunk)
        raw_children.append(
            {
                "text": text,
                "raw_text": chunk.text,
                "heading_path": heading_path,
                "page_no": pages[0] if pages else None,
                "pages": pages,
                "token_count": tokenizer.count_tokens(chunk.text),
            }
        )

    # --- parents: group consecutive children by heading_path, cap ~2000 ----
    parents: list[dict[str, Any]] = []
    children: list[dict[str, Any]] = []
    group: list[dict[str, Any]] = []
    group_tokens = 0
    current_heading: Optional[list[str]] = None

    def flush() -> None:
        nonlocal group, group_tokens
        if not group:
            return
        parent_id = str(uuid.uuid4())
        member_pages = sorted({p for c in group for p in c["pages"]})
        parents.append(
            {
                "id": parent_id,
                "parent_index": len(parents),
                "heading_path": list(current_heading or []),
                "content": "\n\n".join(c["raw_text"] for c in group),
                "page_start": member_pages[0] if member_pages else None,
                "page_end": member_pages[-1] if member_pages else None,
                "token_count": group_tokens,
            }
        )
        for c in group:
            children.append(
                {
                    "id": str(uuid.uuid4()),
                    "parent_id": parent_id,
                    "child_index": len(children),
                    "text": c["text"],
                    "heading_path": c["heading_path"],
                    "page_no": c["page_no"],
                    "pages": c["pages"],
                }
            )
        group = []
        group_tokens = 0

    for child in raw_children:
        heading_changed = current_heading is not None and child["heading_path"] != current_heading
        would_overflow = group and group_tokens + child["token_count"] > PARENT_MAX_TOKENS
        if heading_changed or would_overflow:
            flush()
        current_heading = child["heading_path"]
        group.append(child)
        group_tokens += child["token_count"]
    flush()

    return num_pages, parents, children
