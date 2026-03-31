"""Hybrid retrieval pipeline — dense + lexical → RRF → rerank → select.

Orchestrates the 5-stage hybrid retrieval:
  1. Dense (vector) search          → top dense_top_k
  2. Lexical (BM25) search          → top lexical_top_k
  3. Reciprocal Rank Fusion (RRF)   → merged candidates
  4. Rerank top N candidates         → rerank_top_n
  5. Final context selection          → final_context_k

All stages are independently configurable via HybridRetrievalSettings.
Falls back to dense-only when lexical is disabled.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.providers.base import EmbeddingProvider
from libs.core.settings import HybridRetrievalSettings, get_settings
from libs.retrieval.fusion import reciprocal_rank_fusion
from libs.retrieval.lexical_search import lexical_search
from libs.retrieval.rerankers import (
    Reranker,
    RerankResult,
    SearchResult,
)
from libs.retrieval.search import SearchFilters, vector_search_from_embedding

logger = logging.getLogger("rag.retrieval.hybrid")


@dataclass(frozen=True)
class HybridPipelineResult:
    """Output of the full hybrid pipeline with stage-level diagnostics."""

    results: list[SearchResult]
    # Stage results for evaluation / debugging
    dense_results: list[SearchResult]
    lexical_results: list[SearchResult]
    fused_results: list[SearchResult]
    reranked_results: list[RerankResult]
    # Timing
    dense_ms: int = 0
    lexical_ms: int = 0
    fusion_ms: int = 0
    rerank_ms: int = 0
    total_ms: int = 0
    # Strategy used
    strategy: str = "dense_only"


class HybridRetrievalPipeline:
    """Configurable hybrid retrieval pipeline.

    Usage:
        pipeline = HybridRetrievalPipeline(settings=..., reranker=...)
        result = await pipeline.execute(db, embedding_provider, query, ...)
    """

    def __init__(
        self,
        settings: HybridRetrievalSettings | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self._settings = settings or get_settings().hybrid_retrieval
        self._reranker = reranker

    async def execute(
        self,
        db: AsyncSession,
        embedding_provider: EmbeddingProvider,
        query: str,
        *,
        query_embedding: list[float] | None = None,
        tenant_id: UUID,
        score_threshold: float = 0.0,
        filters: SearchFilters | None = None,
    ) -> HybridPipelineResult:
        """Run the full 5-stage hybrid pipeline."""
        s = self._settings
        t_start = time.perf_counter()

        # Stage 1: Dense search
        t_dense = time.perf_counter()
        if query_embedding is None:
            vectors = await embedding_provider.embed([query])
            query_embedding = vectors[0]

        dense_results = await vector_search_from_embedding(
            db,
            query_embedding,
            tenant_id=tenant_id,
            top_k=s.dense_top_k,
            score_threshold=score_threshold,
            filters=filters,
        )
        dense_ms = int((time.perf_counter() - t_dense) * 1000)

        # Stage 2: Lexical search (if enabled)
        lexical_results: list[SearchResult] = []
        lexical_ms = 0
        if s.enable_lexical:
            t_lex = time.perf_counter()
            lexical_results = await lexical_search(
                db,
                query,
                tenant_id=tenant_id,
                top_k=s.lexical_top_k,
                filters=filters,
            )
            lexical_ms = int((time.perf_counter() - t_lex) * 1000)

        # Stage 3: Fusion
        t_fusion = time.perf_counter()
        if lexical_results:
            fused_results = reciprocal_rank_fusion(
                [dense_results, lexical_results],
                k=s.rrf_k,
                weights=[s.dense_weight, s.lexical_weight],
                top_k=s.rerank_top_n,
            )
            strategy = "hybrid_rrf"
        else:
            fused_results = dense_results[: s.rerank_top_n]
            strategy = "dense_only"
        fusion_ms = int((time.perf_counter() - t_fusion) * 1000)

        # Stage 4: Rerank (if enabled)
        reranked: list[RerankResult] = []
        rerank_ms = 0
        if s.enable_reranking and self._reranker and fused_results:
            t_rerank = time.perf_counter()
            reranked = await self._reranker.rerank(
                query, fused_results, top_n=s.rerank_top_n
            )
            rerank_ms = int((time.perf_counter() - t_rerank) * 1000)
            strategy += "+rerank"

        # Stage 5: Final context selection
        if reranked:
            # Replace scores with reranker scores for downstream
            final = []
            for rr in reranked[: s.final_context_k]:
                final.append(
                    SearchResult(
                        chunk_id=rr.result.chunk_id,
                        document_id=rr.result.document_id,
                        version_id=rr.result.version_id,
                        content=rr.result.content,
                        score=rr.rerank_score,
                        metadata=rr.result.metadata,
                        filename=rr.result.filename,
                        chunk_index=rr.result.chunk_index,
                        sensitivity_level=rr.result.sensitivity_level,
                        language=rr.result.language,
                        tags=rr.result.tags,
                        document_title=rr.result.document_title,
                        version_number=rr.result.version_number,
                        page_number=rr.result.page_number,
                        heading_path=rr.result.heading_path,
                    )
                )
        else:
            final = fused_results[: s.final_context_k]

        total_ms = int((time.perf_counter() - t_start) * 1000)

        logger.info(
            "hybrid_pipeline: strategy=%s dense=%d(%dms) lexical=%d(%dms) "
            "fused=%d(%dms) reranked=%d(%dms) final=%d total=%dms",
            strategy,
            len(dense_results),
            dense_ms,
            len(lexical_results),
            lexical_ms,
            len(fused_results),
            fusion_ms,
            len(reranked),
            rerank_ms,
            len(final),
            total_ms,
        )

        return HybridPipelineResult(
            results=final,
            dense_results=dense_results,
            lexical_results=lexical_results,
            fused_results=fused_results,
            reranked_results=reranked,
            dense_ms=dense_ms,
            lexical_ms=lexical_ms,
            fusion_ms=fusion_ms,
            rerank_ms=rerank_ms,
            total_ms=total_ms,
            strategy=strategy,
        )
