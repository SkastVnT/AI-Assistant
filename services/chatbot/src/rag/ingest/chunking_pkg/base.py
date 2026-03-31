"""
Base chunking interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TextChunk:
    """A single chunk produced by a :class:`Chunker`.

    Attributes:
        text:        The chunk content.
        chunk_index: 0-based position within the document.
        metadata:    Carried-over metadata (page_number, source, …).
    """

    text: str
    chunk_index: int
    metadata: dict = field(default_factory=dict)


class Chunker(ABC):
    """Abstract interface for text chunkers."""

    @abstractmethod
    def chunk(
        self,
        text: str,
        metadata: dict | None = None,
    ) -> list[TextChunk]:
        """Split *text* into chunks, attaching *metadata* to each."""
        ...
