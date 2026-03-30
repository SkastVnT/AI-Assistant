"""Chunker interface and shared data types.

Every chunking strategy must satisfy the ChunkingStrategy protocol.
ChunkResult carries the rich metadata required by DocumentChunk storage.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from libs.ingestion.parsers.base import ParseResult


# ---------------------------------------------------------------------------
# Token estimation
# ---------------------------------------------------------------------------


def estimate_tokens(text: str, *, chars_per_token: int = 4) -> int:
    """Rough token estimate (English ~4 chars/token). Good enough for chunking.

    Replace with tiktoken for exact counts in production.
    """
    return max(1, len(text) // chars_per_token)


# ---------------------------------------------------------------------------
# Heading path helper
# ---------------------------------------------------------------------------


def _heading_path_str(path: list[str]) -> str:
    """Join heading path list into '>' separated string."""
    return " > ".join(path) if path else ""


# ---------------------------------------------------------------------------
# Chunk metadata
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChunkMeta:
    """Rich per-chunk metadata that maps 1:1 to DocumentChunk storage."""

    chunk_id: uuid.UUID
    parent_document_id: uuid.UUID
    parent_version_id: uuid.UUID
    chunk_index: int
    start_offset: int
    end_offset: int
    heading_path: str  # e.g. "Introduction > Background"
    page_number: int | None  # None for non-paged formats
    token_count: int
    # Parent-child relationship (for parent-document retrieval)
    parent_chunk_id: uuid.UUID | None = None
    is_parent: bool = False

    def to_dict(self) -> dict:
        return {
            "chunk_id": str(self.chunk_id),
            "parent_document_id": str(self.parent_document_id),
            "parent_version_id": str(self.parent_version_id),
            "chunk_index": self.chunk_index,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "heading_path": self.heading_path,
            "page_number": self.page_number,
            "token_count": self.token_count,
            "parent_chunk_id": str(self.parent_chunk_id) if self.parent_chunk_id else None,
            "is_parent": self.is_parent,
        }


# ---------------------------------------------------------------------------
# Chunk result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChunkResult:
    """One chunk produced by a chunking strategy."""

    content: str
    meta: ChunkMeta

    def __repr__(self) -> str:
        preview = self.content[:60].replace("\n", "\\n")
        return (
            f"ChunkResult(idx={self.meta.chunk_index}, "
            f"tokens={self.meta.token_count}, "
            f"heading='{self.meta.heading_path}', "
            f"content='{preview}...')"
        )


# ---------------------------------------------------------------------------
# Strategy enum
# ---------------------------------------------------------------------------


class ChunkerType(enum.StrEnum):
    FIXED = "fixed"
    SEMANTIC = "semantic"
    DOCUMENT_AWARE = "document_aware"
    PARENT_CHILD = "parent_child"


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ChunkingStrategy(Protocol):
    """Interface every chunker must satisfy."""

    @property
    def strategy_name(self) -> str:
        """Human-readable name (e.g., 'fixed_token')."""
        ...

    def chunk(
        self,
        text: str,
        *,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
        parse_result: ParseResult | None = None,
    ) -> list[ChunkResult]:
        """Split text into chunks with full metadata.

        Args:
            text: The full document text.
            document_id: Parent document UUID.
            version_id: Parent version UUID.
            parse_result: Optional structured parse output (for document-aware strategies).

        Returns:
            Ordered list of ChunkResult objects.
        """
        ...
