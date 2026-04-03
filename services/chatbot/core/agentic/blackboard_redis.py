"""
Agentic Council — Redis-backed blackboard adapter
===================================================
Optional adapter that serialises ``AgentRunState`` into a Redis key.
Import is lazy (only when ``create_blackboard("redis")`` is called) so
local development never requires a running Redis instance.

Each run is stored as a single JSON blob under the key
``council:run:{run_id}`` with a configurable TTL.

Environment variables
---------------------
``AGENT_BLACKBOARD_REDIS_URL``
    Full Redis URL.  Default: ``redis://localhost:6379/1``.

``AGENT_BLACKBOARD_TTL``
    Key TTL in seconds.  Default: ``3600`` (1 hour).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from core.agentic.config import CouncilConfig
from core.agentic.contracts import (
    CriticOutput,
    PlannerOutput,
    ResearcherOutput,
    RunStatus,
    SynthesizerOutput,
)
from core.agentic.state import AgentRunState, PreContext

logger = logging.getLogger(__name__)

_KEY_PREFIX = "council:run:"


class RedisBlackboard:
    """Redis-backed blackboard adapter.

    Parameters
    ----------
    redis_url:
        Full Redis URL (e.g. ``redis://localhost:6379/1``).
    ttl:
        Key TTL in seconds.  Set to ``0`` to disable expiry.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/1", ttl: int = 3600) -> None:
        try:
            import redis as _redis_lib  # noqa: F811
        except ImportError as exc:
            raise ImportError(
                "The 'redis' package is required for RedisBlackboard. "
                "Install it with:  pip install redis"
            ) from exc

        self._client = _redis_lib.Redis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl
        logger.info("RedisBlackboard connected to %s (ttl=%ds)", redis_url, ttl)

    # ── internal helpers ───────────────────────────────────────────

    def _key(self, run_id: str) -> str:
        return f"{_KEY_PREFIX}{run_id}"

    def _save(self, state: AgentRunState) -> None:
        key = self._key(state.run_id)
        payload = state.model_dump_json()
        if self._ttl > 0:
            self._client.setex(key, self._ttl, payload)
        else:
            self._client.set(key, payload)

    def _load(self, run_id: str) -> AgentRunState | None:
        raw = self._client.get(self._key(run_id))
        if raw is None:
            return None
        return AgentRunState.model_validate_json(raw)

    def _must_load(self, run_id: str) -> AgentRunState:
        state = self._load(run_id)
        if state is None:
            raise KeyError(f"No run with id={run_id!r}")
        return state

    # ── public API (matches BlackboardStore protocol) ─────────────

    def create_run(
        self,
        pre_context: PreContext,
        config: CouncilConfig | None = None,
    ) -> AgentRunState:
        cfg = config or CouncilConfig()
        state = AgentRunState(
            pre_context=pre_context,
            max_rounds=cfg.max_rounds,
        )
        self._save(state)
        return state

    def get_run(self, run_id: str) -> AgentRunState | None:
        return self._load(run_id)

    def update_run_status(self, run_id: str, status: RunStatus) -> None:
        state = self._must_load(run_id)
        state.status = status
        self._save(state)

    def append_planner_tasks(self, run_id: str, output: PlannerOutput) -> None:
        state = self._must_load(run_id)
        state.planner_outputs.append(output)
        self._save(state)

    def append_research_evidence(self, run_id: str, output: ResearcherOutput) -> None:
        state = self._must_load(run_id)
        state.researcher_outputs.append(output)
        self._save(state)

    def append_critic_issues(self, run_id: str, output: CriticOutput) -> None:
        state = self._must_load(run_id)
        state.critic_outputs.append(output)
        self._save(state)

    def set_final_answer(self, run_id: str, output: SynthesizerOutput) -> None:
        state = self._must_load(run_id)
        state.synthesizer_output = output
        state.status = RunStatus.completed
        self._save(state)

    def summarize_trace(self, run_id: str) -> dict:
        state = self._must_load(run_id)
        # Reuse the same logic as InMemoryBlackboard
        return {
            "run_id": state.run_id,
            "status": state.status.value,
            "rounds": state.current_round,
            "total_llm_calls": state.total_llm_calls,
            "total_tokens": state.total_tokens,
            "planner_tasks": sum(
                len(p.tasks) for p in state.planner_outputs
            ),
            "evidence_items": sum(
                len(r.evidence) for r in state.researcher_outputs
            ),
            "critic_issues": sum(
                len(c.issues) for c in state.critic_outputs
            ),
            "has_final_answer": state.synthesizer_output is not None,
            "steps": [
                {
                    "agent": s.agent.value,
                    "round": s.round,
                    "tokens": s.tokens,
                    "elapsed_ms": s.elapsed_ms,
                }
                for s in state.steps
            ],
            "started_at": state.started_at,
        }
