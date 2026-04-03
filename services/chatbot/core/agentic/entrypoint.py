"""
Agentic Council — Router entry point
======================================
Single function called by ``fastapi_app/routers/chat.py`` (and stream.py)
when ``agent_mode == "council"``.

Responsibilities:
  • Build ``CouncilConfig`` + ``PreContext`` from router-level parameters.
  • Run the orchestrator.
  • Convert ``CouncilResult`` → ``ChatResponse``-compatible dict.

This module keeps the router diff small by encapsulating all council
setup and teardown.  The router only needs::

    from core.agentic.entrypoint import run_council
    result = await run_council(...)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, AsyncGenerator

from core.agentic.config import CouncilConfig
from core.agentic.events import CouncilEventEmitter
from core.agentic.orchestrator import CouncilOrchestrator
from core.agentic.state import PreContext

logger = logging.getLogger(__name__)


# ── Feature flag ───────────────────────────────────────────────────────

AGENTIC_V1_ENABLED: bool = os.environ.get("AGENTIC_V1_ENABLED", "false").lower() in (
    "1", "true", "yes",
)
"""Kill-switch for the council mode.  Set ``AGENTIC_V1_ENABLED=true``
in the environment to enable it.  When disabled, ``run_council()``
returns a graceful error dict instead of running the pipeline."""


def is_council_enabled() -> bool:
    """Check if the council feature flag is active."""
    return AGENTIC_V1_ENABLED


# ── Public entry point ─────────────────────────────────────────────────


async def run_council(
    *,
    # Original message (before all augmentation)
    original_message: str,
    # Message after file/MCP/RAG augmentation
    augmented_message: str,
    # Standard request parameters
    language: str = "vi",
    context_type: str = "casual",
    custom_prompt: str = "",
    # RAG results (already retrieved by the router)
    rag_chunks: list[dict[str, Any]] | None = None,
    rag_citations: list[dict[str, Any]] | None = None,
    # MCP context (already injected by the router)
    mcp_context: str = "",
    # Council-specific parameters (from ChatRequest)
    max_agent_iterations: int = 2,
    preferred_planner_model: str | None = None,
    preferred_researcher_model: str | None = None,
    preferred_critic_model: str | None = None,
    preferred_synthesizer_model: str | None = None,
) -> dict[str, Any]:
    """Run the 4-agent council and return a response dict.

    Returns a dict with keys compatible with ``ChatResponse``:
      - ``response``: final answer text
      - ``model``: "council"
      - ``context``: original context_type
      - ``agent_run_id``: unique run ID
      - ``agent_trace_summary``: condensed trace dict
      - ``citations``: RAG citations (passed through)
      - ``thinking_process``: summary of critic loop
      - ``deep_thinking``: True (council always does deep reasoning)
    """
    if not is_council_enabled():
        logger.debug("[Council] Feature flag AGENTIC_V1_ENABLED is off — returning disabled response")
        return _disabled_response(context_type, rag_citations)

    config = _build_config(
        max_agent_iterations=max_agent_iterations,
        preferred_planner_model=preferred_planner_model,
        preferred_researcher_model=preferred_researcher_model,
        preferred_critic_model=preferred_critic_model,
        preferred_synthesizer_model=preferred_synthesizer_model,
    )
    pre = _build_pre_context(
        original_message=original_message,
        augmented_message=augmented_message,
        rag_chunks=rag_chunks,
        rag_citations=rag_citations,
        mcp_context=mcp_context,
        language=language,
        context_type=context_type,
        custom_prompt=custom_prompt,
    )

    # Run the orchestrator (no emitter for non-streaming)
    logger.info(
        "[Council] run_council | max_rounds=%d models: planner=%s researcher=%s critic=%s synth=%s",
        config.max_rounds, config.planner_model, config.researcher_model,
        config.critic_model, config.synthesizer_model,
    )
    orch = CouncilOrchestrator(config)
    result = await orch.run(pre)

    logger.info(
        "[Council] run_council | run_id=%s exit=%s quality=%d",
        result.trace.run_id, result.decision.exit_reason,
        result.decision.final_quality_score,
    )
    return _build_response_dict(result, context_type, rag_citations)


def _disabled_response(
    context_type: str,
    rag_citations: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Return a graceful error when the feature flag is off."""
    return {
        "response": (
            "Council mode is not enabled on this server. "
            "Set AGENTIC_V1_ENABLED=true to activate it."
        ),
        "model": "council",
        "context": context_type,
        "deep_thinking": False,
        "thinking_process": None,
        "citations": rag_citations,
        "agent_run_id": None,
        "agent_trace_summary": None,
    }


# ── Shared builders ────────────────────────────────────────────────────

def _build_config(
    *,
    max_agent_iterations: int,
    preferred_planner_model: str | None,
    preferred_researcher_model: str | None,
    preferred_critic_model: str | None,
    preferred_synthesizer_model: str | None,
) -> CouncilConfig:
    default_config = CouncilConfig()
    return CouncilConfig(
        max_rounds=max_agent_iterations,
        planner_model=preferred_planner_model or default_config.planner_model,
        researcher_model=preferred_researcher_model or default_config.researcher_model,
        critic_model=preferred_critic_model or default_config.critic_model,
        synthesizer_model=preferred_synthesizer_model or default_config.synthesizer_model,
    )


def _build_pre_context(
    *,
    original_message: str,
    augmented_message: str,
    rag_chunks: list[dict[str, Any]] | None,
    rag_citations: list[dict[str, Any]] | None,
    mcp_context: str,
    language: str,
    context_type: str,
    custom_prompt: str,
) -> PreContext:
    return PreContext(
        original_message=original_message,
        augmented_message=augmented_message,
        rag_chunks=rag_chunks or [],
        rag_citations=rag_citations or [],
        mcp_context=mcp_context,
        language=language,
        context_type=context_type,
        custom_prompt=custom_prompt,
    )


def _build_response_dict(result, context_type: str, rag_citations) -> dict[str, Any]:
    """Convert a ``CouncilResult`` into a ``ChatResponse``-compatible dict."""
    trace_summary = {
        "rounds": result.trace.rounds,
        "agents_used": result.trace.agents_used,
        "total_llm_calls": result.trace.total_llm_calls,
        "total_tokens": result.trace.total_tokens,
        "elapsed_seconds": result.trace.elapsed_seconds,
        "decision": result.decision.model_dump(),
    }
    decision = result.decision
    thinking_lines = [
        f"Council completed in {result.trace.rounds} round(s), "
        f"{result.trace.total_llm_calls} LLM calls, "
        f"{result.trace.elapsed_seconds:.1f}s.",
        f"Exit reason: {decision.exit_reason}.",
        f"Quality score: {decision.final_quality_score}/10.",
    ]
    if decision.warnings:
        thinking_lines.append(f"Warnings: {'; '.join(decision.warnings[:3])}")

    return {
        "response": result.answer.content,
        "model": "council",
        "context": context_type,
        "deep_thinking": True,
        "thinking_process": "\n".join(thinking_lines),
        "citations": rag_citations,
        "agent_run_id": result.trace.run_id,
        "agent_trace_summary": trace_summary,
    }


# ── Streaming entry point ─────────────────────────────────────────────

def _sse(event: str, data: dict | str) -> str:
    """Format a single Server-Sent Event line."""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


async def run_council_stream(
    *,
    original_message: str,
    augmented_message: str,
    language: str = "vi",
    context_type: str = "casual",
    custom_prompt: str = "",
    rag_chunks: list[dict[str, Any]] | None = None,
    rag_citations: list[dict[str, Any]] | None = None,
    mcp_context: str = "",
    max_agent_iterations: int = 2,
    preferred_planner_model: str | None = None,
    preferred_researcher_model: str | None = None,
    preferred_critic_model: str | None = None,
    preferred_synthesizer_model: str | None = None,
) -> AsyncGenerator[str, None]:
    """Run the council pipeline and yield SSE-formatted strings.

    Event sequence::

        event: council_event   (one per stage transition)
        event: council_result  (final ChatResponse-compatible dict)

    If the feature flag is off, yields a single ``council_result``
    with the disabled message.
    """
    if not is_council_enabled():
        yield _sse("council_result", _disabled_response(context_type, rag_citations))
        return

    config = _build_config(
        max_agent_iterations=max_agent_iterations,
        preferred_planner_model=preferred_planner_model,
        preferred_researcher_model=preferred_researcher_model,
        preferred_critic_model=preferred_critic_model,
        preferred_synthesizer_model=preferred_synthesizer_model,
    )
    pre = _build_pre_context(
        original_message=original_message,
        augmented_message=augmented_message,
        rag_chunks=rag_chunks,
        rag_citations=rag_citations,
        mcp_context=mcp_context,
        language=language,
        context_type=context_type,
        custom_prompt=custom_prompt,
    )

    emitter = CouncilEventEmitter(run_id="pending")
    orch = CouncilOrchestrator(config, emitter=emitter)

    # Run orchestrator in a background task; consume events in foreground
    result_holder: list = []
    error_holder: list = []

    async def _run_pipeline():
        try:
            result = await orch.run(pre)
            result_holder.append(result)
        except Exception as exc:
            error_holder.append(exc)
        finally:
            await emitter.close()

    task = asyncio.ensure_future(_run_pipeline())

    # The emitter run_id is set to "pending" until the orchestrator
    # creates its state (which sets run_id).  We'll update it from the
    # first event.
    async for event in emitter.events():
        yield _sse("council_event", event.model_dump())

    # Wait for the task to finish (should already be done)
    await task

    if error_holder:
        yield _sse("council_error", {"error": str(error_holder[0])})
        return

    if result_holder:
        response_dict = _build_response_dict(result_holder[0], context_type, rag_citations)
        yield _sse("council_result", response_dict)
