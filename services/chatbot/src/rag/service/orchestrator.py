"""
RAG orchestrator — coordinates retrieval, sanitisation, context
building, and prompt augmentation into a single reusable pipeline.

Entry-points
~~~~~~~~~~~~
- ``retrieve_for_chat()``       — full pipeline used by chat / stream routers
- ``build_rag_context_block()`` — format hits into ``[RAG_CONTEXT]`` block
- ``build_citations()``         — structured citation list for API response

"""
from __future__ import annotations

import logging
from dataclasses import dataclass, replace as _dc_replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .retrieval_service import RetrievalHit
    from .strategy import RetrievalStrategy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public result DTO
# ---------------------------------------------------------------------------


@dataclass
class RAGResult:
    """Outcome of a RAG retrieval attempt."""

    message: str
    """User message — potentially with [RAG_CONTEXT] block prepended."""

    custom_prompt: str
    """System prompt — potentially with grounding instruction appended."""

    citations: list[dict] | None
    """Structured citation list for the API response (None when RAG inactive)."""

    chunk_count: int
    """Number of retrieved chunks (0 when RAG inactive or no hits)."""


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class RAGOrchestrator:
    """Coordinates the full RAG pipeline.

    Parameters
    ----------
    strategy : RetrievalStrategy | None
        ``None`` → a default :class:`RetrievalService` is used.
    """

    def __init__(self, strategy: RetrievalStrategy | None = None) -> None:
        self._strategy = strategy

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def retrieve_for_chat(
        self,
        *,
        message: str,
        custom_prompt: str,
        language: str,
        tenant_id: str,
        collection_ids: list[str],
        top_k: int = 5,
    ) -> RAGResult:
        """Full pipeline: retrieve → sanitise → build context → augment prompt.

        Returns the original *message* / *custom_prompt* unchanged when
        RAG is inactive, collections are empty, or retrieval fails.
        """
        empty = RAGResult(
            message=message,
            custom_prompt=custom_prompt,
            citations=None,
            chunk_count=0,
        )

        if not collection_ids:
            return empty

        try:
            from src.rag import RAG_ENABLED as _rag_on

            if not _rag_on:
                return empty

            from src.rag.security.policies import get_rag_policies
            from src.rag.security.prompt_injection import (
                cap_top_k,
                enforce_query_length,
            )

            policies = get_rag_policies()

            # ── Policy enforcement on inputs ──────────────────────────
            safe_query = enforce_query_length(message, policies=policies)
            safe_top_k = cap_top_k(top_k, policies=policies)

            strategy = self._get_strategy()
            hits = await strategy.retrieve(
                tenant_id=tenant_id,
                query=safe_query,
                top_k=safe_top_k,
                doc_ids=(
                    collection_ids if collection_ids != ["default"] else None
                ),
            )

            # ── Post-retrieval pipeline ───────────────────────────────
            sanitised = self._sanitize_hits(hits)
            capped = self._cap_context(sanitised)
            context_block, citations = self._build_context_and_citations(capped)

            if not context_block:
                return RAGResult(
                    message=message,
                    custom_prompt=custom_prompt,
                    citations=citations or None,
                    chunk_count=0,
                )

            augmented_message = context_block + message
            augmented_prompt = self._augment_prompt(custom_prompt, language)

            return RAGResult(
                message=augmented_message,
                custom_prompt=augmented_prompt,
                citations=citations,
                chunk_count=len(capped),
            )

        except Exception as e:
            logger.warning("[RAG] Retrieval error: %s", e)
            return empty

    # ------------------------------------------------------------------
    # Public building blocks (usable independently)
    # ------------------------------------------------------------------

    def build_rag_context_block(self, hits: list[RetrievalHit]) -> str:
        """Build the ``[RAG_CONTEXT]…[/RAG_CONTEXT]`` block from hits."""
        block, _ = self._build_context_and_citations(hits)
        return block

    def build_citations(self, hits: list[RetrievalHit]) -> list[dict]:
        """Build the structured citation list for the API response."""
        _, citations = self._build_context_and_citations(hits)
        return citations

    # ------------------------------------------------------------------
    # Internal pipeline steps (override in subclass to customise)
    # ------------------------------------------------------------------

    def _get_strategy(self) -> RetrievalStrategy:
        """Lazy-create the default vector strategy when none was injected."""
        if self._strategy is None:
            from src.rag.service import RetrievalService

            self._strategy = RetrievalService()
        return self._strategy

    @staticmethod
    def _build_context_and_citations(
        hits: list[RetrievalHit],
    ) -> tuple[str, list[dict]]:
        """Delegate to the prompt-template layer."""
        from src.rag.prompts import build_grounded_rag_context

        return build_grounded_rag_context(hits)

    @staticmethod
    def _sanitize_hits(
        hits: list[RetrievalHit],
    ) -> list[RetrievalHit]:
        """Filter / rewrite chunks that contain injection patterns."""
        from src.rag.security.policies import get_rag_policies
        from src.rag.security.prompt_injection import sanitize_chunk

        policies = get_rag_policies()
        result: list[RetrievalHit] = []  # type: ignore[type-arg]
        for h in hits:
            sr = sanitize_chunk(h.content, policies=policies)
            if sr.blocked:
                logger.info("[RAG] Blocked chunk %s (injection)", h.chunk_id)
                continue
            if sr.flagged:
                logger.warning(
                    "[RAG] Flagged chunk %s: %s",
                    h.chunk_id,
                    [f.pattern_name for f in sr.flags],
                )
            result.append(_dc_replace(h, content=sr.text))
        return result

    @staticmethod
    def _cap_context(
        hits: list[RetrievalHit],
    ) -> list[RetrievalHit]:
        """Truncate the hit list so total character count fits the budget."""
        from src.rag.security.policies import get_rag_policies

        policies = get_rag_policies()
        capped: list[RetrievalHit] = []  # type: ignore[type-arg]
        total = 0
        for h in hits:
            if total + len(h.content) > policies.max_context_chars:
                break
            capped.append(h)
            total += len(h.content)
        return capped

    @staticmethod
    def _augment_prompt(custom_prompt: str, language: str) -> str:
        """Append the grounding system instruction if not already present."""
        from src.rag.prompts import get_grounded_system_instruction

        if "[RAG_CONTEXT]" in custom_prompt:
            return custom_prompt

        grounding = get_grounded_system_instruction(language)
        return (custom_prompt + "\n" if custom_prompt else "") + grounding
