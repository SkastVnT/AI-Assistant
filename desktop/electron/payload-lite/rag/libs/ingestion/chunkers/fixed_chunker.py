"""Fixed-token chunker with overlap.

Splits text into chunks of approximately N tokens with configurable
overlap.  Tries to break at paragraph / sentence boundaries when possible.
"""

from __future__ import annotations

import uuid

from libs.ingestion.chunkers.base import (
    ChunkMeta,
    ChunkResult,
    ChunkingStrategy,
    estimate_tokens,
)
from libs.ingestion.parsers.base import ParseResult

# Sentence-ending punctuation for boundary detection
_SENTENCE_ENDS = (". ", "! ", "? ", ".\n", "!\n", "?\n")


class FixedTokenChunker:
    """Split text into fixed-size token windows with overlap."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        chars_per_token: int = 4,
    ) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._cpt = chars_per_token

    @property
    def strategy_name(self) -> str:
        return "fixed_token"

    def chunk(
        self,
        text: str,
        *,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
        parse_result: ParseResult | None = None,
    ) -> list[ChunkResult]:
        if not text.strip():
            return []

        char_size = self._chunk_size * self._cpt
        char_overlap = self._chunk_overlap * self._cpt

        results: list[ChunkResult] = []
        start = 0
        idx = 0

        while start < len(text):
            end = min(start + char_size, len(text))

            # Try to snap to a clean boundary
            if end < len(text):
                end = self._snap_boundary(text, start, end, char_size)

            chunk_text = text[start:end].strip()
            if chunk_text:
                results.append(
                    ChunkResult(
                        content=chunk_text,
                        meta=ChunkMeta(
                            chunk_id=uuid.uuid4(),
                            parent_document_id=document_id,
                            parent_version_id=version_id,
                            chunk_index=idx,
                            start_offset=start,
                            end_offset=end,
                            heading_path="",
                            page_number=None,
                            token_count=estimate_tokens(chunk_text, chars_per_token=self._cpt),
                        ),
                    )
                )
                idx += 1

            # Advance with overlap
            if end >= len(text):
                break
            start = end - char_overlap
            if start <= (results[-1].meta.start_offset if results else -1):
                start = end  # safety: never go backwards

        return results

    # ------------------------------------------------------------------

    @staticmethod
    def _snap_boundary(text: str, start: int, end: int, char_size: int) -> int:
        """Try to break at paragraph, then sentence boundary."""
        min_pos = start + char_size // 2

        # Paragraph break
        para = text.rfind("\n\n", start, end)
        if para > min_pos:
            return para + 2

        # Sentence break
        for sep in _SENTENCE_ENDS:
            pos = text.rfind(sep, start, end)
            if pos > min_pos:
                return pos + len(sep)

        return end


assert isinstance(FixedTokenChunker(), ChunkingStrategy)
