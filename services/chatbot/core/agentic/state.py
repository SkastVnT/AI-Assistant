"""
Agentic Council — Mutable run state
====================================
``AgentRunState`` is the single mutable object that flows through
every agent in a council run.  It accumulates outputs and metadata
so each downstream agent can read what happened upstream.

Design rules:
  • Only the orchestrator mutates the top-level status/round fields.
  • Each agent appends to its own output list and the shared ``steps``.
  • Nothing in this module performs I/O.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from core.agentic.contracts import (
    AgentRole,
    CouncilStep,
    CriticOutput,
    PlannerOutput,
    ResearcherOutput,
    RunStatus,
    SynthesizerOutput,
)


class PreContext(BaseModel):
    """Context gathered *before* the council starts.

    Populated by the router from the standard pre-processing pipeline
    (MCP injection, RAG retrieval, web-search results) so the council
    agents can reference it without re-fetching.
    """
    original_message: str = Field(..., description="Raw user message before augmentation")
    augmented_message: str = Field("", description="Message after MCP/RAG/tool injection")
    rag_chunks: list[dict[str, Any]] = Field(default_factory=list)
    rag_citations: list[dict[str, Any]] = Field(default_factory=list)
    web_search_context: str = Field("", description="Pre-fetched web search results")
    mcp_context: str = Field("", description="Pre-injected MCP file content")
    language: str = "vi"
    context_type: str = "casual"
    custom_prompt: str = ""


class AgentRunState(BaseModel):
    """Mutable state bag for one council run.

    Created once by the orchestrator, then passed by reference through
    Planner → Researcher → Critic (→ loop) → Synthesizer.
    """
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    status: RunStatus = RunStatus.pending
    current_round: int = 0
    max_rounds: int = 2

    # Pre-processing context (immutable once set)
    pre_context: PreContext | None = None

    # Accumulated agent outputs — one entry per round
    planner_outputs: list[PlannerOutput] = Field(default_factory=list)
    researcher_outputs: list[ResearcherOutput] = Field(default_factory=list)
    critic_outputs: list[CriticOutput] = Field(default_factory=list)
    synthesizer_output: SynthesizerOutput | None = None

    # Observability trace (each agent appends here)
    steps: list[CouncilStep] = Field(default_factory=list)

    # Cumulative counters
    total_llm_calls: int = 0
    total_tokens: int = 0
    started_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    # ── Convenience helpers ────────────────────────────────────────

    @property
    def latest_plan(self) -> PlannerOutput | None:
        """Most recent Planner output, or *None*."""
        return self.planner_outputs[-1] if self.planner_outputs else None

    @property
    def latest_research(self) -> ResearcherOutput | None:
        """Most recent Researcher output, or *None*."""
        return self.researcher_outputs[-1] if self.researcher_outputs else None

    @property
    def latest_critique(self) -> CriticOutput | None:
        """Most recent Critic output, or *None*."""
        return self.critic_outputs[-1] if self.critic_outputs else None

    def record_step(
        self,
        agent: AgentRole,
        *,
        input_summary: str = "",
        output_summary: str = "",
        tool_calls: list[str] | None = None,
        tokens: int = 0,
        elapsed_ms: int = 0,
    ) -> CouncilStep:
        """Append a ``CouncilStep`` and update cumulative counters."""
        step = CouncilStep(
            agent=agent,
            round=self.current_round,
            input_summary=input_summary[:500],
            output_summary=output_summary[:500],
            tool_calls=tool_calls,
            tokens=tokens,
            elapsed_ms=elapsed_ms,
        )
        self.steps.append(step)
        self.total_llm_calls += 1
        self.total_tokens += tokens
        return step
