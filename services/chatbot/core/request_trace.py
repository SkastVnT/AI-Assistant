from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RequestTrace:
    request_id: str
    conversation_id: str = ""
    message_id: str = ""
    selected_pipeline: str = "normal_chat"
    selected_model: str = ""
    router_decision: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    agent_steps: list[dict[str, Any]] = field(default_factory=list)
    fallback_chain: list[str] = field(default_factory=list)
    latency_ms: int | None = None
    error: str | None = None
    _started_at: float = field(default_factory=time.time, repr=False)

    def mark_tool(self, name: str, status: str = "started", **extra: Any) -> None:
        self.tool_calls.append({"name": name, "status": status, **extra})

    def mark_step(self, name: str, status: str = "done", **extra: Any) -> None:
        self.agent_steps.append({"step": name, "status": status, **extra})

    def finish(self, error: str | None = None) -> None:
        self.error = error
        self.latency_ms = int((time.time() - self._started_at) * 1000)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("_started_at", None)
        return payload


class RequestTraceStore:
    def __init__(self, max_items: int = 1000) -> None:
        self.max_items = max_items
        self._items: list[dict[str, Any]] = []

    def save(self, trace: RequestTrace) -> bool:
        try:
            self._items.append(trace.to_dict())
            if len(self._items) > self.max_items:
                self._items = self._items[-self.max_items :]
            return True
        except Exception as exc:
            logger.warning("trace store save failed: %s", exc)
            return False

    def latest(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._items[-limit:]


TRACE_STORE = RequestTraceStore()
