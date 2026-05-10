"""Reranker abstractions — score (query, passage) pairs for fine-grained relevance.

Provides a Protocol-based interface and two implementations:
1. CrossEncoderReranker — uses a cross-encoder model (e.g. ms-marco-MiniLM)
2. LateInteractionReranker — placeholder for ColBERT-style late interaction

Both rerankers share the same interface so they can be swapped via config.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from libs.retrieval.search import SearchResult

_ScoreFn = Callable[[str, list[tuple[str, str]]], Awaitable[list[float]]]

logger = logging.getLogger("rag.retrieval.rerankers")


# ── Data structures ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RerankResult:
    """A SearchResult with its reranker score attached."""

    result: SearchResult
    rerank_score: float


# ── Protocol ───────────────────────────────────────────────────────────────


@runtime_checkable
class Reranker(Protocol):
    """Score (query, passage) pairs for relevance reranking."""

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        *,
        top_n: int | None = None,
    ) -> list[RerankResult]:
        """Rerank candidates by relevance to query.

        Args:
            query: The user's search query.
            candidates: Pre-retrieved chunks to rerank.
            top_n: Return at most this many results (None = all).

        Returns:
            Results sorted by rerank_score descending.
        """
        ...


# ── Cross-Encoder implementation ──────────────────────────────────────────


class CrossEncoderReranker:
    """Reranker using a cross-encoder model.

    Cross-encoders process (query, passage) pairs jointly through a
    transformer, producing a single relevance score. They are slow
    (O(n) forward passes) but highly accurate.

    In production, this wraps a model served via an inference endpoint
    (e.g. Hugging Face TEI, vLLM, or a local sentence-transformers model).
    For now, it accepts an async scoring function that can be backed by
    any serving infrastructure.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        score_fn: _ScoreFn | None = None,
    ) -> None:
        self._model_name = model_name
        self._score_fn = score_fn or _default_cross_encoder_score

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        *,
        top_n: int | None = None,
    ) -> list[RerankResult]:
        if not candidates:
            return []

        pairs = [(query, c.content) for c in candidates]
        scores = await self._score_fn(self._model_name, pairs)

        scored = [
            RerankResult(result=c, rerank_score=s)
            for c, s in zip(candidates, scores, strict=True)
        ]
        scored.sort(key=lambda x: x.rerank_score, reverse=True)

        if top_n is not None:
            scored = scored[:top_n]

        logger.info(
            "cross_encoder rerank: model=%s candidates=%d returned=%d "
            "top_score=%.4f",
            self._model_name,
            len(candidates),
            len(scored),
            scored[0].rerank_score if scored else 0.0,
        )
        return scored





async def _default_cross_encoder_score(
    model_name: str,
    pairs: list[tuple[str, str]],
) -> list[float]:
    """Default cross-encoder scoring — attempts to use sentence-transformers.

    Falls back to a simple heuristic (word overlap) if the library isn't
    installed, making the pipeline testable without GPU dependencies.
    """
    try:
        from sentence_transformers import CrossEncoder  # type: ignore[import]

        model = CrossEncoder(model_name)
        # CrossEncoder.predict is synchronous; run in executor
        import asyncio

        loop = asyncio.get_running_loop()
        scores = await loop.run_in_executor(
            None, lambda: model.predict(pairs).tolist()
        )
        return scores
    except ImportError:
        logger.warning(
            "sentence-transformers not installed; using word-overlap fallback"
        )
        return _word_overlap_scores(pairs)


def _word_overlap_scores(pairs: list[tuple[str, str]]) -> list[float]:
    """Simple word-overlap heuristic as fallback when no model is available."""
    scores: list[float] = []
    for query, passage in pairs:
        q_words = set(query.lower().split())
        p_words = set(passage.lower().split())
        if not q_words:
            scores.append(0.0)
            continue
        overlap = len(q_words & p_words)
        scores.append(overlap / len(q_words))
    return scores


# ── Late-Interaction (ColBERT) placeholder ─────────────────────────────────


class LateInteractionReranker:
    """Placeholder for ColBERT-style late-interaction reranking.

    ColBERT encodes query tokens and document tokens independently, then
    computes relevance via MaxSim (maximum similarity between each query
    token embedding and all document token embeddings). This is faster
    than cross-encoders for large candidate sets but requires specialized
    model infrastructure.

    This placeholder uses the same word-overlap fallback as the cross-encoder
    default. Replace `_score_fn` with a ColBERT serving endpoint in production.
    """

    def __init__(
        self,
        model_name: str = "colbert-ir/colbertv2.0",
        score_fn: _ScoreFn | None = None,
    ) -> None:
        self._model_name = model_name
        self._score_fn = score_fn or self._default_score

    async def rerank(
        self,
        query: str,
        candidates: list[SearchResult],
        *,
        top_n: int | None = None,
    ) -> list[RerankResult]:
        if not candidates:
            return []

        pairs = [(query, c.content) for c in candidates]
        scores = await self._score_fn(self._model_name, pairs)

        scored = [
            RerankResult(result=c, rerank_score=s)
            for c, s in zip(candidates, scores, strict=True)
        ]
        scored.sort(key=lambda x: x.rerank_score, reverse=True)

        if top_n is not None:
            scored = scored[:top_n]

        logger.info(
            "late_interaction rerank: model=%s candidates=%d returned=%d",
            self._model_name,
            len(candidates),
            len(scored),
        )
        return scored

    @staticmethod
    async def _default_score(
        model_name: str,
        pairs: list[tuple[str, str]],
    ) -> list[float]:
        """Placeholder — ColBERT integration point."""
        logger.warning(
            "LateInteractionReranker using word-overlap fallback; "
            "integrate ColBERT model for production use"
        )
        return _word_overlap_scores(pairs)


# ── Factory ────────────────────────────────────────────────────────────────


def create_reranker(
    reranker_type: str = "cross_encoder",
    model_name: str | None = None,
    score_fn: _ScoreFn | None = None,
) -> Reranker:
    """Create a reranker instance from config."""
    if reranker_type == "cross_encoder":
        return CrossEncoderReranker(
            model_name=model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2",
            score_fn=score_fn,
        )
    if reranker_type == "late_interaction":
        return LateInteractionReranker(
            model_name=model_name or "colbert-ir/colbertv2.0",
            score_fn=score_fn,
        )
    raise ValueError(f"Unknown reranker type: {reranker_type!r}")
