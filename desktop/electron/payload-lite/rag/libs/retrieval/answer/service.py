"""Answer generation service — grounded RAG answer with inline citations.

Pipeline:
    1. Transform query (rewrite/HyDE/decomposition)
    2. Retrieve evidence (hybrid or dense-only)
    3. Build grounded prompt (system + evidence + query)
    4. Generate answer via LLM
    5. Extract and attach structured citations

All timing is captured for observability. The prompt assembly metadata
(chunk count, mode, token budget) is logged — never the raw prompt text
or secrets.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.models import RetrievalTrace
from libs.core.providers.base import EmbeddingProvider, LLMProvider
from libs.core.settings import AnswerGenerationSettings, get_settings
from libs.guardrails.pipeline import (
    run_post_generation_guardrails,
    run_pre_generation_guardrails,
)
from libs.ragops.tracing import SpanCollector
from libs.retrieval.answer.prompts import (
    SYSTEM_PROMPTS,
    build_user_prompt,
    format_evidence,
)
from libs.retrieval.hybrid import HybridRetrievalPipeline
from libs.retrieval.search import SearchFilters
from libs.retrieval.service import (
    RetrievalRequest,
    RetrievalResponse,
    retrieve,
)
from libs.retrieval.transforms.pipeline import QueryTransformPipeline

logger = logging.getLogger("rag.answer")

# Regex to find [Source N] references in the generated answer
_CITATION_PATTERN = re.compile(r"\[Source\s+(\d+)\]")


# ── Data structures ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Citation:
    """Structured citation produced by the answer pipeline."""

    source_index: int
    chunk_id: UUID
    document_id: UUID
    version_id: UUID
    filename: str
    content_snippet: str
    score: float
    page_number: int | None = None
    heading_path: str | None = None


@dataclass(frozen=True)
class AnswerResult:
    """Full answer pipeline result."""

    answer: str
    citations: list[Citation]
    query: str
    mode: str
    evidence_used: int
    trace_id: UUID | None = None
    retrieval_ms: int = 0
    generation_ms: int = 0
    total_ms: int = 0
    retrieval_response: RetrievalResponse | None = None


# ── Evidence preparation ───────────────────────────────────────────────────


def _prepare_evidence(
    retrieval: RetrievalResponse,
) -> list[dict]:
    """Build evidence block dicts from retrieval chunks."""
    blocks: list[dict] = []
    for i, chunk in enumerate(retrieval.chunks, 1):
        blocks.append({
            "source_index": i,
            "filename": chunk.filename,
            "content": chunk.content,
            "score": chunk.score,
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "version_id": chunk.version_id,
            "page_number": chunk.page_number,
            "heading_path": chunk.heading_path,
        })
    return blocks


# ── Citation extraction ────────────────────────────────────────────────────


def extract_citations(
    answer_text: str,
    evidence_blocks: list[dict],
) -> list[Citation]:
    """Parse [Source N] references from the answer and build Citation objects.

    Only references that match an actual evidence block are returned.
    Duplicates are collapsed — each source index appears at most once.
    """
    evidence_by_idx = {e["source_index"]: e for e in evidence_blocks}
    seen: set[int] = set()
    citations: list[Citation] = []

    for match in _CITATION_PATTERN.finditer(answer_text):
        idx = int(match.group(1))
        if idx in seen or idx not in evidence_by_idx:
            continue
        seen.add(idx)
        e = evidence_by_idx[idx]
        snippet = e["content"][:300]
        citations.append(Citation(
            source_index=idx,
            chunk_id=e["chunk_id"],
            document_id=e["document_id"],
            version_id=e["version_id"],
            filename=e["filename"],
            content_snippet=snippet,
            score=e["score"],
            page_number=e.get("page_number"),
            heading_path=e.get("heading_path"),
        ))

    return citations


# ── Core generation ────────────────────────────────────────────────────────


def _max_tokens_for_mode(
    mode: str, settings: AnswerGenerationSettings,
) -> int:
    return {
        "concise": settings.max_tokens_concise,
        "standard": settings.max_tokens_standard,
        "detailed": settings.max_tokens_detailed,
    }.get(mode, settings.max_tokens_standard)


async def _generate_with_timeout(
    llm: LLMProvider,
    user_prompt: str,
    system_prompt: str,
    *,
    temperature: float,
    max_tokens: int,
    timeout_ms: int,
) -> str:
    """Call LLM with a timeout guard."""
    coro = llm.complete(
        user_prompt,
        system=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if timeout_ms > 0:
        return await asyncio.wait_for(
            coro, timeout=timeout_ms / 1000,
        )
    return await coro


# ── Main pipeline ──────────────────────────────────────────────────────────


async def generate_grounded_answer(
    db: AsyncSession,
    embedding_provider: EmbeddingProvider,
    llm: LLMProvider,
    *,
    query: str,
    tenant_id: UUID,
    user_id: UUID | None = None,
    mode: str = "standard",
    top_k: int = 5,
    score_threshold: float = 0.0,
    filters: SearchFilters | None = None,
    transform_pipeline: QueryTransformPipeline | None = None,
    hybrid_pipeline: HybridRetrievalPipeline | None = None,
) -> AnswerResult:
    """Execute the full answer-generation pipeline.

    Steps:
        1. Transform query (optional)
        2. Retrieve evidence chunks
        3. Build grounded prompt (system + evidence + query)
        4. Generate answer via LLM
        5. Extract inline citations → structured Citation objects
    """
    settings = get_settings().answer_generation
    if mode not in SYSTEM_PROMPTS:
        mode = settings.default_mode

    t_start = time.perf_counter()
    collector = SpanCollector() if get_settings().ragops.tracing_enabled else None

    # ── Step 1 + 2: Retrieve evidence ──────────────────────────────────
    req = RetrievalRequest(
        tenant_id=tenant_id,
        user_id=user_id,
        query=query,
        top_k=top_k,
        score_threshold=score_threshold,
        filters=filters,
    )

    retrieval = await retrieve(
        db,
        embedding_provider,
        req,
        llm=llm,
        transform_pipeline=transform_pipeline,
        hybrid_pipeline=hybrid_pipeline,
    )
    retrieval_ms = retrieval.retrieval_ms
    if collector:
        collector.add_span(
            "retrieval", duration_ms=retrieval_ms,
            strategy=retrieval.retrieval_strategy,
            embedding_model=retrieval.embedding_model,
            top_k=top_k, returned=len(retrieval.chunks),
            transform_ms=retrieval.transform_ms,
            dense_ms=retrieval.dense_ms, dense_count=retrieval.dense_count,
            lexical_ms=retrieval.lexical_ms, lexical_count=retrieval.lexical_count,
            fusion_ms=retrieval.fusion_ms, fused_count=retrieval.fused_count,
            rerank_ms=retrieval.rerank_ms, reranked_count=retrieval.reranked_count,
        )

    # ── Step 3: Build grounded prompt ──────────────────────────────────
    evidence_blocks = _prepare_evidence(retrieval)

    # ── Step 3.5: Pre-generation guardrails ────────────────────────────
    t_guard_pre = time.perf_counter()
    _safe_evidence, evidence_text, _guard_events = await run_pre_generation_guardrails(
        db,
        evidence_blocks=evidence_blocks,
        evidence_formatter=format_evidence,
        tenant_id=tenant_id,
        trace_id=retrieval.trace_id,
        user_id=user_id,
    )
    if collector:
        collector.add_span(
            "guardrails_pre",
            duration_ms=int((time.perf_counter() - t_guard_pre) * 1000),
            events=_guard_events,
        )

    system_prompt = SYSTEM_PROMPTS[mode]
    user_prompt = build_user_prompt(query, evidence_text)

    max_tokens = _max_tokens_for_mode(mode, settings)

    logger.info(
        "answer_prompt mode=%s evidence_chunks=%d max_tokens=%d "
        "retrieval_ms=%d tenant=%s",
        mode,
        len(evidence_blocks),
        max_tokens,
        retrieval_ms,
        tenant_id,
    )

    # ── Step 4: Generate answer ────────────────────────────────────────
    t_gen = time.perf_counter()
    try:
        answer_text = await _generate_with_timeout(
            llm,
            user_prompt,
            system_prompt,
            temperature=settings.temperature,
            max_tokens=max_tokens,
            timeout_ms=settings.timeout_ms,
        )
    except TimeoutError:
        logger.warning("answer generation timed out after %dms", settings.timeout_ms)
        answer_text = (
            "I was unable to generate an answer within the time limit. "
            "Please try again or simplify your question."
        )
    generation_ms = int((time.perf_counter() - t_gen) * 1000)
    if collector:
        collector.add_span(
            "generation", duration_ms=generation_ms,
            model=getattr(llm, "model", None),
            mode=mode, max_tokens=max_tokens,
            temperature=settings.temperature,
        )
    total_ms = int((time.perf_counter() - t_start) * 1000)

    # ── Step 5: Extract citations ──────────────────────────────────────
    citations = extract_citations(answer_text, evidence_blocks)

    # ── Step 5.5: Post-generation guardrails ───────────────────────────
    t_guard_post = time.perf_counter()
    post_guard = await run_post_generation_guardrails(
        db,
        answer_text=answer_text,
        evidence_count=len(evidence_blocks),
        tenant_id=tenant_id,
        trace_id=retrieval.trace_id,
        user_id=user_id,
    )
    if not post_guard.allowed:
        answer_text = post_guard.answer
        citations = []  # blocked response has no citations

    elif post_guard.answer != answer_text:
        # PII was redacted — update answer text
        answer_text = post_guard.answer

    if collector:
        collector.add_span(
            "guardrails_post",
            duration_ms=int((time.perf_counter() - t_guard_post) * 1000),
            allowed=post_guard.allowed,
        )

    # ── Trace update ───────────────────────────────────────────────────
    # Update the trace that retrieve() already created with answer info
    if retrieval.trace_id:
        trace = await db.get(RetrievalTrace, retrieval.trace_id)
        if trace:
            trace.answer_text = answer_text
            trace.llm_model = getattr(llm, "model", None)
            trace.generation_latency_ms = generation_ms
            trace.latency_ms = total_ms
            trace.metadata_["answer_mode"] = mode
            trace.metadata_["evidence_count"] = len(evidence_blocks)
            trace.metadata_["citation_count"] = len(citations)
            if collector:
                trace.metadata_["spans"] = collector.to_dict()
            await db.flush()

    logger.info(
        "answer_generated tenant=%s query=%r mode=%s citations=%d "
        "retrieval_ms=%d generation_ms=%d total_ms=%d trace=%s",
        tenant_id,
        query[:80],
        mode,
        len(citations),
        retrieval_ms,
        generation_ms,
        total_ms,
        retrieval.trace_id,
    )

    return AnswerResult(
        answer=answer_text,
        citations=citations,
        query=query,
        mode=mode,
        evidence_used=len(evidence_blocks),
        trace_id=retrieval.trace_id,
        retrieval_ms=retrieval_ms,
        generation_ms=generation_ms,
        total_ms=total_ms,
        retrieval_response=retrieval,
    )
