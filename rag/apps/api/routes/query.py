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
