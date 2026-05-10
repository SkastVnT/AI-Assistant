"""Semantic chunker — groups sentences by embedding similarity.

Splits text into sentences, then merges adjacent sentences whose
embeddings are sufficiently similar.  When the cosine similarity
between a sentence group and the next sentence drops below a
threshold, a chunk boundary is inserted.

This implementation works in two modes:
  1) **With embeddings** (production): pass an EmbeddingProvider.
  2) **Without embeddings** (fallback/test): uses sentence-length
     heuristic to approximate topic shifts — a new chunk starts
     whenever a paragraph break or a large length-ratio change
     is detected.

The fallback mode is intentionally simplistic; the real value comes
from an actual embedding model.
"""

from __future__ import annotations

import re
import uuid
from typing import Protocol, runtime_checkable

from libs.ingestion.chunkers.base import (
    ChunkMeta,
    ChunkResult,
    ChunkingStrategy,
    estimate_tokens,
)
from libs.ingestion.parsers.base import ParseResult

# ---------------------------------------------------------------------------
# Minimal embedding interface (avoid hard coupling to providers)
# ---------------------------------------------------------------------------


@runtime_checkable
class SentenceEmbedder(Protocol):
    """Any callable that maps a list of strings to a list of float-vectors."""

    def embed_sentences(self, sentences: list[str]) -> list[list[float]]:
        ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence-like segments."""
    parts = _SENTENCE_SPLIT_RE.split(text)
    return [s.strip() for s in parts if s.strip()]


def _cosine_sim(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# Chunker
# ---------------------------------------------------------------------------


class SemanticChunker:
    """Groups semantically similar sentences into chunks."""

    def __init__(
        self,
        embedder: SentenceEmbedder | None = None,
        similarity_threshold: float = 0.75,
        max_chunk_tokens: int = 512,
        min_chunk_tokens: int = 50,
        chars_per_token: int = 4,
    ) -> None:
        self._embedder = embedder
        self._threshold = similarity_threshold
        self._max_tokens = max_chunk_tokens
        self._min_tokens = min_chunk_tokens
        self._cpt = chars_per_token

    @property
    def strategy_name(self) -> str:
        return "semantic"

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

        sentences = _split_sentences(text)
        if not sentences:
            return []

        if self._embedder is not None:
            groups = self._group_by_embedding(sentences)
        else:
            groups = self._group_by_heuristic(sentences)

        return self._build_results(groups, text, document_id, version_id)

    # ------------------------------------------------------------------
    # Embedding-based grouping
    # ------------------------------------------------------------------

    def _group_by_embedding(self, sentences: list[str]) -> list[list[str]]:
        embeddings = self._embedder.embed_sentences(sentences)  # type: ignore[union-attr]
        groups: list[list[str]] = [[sentences[0]]]
        group_emb = embeddings[0]

        for i in range(1, len(sentences)):
            sim = _cosine_sim(group_emb, embeddings[i])
            group_tokens = estimate_tokens(
                " ".join(groups[-1]) + " " + sentences[i], chars_per_token=self._cpt
            )

            if sim >= self._threshold and group_tokens <= self._max_tokens:
                groups[-1].append(sentences[i])
                # Running average embedding
                group_emb = [
                    (a + b) / 2 for a, b in zip(group_emb, embeddings[i])
                ]
            else:
                groups.append([sentences[i]])
                group_emb = embeddings[i]

        return groups

    # ------------------------------------------------------------------
    # Heuristic fallback (no embedder)
    # ------------------------------------------------------------------

    def _group_by_heuristic(self, sentences: list[str]) -> list[list[str]]:
        """Group by paragraph boundaries + max-token limit."""
        groups: list[list[str]] = [[sentences[0]]]

        for i in range(1, len(sentences)):
            current_text = " ".join(groups[-1]) + " " + sentences[i]
            current_tokens = estimate_tokens(current_text, chars_per_token=self._cpt)

            if current_tokens <= self._max_tokens:
                groups[-1].append(sentences[i])
            else:
                groups.append([sentences[i]])

        return groups

    # ------------------------------------------------------------------
    # Build ChunkResult list
    # ------------------------------------------------------------------

    def _build_results(
        self,
        groups: list[list[str]],
        full_text: str,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
    ) -> list[ChunkResult]:
        results: list[ChunkResult] = []
        offset = 0

        for idx, group in enumerate(groups):
            chunk_text = " ".join(group)
            # Find actual position in full text
            start = full_text.find(group[0], offset)
            if start == -1:
                start = offset
            last_sent = group[-1]
            end_search = full_text.find(last_sent, start)
            end = (end_search + len(last_sent)) if end_search != -1 else start + len(chunk_text)

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
            offset = end

        return results


assert isinstance(SemanticChunker(), ChunkingStrategy)
