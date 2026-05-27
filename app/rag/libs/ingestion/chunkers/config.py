"""Chunking configuration, presets, and strategy comparison.

Provides:
  - ChunkingPreset: named config bundles for different document types
  - get_preset(): look up a preset by name
  - compare_strategies(): run multiple chunkers on the same text
  - DEFAULT_PRESETS: recommended defaults for policy docs, technical docs,
    code repos
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from libs.ingestion.chunkers.base import (
    ChunkerType,
    ChunkingStrategy,
    ChunkResult,
)


# ---------------------------------------------------------------------------
# Preset dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ChunkingPreset:
    """Named configuration bundle for a chunking strategy."""

    name: str
    description: str
    strategy: ChunkerType
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "strategy": self.strategy.value,
            "params": self.params,
        }


# ---------------------------------------------------------------------------
# Default presets
# ---------------------------------------------------------------------------

DEFAULT_PRESETS: dict[str, ChunkingPreset] = {
    "policy_documents": ChunkingPreset(
        name="policy_documents",
        description=(
            "Optimized for legal/policy documents with numbered sections. "
            "Uses document-aware chunking to respect heading hierarchy. "
            "Larger chunks (768 tokens) preserve clause context."
        ),
        strategy=ChunkerType.DOCUMENT_AWARE,
        params={
            "max_chunk_tokens": 768,
            "min_chunk_tokens": 100,
            "overlap_tokens": 0,
        },
    ),
    "technical_docs": ChunkingPreset(
        name="technical_docs",
        description=(
            "For README files, API docs, tutorials with code blocks. "
            "Uses document-aware chunking to keep code blocks intact. "
            "Medium chunks (512 tokens) balance specificity and context."
        ),
        strategy=ChunkerType.DOCUMENT_AWARE,
        params={
            "max_chunk_tokens": 512,
            "min_chunk_tokens": 50,
            "overlap_tokens": 0,
        },
    ),
    "code_repository": ChunkingPreset(
        name="code_repository",
        description=(
            "For source code files. Uses fixed-token chunking with overlap "
            "since code rarely has heading structure. Smaller chunks (256 tokens) "
            "for function-level retrieval, with 32-token overlap for context."
        ),
        strategy=ChunkerType.FIXED,
        params={
            "chunk_size": 256,
            "chunk_overlap": 32,
        },
    ),
    "general": ChunkingPreset(
        name="general",
        description=(
            "General-purpose default. Fixed-token with moderate size and overlap. "
            "Works well when document type is unknown."
        ),
        strategy=ChunkerType.FIXED,
        params={
            "chunk_size": 512,
            "chunk_overlap": 64,
        },
    ),
    "parent_child_retrieval": ChunkingPreset(
        name="parent_child_retrieval",
        description=(
            "Two-level chunking for parent-document retrieval. "
            "Small child chunks (256 tokens) for precise matching, "
            "large parent chunks (2048 tokens) returned for LLM context."
        ),
        strategy=ChunkerType.PARENT_CHILD,
        params={
            "parent_chunk_size": 2048,
            "child_chunk_size": 256,
            "child_overlap": 32,
        },
    ),
    "semantic_grouping": ChunkingPreset(
        name="semantic_grouping",
        description=(
            "Groups sentences by embedding similarity for topic-coherent chunks. "
            "Best with an embedding model; falls back to heuristic grouping. "
            "Good for conversational or unstructured text."
        ),
        strategy=ChunkerType.SEMANTIC,
        params={
            "similarity_threshold": 0.75,
            "max_chunk_tokens": 512,
            "min_chunk_tokens": 50,
        },
    ),
}

# MVP recommendation
MVP_PRESET = "general"


def get_preset(name: str) -> ChunkingPreset:
    """Look up a chunking preset by name.

    Raises KeyError if preset not found.
    """
    if name not in DEFAULT_PRESETS:
        available = ", ".join(sorted(DEFAULT_PRESETS.keys()))
        raise KeyError(f"Unknown preset '{name}'. Available: {available}")
    return DEFAULT_PRESETS[name]


def list_presets() -> list[dict]:
    """Return all available presets as dicts."""
    return [p.to_dict() for p in DEFAULT_PRESETS.values()]


# ---------------------------------------------------------------------------
# Strategy comparison helper
# ---------------------------------------------------------------------------


@dataclass
class ComparisonResult:
    """Result of comparing a single strategy on the same text."""

    strategy_name: str
    preset_name: str
    num_chunks: int
    avg_tokens: float
    min_tokens: int
    max_tokens: int
    total_tokens: int
    chunks: list[ChunkResult]

    def summary(self) -> str:
        return (
            f"[{self.preset_name}] strategy={self.strategy_name}: "
            f"{self.num_chunks} chunks, "
            f"avg={self.avg_tokens:.0f} tokens, "
            f"range=[{self.min_tokens}, {self.max_tokens}]"
        )


def compare_strategies(
    text: str,
    preset_names: list[str] | None = None,
    *,
    document_id: uuid.UUID | None = None,
    version_id: uuid.UUID | None = None,
    parse_result: Any = None,
) -> list[ComparisonResult]:
    """Run multiple chunking strategies on the same text and compare.

    Args:
        text: Document text to chunk.
        preset_names: List of preset names. Defaults to all presets.
        document_id: Optional doc ID (auto-generated if None).
        version_id: Optional version ID (auto-generated if None).
        parse_result: Optional ParseResult for structure-aware strategies.

    Returns:
        List of ComparisonResult, one per strategy tried.
    """
    from libs.ingestion.chunkers.registry import get_chunker

    doc_id = document_id or uuid.uuid4()
    ver_id = version_id or uuid.uuid4()
    names = preset_names or list(DEFAULT_PRESETS.keys())

    results: list[ComparisonResult] = []

    for name in names:
        preset = get_preset(name)
        chunker = get_chunker(preset.strategy, **preset.params)
        chunks = chunker.chunk(
            text,
            document_id=doc_id,
            version_id=ver_id,
            parse_result=parse_result,
        )

        if chunks:
            token_counts = [c.meta.token_count for c in chunks]
            avg = sum(token_counts) / len(token_counts)
            results.append(
                ComparisonResult(
                    strategy_name=chunker.strategy_name,
                    preset_name=name,
                    num_chunks=len(chunks),
                    avg_tokens=avg,
                    min_tokens=min(token_counts),
                    max_tokens=max(token_counts),
                    total_tokens=sum(token_counts),
                    chunks=chunks,
                )
            )
        else:
            results.append(
                ComparisonResult(
                    strategy_name=chunker.strategy_name,
                    preset_name=name,
                    num_chunks=0,
                    avg_tokens=0,
                    min_tokens=0,
                    max_tokens=0,
                    total_tokens=0,
                    chunks=[],
                )
            )

    return results
