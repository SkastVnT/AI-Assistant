"""
xAI Native Multi-Agent — Typed contracts
==========================================
Data structures for the xAI Responses API integration.
Pure data — no I/O, no business logic.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────

class ReasoningEffort(str, Enum):
    """Maps to xAI ``reasoning.effort`` / agent_count configuration.

    low/medium  → 4 agents
    high        → 16 agents
    """
    low = "low"
    medium = "medium"
    high = "high"


class XaiNativeStatus(str, Enum):
    """Lifecycle status of a native xAI call."""
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


# ── Configuration ──────────────────────────────────────────────────────

class XaiNativeConfig(BaseModel):
    """Runtime configuration for a single xAI native research call."""
    model: str = Field(
        "grok-4.20-multi-agent",
        description="xAI model to use (must support Responses API)",
    )
    reasoning_effort: ReasoningEffort = Field(
        ReasoningEffort.high,
        description="Reasoning effort: low/medium → 4 agents, high → 16 agents",
    )
    enable_web_search: bool = Field(
        True, description="Enable server-side web_search tool",
    )
    enable_x_search: bool = Field(
        False, description="Enable server-side x_search (Twitter/X) tool",
    )
    timeout_seconds: int = Field(
        300,
        ge=30,
        le=600,
        description="HTTP request timeout in seconds (multi-agent can be slow)",
    )


# ── Response models ────────────────────────────────────────────────────

class XaiUsage(BaseModel):
    """Token usage from xAI Responses API."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    reasoning_tokens: int = 0
    num_sources_used: int = 0
    num_server_side_tools_used: int = 0


class XaiAnnotation(BaseModel):
    """A citation/annotation from xAI's response."""
    type: str = ""
    url: str | None = None
    title: str | None = None
    start_index: int | None = None
    end_index: int | None = None


class XaiNativeResult(BaseModel):
    """Normalized result from a single xAI Responses API call."""
    response_id: str = ""
    status: XaiNativeStatus = XaiNativeStatus.completed
    content: str = ""
    model: str = ""
    usage: XaiUsage = Field(default_factory=XaiUsage)
    annotations: list[XaiAnnotation] = Field(default_factory=list)
    elapsed_seconds: float = 0.0
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.status == XaiNativeStatus.completed and not self.error

    def to_trace_summary(self) -> dict[str, Any]:
        """Return safe metadata (no hidden reasoning or internal state)."""
        return {
            "response_id": self.response_id,
            "model": self.model,
            "status": self.status.value,
            "reasoning_effort": None,  # set by caller
            "total_tokens": self.usage.total_tokens,
            "reasoning_tokens": self.usage.reasoning_tokens,
            "sources_used": self.usage.num_sources_used,
            "server_tool_calls": self.usage.num_server_side_tools_used,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
        }
