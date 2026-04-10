"""Reciprocal Rank Fusion (RRF) — merges ranked lists from multiple retrievers.

Formula per document d across result lists L₁, L₂, ... Lₙ:

    RRF(d) = Σᵢ  wᵢ / (k + rankᵢ(d))

where:
    k       = smoothing constant (default 60, controls how steeply rank matters)
    rankᵢ   = 1-based rank of d in list i (∞ if absent → contributes 0)
    wᵢ      = per-list weight (default 1.0 for all)

Reference: Cormack, Clarke & Buettcher (2009) — "Reciprocal Rank Fusion
outperforms Condorcet and individual Rank Learning methods"
"""

from __future__ import annotations

from uuid import UUID

from libs.retrieval.search import SearchResult


def reciprocal_rank_fusion(
    ranked_lists: list[list[SearchResult]],
    *,
    k: int = 60,
    weights: list[float] | None = None,
    top_k: int | None = None,
) -> list[SearchResult]:
    """Fuse multiple ranked result lists using RRF.

    Args:
        ranked_lists: Each sub-list is ordered by descending relevance.
        k: RRF smoothing constant (higher → flatter rank contribution).
        weights: Per-list weight multiplier (len must match ranked_lists).
        top_k: Return at most this many results (None = all).

    Returns:
        Deduplicated results sorted by RRF score descending.
        Each SearchResult.score is replaced by the RRF score.
    """
    if not ranked_lists:
        return []

    n_lists = len(ranked_lists)
    if weights is None:
        weights = [1.0] * n_lists
    if len(weights) != n_lists:
        raise ValueError(f"weights length {len(weights)} != ranked_lists length {n_lists}")

    # Accumulate RRF scores per chunk_id
    rrf_scores: dict[UUID, float] = {}
    best_result: dict[UUID, SearchResult] = {}

    for list_idx, results in enumerate(ranked_lists):
        w = weights[list_idx]
        for rank_0, result in enumerate(results):
            rank_1 = rank_0 + 1  # 1-based rank
            contribution = w / (k + rank_1)
            rrf_scores[result.chunk_id] = (
                rrf_scores.get(result.chunk_id, 0.0) + contribution
            )
            # Keep the result with the richest metadata (first seen wins)
            if result.chunk_id not in best_result:
                best_result[result.chunk_id] = result

    # Build output with RRF score replacing original score
    fused: list[SearchResult] = []
    for chunk_id, rrf_score in sorted(
        rrf_scores.items(), key=lambda kv: kv[1], reverse=True
    ):
        original = best_result[chunk_id]
        fused.append(
            SearchResult(
                chunk_id=original.chunk_id,
                document_id=original.document_id,
                version_id=original.version_id,
                content=original.content,
                score=rrf_score,
                metadata=original.metadata,
                filename=original.filename,
                chunk_index=original.chunk_index,
                sensitivity_level=original.sensitivity_level,
                language=original.language,
                tags=original.tags,
                document_title=original.document_title,
                version_number=original.version_number,
                page_number=original.page_number,
                heading_path=original.heading_path,
            )
        )

    if top_k is not None:
        fused = fused[:top_k]

    return fused
