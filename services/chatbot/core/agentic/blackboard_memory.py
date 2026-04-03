"""
Agentic Council — In-memory blackboard adapter
================================================
Default adapter: stores ``AgentRunState`` instances in a plain ``dict``
keyed by ``run_id``.  Perfectly adequate for single-process / single-
request usage and local development.

Thread-safety: a ``threading.Lock`` guards mutations so concurrent
test-runners or threaded ASGI servers won't corrupt state.
"""
from __future__ import annotations

import threading
from datetime import datetime
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


class InMemoryBlackboard:
    """Dict-backed blackboard — the default adapter."""

    def __init__(self) -> None:
        self._runs: dict[str, AgentRunState] = {}
        self._lock = threading.Lock()

    # ── helpers ────────────────────────────────────────────────────

    def _must_get(self, run_id: str) -> AgentRunState:
        state = self._runs.get(run_id)
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
        with self._lock:
            self._runs[state.run_id] = state
        return state

    def get_run(self, run_id: str) -> AgentRunState | None:
        with self._lock:
            return self._runs.get(run_id)

    def update_run_status(self, run_id: str, status: RunStatus) -> None:
        with self._lock:
            self._must_get(run_id).status = status

    def append_planner_tasks(self, run_id: str, output: PlannerOutput) -> None:
        with self._lock:
            self._must_get(run_id).planner_outputs.append(output)

    def append_research_evidence(self, run_id: str, output: ResearcherOutput) -> None:
        with self._lock:
            self._must_get(run_id).researcher_outputs.append(output)

    def append_critic_issues(self, run_id: str, output: CriticOutput) -> None:
        with self._lock:
            self._must_get(run_id).critic_outputs.append(output)

    def set_final_answer(self, run_id: str, output: SynthesizerOutput) -> None:
        with self._lock:
            state = self._must_get(run_id)
            state.synthesizer_output = output
            state.status = RunStatus.completed

    def summarize_trace(self, run_id: str) -> dict:
        with self._lock:
            state = self._must_get(run_id)
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

    # convenience for tests / debugging
    def clear(self) -> None:
        """Remove all stored runs."""
        with self._lock:
            self._runs.clear()

    def __len__(self) -> int:
        return len(self._runs)
