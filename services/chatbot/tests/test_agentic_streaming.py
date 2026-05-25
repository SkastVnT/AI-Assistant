"""
Tests for council streaming events (Step 10).

Covers:
    - CouncilEvent schema validation
    - CouncilEventEmitter publish/subscribe
    - Orchestrator emits events at stage transitions

Run from services/chatbot/:
    python -m pytest tests/test_agentic_streaming.py -v
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.agentic.events import (
    CouncilEvent,
    CouncilEventEmitter,
    EventStage,
    EventStatus,
)


# ---------------------------------------------------------------------------
# CouncilEvent schema tests
# ---------------------------------------------------------------------------

class TestCouncilEvent:
    def test_minimal_event(self):
        e = CouncilEvent(run_id="r1", stage=EventStage.planning, role="planner", status=EventStatus.started)
        assert e.run_id == "r1"
        assert e.stage == EventStage.planning
        assert e.role == "planner"
        assert e.status == EventStatus.started
        assert e.round == 1
        assert e.short_message == ""
        assert e.timestamp  # auto-populated

    def test_full_event(self):
        e = CouncilEvent(
            run_id="r2",
            stage=EventStage.researching,
            role="researcher",
            status=EventStatus.completed,
            round=3,
            short_message="Found 5 items",
        )
        assert e.round == 3
        assert e.short_message == "Found 5 items"

    def test_model_dump_json(self):
        e = CouncilEvent(run_id="r3", stage=EventStage.completed, role="orchestrator", status=EventStatus.completed)
        d = e.model_dump()
        assert d["run_id"] == "r3"
        assert d["stage"] == "completed"
        assert d["role"] == "orchestrator"
        assert d["status"] == "completed"

    def test_all_stages(self):
        for stage in EventStage:
            e = CouncilEvent(run_id="r", stage=stage, role="x", status=EventStatus.started)
            assert e.stage == stage

    def test_all_statuses(self):
        for status in EventStatus:
            e = CouncilEvent(run_id="r", stage=EventStage.planning, role="x", status=status)
            assert e.status == status

    def test_short_message_truncated(self):
        long_msg = "x" * 500
        e = CouncilEvent(run_id="r", stage=EventStage.planning, role="planner", status=EventStatus.started, short_message=long_msg)
        # The emitter truncates to 300; the schema itself stores whatever it gets
        assert len(e.short_message) == 500


# ---------------------------------------------------------------------------
# CouncilEventEmitter tests
# ---------------------------------------------------------------------------

class TestCouncilEventEmitter:
    @pytest.mark.asyncio
    async def test_emit_and_consume(self):
        emitter = CouncilEventEmitter(run_id="test-run")
        await emitter.emit(stage=EventStage.planning, role="planner", status=EventStatus.started)
        await emitter.emit(stage=EventStage.planning, role="planner", status=EventStatus.completed,
                           short_message="Done planning")
        await emitter.close()

        events = []
        async for e in emitter.events():
            events.append(e)

        assert len(events) == 2
        assert events[0].stage == EventStage.planning
        assert events[0].status == EventStatus.started
        assert events[1].short_message == "Done planning"

    @pytest.mark.asyncio
    async def test_close_terminates_generator(self):
        emitter = CouncilEventEmitter(run_id="test")
        await emitter.close()

        events = []
        async for e in emitter.events():
            events.append(e)
        assert events == []

    @pytest.mark.asyncio
    async def test_emit_returns_event(self):
        emitter = CouncilEventEmitter(run_id="r")
        event = await emitter.emit(stage=EventStage.failed, role="orch", status=EventStatus.completed)
        await emitter.close()
        assert isinstance(event, CouncilEvent)
        assert event.run_id == "r"

    @pytest.mark.asyncio
    async def test_concurrent_emit_and_consume(self):
        """Emitter in a task, consumer in the main coroutine."""
        emitter = CouncilEventEmitter(run_id="concurrent")
        events_collected = []

        async def producer():
            for i in range(5):
                await emitter.emit(
                    stage=EventStage.researching, role="researcher",
                    status=EventStatus.progress, round=i + 1,
                    short_message=f"step {i + 1}",
                )
            await emitter.close()

        async def consumer():
            async for e in emitter.events():
                events_collected.append(e)

        await asyncio.gather(producer(), consumer())
        assert len(events_collected) == 5
        assert events_collected[0].short_message == "step 1"
        assert events_collected[4].short_message == "step 5"


# ---------------------------------------------------------------------------
# Orchestrator emits events
# ---------------------------------------------------------------------------

class TestOrchestratorEmitsEvents:
    """Verify the orchestrator calls the emitter at each stage."""

    @pytest.mark.asyncio
    async def test_full_pipeline_emits_events(self):
        from core.agentic.config import CouncilConfig
        from core.agentic.orchestrator import CouncilOrchestrator
        from core.agentic.state import PreContext
        from core.agentic.contracts import (
            PlannerOutput, TaskNode, ResearcherOutput,
            EvidenceItem, CriticOutput, SynthesizerOutput,
            FinalAnswer,
        )

        config = CouncilConfig(max_rounds=1)
        emitter = CouncilEventEmitter(run_id="orch-test")
        orch = CouncilOrchestrator(config, emitter=emitter)

        # Mock all four agents
        plan = PlannerOutput(approach="test", tasks=[TaskNode(question="q1")])
        research = ResearcherOutput(evidence=[EvidenceItem(source="llm", content="data")], summary="ok")
        critique = CriticOutput(quality_score=9, verdict="pass")
        synth = SynthesizerOutput(answer=FinalAnswer(content="Final answer", confidence=0.9))

        async def mock_execute(state):
            pass

        with patch.object(orch._planner, "execute", side_effect=_make_agent_mock(plan, "planner")), \
             patch.object(orch._researcher, "execute", side_effect=_make_agent_mock(research, "researcher")), \
             patch.object(orch._critic, "execute", side_effect=_make_agent_mock(critique, "critic")), \
             patch.object(orch._synthesizer, "execute", side_effect=_make_agent_mock(synth, "synthesizer")):

            pre = PreContext(original_message="test question")

            # Collect events in background
            collected = []

            async def collect():
                async for e in emitter.events():
                    collected.append(e)

            collect_task = asyncio.ensure_future(collect())
            result = await orch.run(pre)
            await emitter.close()
            await collect_task

        # Should have: plan start/end, research start/end, synth start/end,
        # critic start, critic completed (pass), completed
        stages = [(e.stage.value, e.role, e.status.value) for e in collected]

        # Verify key transitions present
        assert ("planning", "planner", "started") in stages
        assert ("planning", "planner", "completed") in stages
        assert ("researching", "researcher", "started") in stages
        assert ("researching", "researcher", "completed") in stages
        assert ("synthesizing", "synthesizer", "started") in stages
        assert ("synthesizing", "synthesizer", "completed") in stages
        assert ("critiquing", "critic", "started") in stages

        # At least 7 events for a single round
        assert len(collected) >= 7

    @pytest.mark.asyncio
    async def test_no_emitter_no_crash(self):
        """Orchestrator without emitter must still work."""
        from core.agentic.config import CouncilConfig
        from core.agentic.orchestrator import CouncilOrchestrator
        from core.agentic.state import PreContext
        from core.agentic.contracts import (
            PlannerOutput, TaskNode, ResearcherOutput,
            EvidenceItem, CriticOutput, SynthesizerOutput,
            FinalAnswer,
        )

        config = CouncilConfig(max_rounds=1)
        orch = CouncilOrchestrator(config)  # No emitter

        plan = PlannerOutput(approach="test", tasks=[TaskNode(question="q1")])
        research = ResearcherOutput(evidence=[EvidenceItem(source="llm", content="data")], summary="ok")
        critique = CriticOutput(quality_score=9, verdict="pass")
        synth = SynthesizerOutput(answer=FinalAnswer(content="Answer", confidence=0.9))

        with patch.object(orch._planner, "execute", side_effect=_make_agent_mock(plan, "planner")), \
             patch.object(orch._researcher, "execute", side_effect=_make_agent_mock(research, "researcher")), \
             patch.object(orch._critic, "execute", side_effect=_make_agent_mock(critique, "critic")), \
             patch.object(orch._synthesizer, "execute", side_effect=_make_agent_mock(synth, "synthesizer")):

            pre = PreContext(original_message="test")
            result = await orch.run(pre)

        assert result.answer.content == "Answer"


async def _mock_agent(state, output, role):
    """Helper to mock agent execute: append output to state."""
    from core.agentic.contracts import (
        PlannerOutput, ResearcherOutput, CriticOutput, SynthesizerOutput,
    )
    if isinstance(output, PlannerOutput):
        state.planner_outputs.append(output)
    elif isinstance(output, ResearcherOutput):
        state.researcher_outputs.append(output)
    elif isinstance(output, CriticOutput):
        state.critic_outputs.append(output)
    elif isinstance(output, SynthesizerOutput):
        state.synthesizer_output = output


def _make_agent_mock(output, role):
    """Create an AsyncMock whose side_effect calls _mock_agent."""
    async def _side_effect(state):
        await _mock_agent(state, output, role)
    return _side_effect


