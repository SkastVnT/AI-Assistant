"""Retrieval service — orchestrates transform → hybrid retrieve → trace.

Supports:
- Query transformations (rewrite, acronym expansion, HyDE, decomposition)
- Hybrid retrieval (dense + lexical + RRF fusion + reranking)
- All stages gated by independent feature flags
"""

from __future__ import annotations

import logging
import time
import uuid as _uuid
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.models import RetrievalTrace
from libs.core.providers.base import EmbeddingProvider, LLMProvider
from libs.retrieval.hybrid import HybridPipelineResult, HybridRetrievalPipeline
from libs.retrieval.search import (
    SearchFilters,
    SearchResult,
    vector_search_from_embedding,
)
from libs.retrieval.transforms.pipeline import (
    QueryTransformPipeline,
    TransformContext,
)

logger = logging.getLogger("rag.retrieval.service")


@dataclass(frozen=True)
class RetrievalRequest:
    """Validated retrieval parameters (built from API schema)."""

    tenant_id: UUID
    user_id: UUID | None
    query: str
    top_k: int = 5
    score_threshold: float = 0.0
    filters: SearchFilters | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    """Single retrieved chunk with full citation metadata."""

    chunk_id: UUID
    document_id: UUID
    version_id: UUID
    content: str
    score: float
    chunk_index: int
    document_title: str
    filename: str
    version_number: int
    page_number: int | None
    heading_path: str | None
    sensitivity_level: str
    language: str
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResponse:
    """Full retrieval result with trace info."""

    query: str
    chunks: list[RetrievedChunk]
    total_found: int
    trace_id: UUID | None
    retrieval_ms: int
    embedding_model: str | None = None
    transformed_query: str | None = None
    sub_queries: list[str] = field(default_factory=list)
    transform_log: list[dict] = field(default_factory=list)
    transform_ms: int = 0
    # Hybrid retrieval diagnostics
    retrieval_strategy: str = "vector_cosine"
    dense_count: int = 0
    lexical_count: int = 0
    fused_count: int = 0
    reranked_count: int = 0
    dense_ms: int = 0
    lexical_ms: int = 0
    fusion_ms: int = 0
    rerank_ms: int = 0


def _to_retrieved_chunk(sr: SearchResult) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=sr.chunk_id,
        document_id=sr.document_id,
        version_id=sr.version_id,
        content=sr.content,
        score=sr.score,
        chunk_index=sr.chunk_index,
        document_title=sr.document_title,
        filename=sr.filename,
        version_number=sr.version_number,
        page_number=sr.page_number,
        heading_path=sr.heading_path,
        sensitivity_level=sr.sensitivity_level,
        language=sr.language,
        tags=sr.tags,
        metadata=sr.metadata,
    )


def _merge_and_dedupe(
    results_per_query: list[list[SearchResult]],
    top_k: int,
) -> list[SearchResult]:
    """Merge results from multiple sub-queries, deduplicate by chunk_id, keep top-k."""
    seen: dict[UUID, SearchResult] = {}
    for results in results_per_query:
        for r in results:
            existing = seen.get(r.chunk_id)
            if existing is None or r.score > existing.score:
                seen[r.chunk_id] = r
    merged = sorted(seen.values(), key=lambda r: r.score, reverse=True)
    return merged[:top_k]


async def _embed_and_search(
    db: AsyncSession,
    embedding_provider: EmbeddingProvider,
    text: str,
    *,
    tenant_id: UUID,
    top_k: int,
    score_threshold: float,
    filters: SearchFilters | None,
) -> list[SearchResult]:
    """Embed a single text and run vector search."""
    vectors = await embedding_provider.embed([text])
    return await vector_search_from_embedding(
        db,
        vectors[0],
        tenant_id=tenant_id,
        top_k=top_k,
        score_threshold=score_threshold,
        filters=filters,
    )


async def _run_hybrid_pipeline(
    db: AsyncSession,
    embedding_provider: EmbeddingProvider,
    query: str,
    *,
    query_embedding: list[float] | None = None,
    tenant_id: UUID,
    top_k: int,
    score_threshold: float,
    filters: SearchFilters | None,
    hybrid_pipeline: HybridRetrievalPipeline | None = None,
) -> HybridPipelineResult | None:
    """Run hybrid pipeline if available, else return None."""
    if hybrid_pipeline is None:
        return None
    return await hybrid_pipeline.execute(
        db,
        embedding_provider,
        query,
        query_embedding=query_embedding,
        tenant_id=tenant_id,
        score_threshold=score_threshold,
        filters=filters,
    )


async def retrieve(
    db: AsyncSession,
    embedding_provider: EmbeddingProvider,
    request: RetrievalRequest,
    *,
    llm: LLMProvider | None = None,
    transform_pipeline: QueryTransformPipeline | None = None,
    hybrid_pipeline: HybridRetrievalPipeline | None = None,
) -> RetrievalResponse:
    """Execute retrieval: [transform] → [hybrid | dense] → trace.

    When a HybridRetrievalPipeline is provided, uses the 5-stage pipeline:
    dense → lexical → RRF fusion → rerank → final selection.
    Otherwise falls back to dense-only retrieval.

    Query transforms (rewrite, HyDE, decomposition) are applied before
    the retrieval stage when a TransformPipeline is provided.
    """
    t_start = time.perf_counter()

    # Step 1: Query transformation (optional)
    ctx: TransformContext | None = None
    if transform_pipeline:
        t_tx = time.perf_counter()
        ctx = await transform_pipeline.transform(request.query)
        transform_ms = int((time.perf_counter() - t_tx) * 1000)
    else:
        transform_ms = 0

    # Step 2: Determine search text
    search_text = ctx.effective_query if ctx else request.query
    hyde_text = ctx.hyde_text if ctx else None
    sub_queries = ctx.sub_queries if ctx else []

    # Step 3: Execute retrieval (hybrid or dense-only)
    t_search_start = time.perf_counter()

    hybrid_result: HybridPipelineResult | None = None

    if sub_queries:
        # Decomposition: run each sub-query, merge results
        results_per_query: list[list[SearchResult]] = []
        for sq in sub_queries:
            sq_results = await _embed_and_search(
                db, embedding_provider, sq,
                tenant_id=request.tenant_id, top_k=request.top_k,
                score_threshold=request.score_threshold, filters=request.filters,
            )
            results_per_query.append(sq_results)
        all_results = _merge_and_dedupe(results_per_query, request.top_k)
        retrieval_strategy = "decomposition"
    elif hybrid_pipeline:
        # Hybrid pipeline: dense + lexical → RRF → rerank
        embed_text = hyde_text or search_text
        vectors = await embedding_provider.embed([embed_text])
        query_embedding = vectors[0]

        hybrid_result = await hybrid_pipeline.execute(
            db,
            embedding_provider,
            search_text,
            query_embedding=query_embedding,
            tenant_id=request.tenant_id,
            score_threshold=request.score_threshold,
            filters=request.filters,
        )
        all_results = hybrid_result.results
        retrieval_strategy = hybrid_result.strategy
    elif hyde_text:
        # HyDE without hybrid: embed hypothetical document
        all_results = await _embed_and_search(
            db, embedding_provider, hyde_text,
            tenant_id=request.tenant_id, top_k=request.top_k,
            score_threshold=request.score_threshold, filters=request.filters,
        )
        retrieval_strategy = "hyde_vector"
    else:
        # Baseline dense search
        all_results = await _embed_and_search(
            db, embedding_provider, search_text,
            tenant_id=request.tenant_id, top_k=request.top_k,
            score_threshold=request.score_threshold, filters=request.filters,
        )
        retrieval_strategy = "vector_cosine"

    search_ms = int((time.perf_counter() - t_search_start) * 1000)
    total_ms = int((time.perf_counter() - t_start) * 1000)

    chunks = [_to_retrieved_chunk(r) for r in all_results]

    # Step 4: Retrieval trace
    transformed_query = ctx.effective_query if ctx else None
    trace_id = _uuid.uuid4()
    trace = RetrievalTrace(
        id=trace_id,
        tenant_id=request.tenant_id,
        user_id=request.user_id,
        query_text=request.query,
        transformed_query=transformed_query if transformed_query != request.query else None,
        retrieval_strategy=retrieval_strategy,
        top_k=request.top_k,
        retrieved_chunks=[
            {"chunk_id": str(c.chunk_id), "score": c.score, "rank": i + 1}
            for i, c in enumerate(chunks)
        ],
        retrieval_latency_ms=total_ms,
        metadata_={
            "transform_ms": transform_ms,
            "search_ms": search_ms,
            "transform_log": ctx.transform_log if ctx else [],
            "sub_queries": sub_queries,
            "retrieval_strategy": retrieval_strategy,
            "dense_count": (
                len(hybrid_result.dense_results) if hybrid_result
                else len(all_results)
            ),
            "lexical_count": len(hybrid_result.lexical_results) if hybrid_result else 0,
            "fused_count": len(hybrid_result.fused_results) if hybrid_result else 0,
            "reranked_count": len(hybrid_result.reranked_results) if hybrid_result else 0,
        },
    )
    db.add(trace)
    await db.flush()

    logger.info(
        "retrieval tenant=%s query=%r strategy=%s top_k=%d returned=%d "
        "transform_ms=%d search_ms=%d total_ms=%d trace=%s",
        request.tenant_id,
        request.query[:80],
        retrieval_strategy,
        request.top_k,
        len(chunks),
        transform_ms,
        search_ms,
        total_ms,
        trace_id,
    )

    return RetrievalResponse(
        query=request.query,
        chunks=chunks,
        total_found=len(chunks),
        trace_id=trace_id,
        retrieval_ms=total_ms,
        embedding_model=getattr(embedding_provider, "model", None),
        transformed_query=transformed_query if transformed_query != request.query else None,
        sub_queries=sub_queries,
        transform_log=ctx.transform_log if ctx else [],
        transform_ms=transform_ms,
        retrieval_strategy=retrieval_strategy,
        dense_count=len(hybrid_result.dense_results) if hybrid_result else len(all_results),
        lexical_count=len(hybrid_result.lexical_results) if hybrid_result else 0,
        fused_count=len(hybrid_result.fused_results) if hybrid_result else 0,
        reranked_count=len(hybrid_result.reranked_results) if hybrid_result else 0,
        dense_ms=hybrid_result.dense_ms if hybrid_result else search_ms,
        lexical_ms=hybrid_result.lexical_ms if hybrid_result else 0,
        fusion_ms=hybrid_result.fusion_ms if hybrid_result else 0,
        rerank_ms=hybrid_result.rerank_ms if hybrid_result else 0,
    )
