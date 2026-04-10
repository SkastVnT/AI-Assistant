"""Query / RAG routes."""

import time
import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import db_session, embedding_provider, llm_provider
from apps.api.schemas import QueryRequest, QueryResponse, SourceChunk
from libs.core.models import RetrievalTrace
from libs.core.providers.base import EmbeddingProvider, LLMProvider
from libs.retrieval.generator import generate_answer
from libs.retrieval.search import SearchFilters, vector_search

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import (
    auth_context,
    db_session,
    embedding_provider,
    llm_provider,
    post_filter_authz,
    pre_filter_authz,
)
from apps.api.schemas import (
    AnswerRequest,
    AnswerResponse,
    CitationRef,
    QueryRequest,
    QueryResponse,
    RetrievedChunkResponse,
    RetrieveRequest,
    RetrieveResponse,
    SourceChunk,
)
from libs.auth.authorization import PostFilterAuthorization, PreFilterAuthorization
from libs.auth.context import AuthContext
from libs.core.models import RetrievalTrace
from libs.core.providers.base import EmbeddingProvider, LLMProvider
from libs.core.settings import get_settings
from libs.retrieval.answer.service import generate_grounded_answer
from libs.retrieval.generator import generate_answer
from libs.retrieval.hybrid import HybridRetrievalPipeline
from libs.retrieval.rerankers import create_reranker
from libs.retrieval.search import SearchFilters, vector_search
from libs.retrieval.service import RetrievalRequest, retrieve
from libs.retrieval.transforms.pipeline import QueryTransformPipeline

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/", response_model=QueryResponse)
async def query_rag(
    body: QueryRequest,
    db: AsyncSession = Depends(db_session),
    embedder: EmbeddingProvider = Depends(embedding_provider),
    llm: LLMProvider = Depends(llm_provider),
    x_tenant_id: str = Header(...),
) -> QueryResponse:
    """Ask a question — retrieves relevant chunks and generates an answer."""
    tenant_id = uuid.UUID(x_tenant_id)
    auth: AuthContext = Depends(auth_context),
    db: AsyncSession = Depends(db_session),
    embedder: EmbeddingProvider = Depends(embedding_provider),
    llm: LLMProvider = Depends(llm_provider),
    pre_authz: PreFilterAuthorization = Depends(pre_filter_authz),
    post_authz: PostFilterAuthorization = Depends(post_filter_authz),
) -> QueryResponse:
    """Ask a question — retrieves relevant chunks and generates an answer."""
    tenant_id = auth.tenant_id
    t_start = time.perf_counter()

    # Build search filters from request
    search_filters: SearchFilters | None = None
    if body.filters:
        search_filters = SearchFilters(
            sensitivity_level=(
                body.filters.sensitivity_levels[0]
                if body.filters.sensitivity_levels
                else None
            ),
            language=(
                body.filters.languages[0] if body.filters.languages else None
            ),
            tags=body.filters.tags,
        )

    # Apply pre-filter authorization (sensitivity ceiling)
    search_filters = await pre_authz.apply(auth, search_filters)

    t_retrieval_start = time.perf_counter()
    results = await vector_search(
        db=db,
        embedding_provider=embedder,
        query=body.query,
        tenant_id=tenant_id,
        top_k=body.top_k,
        score_threshold=body.score_threshold,
        filters=search_filters,
    )
    retrieval_ms = int((time.perf_counter() - t_retrieval_start) * 1000)

    # Apply post-filter authorization (defense-in-depth)
    results = await post_authz.apply(auth, results)

    t_gen_start = time.perf_counter()
    answer = await generate_answer(llm=llm, query=body.query, results=results)
    generation_ms = int((time.perf_counter() - t_gen_start) * 1000)

    total_ms = int((time.perf_counter() - t_start) * 1000)

    sources = [
        SourceChunk(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            version_id=r.version_id,
            filename=r.filename,
            content=r.content,
            score=r.score,
            chunk_index=r.chunk_index,
        )
        for r in results
    ]

    # Record retrieval trace for observability
    trace = RetrievalTrace(
        tenant_id=tenant_id,
        query_text=body.query,
        retrieval_strategy="vector_cosine",
        top_k=body.top_k,
        retrieved_chunks=[
            {"chunk_id": str(s.chunk_id), "score": s.score} for s in sources
        ],
        answer_text=answer,
        latency_ms=total_ms,
        retrieval_latency_ms=retrieval_ms,
        generation_latency_ms=generation_ms,
    )
    db.add(trace)

    return QueryResponse(
        answer=answer, sources=sources, query=body.query, trace_id=trace.id
    )


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_chunks(
    body: RetrieveRequest,
    auth: AuthContext = Depends(auth_context),
    db: AsyncSession = Depends(db_session),
    embedder: EmbeddingProvider = Depends(embedding_provider),
    llm: LLMProvider = Depends(llm_provider),
    pre_authz: PreFilterAuthorization = Depends(pre_filter_authz),
) -> RetrieveResponse:
    """Retrieve relevant chunks without LLM generation.

    Returns top-k chunks with citation metadata and similarity scores.
    Query transformations (rewrite, HyDE, decomposition) are applied
    automatically when enabled via QT_* environment variables.
    """
    tenant_id = auth.tenant_id
    user_id = auth.user_id

    # Build filters
    search_filters: SearchFilters | None = None
    if body.filters:
        search_filters = SearchFilters(
            sensitivity_level=(
                body.filters.sensitivity_levels[0]
                if body.filters.sensitivity_levels
                else None
            ),
            language=(
                body.filters.languages[0]
                if body.filters.languages
                else None
            ),
            source_ids=body.filters.source_ids,
        )

    # Apply authorization pre-filter (sensitivity ceiling)
    search_filters = await pre_authz.apply(auth, search_filters)

    req = RetrievalRequest(
        tenant_id=tenant_id,
        user_id=user_id,
        query=body.query,
        top_k=body.top_k,
        score_threshold=body.score_threshold,
        filters=search_filters,
    )

    pipeline = QueryTransformPipeline(llm=llm)

    # Build hybrid pipeline if enabled
    settings = get_settings()
    hybrid_settings = settings.hybrid_retrieval
    hybrid = None
    if hybrid_settings.enable_lexical or hybrid_settings.enable_reranking:
        reranker = None
        if hybrid_settings.enable_reranking:
            reranker = create_reranker(
                hybrid_settings.reranker_type,
                hybrid_settings.reranker_model,
            )
        hybrid = HybridRetrievalPipeline(
            settings=hybrid_settings, reranker=reranker
        )

    result = await retrieve(
        db, embedder, req,
        llm=llm, transform_pipeline=pipeline, hybrid_pipeline=hybrid,
    )

    return RetrieveResponse(
        query=result.query,
        chunks=[
            RetrievedChunkResponse(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                version_id=c.version_id,
                content=c.content,
                score=c.score,
                chunk_index=c.chunk_index,
                document_title=c.document_title,
                filename=c.filename,
                version_number=c.version_number,
                page_number=c.page_number,
                heading_path=c.heading_path,
                sensitivity_level=c.sensitivity_level,
                language=c.language,
                tags=c.tags,
                metadata=c.metadata,
            )
            for c in result.chunks
        ],
        total_found=result.total_found,
        trace_id=result.trace_id,
        retrieval_ms=result.retrieval_ms,
        embedding_model=result.embedding_model,
        transformed_query=result.transformed_query,
        sub_queries=result.sub_queries,
        transform_log=result.transform_log,
        transform_ms=result.transform_ms,
        retrieval_strategy=result.retrieval_strategy,
        dense_count=result.dense_count,
        lexical_count=result.lexical_count,
        fused_count=result.fused_count,
        reranked_count=result.reranked_count,
        dense_ms=result.dense_ms,
        lexical_ms=result.lexical_ms,
        fusion_ms=result.fusion_ms,
        rerank_ms=result.rerank_ms,
    )


def _build_search_filters(filters) -> SearchFilters | None:
    """Convert API filter schema to internal SearchFilters."""
    if filters is None:
        return None
    return SearchFilters(
        sensitivity_level=(
            filters.sensitivity_levels[0]
            if filters.sensitivity_levels
            else None
        ),
        language=(
            filters.languages[0] if filters.languages else None
        ),
        source_ids=getattr(filters, "source_ids", None),
    )


def _build_hybrid_pipeline() -> HybridRetrievalPipeline | None:
    """Build hybrid pipeline from settings when enabled."""
    settings = get_settings()
    hs = settings.hybrid_retrieval
    if not (hs.enable_lexical or hs.enable_reranking):
        return None
    reranker = None
    if hs.enable_reranking:
        reranker = create_reranker(hs.reranker_type, hs.reranker_model)
    return HybridRetrievalPipeline(settings=hs, reranker=reranker)


@router.post("/answer", response_model=AnswerResponse)
async def answer_query(
    body: AnswerRequest,
    auth: AuthContext = Depends(auth_context),
    db: AsyncSession = Depends(db_session),
    embedder: EmbeddingProvider = Depends(embedding_provider),
    llm: LLMProvider = Depends(llm_provider),
    pre_authz: PreFilterAuthorization = Depends(pre_filter_authz),
) -> AnswerResponse:
    """Generate a grounded answer with structured citations.

    Pipeline:
        1. Transform query (rewrite/HyDE/decomposition via QT_* flags)
        2. Retrieve evidence (hybrid or dense-only via HYBRID_* flags)
        3. Build grounded prompt (system instructions + evidence + query)
        4. Generate answer via LLM
        5. Extract [Source N] citations → structured CitationRef list
    """
    tenant_id = auth.tenant_id
    user_id = auth.user_id

    search_filters = _build_search_filters(body.filters)
    # Apply authorization pre-filter (sensitivity ceiling)
    search_filters = await pre_authz.apply(auth, search_filters)

    pipeline = QueryTransformPipeline(llm=llm)
    hybrid = _build_hybrid_pipeline()

    result = await generate_grounded_answer(
        db,
        embedder,
        llm,
        query=body.query,
        tenant_id=tenant_id,
        user_id=user_id,
        mode=body.mode,
        top_k=body.top_k,
        score_threshold=body.score_threshold,
        filters=search_filters,
        transform_pipeline=pipeline,
        hybrid_pipeline=hybrid,
    )

    return AnswerResponse(
        answer=result.answer,
        citations=[
            CitationRef(
                source_index=c.source_index,
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                version_id=c.version_id,
                filename=c.filename,
                content_snippet=c.content_snippet,
                score=c.score,
                page_number=c.page_number,
                heading_path=c.heading_path,
            )
            for c in result.citations
        ],
        query=result.query,
        mode=result.mode,
        evidence_used=result.evidence_used,
        trace_id=result.trace_id,
        retrieval_ms=result.retrieval_ms,
        generation_ms=result.generation_ms,
        total_ms=result.total_ms,
    )
