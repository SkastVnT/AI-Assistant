"""Query transformation pipeline — interface and individual transforms.

Each transform takes a TransformContext and returns an updated one.
The pipeline runs enabled transforms sequentially, respecting timeouts.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field

from libs.core.providers.base import LLMProvider
from libs.core.settings import QueryTransformSettings, get_settings
from libs.retrieval.transforms.prompts import (
    DECOMPOSITION_SYSTEM,
    DECOMPOSITION_USER,
    HYDE_SYSTEM,
    HYDE_USER,
    REWRITE_SYSTEM,
    REWRITE_USER,
)

logger = logging.getLogger("rag.retrieval.transforms")


# ── Data structures ────────────────────────────────────────────────────────


@dataclass
class TransformContext:
    """Mutable context carried through the pipeline."""

    original_query: str
    rewritten_query: str | None = None
    expanded_query: str | None = None
    hyde_document: str | None = None
    sub_queries: list[str] = field(default_factory=list)
    transform_log: list[dict] = field(default_factory=list)
    total_transform_ms: int = 0

    @property
    def effective_query(self) -> str:
        """The best query to use for embedding — last non-None transform."""
        return (
            self.rewritten_query
            or self.expanded_query
            or self.original_query
        )

    @property
    def queries_for_retrieval(self) -> list[str]:
        """All queries to run through retrieval (supports decomposition)."""
        if self.sub_queries:
            return self.sub_queries
        return [self.effective_query]

    @property
    def hyde_text(self) -> str | None:
        """If HyDE is active, this text is embedded instead of the query."""
        return self.hyde_document


# ── Individual transforms ──────────────────────────────────────────────────


async def _call_llm_with_timeout(
    llm: LLMProvider,
    system: str,
    user: str,
    timeout_ms: int,
) -> str | None:
    """Call LLM with a timeout. Returns None on timeout or error."""
    timeout_s = timeout_ms / 1000 if timeout_ms > 0 else None
    try:
        coro = llm.complete(user, system=system, temperature=0.0, max_tokens=512)
        if timeout_s:
            result = await asyncio.wait_for(coro, timeout=timeout_s)
        else:
            result = await coro
        return result.strip()
    except TimeoutError:
        logger.warning("LLM call timed out after %dms", timeout_ms)
        return None
    except Exception:
        logger.exception("LLM call failed")
        return None


async def rewrite_query(
    ctx: TransformContext,
    llm: LLMProvider,
    settings: QueryTransformSettings,
) -> TransformContext:
    """Rewrite the query for better retrieval precision."""
    t0 = time.perf_counter()
    result = await _call_llm_with_timeout(
        llm,
        system=REWRITE_SYSTEM,
        user=REWRITE_USER.format(query=ctx.original_query),
        timeout_ms=settings.rewrite_timeout_ms,
    )
    elapsed = int((time.perf_counter() - t0) * 1000)

    if result:
        ctx.rewritten_query = result
        ctx.transform_log.append({
            "transform": "rewrite",
            "input": ctx.original_query,
            "output": result,
            "ms": elapsed,
        })
        logger.info("rewrite: %r → %r (%dms)", ctx.original_query, result, elapsed)
    else:
        ctx.transform_log.append({
            "transform": "rewrite",
            "input": ctx.original_query,
            "output": None,
            "ms": elapsed,
            "skipped": True,
        })
    ctx.total_transform_ms += elapsed
    return ctx


def expand_acronyms(
    ctx: TransformContext,
    settings: QueryTransformSettings,
) -> TransformContext:
    """Expand known acronyms in the query using domain dictionary."""
    t0 = time.perf_counter()
    acronym_dict = settings.acronym_dict
    if not acronym_dict:
        return ctx

    query = ctx.rewritten_query or ctx.original_query
    expanded = query
    applied: list[str] = []

    for abbr, full in acronym_dict.items():
        pattern = re.compile(r"\b" + re.escape(abbr) + r"\b", re.IGNORECASE)
        if pattern.search(expanded):
            expanded = pattern.sub(f"{abbr} ({full})", expanded, count=1)
            applied.append(f"{abbr}→{full}")

    elapsed = int((time.perf_counter() - t0) * 1000)
    if applied:
        ctx.expanded_query = expanded
        ctx.transform_log.append({
            "transform": "acronym_expansion",
            "input": query,
            "output": expanded,
            "expansions": applied,
            "ms": elapsed,
        })
        logger.info("acronym_expansion: %r → %r", query, expanded)
    ctx.total_transform_ms += elapsed
    return ctx


async def generate_hyde_document(
    ctx: TransformContext,
    llm: LLMProvider,
    settings: QueryTransformSettings,
) -> TransformContext:
    """Generate a hypothetical document for HyDE embedding."""
    t0 = time.perf_counter()
    query = ctx.effective_query
    result = await _call_llm_with_timeout(
        llm,
        system=HYDE_SYSTEM,
        user=HYDE_USER.format(query=query),
        timeout_ms=settings.hyde_timeout_ms,
    )
    elapsed = int((time.perf_counter() - t0) * 1000)

    if result:
        ctx.hyde_document = result
        ctx.transform_log.append({
            "transform": "hyde",
            "input": query,
            "output": result[:200] + ("..." if len(result) > 200 else ""),
            "ms": elapsed,
        })
        logger.info("hyde: generated %d chars from %r (%dms)", len(result), query, elapsed)
    else:
        ctx.transform_log.append({
            "transform": "hyde",
            "input": query,
            "output": None,
            "ms": elapsed,
            "skipped": True,
        })
    ctx.total_transform_ms += elapsed
    return ctx


async def decompose_query(
    ctx: TransformContext,
    llm: LLMProvider,
    settings: QueryTransformSettings,
) -> TransformContext:
    """Decompose a complex query into sub-queries for multi-hop retrieval."""
    t0 = time.perf_counter()
    query = ctx.effective_query
    system = DECOMPOSITION_SYSTEM.format(max_sub_queries=settings.max_sub_queries)
    result = await _call_llm_with_timeout(
        llm,
        system=system,
        user=DECOMPOSITION_USER.format(query=query),
        timeout_ms=settings.decomposition_timeout_ms,
    )
    elapsed = int((time.perf_counter() - t0) * 1000)

    if result:
        lines = [
            re.sub(r"^\d+[\.\)]\s*", "", line).strip()
            for line in result.splitlines()
            if line.strip()
        ]
        sub_queries = [q for q in lines if q][:settings.max_sub_queries]

        if len(sub_queries) > 1:
            ctx.sub_queries = sub_queries
        # If LLM returned just 1 line, keep original (not truly decomposable)

        ctx.transform_log.append({
            "transform": "decomposition",
            "input": query,
            "output": sub_queries,
            "ms": elapsed,
        })
        logger.info("decomposition: %r → %d sub-queries (%dms)", query, len(sub_queries), elapsed)
    else:
        ctx.transform_log.append({
            "transform": "decomposition",
            "input": query,
            "output": None,
            "ms": elapsed,
            "skipped": True,
        })
    ctx.total_transform_ms += elapsed
    return ctx


# ── Pipeline ───────────────────────────────────────────────────────────────


class QueryTransformPipeline:
    """Runs enabled query transformations in sequence.

    Order: rewrite → acronym expansion → HyDE → decomposition
    Each step is independently toggled via QueryTransformSettings.
    """

    def __init__(
        self,
        llm: LLMProvider | None = None,
        settings: QueryTransformSettings | None = None,
    ) -> None:
        self._llm = llm
        self._settings = settings or get_settings().query_transform

    async def transform(self, query: str) -> TransformContext:
        """Run the full transformation pipeline on a raw query."""
        ctx = TransformContext(original_query=query)
        s = self._settings

        # 1. Rewrite
        if s.enable_rewrite and self._llm:
            ctx = await rewrite_query(ctx, self._llm, s)

        # 2. Acronym expansion (no LLM needed)
        if s.enable_acronym_expansion:
            ctx = expand_acronyms(ctx, s)

        # 3. HyDE
        if s.enable_hyde and self._llm:
            ctx = await generate_hyde_document(ctx, self._llm, s)

        # 4. Decomposition
        if s.enable_decomposition and self._llm:
            ctx = await decompose_query(ctx, self._llm, s)

        logger.info(
            "transform_pipeline: original=%r effective=%r "
            "sub_queries=%d hyde=%s total_ms=%d",
            ctx.original_query,
            ctx.effective_query,
            len(ctx.sub_queries),
            ctx.hyde_document is not None,
            ctx.total_transform_ms,
        )
        return ctx
