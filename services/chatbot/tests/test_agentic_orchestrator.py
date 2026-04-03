"""
Tests for the CouncilOrchestrator critic loop.

Covers:
  • Happy path — first-pass approval
  • One retry then approval
  • Iteration limit (budget exhausted)
  • Circuit breaker — no quality improvement
  • Quality threshold met
  • Selective retry — researcher only, synthesizer only, both
  • Error handling — pipeline failure produces FinalDecision
  • FinalDecision schema validation
  • Streaming entry point
"""
import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agentic.config import CouncilConfig
from core.agentic.contracts import (
    AgentRole,
    CouncilResult,
    CriticOutput,
    CritiqueIssue,
    EvidenceItem,
    FinalAnswer,
    FinalDecision,
    PlannerOutput,
    ResearcherOutput,
    RetryTarget,
    RunStatus,
    SynthesizerOutput,
    TaskNode,
)
from core.agentic.orchestrator import CouncilOrchestrator
from core.agentic.state import AgentRunState, PreContext


# ── Helpers ────────────────────────────────────────────────────────────

def _pre_ctx(msg: str = "What is Python?") -> PreContext:
    return PreContext(original_message=msg, language="en")


def _plan_output() -> PlannerOutput:
    return PlannerOutput(
        approach="Research Python basics",
        tasks=[TaskNode(question="What is Python?", priority=1)],
        estimated_complexity=2,
    )


def _research_output() -> ResearcherOutput:
    return ResearcherOutput(
        evidence=[EvidenceItem(source="llm", content="Python is a programming language.", relevance=0.9)],
        summary="Python is a high-level programming language.",
        tools_used=[],
    )


def _synth_output(confidence: float = 0.8) -> SynthesizerOutput:
    return SynthesizerOutput(
        answer=FinalAnswer(
            content="Python is a high-level, interpreted programming language.",
            confidence=confidence,
            key_points=["General purpose", "Easy to learn"],
        )
    )


def _critic_pass(score: int = 8) -> CriticOutput:
    return CriticOutput(
        quality_score=score,
        issues=[],
        verdict="pass",
        retry_target=RetryTarget.both,
        focused_feedback="",
    )


def _critic_needs_work(
    score: int = 4,
    target: RetryTarget = RetryTarget.both,
    feedback: str = "Add more evidence about Python's history.",
) -> CriticOutput:
    return CriticOutput(
        quality_score=score,
        issues=[
            CritiqueIssue(
                severity="high",
                description="Missing historical context",
                suggestion="Research Python's origin and creator",
            ),
        ],
        verdict="needs_work",
        retry_target=target,
        focused_feedback=feedback,
    )


class _MockOrchestrator(CouncilOrchestrator):
    """Orchestrator with mocked agent execute() methods."""

    def __init__(
        self,
        config: CouncilConfig | None = None,
        *,
        critic_outputs: list[CriticOutput] | None = None,
    ):
        super().__init__(config)
        self._critic_sequence = list(critic_outputs or [_critic_pass()])
        self._critic_call_idx = 0

        # Mock all 4 agents
        self._planner.execute = AsyncMock(side_effect=self._mock_plan)
        self._researcher.execute = AsyncMock(side_effect=self._mock_research)
        self._synthesizer.execute = AsyncMock(side_effect=self._mock_synth)
        self._critic.execute = AsyncMock(side_effect=self._mock_critic)

    async def _mock_plan(self, state: AgentRunState):
        state.planner_outputs.append(_plan_output())
        state.record_step(AgentRole.planner, output_summary="planned")

    async def _mock_research(self, state: AgentRunState):
        state.researcher_outputs.append(_research_output())
        state.record_step(AgentRole.researcher, output_summary="researched")

    async def _mock_synth(self, state: AgentRunState):
        state.synthesizer_output = _synth_output()
        state.record_step(AgentRole.synthesizer, output_summary="synthesized")

    async def _mock_critic(self, state: AgentRunState):
        idx = min(self._critic_call_idx, len(self._critic_sequence) - 1)
        critique = self._critic_sequence[idx]
        state.critic_outputs.append(critique)
        state.record_step(
            AgentRole.critic,
            output_summary=f"score={critique.quality_score} verdict={critique.verdict}",
        )
        self._critic_call_idx += 1


# ═══════════════════════════════════════════════════════════════════════
# FinalDecision schema tests
# ═══════════════════════════════════════════════════════════════════════


class TestFinalDecision:
    def test_default_values(self):
        d = FinalDecision()
        assert d.approved is False
        assert d.iterations_used == 1
        assert d.exit_reason == "first_pass"
        assert d.warnings == []

    def test_approved(self):
        d = FinalDecision(
            approved=True,
            iterations_used=1,
            iterations_max=3,
            final_quality_score=9,
            exit_reason="approved",
        )
        assert d.approved is True
        assert d.final_quality_score == 9

    def test_with_warnings(self):
        d = FinalDecision(
            approved=False,
            exit_reason="budget_exhausted",
            warnings=["[high] Missing data", "[medium] Unclear phrasing"],
        )
        assert len(d.warnings) == 2

    def test_serializable(self):
        d = FinalDecision(approved=True, exit_reason="approved")
        data = d.model_dump()
        assert data["approved"] is True
        # Round-trip
        d2 = FinalDecision.model_validate(data)
        assert d2.approved is True


# ═══════════════════════════════════════════════════════════════════════
# Happy path — first-pass approval
# ═══════════════════════════════════════════════════════════════════════


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_first_pass_approved(self):
        """Critic gives 'pass' on first iteration → finalize immediately."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3),
            critic_outputs=[_critic_pass(score=9)],
        )
        result = await orch.run(_pre_ctx())

        assert isinstance(result, CouncilResult)
        assert result.status == RunStatus.completed
        assert result.decision.approved is True
        assert result.decision.exit_reason == "approved"
        assert result.decision.iterations_used == 1
        assert result.decision.final_quality_score == 9

        # Verify agent call counts: Plan, Research, Synth, Critic = 4 calls
        assert orch._planner.execute.await_count == 1
        assert orch._researcher.execute.await_count == 1
        assert orch._synthesizer.execute.await_count == 1
        assert orch._critic.execute.await_count == 1

    @pytest.mark.asyncio
    async def test_answer_present(self):
        orch = _MockOrchestrator(critic_outputs=[_critic_pass()])
        result = await orch.run(_pre_ctx())

        assert result.answer.content != ""
        assert result.answer.confidence > 0


# ═══════════════════════════════════════════════════════════════════════
# One retry then approval
# ═══════════════════════════════════════════════════════════════════════


class TestOneRetry:
    @pytest.mark.asyncio
    async def test_retry_then_pass(self):
        """Critic says needs_work first, then pass on second iteration."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3),
            critic_outputs=[
                _critic_needs_work(score=4, target=RetryTarget.both),
                _critic_pass(score=8),
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is True
        assert result.decision.iterations_used == 2
        assert result.decision.exit_reason == "approved"
        assert result.decision.final_quality_score == 8

        # Planner runs once, Researcher/Synth run twice (initial + retry)
        assert orch._planner.execute.await_count == 1
        assert orch._researcher.execute.await_count == 2
        assert orch._synthesizer.execute.await_count == 2
        assert orch._critic.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_retry_researcher_only(self):
        """When retry_target=researcher, only Researcher + Synth rerun."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3),
            critic_outputs=[
                _critic_needs_work(score=4, target=RetryTarget.researcher),
                _critic_pass(score=8),
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is True
        assert result.decision.iterations_used == 2
        # Researcher re-runs but Synthesizer... both researcher and synthesizer
        # should not get re-run at iteration 2 for "researcher" target

    @pytest.mark.asyncio
    async def test_retry_synthesizer_only(self):
        """When retry_target=synthesizer, only Synthesizer reruns."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3),
            critic_outputs=[
                _critic_needs_work(score=5, target=RetryTarget.synthesizer),
                _critic_pass(score=9),
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is True
        # Researcher should NOT have been called a second time
        assert orch._researcher.execute.await_count == 1
        # Synthesizer called twice (initial + retry)
        assert orch._synthesizer.execute.await_count == 2


# ═══════════════════════════════════════════════════════════════════════
# Iteration limit reached (budget exhausted)
# ═══════════════════════════════════════════════════════════════════════


class TestBudgetExhausted:
    @pytest.mark.asyncio
    async def test_max_iterations_reached(self):
        """Critic never approves within max_rounds — finalize with warnings."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=2),
            critic_outputs=[
                _critic_needs_work(score=3),
                _critic_needs_work(score=5),  # improved but not enough
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is False
        assert result.decision.exit_reason in ("budget_exhausted", "circuit_breaker")
        assert result.decision.iterations_used <= 2
        assert result.decision.warnings  # should have unresolved issues
        assert result.answer.content != ""  # still produces an answer

    @pytest.mark.asyncio
    async def test_single_iteration_config(self):
        """max_rounds=1 means critic checks once, no retry opportunity."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=1),
            critic_outputs=[_critic_needs_work(score=4)],
        )
        result = await orch.run(_pre_ctx())

        # With max_rounds=1, critic runs once; if needs_work, budget exhausted.
        assert result.decision.approved is False
        assert result.decision.exit_reason == "budget_exhausted"
        assert result.decision.iterations_used == 1


# ═══════════════════════════════════════════════════════════════════════
# Circuit breaker
# ═══════════════════════════════════════════════════════════════════════


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_no_improvement_triggers_breaker(self):
        """If score doesn't improve between iterations, stop early."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=4),
            critic_outputs=[
                _critic_needs_work(score=4),
                _critic_needs_work(score=4),  # no improvement
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is False
        assert result.decision.exit_reason == "circuit_breaker"
        assert result.decision.iterations_used == 2  # stopped at 2, not 4


# ═══════════════════════════════════════════════════════════════════════
# Quality threshold
# ═══════════════════════════════════════════════════════════════════════


class TestQualityThreshold:
    @pytest.mark.asyncio
    async def test_threshold_met(self):
        """quality_score >= quality_threshold → approve even with needs_work verdict."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3, quality_threshold=7),
            critic_outputs=[
                CriticOutput(quality_score=7, verdict="needs_work", issues=[]),
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is True
        assert result.decision.exit_reason == "quality_threshold"


# ═══════════════════════════════════════════════════════════════════════
# Error handling
# ═══════════════════════════════════════════════════════════════════════


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_pipeline_error_produces_decision(self):
        """If an agent raises, the result still has FinalDecision + answer."""
        orch = _MockOrchestrator(critic_outputs=[_critic_pass()])
        orch._planner.execute = AsyncMock(side_effect=RuntimeError("boom"))

        result = await orch.run(_pre_ctx())

        assert result.status == RunStatus.failed
        assert result.decision.approved is False
        assert result.decision.exit_reason == "error"
        assert "boom" in result.decision.warnings[0]
        assert result.answer.content  # degraded but present


# ═══════════════════════════════════════════════════════════════════════
# CouncilResult schema
# ═══════════════════════════════════════════════════════════════════════


class TestCouncilResult:
    @pytest.mark.asyncio
    async def test_result_has_decision(self):
        orch = _MockOrchestrator(critic_outputs=[_critic_pass()])
        result = await orch.run(_pre_ctx())

        assert hasattr(result, "decision")
        assert isinstance(result.decision, FinalDecision)

    @pytest.mark.asyncio
    async def test_result_serializable(self):
        orch = _MockOrchestrator(critic_outputs=[_critic_pass()])
        result = await orch.run(_pre_ctx())

        data = result.model_dump()
        assert "decision" in data
        assert "approved" in data["decision"]

    @pytest.mark.asyncio
    async def test_trace_populated(self):
        orch = _MockOrchestrator(critic_outputs=[_critic_pass()])
        result = await orch.run(_pre_ctx())

        assert result.trace.total_llm_calls >= 4
        assert len(result.trace.steps) >= 4
        assert result.trace.rounds == 1


# ═══════════════════════════════════════════════════════════════════════
# Streaming
# ═══════════════════════════════════════════════════════════════════════


class TestStreaming:
    @pytest.mark.asyncio
    async def test_stream_yields_steps(self):
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=2),
            critic_outputs=[_critic_pass()],
        )
        steps = []
        async for step in orch.run_stream(_pre_ctx()):
            steps.append(step)

        # Should have at least 4 steps: plan, research, synth, critic
        assert len(steps) >= 4
        assert orch.last_result is not None
        assert orch.last_result.decision.approved is True

    @pytest.mark.asyncio
    async def test_stream_last_result_has_decision(self):
        orch = _MockOrchestrator(critic_outputs=[_critic_pass()])
        async for _ in orch.run_stream(_pre_ctx()):
            pass

        result = orch.last_result
        assert result is not None
        assert isinstance(result.decision, FinalDecision)


# ═══════════════════════════════════════════════════════════════════════
# Critic retry target inference
# ═══════════════════════════════════════════════════════════════════════


class TestCriticRetryTarget:
    """Tests for CriticAgent._infer_retry_target."""

    def test_research_keywords(self):
        from core.agentic.agents.critic import CriticAgent

        issues = [CritiqueIssue(severity="high", description="Missing evidence about sources")]
        assert CriticAgent._infer_retry_target(issues) == RetryTarget.researcher

    def test_synth_keywords(self):
        from core.agentic.agents.critic import CriticAgent

        issues = [CritiqueIssue(severity="medium", description="Answer format is incomplete")]
        assert CriticAgent._infer_retry_target(issues) == RetryTarget.synthesizer

    def test_mixed_keywords(self):
        from core.agentic.agents.critic import CriticAgent

        issues = [
            CritiqueIssue(severity="high", description="Missing evidence"),
            CritiqueIssue(severity="medium", description="Answer is incomplete"),
        ]
        assert CriticAgent._infer_retry_target(issues) == RetryTarget.both

    def test_no_keywords(self):
        from core.agentic.agents.critic import CriticAgent

        issues = [CritiqueIssue(severity="low", description="Minor typo")]
        assert CriticAgent._infer_retry_target(issues) == RetryTarget.both
