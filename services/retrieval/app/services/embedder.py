"""Query embedder — intfloat/multilingual-e5-large convention (docs/CONTRACTS.md).

- Queries are prefixed with "query: " (children were indexed with "passage: ").
- Embeddings are L2-normalized, 1024-dim, cosine distance in Qdrant.
"""

from sentence_transformers import SentenceTransformer


class Embedder:
    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name, device="cpu")

    def get_sentence_embedding_dimension(self) -> int | None:
        """Exposed for the startup fail-fast EMBEDDING_DIM check."""
        return self._model.get_sentence_embedding_dimension()

    def embed_query(self, text: str) -> list[float]:
        """Embed a chat query with the mandatory "query: " prefix, normalized."""
        vector = self._model.encode(
            "query: " + text.strip(),
            normalize_embeddings=True,
        )
        return vector.tolist()
