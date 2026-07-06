"""e5 embedding — the "passage: " prefix convention is centralized HERE.

CONTRACTS.md (Embedding Convention): intfloat/multilingual-e5-large, 1024-dim,
cosine, L2-normalized; indexed child text is prefixed with "passage: ".
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import get_settings

PASSAGE_PREFIX = "passage: "


class Embedder:
    def __init__(self, model_name: str) -> None:
        self.model = SentenceTransformer(model_name)

    def dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        """Prefix each text with "passage: ", encode L2-normalized."""
        prefixed = [PASSAGE_PREFIX + t for t in texts]
        vectors = self.model.encode(
            prefixed,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vectors.tolist()


@lru_cache
def get_embedder() -> Embedder:
    """Load the SentenceTransformer once per process."""
    return Embedder(get_settings().embedding_model)
