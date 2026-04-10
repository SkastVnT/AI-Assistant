"""
Abstract base class for embedding providers.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Uniform interface for text → vector embedding.

    Subclasses must implement ``embed_texts``, ``embed_query``, and the
    ``dimension`` property.  After construction ``validate_dimension`` is
    available to assert that vectors match the configured ``RAG_EMBED_DIM``.
    """

    # ── abstract API ───────────────────────────────────────────────────

    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts.  Returns one vector per input."""
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single search query."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimensionality of the vectors returned by this provider."""
        ...

    # ── backward-compat alias ──────────────────────────────────────────

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Alias kept for callers that use the old ``embed()`` name."""
        return self.embed_texts(texts)

    @property
    def dimensions(self) -> int:
        """Alias kept for callers that use the old ``dimensions`` name."""
        return self.dimension

    # ── validation helper ──────────────────────────────────────────────

    def validate_dimension(self, expected: int) -> None:
        """Raise if provider's dimension doesn't match *expected*."""
        if self.dimension != expected:
            raise ValueError(
                f"Embedding dimension mismatch: provider returns {self.dimension}, "
                f"but RAG_EMBED_DIM={expected}"
            )
