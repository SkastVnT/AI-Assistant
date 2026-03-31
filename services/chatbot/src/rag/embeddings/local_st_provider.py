"""
Local sentence-transformers embedding provider.

Runs entirely on-device — no API key required.
Model is loaded lazily on first call and cached for the process lifetime.
"""
from __future__ import annotations

import logging

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)


class LocalSTProvider(EmbeddingProvider):
    """Embeddings via a local ``sentence-transformers`` model."""

    def __init__(
        self,
        model: str = "all-MiniLM-L6-v2",
        dim: int = 384,
    ):
        self._model_name = model
        self._dim = dim
        self._model = None  # lazy load
        logger.info("[embeddings] Local ST provider  model=%s  dim=%d", model, dim)

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            # Verify actual dimension matches declared dimension
            actual = self._model.get_sentence_embedding_dimension()
            if actual != self._dim:
                logger.warning(
                    "[embeddings] Model %s produces dim=%d but RAG_EMBED_DIM=%d",
                    self._model_name,
                    actual,
                    self._dim,
                )
        return self._model

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
