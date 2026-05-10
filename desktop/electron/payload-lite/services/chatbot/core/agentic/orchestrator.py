"""
Agentic Council — Orchestrator
================================
Runs the Planner → Researcher → Synthesizer → Critic loop with
selective retry and a circuit breaker.

State machine
~~~~~~~~~~~~~
::

    ┌─── Plan ───► Research ───► Synthesize ───► Critic ──┐
    │                                                       │
    │  verdict == "pass"  ──────────────────► Finalize      │
    │  quality >= threshold ────────────────► Finalize      │
    │  iteration budget exhausted ─────────► Finalize+warn  │
    │  no quality improvement (breaker) ───► Finalize+warn  │
    │  needs_work + budget remains ────────► Selective Retry │
    │                                                       │
    │  retry_target == researcher  → re-run Research + Synth│
    │  retry_target == synthesizer → re-run Synth only      │
    │  retry_target == both        → re-run Research + Synth│
    └───────────────────────────────── (loop) ◄─────────────┘

Integration:
  • Called from ``fastapi_app/routers/stream.py`` (and ``chat.py``)
    when ``agent_mode == "council"``.
  • Does **not** touch Flask or session objects — pure async.
"""
from __future__ import annotations

import logging
import time
from typing import AsyncGenerator

from core.agentic.config import CouncilConfig
from core.agentic.contracts import (
    AgentRole,
    CouncilResult,
    CouncilStep,
    CouncilTrace,
    FinalAnswer,
    FinalDecision,
    RetryTarget,
    RunStatus,
    SynthesizerOutput,
)
from core.agentic.events import CouncilEventEmitter, EventStage, EventStatus
from core.agentic.state import AgentRunState, PreContext

from core.agentic.agents.planner import PlannerAgent
from core.agentic.agents.researcher import ResearcherAgent
from core.agentic.agents.critic import CriticAgent
from core.agentic.agents.synthesizer import SynthesizerAgent

logger = logging.getLogger(__name__)

# Circuit-breaker: if consecutive critic scores don't improve by at
# least this many points, stop iterating.
_MIN_SCORE_IMPROVEMENT = 0


class CouncilOrchestrator:
    """Drive the 4-agent council loop with selective retry.

    Usage (non-streaming)::

        orch = CouncilOrchestrator(config)
        result = await orch.run(pre_context)

    Usage (streaming — yields SSE-ready steps)::

        async for step in orch.run_stream(pre_context):
            yield sse("council_step", step.model_dump())
    """

    def __init__(self, config: CouncilConfig | None = None, *, emitter: CouncilEventEmitter | None = None) -> None:
        self.config = config or CouncilConfig()
        self._emitter = emitter
        self._planner = PlannerAgent(self.config)
        self._researcher = ResearcherAgent(self.config)
        self._critic = CriticAgent(self.config)
        self._synthesizer = SynthesizerAgent(self.config)

    async def _emit(
        self,
        stage: EventStage,
        role: str,
        status: EventStatus,
        round: int,
        short_message: str = "",
    ) -> None:
        """Fire a progress event if an emitter is attached (no-op otherwise)."""
        if self._emitter is not None:
            await self._emitter.emit(
                stage=stage, role=role, status=status,
                round=round, short_message=short_message,
            )

    # ── Non-streaming entry point ──────────────────────────────────

    async def run(self, pre_context: PreContext) -> CouncilResult:
        """Execute the full council pipeline and return the result."""
        state = self._init_state(pre_context)
        start = time.monotonic()

        logger.info(
            "[Council] run_id=%s | Starting council pipeline | max_rounds=%d | "
            "models: planner=%s researcher=%s critic=%s synthesizer=%s",
            state.run_id, self.config.max_rounds,
            self.config.planner_model, self.config.researcher_model,
            self.config.critic_model, self.config.synthesizer_model,
        )

        try:
            decision = await self._execute_loop(state)
        except Exception as exc:
            logger.error(
                "[Council] run_id=%s | Pipeline failed | reason=%s",
                state.run_id, exc,
            )
            state.status = RunStatus.failed
            await self._emit(EventStage.failed, "orchestrator", EventStatus.completed,
                             max(1, state.current_round), f"Pipeline error: {exc}")
            decision = FinalDecision(
                approved=False,
                iterations_used=max(1, state.current_round),
                iterations_max=self.config.max_rounds,
                final_quality_score=1,
                exit_reason="error",
                warnings=[f"Pipeline error: {exc}"],
            )
            if state.synthesizer_output is None:
                state.synthesizer_output = SynthesizerOutput(
                    answer=FinalAnswer(
                        content=f"Council pipeline error: {exc}",
                        confidence=0.0,
                    )
                )

        elapsed = time.monotonic() - start
        logger.info(
            "[Council] run_id=%s | Finished | exit=%s approved=%s "
            "quality=%d rounds=%d llm_calls=%d tokens=%d elapsed=%.2fs",
            state.run_id, decision.exit_reason, decision.approved,
            decision.final_quality_score, state.current_round,
            state.total_llm_calls, state.total_tokens, elapsed,
        )
        return self._build_result(state, elapsed, decision)

    # ── Streaming entry point ──────────────────────────────────────

    async def run_stream(
        self, pre_context: PreContext
    ) -> AsyncGenerator[CouncilStep, None]:
        """Execute the council pipeline, yielding each ``CouncilStep``."""
        state = self._init_state(pre_context)
        start = time.monotonic()
        self._last_result: CouncilResult | None = None

        try:
            decision = await self._execute_loop(state, yield_steps=True, _steps_out=[])
            # Yield any steps we haven't yielded yet
            # (we use the _steps_out list as a side-channel)
        except Exception as exc:
            logger.error(
                "[Council] run_id=%s | Streaming pipeline failed | reason=%s",
                state.run_id, exc,
            )
            state.status = RunStatus.failed
            await self._emit(EventStage.failed, "orchestrator", EventStatus.completed,
                             max(1, state.current_round), f"Pipeline error: {exc}")
            decision = FinalDecision(
                approved=False,
                iterations_used=max(1, state.current_round),
                iterations_max=self.config.max_rounds,
                final_quality_score=1,
                exit_reason="error",
                warnings=[f"Pipeline error: {exc}"],
            )

        elapsed = time.monotonic() - start
        self._last_result = self._build_result(state, elapsed, decision)

        # Yield all accumulated steps
        for step in state.steps:
            yield step

    @property
    def last_result(self) -> CouncilResult | None:
        return getattr(self, "_last_result", None)

    # ── Core state machine ─────────────────────────────────────────

    async def _execute_loop(
        self,
        state: AgentRunState,
        *,
        yield_steps: bool = False,
        _steps_out: list | None = None,
    ) -> FinalDecision:
        """Run the Plan → Research → Synthesize → Critic loop.

        Returns a ``FinalDecision`` summarising why the loop terminated.
        """
        max_iterations = self.config.max_rounds
        prev_score: int | None = None

        # ── Iteration 1: full pipeline ─────────────────────────────
        state.current_round = 1
        logger.info("[Council] run_id=%s | round=1 | stage=planning", state.run_id)

        state.status = RunStatus.planning
        await self._emit(EventStage.planning, "planner", EventStatus.started, 1,
                         "Decomposing task into sub-questions")
        await self._planner.execute(state)
        await self._emit(EventStage.planning, "planner", EventStatus.completed, 1,
                         f"{len(state.latest_plan.tasks) if state.latest_plan else 0} sub-tasks created")

        logger.info("[Council] run_id=%s | round=1 | stage=researching", state.run_id)
        state.status = RunStatus.researching
        await self._emit(EventStage.researching, "researcher", EventStatus.started, 1,
                         "Collecting evidence")
        await self._researcher.execute(state)
        await self._emit(EventStage.researching, "researcher", EventStatus.completed, 1,
                         f"{len(state.latest_research.evidence) if state.latest_research else 0} evidence items gathered")

        logger.info("[Council] run_id=%s | round=1 | stage=synthesizing", state.run_id)
        state.status = RunStatus.synthesizing
        await self._emit(EventStage.synthesizing, "synthesizer", EventStatus.started, 1,
                         "Composing initial response")
        await self._synthesizer.execute(state)
        await self._emit(EventStage.synthesizing, "synthesizer", EventStatus.completed, 1,
                         "Initial response ready")

        # Single-iteration fast path (no critic needed)
        if max_iterations < 1:
            state.status = RunStatus.completed
            await self._emit(EventStage.completed, "orchestrator", EventStatus.completed, 1,
                             "Completed on first pass (no critic)")
            return FinalDecision(
                approved=True,
                iterations_used=1,
                iterations_max=max_iterations,
                final_quality_score=7,
                exit_reason="first_pass",
            )

        logger.info("[Council] run_id=%s | round=1 | stage=critiquing", state.run_id)
        state.status = RunStatus.critiquing
        await self._emit(EventStage.critiquing, "critic", EventStatus.started, 1,
                         "Reviewing answer quality")
        await self._critic.execute(state)

        critique = state.latest_critique
        if critique is None:
            state.status = RunStatus.completed
            await self._emit(EventStage.completed, "critic", EventStatus.completed, 1,
                             "Approved on first pass")
            return FinalDecision(
                approved=True,
                iterations_used=1,
                iterations_max=max_iterations,
                final_quality_score=7,
                exit_reason="first_pass",
            )

        await self._emit(EventStage.critiquing, "critic", EventStatus.completed, 1,
                         f"Score {critique.quality_score}/10 — verdict: {critique.verdict}")

        # Check first-pass exit conditions
        decision = self._check_exit(critique, iteration=1, max_iter=max_iterations)
        if decision is not None:
            state.status = RunStatus.completed
            await self._emit(EventStage.completed, "orchestrator", EventStatus.completed, 1,
                             f"Finished — {decision.exit_reason}")
            return decision

        prev_score = critique.quality_score

        # ── Iteration 2+: selective retry loop ─────────────────────
        for iteration in range(2, max_iterations + 1):
            state.current_round = iteration

            target = critique.retry_target
            feedback = critique.focused_feedback

            logger.info(
                "[Council] run_id=%s | round=%d | retry target=%s | feedback=%s",
                state.run_id,
                iteration,
                target.value,
                feedback[:80] if feedback else "(none)",
            )

            await self._emit(EventStage.retrying, "orchestrator", EventStatus.started, iteration,
                             f"Retrying {target.value} (round {iteration})")

            # Selectively re-run only the stages the Critic requested
            if target in (RetryTarget.researcher, RetryTarget.both):
                # Inject critic feedback into pre_context for researcher
                if feedback and state.pre_context:
                    state.pre_context.custom_prompt = (
                        state.pre_context.custom_prompt
                        + f"\n\n[CRITIC FEEDBACK — iteration {iteration}]: {feedback}"
                    )
                state.status = RunStatus.researching
                await self._emit(EventStage.researching, "researcher", EventStatus.started, iteration,
                                 "Re-collecting evidence based on critic feedback")
                await self._researcher.execute(state)
                await self._emit(EventStage.researching, "researcher", EventStatus.completed, iteration,
                                 "Evidence updated")

            if target in (RetryTarget.synthesizer, RetryTarget.both):
                state.status = RunStatus.synthesizing
                await self._emit(EventStage.synthesizing, "synthesizer", EventStatus.started, iteration,
                                 "Re-composing response with new evidence")
                await self._synthesizer.execute(state)
                await self._emit(EventStage.synthesizing, "synthesizer", EventStatus.completed, iteration,
                                 "Response updated")

            # Re-critique
            state.status = RunStatus.critiquing
            await self._emit(EventStage.critiquing, "critic", EventStatus.started, iteration,
                             "Re-reviewing answer")
            await self._critic.execute(state)

            critique = state.latest_critique
            if critique is None:
                state.status = RunStatus.completed
                await self._emit(EventStage.completed, "orchestrator", EventStatus.completed, iteration,
                                 "Approved after retry")
                return FinalDecision(
                    approved=True,
                    iterations_used=iteration,
                    iterations_max=max_iterations,
                    final_quality_score=prev_score or 5,
                    exit_reason="approved",
                )

            await self._emit(EventStage.critiquing, "critic", EventStatus.completed, iteration,
                             f"Score {critique.quality_score}/10 — verdict: {critique.verdict}")

            # Circuit breaker: no improvement
            if prev_score is not None and critique.quality_score <= prev_score + _MIN_SCORE_IMPROVEMENT:
                logger.info(
                    "[Council] run_id=%s | Circuit breaker | score %d → %d (no improvement)",
                    state.run_id, prev_score, critique.quality_score,
                )
                state.status = RunStatus.completed
                await self._emit(EventStage.completed, "orchestrator", EventStatus.completed, iteration,
                                 "Stopped — no quality improvement (circuit breaker)")
                warnings = [
                    f"[{i.severity}] {i.description}"
                    for i in critique.issues
                ]
                return FinalDecision(
                    approved=False,
                    iterations_used=iteration,
                    iterations_max=max_iterations,
                    final_quality_score=critique.quality_score,
                    exit_reason="circuit_breaker",
                    warnings=warnings,
                )

            # Normal exit check
            decision = self._check_exit(critique, iteration=iteration, max_iter=max_iterations)
            if decision is not None:
                state.status = RunStatus.completed
                await self._emit(EventStage.completed, "orchestrator", EventStatus.completed, iteration,
                                 f"Finished — {decision.exit_reason}")
                return decision

            prev_score = critique.quality_score

        # Budget exhausted
        state.status = RunStatus.completed
        await self._emit(EventStage.completed, "orchestrator", EventStatus.completed,
                         max_iterations, "Budget exhausted — returning best answer")
        warnings = [
            f"[{i.severity}] {i.description}"
            for i in (critique.issues if critique else [])
        ]
        return FinalDecision(
            approved=False,
            iterations_used=max_iterations,
            iterations_max=max_iterations,
            final_quality_score=critique.quality_score if critique else 5,
            exit_reason="budget_exhausted",
            warnings=warnings,
        )

    # ── Exit-condition helper ─────────────────────────────────────

    def _check_exit(
        self,
        critique: object,
        *,
        iteration: int,
        max_iter: int,
    ) -> FinalDecision | None:
        """Return a FinalDecision if the loop should stop, else None."""
        verdict = getattr(critique, "verdict", "needs_work")
        score = getattr(critique, "quality_score", 5)
        issues = getattr(critique, "issues", [])

        # Approved
        if verdict == "pass":
            return FinalDecision(
                approved=True,
                iterations_used=iteration,
                iterations_max=max_iter,
                final_quality_score=score,
                exit_reason="approved",
            )

        # Quality threshold met
        if score >= self.config.quality_threshold:
            return FinalDecision(
                approved=True,
                iterations_used=iteration,
                iterations_max=max_iter,
                final_quality_score=score,
                exit_reason="quality_threshold",
            )

        # Budget exhausted *at* the last iteration
        if iteration >= max_iter:
            warnings = [
                f"[{i.severity}] {i.description}"
                for i in issues
            ]
            return FinalDecision(
                approved=False,
                iterations_used=iteration,
                iterations_max=max_iter,
                final_quality_score=score,
                exit_reason="budget_exhausted",
                warnings=warnings,
            )

        return None  # keep iterating

    # ── Internals ──────────────────────────────────────────────────

    def _init_state(self, pre_context: PreContext) -> AgentRunState:
        return AgentRunState(
            max_rounds=self.config.max_rounds,
            pre_context=pre_context,
        )

    def _build_result(
        self,
        state: AgentRunState,
        elapsed: float,
        decision: FinalDecision,
    ) -> CouncilResult:
        answer = (
            state.synthesizer_output.answer
            if state.synthesizer_output
            else FinalAnswer(content="(no answer produced)", confidence=0.0)
        )
        trace = CouncilTrace(
            run_id=state.run_id,
            rounds=state.current_round,
            agents_used=[s.agent.value for s in state.steps],
            total_llm_calls=state.total_llm_calls,
            total_tokens=state.total_tokens,
            elapsed_seconds=round(elapsed, 3),
            steps=state.steps,
        )
        return CouncilResult(
            answer=answer,
            trace=trace,
            decision=decision,
            status=state.status,
        )
