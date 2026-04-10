"""
Focused tests for the critic retry loop.

Covers:
    - Selective retry targets (researcher, synthesizer, both)
    - Critic feedback injection into pre_context
    - Circuit breaker with non-improving scores
    - Quality threshold override of verdict
    - Multiple retry iterations with score progression
    - CriticAgent._infer_retry_target edge cases
    - Critic output normalization (score clamping, severity)

Run from services/chatbot/:
    python -m pytest tests/test_agentic_critic_loop.py -v
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agentic.config import CouncilConfig
from core.agentic.contracts import (
    AgentRole,
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

def _pre_ctx(msg: str = "Explain recursion") -> PreContext:
    return PreContext(original_message=msg, language="en")


def _plan() -> PlannerOutput:
    return PlannerOutput(
        approach="Explain step by step",
        tasks=[TaskNode(question="What is recursion?", priority=1)],
        estimated_complexity=3,
    )


def _research() -> ResearcherOutput:
    return ResearcherOutput(
        evidence=[EvidenceItem(source="llm", content="Recursion is self-reference.", relevance=0.9)],
        summary="Recursion is a function calling itself.",
        tools_used=[],
    )


def _synth(confidence: float = 0.8) -> SynthesizerOutput:
    return SynthesizerOutput(
        answer=FinalAnswer(
            content="Recursion is when a function calls itself.",
            confidence=confidence,
            key_points=["Base case", "Recursive case"],
        )
    )


def _critic_pass(score: int = 8) -> CriticOutput:
    return CriticOutput(quality_score=score, issues=[], verdict="pass")


def _critic_fail(
    score: int = 4,
    target: RetryTarget = RetryTarget.both,
    feedback: str = "Needs more depth.",
) -> CriticOutput:
    return CriticOutput(
        quality_score=score,
        issues=[CritiqueIssue(severity="high", description="Shallow explanation")],
        verdict="needs_work",
        retry_target=target,
        focused_feedback=feedback,
    )


class _MockOrchestrator(CouncilOrchestrator):
    """Orchestrator with mocked agent execute() methods and call tracking."""

    def __init__(self, config=None, *, critic_outputs=None):
        super().__init__(config or CouncilConfig(max_rounds=3))
        self._critic_seq = list(critic_outputs or [_critic_pass()])
        self._critic_idx = 0
        self._research_call_count = 0
        self._synth_call_count = 0
        self._feedback_captured: list[str] = []

        self._planner.execute = AsyncMock(side_effect=self._mock_plan)
        self._researcher.execute = AsyncMock(side_effect=self._mock_research)
        self._synthesizer.execute = AsyncMock(side_effect=self._mock_synth)
        self._critic.execute = AsyncMock(side_effect=self._mock_critic)

    async def _mock_plan(self, state: AgentRunState):
        state.planner_outputs.append(_plan())
        state.record_step(AgentRole.planner, output_summary="planned")

    async def _mock_research(self, state: AgentRunState):
        self._research_call_count += 1
        if state.pre_context and state.pre_context.custom_prompt:
            self._feedback_captured.append(state.pre_context.custom_prompt)
        state.researcher_outputs.append(_research())
        state.record_step(AgentRole.researcher, output_summary="researched")

    async def _mock_synth(self, state: AgentRunState):
        self._synth_call_count += 1
        state.synthesizer_output = _synth()
        state.record_step(AgentRole.synthesizer, output_summary="synthesized")

    async def _mock_critic(self, state: AgentRunState):
        idx = min(self._critic_idx, len(self._critic_seq) - 1)
        critique = self._critic_seq[idx]
        state.critic_outputs.append(critique)
        state.record_step(AgentRole.critic, output_summary=f"score={critique.quality_score}")
        self._critic_idx += 1


# ═══════════════════════════════════════════════════════════════════════
# Selective retry targets
# ═══════════════════════════════════════════════════════════════════════

class TestSelectiveRetry:
    """Verify that retry_target controls which agents are re-run."""

    @pytest.mark.asyncio
    async def test_researcher_target_reruns_researcher_only(self):
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3),
            critic_outputs=[
                _critic_fail(score=4, target=RetryTarget.researcher),
                _critic_pass(score=8),
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is True
        assert result.decision.iterations_used == 2
        # Researcher: 1 initial + 1 retry = 2
        assert orch._research_call_count == 2
        # Synthesizer: 1 initial only (researcher target does NOT rerun synth)
        assert orch._synth_call_count == 1

    @pytest.mark.asyncio
    async def test_synthesizer_target_reruns_synthesizer_only(self):
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3),
            critic_outputs=[
                _critic_fail(score=5, target=RetryTarget.synthesizer),
                _critic_pass(score=9),
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is True
        # Researcher: 1 initial only (synthesizer target does NOT rerun research)
        assert orch._research_call_count == 1
        # Synthesizer: 1 initial + 1 retry = 2
        assert orch._synth_call_count == 2

    @pytest.mark.asyncio
    async def test_both_target_reruns_both(self):
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3),
            critic_outputs=[
                _critic_fail(score=3, target=RetryTarget.both),
                _critic_pass(score=8),
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is True
        assert orch._research_call_count == 2
        assert orch._synth_call_count == 2


# ═══════════════════════════════════════════════════════════════════════
# Critic feedback injection
# ═══════════════════════════════════════════════════════════════════════

class TestFeedbackInjection:
    """Verify critic feedback is appended to pre_context.custom_prompt."""

    @pytest.mark.asyncio
    async def test_feedback_injected_on_retry(self):
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3),
            critic_outputs=[
                _critic_fail(score=4, target=RetryTarget.researcher, feedback="Add recursion examples"),
                _critic_pass(score=8),
            ],
        )
        await orch.run(_pre_ctx())

        # The researcher should have received the critic feedback
        assert any("Add recursion examples" in fb for fb in orch._feedback_captured)

    @pytest.mark.asyncio
    async def test_feedback_accumulates_across_rounds(self):
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=4),
            critic_outputs=[
                _critic_fail(score=3, feedback="More depth"),
                _critic_fail(score=5, feedback="Add examples"),
                _critic_pass(score=8),
            ],
        )
        await orch.run(_pre_ctx())

        # By the third round, both feedbacks should be present
        last_feedback = orch._feedback_captured[-1] if orch._feedback_captured else ""
        assert "More depth" in last_feedback
        assert "Add examples" in last_feedback


# ═══════════════════════════════════════════════════════════════════════
# Circuit breaker edge cases
# ═══════════════════════════════════════════════════════════════════════

class TestCircuitBreakerEdges:
    @pytest.mark.asyncio
    async def test_score_decreases_triggers_breaker(self):
        """If score goes DOWN, circuit breaker should still fire."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=4),
            critic_outputs=[
                _critic_fail(score=5),
                _critic_fail(score=3),  # decreased
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.exit_reason == "circuit_breaker"
        assert result.decision.iterations_used == 2

    @pytest.mark.asyncio
    async def test_same_score_triggers_breaker(self):
        """Equal score between rounds → no improvement → breaker."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=4),
            critic_outputs=[
                _critic_fail(score=6),
                _critic_fail(score=6),  # same
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.exit_reason == "circuit_breaker"

    @pytest.mark.asyncio
    async def test_improving_score_avoids_breaker(self):
        """Score improves each round → no breaker → reaches approval or budget."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=4),
            critic_outputs=[
                _critic_fail(score=3),
                _critic_fail(score=5),  # improved → no breaker
                _critic_pass(score=8),  # approved
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is True
        assert result.decision.iterations_used == 3
        assert result.decision.exit_reason == "approved"


# ═══════════════════════════════════════════════════════════════════════
# Quality threshold overrides verdict
# ═══════════════════════════════════════════════════════════════════════

class TestQualityThresholdOverride:
    @pytest.mark.asyncio
    async def test_needs_work_but_high_score(self):
        """verdict=needs_work but score >= threshold → approved via threshold."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3, quality_threshold=6),
            critic_outputs=[
                CriticOutput(quality_score=7, verdict="needs_work", issues=[]),
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is True
        assert result.decision.exit_reason == "quality_threshold"

    @pytest.mark.asyncio
    async def test_threshold_exact_boundary(self):
        """Score exactly equals threshold → should approve."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=3, quality_threshold=8),
            critic_outputs=[
                CriticOutput(quality_score=8, verdict="needs_work", issues=[]),
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is True

    @pytest.mark.asyncio
    async def test_below_threshold_needs_work(self):
        """Score below threshold + needs_work → keep iterating."""
        orch = _MockOrchestrator(
            CouncilConfig(max_rounds=2, quality_threshold=8),
            critic_outputs=[
                CriticOutput(quality_score=5, verdict="needs_work",
                             issues=[CritiqueIssue(severity="high", description="Incomplete")]),
                CriticOutput(quality_score=5, verdict="needs_work",
                             issues=[CritiqueIssue(severity="high", description="Still incomplete")]),
            ],
        )
        result = await orch.run(_pre_ctx())

        assert result.decision.approved is False


# ═══════════════════════════════════════════════════════════════════════
# CriticAgent._infer_retry_target
# ═══════════════════════════════════════════════════════════════════════

class TestInferRetryTarget:
    """Focus on the keyword-based heuristic in CriticAgent."""

    def _infer(self, issues: list[CritiqueIssue]) -> RetryTarget:
        from core.agentic.agents.critic import CriticAgent
        return CriticAgent._infer_retry_target(issues)

    def test_evidence_keywords(self):
        issues = [CritiqueIssue(severity="high", description="Missing evidence from sources")]
        assert self._infer(issues) == RetryTarget.researcher

    def test_data_keyword(self):
        issues = [CritiqueIssue(severity="medium", description="Insufficient data provided")]
        assert self._infer(issues) == RetryTarget.researcher

    def test_source_keyword(self):
        issues = [CritiqueIssue(severity="medium", description="Need better source for claim")]
        assert self._infer(issues) == RetryTarget.researcher

    def test_format_keywords(self):
        issues = [CritiqueIssue(severity="low", description="Answer format needs improvement")]
        assert self._infer(issues) == RetryTarget.synthesizer

    def test_clarity_keyword(self):
        issues = [CritiqueIssue(severity="medium", description="Improve clarity of explanation")]
        assert self._infer(issues) == RetryTarget.synthesizer

    def test_structure_keyword(self):
        issues = [CritiqueIssue(severity="medium", description="Draft needs coherent rewrite")]
        assert self._infer(issues) == RetryTarget.synthesizer

    def test_mixed_research_and_synth(self):
        issues = [
            CritiqueIssue(severity="high", description="Need more evidence"),
            CritiqueIssue(severity="medium", description="Improve format"),
        ]
        assert self._infer(issues) == RetryTarget.both

    def test_empty_issues(self):
        assert self._infer([]) == RetryTarget.both

    def test_no_matching_keywords(self):
        issues = [CritiqueIssue(severity="low", description="Minor concern")]
        assert self._infer(issues) == RetryTarget.both


# ═══════════════════════════════════════════════════════════════════════
# Critic output normalization
# ═══════════════════════════════════════════════════════════════════════

class TestCriticOutputNormalization:
    def test_quality_score_clamped(self):
        """quality_score is constrained to 1-10 by Pydantic."""
        c = CriticOutput(quality_score=10, verdict="pass")
        assert c.quality_score == 10

    def test_issues_default_empty(self):
        c = CriticOutput(quality_score=5, verdict="needs_work")
        assert c.issues == []

    def test_retry_target_default(self):
        c = CriticOutput(quality_score=5, verdict="needs_work")
        assert c.retry_target == RetryTarget.both

    def test_focused_feedback_default_empty(self):
        c = CriticOutput(quality_score=5, verdict="pass")
        assert c.focused_feedback == ""

    def test_full_critic_output_round_trip(self):
        c = CriticOutput(
            quality_score=6,
            issues=[
                CritiqueIssue(severity="high", description="Missing data"),
                CritiqueIssue(severity="low", description="Minor typo", suggestion="Fix it"),
            ],
            verdict="needs_work",
            retry_target=RetryTarget.researcher,
            focused_feedback="Get more data from RAG",
        )
        data = c.model_dump()
        c2 = CriticOutput.model_validate(data)
        assert c2.quality_score == 6
        assert len(c2.issues) == 2
        assert c2.retry_target == RetryTarget.researcher
