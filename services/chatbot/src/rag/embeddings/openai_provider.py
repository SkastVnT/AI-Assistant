"""
OpenAI embedding provider (text-embedding-3-*).
"""
from __future__ import annotations

import logging

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(EmbeddingProvider):
    """Embeddings via the OpenAI ``/v1/embeddings`` API."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        dim: int = 1536,
    ):
        from openai import OpenAI

        self._client = OpenAI()  # reads OPENAI_API_KEY from env
        self._model = model
        self._dim = dim
        logger.info("[embeddings] OpenAI provider  model=%s  dim=%d", model, dim)

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        resp = self._client.embeddings.create(
            input=texts,
            model=self._model,
            dimensions=self._dim,
        )
        return [item.embedding for item in resp.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
