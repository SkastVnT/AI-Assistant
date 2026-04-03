"""
Agentic Council — FastAPI entry point
======================================
Thin bridge between the FastAPI ``_do_chat()`` router and the
:class:`CouncilOrchestrator`.  Keeps router changes minimal:
the router calls :func:`run_council` and gets back a dict that
maps directly to ``ChatResponse`` fields.

Feature flag
~~~~~~~~~~~~
Set ``AGENTIC_V1_ENABLED=true`` in environment to activate council mode.
When the flag is ``false`` (default), requesting ``agent_mode="council"``
returns a graceful error message — existing behaviour is never broken.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from core.agentic.config import CouncilConfig
from core.agentic.contracts import AgentRole, CouncilResult
from core.agentic.orchestrator import CouncilOrchestrator
from core.agentic.state import PreContext

logger = logging.getLogger(__name__)

# ── Feature flag ───────────────────────────────────────────────────────

AGENTIC_V1_ENABLED: bool = os.getenv("AGENTIC_V1_ENABLED", "false").lower() in (
    "true",
    "1",
    "yes",
)


def is_council_enabled() -> bool:
    """Check whether the agentic council feature is turned on."""
    return AGENTIC_V1_ENABLED


# ── Public API ─────────────────────────────────────────────────────────


async def run_council(
    *,
    original_message: str,
    augmented_message: str,
    rag_chunks: list[dict[str, Any]],
    rag_citations: list[dict[str, Any]],
    mcp_context: str,
    language: str,
    context_type: str,
    custom_prompt: str,
    # Per-role model overrides from ChatRequest
    max_agent_iterations: int = 2,
    preferred_planner_model: str | None = None,
    preferred_researcher_model: str | None = None,
    preferred_critic_model: str | None = None,
    preferred_synthesizer_model: str | None = None,
) -> dict[str, Any]:
    """Run the 4-agent council and return ChatResponse-compatible fields.

    Returns a dict with keys:
      - ``response``             — synthesized answer text
      - ``agent_run_id``         — unique council run ID
      - ``agent_trace_summary``  — condensed trace dict
      - ``citations``            — merged citations (RAG + council)

    Raises :class:`RuntimeError` if the feature flag is disabled.
    """
    if not is_council_enabled():
        raise RuntimeError(
            "Council mode is not enabled. "
            "Set AGENTIC_V1_ENABLED=true to activate."
        )

    # Build CouncilConfig with any per-role model overrides
    config_kwargs: dict[str, Any] = {"max_rounds": max_agent_iterations}
    if preferred_planner_model:
        config_kwargs["planner_model"] = preferred_planner_model
    if preferred_researcher_model:
        config_kwargs["researcher_model"] = preferred_researcher_model
    if preferred_critic_model:
        config_kwargs["critic_model"] = preferred_critic_model
    if preferred_synthesizer_model:
        config_kwargs["synthesizer_model"] = preferred_synthesizer_model

    config = CouncilConfig(**config_kwargs)

    # Build PreContext from router-supplied values
    pre_context = PreContext(
        original_message=original_message,
        augmented_message=augmented_message,
        rag_chunks=rag_chunks,
        rag_citations=rag_citations,
        mcp_context=mcp_context,
        language=language,
        context_type=context_type,
        custom_prompt=custom_prompt,
    )

    logger.info(
        "[Council] Starting council run — lang=%s, context=%s, max_rounds=%d",
        language,
        context_type,
        config.max_rounds,
    )

    orchestrator = CouncilOrchestrator(config)
    result: CouncilResult = await orchestrator.run(pre_context)

    return _map_result(result, rag_citations)


# ── Internal helpers ───────────────────────────────────────────────────


def _map_result(
    result: CouncilResult,
    rag_citations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Convert ``CouncilResult`` → dict compatible with ``ChatResponse`` fields."""
    trace = result.trace
    decision = result.decision

    trace_summary: dict[str, Any] = {
        "rounds": trace.rounds,
        "agents_used": trace.agents_used,
        "total_llm_calls": trace.total_llm_calls,
        "total_tokens": trace.total_tokens,
        "elapsed_seconds": round(trace.elapsed_seconds, 2),
        "status": result.status.value,
        "approved": decision.approved,
        "exit_reason": decision.exit_reason,
        "final_quality_score": decision.final_quality_score,
    }
    if decision.warnings:
        trace_summary["warnings"] = decision.warnings

    # Merge RAG citations with any council-produced citations
    merged_citations = list(rag_citations) if rag_citations else []
    if result.answer.citations:
        merged_citations.extend(result.answer.citations)

    return {
        "response": result.answer.content,
        "agent_run_id": trace.run_id,
        "agent_trace_summary": trace_summary,
        "citations": merged_citations or None,
    }
