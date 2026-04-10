"""Core types for the agentic RAG layer.

Defines the agent state machine, tool call/result records, turn history,
and stop conditions. All types are plain dataclasses — no framework deps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

# ═══════════════════════════════════════════════════════════════════════
# Agent State Machine
# ═══════════════════════════════════════════════════════════════════════


class AgentPhase(Enum):
    """Phases in the agentic loop."""

    PLAN = "plan"           # Decompose the task into sub-goals
    ACT = "act"             # Select and execute a tool
    OBSERVE = "observe"     # Process the tool result
    REFLECT = "reflect"     # Self-check: is evidence sufficient?
    ANSWER = "answer"       # Synthesise final grounded answer
    DONE = "done"           # Terminal state — success
    ERROR = "error"         # Terminal state — failure / limit hit


class StopReason(Enum):
    """Why the agent loop terminated."""

    ANSWERED = "answered"                   # Agent produced a final answer
    MAX_ITERATIONS = "max_iterations"       # Hit iteration budget
    MAX_TOKENS = "max_tokens"               # Token budget exhausted
    NO_TOOLS_SELECTED = "no_tools_selected" # Planner couldn't pick a tool
    POLICY_BLOCKED = "policy_blocked"       # Safety check rejected the task
    ERROR = "error"                         # Unrecoverable error


# ═══════════════════════════════════════════════════════════════════════
# Tool call / result records
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ToolCall:
    """A request to invoke a tool."""

    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = field(default_factory=lambda: uuid4().hex[:12])
    rationale: str = ""  # Why the planner chose this tool


@dataclass
class ToolResult:
    """The result of executing a ToolCall."""

    call_id: str
    tool_name: str
    output: str = ""            # Serialised result (for the LLM context)
    success: bool = True
    error: str | None = None
    metadata: dict = field(default_factory=dict)  # timing, token counts, etc.


# ═══════════════════════════════════════════════════════════════════════
# Turn record (one iteration of the loop)
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class Turn:
    """One complete iteration through the agent loop.

    Each turn may produce a plan, a tool call, a tool result,
    and a reflection. Turns accumulate in the agent state.
    """

    index: int
    phase: AgentPhase
    plan: str | None = None
    tool_call: ToolCall | None = None
    tool_result: ToolResult | None = None
    reflection: str | None = None
    is_final: bool = False

    def to_dict(self) -> dict:
        d: dict = {"index": self.index, "phase": self.phase.value}
        if self.plan:
            d["plan"] = self.plan
        if self.tool_call:
            d["tool_call"] = {
                "tool": self.tool_call.tool_name,
                "args": self.tool_call.arguments,
                "rationale": self.tool_call.rationale,
            }
        if self.tool_result:
            d["tool_result"] = {
                "tool": self.tool_result.tool_name,
                "output": self.tool_result.output[:500],
                "success": self.tool_result.success,
            }
        if self.reflection:
            d["reflection"] = self.reflection
        return d


# ═══════════════════════════════════════════════════════════════════════
# Agent state — accumulates across turns
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class AgentState:
    """Complete state of an agent execution.

    Passed through every phase; mutated by the controller.
    """

    task_id: str = field(default_factory=lambda: uuid4().hex)
    query: str = ""
    tenant_id: UUID | None = None
    user_id: UUID | None = None

    # Phase tracking
    phase: AgentPhase = AgentPhase.PLAN
    iteration: int = 0

    # Accumulated history
    turns: list[Turn] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)  # collected evidence snippets
    sub_queries: list[str] = field(default_factory=list)  # decomposed sub-questions

    # Final output
    answer: str | None = None
    stop_reason: StopReason | None = None

    # Budget tracking
    total_tokens_used: int = 0
    total_tool_calls: int = 0

    def is_terminal(self) -> bool:
        return self.phase in (AgentPhase.DONE, AgentPhase.ERROR)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "query": self.query,
            "phase": self.phase.value,
            "iteration": self.iteration,
            "turns": [t.to_dict() for t in self.turns],
            "evidence_count": len(self.evidence),
            "answer": self.answer,
            "stop_reason": self.stop_reason.value if self.stop_reason else None,
            "total_tool_calls": self.total_tool_calls,
            "total_tokens_used": self.total_tokens_used,
        }


# ═══════════════════════════════════════════════════════════════════════
# Agent configuration
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class AgentConfig:
    """Runtime configuration for the agent controller.

    These are derived from AgentSettings but bundled for easy passing.
    """

    max_iterations: int = 6
    max_tokens: int = 32000
    max_tool_calls: int = 10
    max_evidence_items: int = 20
    reflection_threshold: float = 0.7  # Confidence to stop iterating
    planning_temperature: float = 0.2
    answer_temperature: float = 0.1
    enable_web_tool: bool = False
    enable_python_tool: bool = False
