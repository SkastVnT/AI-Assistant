"""
Agentic Council — Blackboard protocol
=======================================
Defines the abstract interface for run-state persistence.

Two concrete adapters ship out-of-the-box:

* ``InMemoryBlackboard`` — dict-backed, zero dependencies (default).
* ``RedisBlackboard``    — optional, created via ``create_blackboard("redis")``.

Every method is synchronous so request-scoped code can call it without
``await``, but the public surface is kept deliberately thin so a future
async variant can be layered on top.
"""
from __future__ import annotations

import logging
import os
from typing import Protocol, runtime_checkable

from core.agentic.config import CouncilConfig
from core.agentic.contracts import (
    CouncilTrace,
    CriticOutput,
    PlannerOutput,
    ResearcherOutput,
    RunStatus,
    SynthesizerOutput,
)
from core.agentic.state import AgentRunState, PreContext

logger = logging.getLogger(__name__)


# ── Protocol (structural typing) ──────────────────────────────────────

@runtime_checkable
class BlackboardStore(Protocol):
    """Abstract interface every blackboard adapter must satisfy."""

    def create_run(
        self,
        pre_context: PreContext,
        config: CouncilConfig | None = None,
    ) -> AgentRunState: ...

    def get_run(self, run_id: str) -> AgentRunState | None: ...

    def update_run_status(self, run_id: str, status: RunStatus) -> None: ...

    def append_planner_tasks(self, run_id: str, output: PlannerOutput) -> None: ...

    def append_research_evidence(self, run_id: str, output: ResearcherOutput) -> None: ...

    def append_critic_issues(self, run_id: str, output: CriticOutput) -> None: ...

    def set_final_answer(self, run_id: str, output: SynthesizerOutput) -> None: ...

    def summarize_trace(self, run_id: str) -> dict: ...


# ── Factory ────────────────────────────────────────────────────────────

def create_blackboard(backend: str | None = None) -> BlackboardStore:
    """Instantiate the requested blackboard adapter.

    Parameters
    ----------
    backend:
        ``"memory"`` (default) or ``"redis"``.
        When *None* the env-var ``AGENT_BLACKBOARD_BACKEND`` is consulted,
        falling back to ``"memory"``.

    Environment variables (Redis only):
        ``AGENT_BLACKBOARD_REDIS_URL`` — full Redis URL
            (default ``redis://localhost:6379/1``).
        ``AGENT_BLACKBOARD_TTL`` — key TTL in seconds (default ``3600``).
    """
    backend = (backend or os.getenv("AGENT_BLACKBOARD_BACKEND", "memory")).lower()

    if backend == "redis":
        from core.agentic.blackboard_redis import RedisBlackboard  # lazy

        url = os.getenv("AGENT_BLACKBOARD_REDIS_URL", "redis://localhost:6379/1")
        ttl = int(os.getenv("AGENT_BLACKBOARD_TTL", "3600"))
        logger.info("Blackboard backend: redis (%s, ttl=%ds)", url, ttl)
        return RedisBlackboard(redis_url=url, ttl=ttl)

    if backend != "memory":
        logger.warning("Unknown blackboard backend %r — falling back to memory", backend)

    from core.agentic.blackboard_memory import InMemoryBlackboard  # lazy

    logger.info("Blackboard backend: in-memory")
    return InMemoryBlackboard()
