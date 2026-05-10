"""Parent-child chunker for parent document retrieval.

Creates a two-level hierarchy:
  - **Parent chunks** (large windows, ~2000 tokens) for context
  - **Child chunks** (small windows, ~256 tokens) for precise retrieval

At retrieval time, the system matches on child chunks but returns
the parent chunk for richer LLM context.  Each child carries a
parent_chunk_id linking it to its parent.

This strategy improves recall for questions that require surrounding
context beyond the small retrieval window.
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
from libs.ingestion.parsers.base import ParseResult


class ParentChildChunker:
    """Two-level chunking: large parents with small children."""

    def __init__(
        self,
        parent_chunk_size: int = 2048,
        child_chunk_size: int = 256,
        child_overlap: int = 32,
        chars_per_token: int = 4,
    ) -> None:
        self._parent_size = parent_chunk_size
        self._child_size = child_chunk_size
        self._child_overlap = child_overlap
        self._cpt = chars_per_token

    @property
    def strategy_name(self) -> str:
        return "parent_child"

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

        # 1) Create parent chunks (large, no overlap)
        parent_chunker = FixedTokenChunker(
            chunk_size=self._parent_size,
            chunk_overlap=0,
            chars_per_token=self._cpt,
        )
        parent_chunks = parent_chunker.chunk(
            text, document_id=document_id, version_id=version_id
        )

        # Mark parents
        parents: list[ChunkResult] = []
        for pc in parent_chunks:
            parents.append(
                ChunkResult(
                    content=pc.content,
                    meta=ChunkMeta(
                        chunk_id=pc.meta.chunk_id,
                        parent_document_id=document_id,
                        parent_version_id=version_id,
                        chunk_index=pc.meta.chunk_index,
                        start_offset=pc.meta.start_offset,
                        end_offset=pc.meta.end_offset,
                        heading_path=pc.meta.heading_path,
                        page_number=pc.meta.page_number,
                        token_count=pc.meta.token_count,
                        parent_chunk_id=None,
                        is_parent=True,
                    ),
                )
            )

        # 2) Create child chunks within each parent
        child_chunker = FixedTokenChunker(
            chunk_size=self._child_size,
            chunk_overlap=self._child_overlap,
            chars_per_token=self._cpt,
        )

        children: list[ChunkResult] = []
        global_child_idx = len(parents)  # children are indexed after parents

        for parent in parents:
            child_results = child_chunker.chunk(
                parent.content, document_id=document_id, version_id=version_id
            )

            for child in child_results:
                # Rebase offsets relative to full document
                abs_start = parent.meta.start_offset + child.meta.start_offset
                abs_end = parent.meta.start_offset + child.meta.end_offset

                children.append(
                    ChunkResult(
                        content=child.content,
                        meta=ChunkMeta(
                            chunk_id=uuid.uuid4(),
                            parent_document_id=document_id,
                            parent_version_id=version_id,
                            chunk_index=global_child_idx,
                            start_offset=abs_start,
                            end_offset=abs_end,
                            heading_path=child.meta.heading_path,
                            page_number=child.meta.page_number,
                            token_count=child.meta.token_count,
                            parent_chunk_id=parent.meta.chunk_id,
                            is_parent=False,
                        ),
                    )
                )
                global_child_idx += 1

        return parents + children


assert isinstance(ParentChildChunker(), ChunkingStrategy)
