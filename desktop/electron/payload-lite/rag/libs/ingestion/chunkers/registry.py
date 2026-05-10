"""Registry — maps ChunkerType to concrete chunker instances."""

from __future__ import annotations

from typing import Any

from libs.ingestion.chunkers.base import ChunkerType, ChunkingStrategy


def get_chunker(strategy: ChunkerType | str, **kwargs: Any) -> ChunkingStrategy:
    """Instantiate a chunker by strategy type.

    Extra kwargs are forwarded to the chunker constructor.
    """
    if isinstance(strategy, str):
        strategy = ChunkerType(strategy)

    if strategy == ChunkerType.FIXED:
        from libs.ingestion.chunkers.fixed_chunker import FixedTokenChunker

        return FixedTokenChunker(**kwargs)

    if strategy == ChunkerType.SEMANTIC:
        from libs.ingestion.chunkers.semantic_chunker import SemanticChunker

        return SemanticChunker(**kwargs)

    if strategy == ChunkerType.DOCUMENT_AWARE:
        from libs.ingestion.chunkers.document_aware_chunker import DocumentAwareChunker

        return DocumentAwareChunker(**kwargs)

    if strategy == ChunkerType.PARENT_CHILD:
        from libs.ingestion.chunkers.parent_child_chunker import ParentChildChunker

        return ParentChildChunker(**kwargs)

    raise ValueError(f"Unknown chunker strategy: {strategy}")
