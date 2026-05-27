"""Fail-safe central trace helper for chat requests."""

from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    agent: str
    status: str
    latency_ms: int | None = None
    tools_called: list[str] = field(default_factory=list)
    score: float | None = None


@dataclass
class RequestTrace:
    conversation_id: str
    message_id: str
    user_input: str
    selected_pipeline: str | None = None
    selected_model: str | None = None
    router_confidence: float | None = None
    agent_steps: list[AgentStep] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    total_latency_ms: int | None = None
    error: str | None = None
    fallback_chain: list[str] = field(default_factory=list)
    _started_at: float = field(default_factory=time.time, repr=False)

    def finish(self, error: str | None = None) -> None:
        self.error = error
        self.total_latency_ms = int((time.time() - self._started_at) * 1000)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("_started_at", None)
        return payload


class InMemoryTraceStore:
    def __init__(self, max_items: int = 1000) -> None:
        self.max_items = max_items
        self._items: list[dict[str, Any]] = []

    def save(self, trace: RequestTrace) -> bool:
        try:
            self._items.append(trace.to_dict())
            if len(self._items) > self.max_items:
                self._items = self._items[-self.max_items :]
            return True
        except Exception as exc:  # fail-safe by design
            logger.warning("trace save failed: %s", exc)
            return False

    def latest(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._items[-limit:]
