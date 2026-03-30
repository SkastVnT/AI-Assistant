"""Document-aware chunker for Markdown and HTML content.

Uses the structured ParseResult from the parser stage to create chunks
that respect document structure: headings, sections, code blocks, tables.
Preserves heading paths so that each chunk carries its section context.

Falls back to fixed-token chunking if no ParseResult is provided.
"""

from __future__ import annotations

import uuid

from libs.ingestion.chunkers.base import (
    ChunkMeta,
    ChunkResult,
    ChunkingStrategy,
    estimate_tokens,
)
from libs.ingestion.chunkers.fixed_chunker import FixedTokenChunker
from libs.ingestion.parsers.base import ElementType, ParseResult


class DocumentAwareChunker:
    """Chunk text while respecting document structure (headings, sections)."""

    def __init__(
        self,
        max_chunk_tokens: int = 512,
        min_chunk_tokens: int = 50,
        overlap_tokens: int = 0,
        chars_per_token: int = 4,
    ) -> None:
        self._max_tokens = max_chunk_tokens
        self._min_tokens = min_chunk_tokens
        self._overlap_tokens = overlap_tokens
        self._cpt = chars_per_token

    @property
    def strategy_name(self) -> str:
        return "document_aware"

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

        # No structure available → fall back to fixed chunker
        if parse_result is None or not parse_result.elements:
            fallback = FixedTokenChunker(
                chunk_size=self._max_tokens,
                chunk_overlap=self._overlap_tokens,
                chars_per_token=self._cpt,
            )
            return fallback.chunk(text, document_id=document_id, version_id=version_id)

        return self._chunk_structured(text, parse_result, document_id, version_id)

    # ------------------------------------------------------------------
    # Structure-aware chunking
    # ------------------------------------------------------------------

    def _chunk_structured(
        self,
        text: str,
        parse_result: ParseResult,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> list[ChunkResult]:
        results: list[ChunkResult] = []
        heading_stack: list[tuple[int, str]] = []  # (level, text)

        # Accumulator for current section
        current_parts: list[str] = []
        current_tokens = 0
        section_start_offset = 0
        current_page: int | None = None

        idx = 0

        for elem in parse_result.elements:
            elem_tokens = estimate_tokens(elem.content, chars_per_token=self._cpt)

            if elem.type == ElementType.PAGE_BREAK:
                current_page = elem.page
                continue

            if elem.page is not None:
                current_page = elem.page

            # Heading → flush current accumulator, update heading stack
            if elem.type in (ElementType.HEADING, ElementType.TITLE):
                if current_parts:
                    idx = self._flush_section(
                        results, current_parts, current_tokens, heading_stack,
                        section_start_offset, current_page, idx,
                        document_id, version_id, text,
                    )
                    current_parts = []
                    current_tokens = 0

                level = elem.level or 1
                # Pop headings at same or deeper level
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, elem.content))

                section_start_offset = text.find(elem.content, section_start_offset)
                if section_start_offset == -1:
                    section_start_offset = 0
                continue

            # Would exceed max → flush
            if current_tokens + elem_tokens > self._max_tokens and current_parts:
                idx = self._flush_section(
                    results, current_parts, current_tokens, heading_stack,
                    section_start_offset, current_page, idx,
                    document_id, version_id, text,
                )
                current_parts = []
                current_tokens = 0
                section_start_offset = text.find(
                    elem.content, results[-1].meta.end_offset if results else 0
                )
                if section_start_offset == -1:
                    section_start_offset = results[-1].meta.end_offset if results else 0

            # Large single element (e.g., big code block / table)
            if elem_tokens > self._max_tokens:
                # Emit as its own chunk
                start = text.find(elem.content, section_start_offset)
                if start == -1:
                    start = section_start_offset
                end = start + len(elem.content)

                results.append(
                    ChunkResult(
                        content=elem.content,
                        meta=ChunkMeta(
                            chunk_id=uuid.uuid4(),
                            parent_document_id=document_id,
                            parent_version_id=version_id,
                            chunk_index=idx,
                            start_offset=start,
                            end_offset=end,
                            heading_path=self._heading_path(heading_stack),
                            page_number=current_page,
                            token_count=elem_tokens,
                        ),
                    )
                )
                idx += 1
                section_start_offset = end
                continue

            current_parts.append(elem.content)
            current_tokens += elem_tokens

        # Flush remainder
        if current_parts:
            self._flush_section(
                results, current_parts, current_tokens, heading_stack,
                section_start_offset, current_page, idx,
                document_id, version_id, text,
            )

        return results

    # ------------------------------------------------------------------

    def _flush_section(
        self,
        results: list[ChunkResult],
        parts: list[str],
        tokens: int,
        heading_stack: list[tuple[int, str]],
        section_start: int,
        page: int | None,
        idx: int,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
        full_text: str,
    ) -> int:
        """Emit accumulated parts as a chunk, return next idx."""
        chunk_text = "\n\n".join(parts)
        if not chunk_text.strip():
            return idx

        # Find position in full text
        start = full_text.find(parts[0], section_start)
        if start == -1:
            start = section_start
        end = start + len(chunk_text)
        # Adjust end for actual position of last part
        last_pos = full_text.find(parts[-1], start)
        if last_pos != -1:
            end = last_pos + len(parts[-1])

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
                    heading_path=self._heading_path(heading_stack),
                    page_number=page,
                    token_count=estimate_tokens(chunk_text, chars_per_token=self._cpt),
                ),
            )
        )
        return idx + 1

    @staticmethod
    def _heading_path(stack: list[tuple[int, str]]) -> str:
        return " > ".join(h[1] for h in stack)


assert isinstance(DocumentAwareChunker(), ChunkingStrategy)
