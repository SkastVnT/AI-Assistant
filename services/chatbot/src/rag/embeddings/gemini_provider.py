"""
Google Gemini embedding provider.
"""
from __future__ import annotations

import logging
import os

from .base import EmbeddingProvider

logger = logging.getLogger(__name__)


class GeminiProvider(EmbeddingProvider):
    """Embeddings via the Google ``genai`` SDK (Gemini / text-embedding-004)."""

    def __init__(
        self,
        model: str = "text-embedding-004",
        dim: int = 768,
    ):
        from google import genai

        api_key = os.getenv("GEMINI_API_KEY_1") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "No Gemini API key found (set GEMINI_API_KEY_1 or GOOGLE_API_KEY)"
            )
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._dim = dim
        logger.info("[embeddings] Gemini provider  model=%s  dim=%d", model, dim)

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        result = self._client.models.embed_content(
            model=self._model,
            contents=texts,
        )
        return [e.values for e in result.embeddings]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
