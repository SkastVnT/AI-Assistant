"""
Agentic Council — Typed contracts
==================================
All shared data structures for the 4-agent internal orchestration layer.

Design goals:
  • Pure data — no business logic, no I/O.
  • Compatible with Pydantic v2 *and* plain dataclass usage.
  • Every field is typed and documented so downstream agents, the
    orchestrator, and the FastAPI layer can rely on them without guessing.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────

class AgentMode(str, Enum):
    """Top-level orchestration mode sent by the client.

    * ``off``      — default single-agent path (current behaviour).
    * ``council``  — 4-agent internal orchestration.
    * ``grok_native_research`` — xAI native multi-agent research via Responses API.
    * ``xai_native`` — (future) native xAI multi-agent; **not implemented**.
    """
    off = "off"
    council = "council"
    grok_native_research = "grok_native_research"
    # xai_native = "xai_native"  # placeholder — uncomment when ready


class AgentStrategy(str, Enum):
    """Execution strategy for the council orchestrator.

    * ``sequential``          — Planner → Researcher → Critic (serial).
    * ``parallel_research``   — Researcher tasks run concurrently.
    """
    sequential = "sequential"
    parallel_research = "parallel_research"


class AgentRole(str, Enum):
    """Named role for each council participant."""
    planner = "planner"
    researcher = "researcher"
    critic = "critic"
    synthesizer = "synthesizer"
    # Future roles can be added here without breaking existing code.


class RunStatus(str, Enum):
    """Lifecycle status of a council run."""
    pending = "pending"
    planning = "planning"
    researching = "researching"
    critiquing = "critiquing"
    synthesizing = "synthesizing"
    completed = "completed"
    failed = "failed"


# ── Fine-grained data objects ──────────────────────────────────────────

class TaskNode(BaseModel):
    """A single sub-task produced by the Planner.

    The Planner decomposes the user's question into an ordered list of
    ``TaskNode`` items.  Each node may suggest tools for the Researcher.
    """
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    question: str = Field(..., description="Sub-question or action to investigate")
    suggested_tools: list[str] = Field(
        default_factory=list,
        description="Tool hints for the Researcher: 'web_search', 'rag_query', 'mcp_read'",
    )
    priority: int = Field(1, ge=1, le=5, description="1 = highest priority")
    depends_on: list[str] = Field(
        default_factory=list,
        description="IDs of TaskNodes that must be resolved first",
    )


class EvidenceItem(BaseModel):
    """A single piece of evidence gathered by the Researcher."""
    source: str = Field(..., description="Where this came from: 'web', 'rag', 'mcp', 'llm'")
    content: str = Field(..., description="The actual evidence text")
    url: str | None = Field(None, description="Source URL if applicable")
    relevance: float = Field(1.0, ge=0.0, le=1.0, description="Relevance score 0-1")
    task_id: str | None = Field(None, description="TaskNode.id this evidence addresses")


class CritiqueIssue(BaseModel):
    """A single issue raised by the Critic."""
    severity: str = Field("medium", description="'low', 'medium', 'high'")
    description: str = Field(..., description="What is wrong or missing")
    suggestion: str = Field("", description="How to fix it")
    task_id: str | None = Field(None, description="TaskNode.id this issue relates to")


class FinalAnswer(BaseModel):
    """The synthesized output produced by the Synthesizer."""
    content: str = Field(..., description="Markdown-formatted final answer")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Self-assessed confidence")
    key_points: list[str] = Field(default_factory=list, description="Bullet-point key takeaways")
    citations: list[dict[str, Any]] = Field(default_factory=list, description="Source citations")


# ── Per-agent output wrappers ──────────────────────────────────────────

class PlannerOutput(BaseModel):
    """Structured output from the Planner agent."""
    approach: str = Field("", description="High-level approach description")
    tasks: list[TaskNode] = Field(default_factory=list)
    estimated_complexity: int = Field(1, ge=1, le=10)


class ResearcherOutput(BaseModel):
    """Structured output from the Researcher agent."""
    evidence: list[EvidenceItem] = Field(default_factory=list)
    summary: str = Field("", description="Prose summary of all findings")
    tools_used: list[str] = Field(default_factory=list)


class RetryTarget(str, Enum):
    """Which stage(s) the Critic wants re-run on a ``needs_work`` verdict."""
    researcher = "researcher"
    synthesizer = "synthesizer"
    both = "both"


class CriticOutput(BaseModel):
    """Structured output from the Critic agent."""
    quality_score: int = Field(5, ge=1, le=10, description="Overall quality 1-10")
    issues: list[CritiqueIssue] = Field(default_factory=list)
    verdict: str = Field(
        "needs_work",
        description="'pass' — good enough for synthesis, 'needs_work' — another round needed",
    )
    retry_target: RetryTarget = Field(
        RetryTarget.both,
        description="Which stage to re-run: 'researcher', 'synthesizer', or 'both'",
    )
    focused_feedback: str = Field(
        "",
        description="Machine-readable instruction for the retry stage(s)",
    )


class SynthesizerOutput(BaseModel):
    """Structured output from the Synthesizer agent."""
    answer: FinalAnswer


class FinalDecision(BaseModel):
    """Summary attached to every ``CouncilResult`` — tells the caller
    what the critic loop concluded regardless of whether the answer
    was approved or the budget was exhausted.
    """
    approved: bool = Field(False, description="True if Critic gave 'pass' verdict")
    iterations_used: int = Field(1, ge=1)
    iterations_max: int = Field(2, ge=1)
    final_quality_score: int = Field(5, ge=1, le=10)
    exit_reason: str = Field(
        "first_pass",
        description=(
            "'approved' — critic passed; "
            "'quality_threshold' — score met threshold; "
            "'budget_exhausted' — max iterations reached; "
            "'circuit_breaker' — no quality improvement detected; "
            "'error' — pipeline failure"
        ),
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Unresolved issues carried into the final answer",
    )


# ── Trace / observability ──────────────────────────────────────────────

class CouncilStep(BaseModel):
    """One step in the council execution trace (sent via SSE)."""
    agent: AgentRole
    round: int = 1
    input_summary: str = Field("", description="Truncated input for display")
    output_summary: str = Field("", description="Truncated output for display")
    tool_calls: list[str] | None = None
    tokens: int = 0
    elapsed_ms: int = 0


class CouncilTrace(BaseModel):
    """Full trace of a council run (attached to ChatResponse)."""
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    rounds: int = 0
    agents_used: list[str] = Field(default_factory=list)
    total_llm_calls: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0
    steps: list[CouncilStep] = Field(default_factory=list)


class CouncilResult(BaseModel):
    """Final return value from the orchestrator."""
    answer: FinalAnswer
    trace: CouncilTrace
    decision: FinalDecision = Field(default_factory=FinalDecision)
    status: RunStatus = RunStatus.completed
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
