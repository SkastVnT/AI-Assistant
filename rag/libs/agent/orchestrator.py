"""Agentic answer entry point — wraps the full agent loop.

This is the primary integration surface. The standard answer API
remains unchanged; this module provides an alternative path for
complex queries that benefit from multi-step retrieval.

Usage:
    from libs.agent.orchestrator import agentic_answer

    result = await agentic_answer(
        query="Compare our Q3 and Q4 revenue figures and explain trends",
        auth=auth_context,
        llm=llm_provider,
        retrieve_fn=retrieve,
        settings=settings,
    )
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from libs.agent.controller import AgentController
from libs.agent.tools import build_tool_registry
from libs.agent.types import AgentConfig, AgentState, StopReason

if TYPE_CHECKING:
    from libs.auth.context import AuthContext
    from libs.core.providers.base import LLMProvider
    from libs.core.settings import AgentSettings
    from libs.ragops.tracing import SpanCollector

logger = logging.getLogger("rag.agent.orchestrator")


# ═══════════════════════════════════════════════════════════════════════
# Response type
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class AgentResponse:
    """Final response from the agentic pipeline."""

    answer: str
    query: str
    task_id: str
    iterations: int
    tool_calls: int
    stop_reason: str
    turns: list[dict] = field(default_factory=list)
    total_ms: float = 0.0
    trace_id: UUID | None = None

    @property
    def success(self) -> bool:
        return self.stop_reason == StopReason.ANSWERED.value


# ═══════════════════════════════════════════════════════════════════════
# Main entry point
# ═══════════════════════════════════════════════════════════════════════


async def agentic_answer(
    *,
    query: str,
    auth: AuthContext,
    llm: LLMProvider,
    retrieve_fn,
    settings: AgentSettings | None = None,
    validate_fn=None,
    span_collector: SpanCollector | None = None,
) -> AgentResponse:
    """Execute the agentic RAG pipeline for a complex query.

    Parameters
    ----------
    query:
        The user's query.
    auth:
        Authenticated user context (tenant + role + sensitivity).
    llm:
        LLM provider for planning, tool selection, and answer generation.
    retrieve_fn:
        Async retrieval function matching the retriever tool interface.
    settings:
        Optional AgentSettings; uses defaults if None.
    validate_fn:
        Optional async policy validation function for the policy tool.
    span_collector:
        Optional tracing collector for observability.

    Returns
    -------
    AgentResponse with the final answer and execution metadata.
    """
    t0 = time.perf_counter()

    # Build config from settings or use defaults
    config = _settings_to_config(settings) if settings else AgentConfig()

    # Build tool registry
    registry = build_tool_registry(
        retrieve_fn=retrieve_fn,
        validate_fn=validate_fn,
        enable_web=config.enable_web_tool,
        enable_python=config.enable_python_tool,
    )

    # Create and run the controller
    controller = AgentController(
        llm=llm,
        tool_registry=registry,
        config=config,
        span_collector=span_collector,
    )

    state: AgentState = await controller.run(query, auth)

    elapsed_ms = (time.perf_counter() - t0) * 1000

    response = AgentResponse(
        answer=state.answer or "No answer produced.",
        query=query,
        task_id=state.task_id,
        iterations=state.iteration,
        tool_calls=state.total_tool_calls,
        stop_reason=state.stop_reason.value if state.stop_reason else "unknown",
        turns=[t.to_dict() for t in state.turns],
        total_ms=round(elapsed_ms, 1),
    )

    logger.info(
        "agentic_answer: task=%s iterations=%d tools=%d reason=%s ms=%.1f",
        state.task_id, state.iteration, state.total_tool_calls,
        response.stop_reason, elapsed_ms,
    )
    return response


# ═══════════════════════════════════════════════════════════════════════
# Complexity classifier — should this query use agentic path?
# ═══════════════════════════════════════════════════════════════════════


def should_use_agent(query: str, *, auto_route: bool = True) -> bool:
    """Heuristic check whether a query is complex enough for the agent.

    Returns True if the query appears to need multi-step reasoning.
    The standard answer pipeline handles simple factual queries better.
    """
    if not auto_route:
        return False

    q_lower = query.lower()

    # Multi-part indicators
    multi_part_signals = [
        " and ", " compare ", " contrast ", " versus ", " vs ",
        " both ", " each ", " respectively ",
        " step by step", " first ", " then ",
        " relationship between", " how does .* affect",
    ]

    # Analytical indicators
    analytical_signals = [
        "analyze", "analyse", "evaluate", "assess",
        "summarize across", "synthesize", "combine",
        "what are the implications", "pros and cons",
    ]

    signal_count = sum(1 for s in multi_part_signals if s in q_lower)
    signal_count += sum(1 for s in analytical_signals if s in q_lower)

    # Long queries (>100 chars) with signals are likely complex
    if len(query) > 100 and signal_count >= 1:
        return True
    # Short queries need stronger signals
    return signal_count >= 2


# ═══════════════════════════════════════════════════════════════════════
# Config bridge
# ═══════════════════════════════════════════════════════════════════════


def _settings_to_config(settings: AgentSettings) -> AgentConfig:
    """Convert AgentSettings (pydantic) to AgentConfig (dataclass)."""
    return AgentConfig(
        max_iterations=settings.max_iterations,
        max_tokens=settings.max_tokens,
        max_tool_calls=settings.max_tool_calls,
        max_evidence_items=settings.max_evidence_items,
        reflection_threshold=settings.reflection_threshold,
        planning_temperature=settings.planning_temperature,
        answer_temperature=settings.answer_temperature,
        enable_web_tool=settings.enable_web_tool,
        enable_python_tool=settings.enable_python_tool,
    )
