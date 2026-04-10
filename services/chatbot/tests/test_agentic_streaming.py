"""
Tests for council streaming events (Step 10).

Covers:
    - CouncilEvent schema validation
    - CouncilEventEmitter publish/subscribe
    - Orchestrator emits events at stage transitions
    - /chat/council/stream SSE route
    - Feature-flag-disabled graceful SSE response

Run from services/chatbot/:
    python -m pytest tests/test_agentic_streaming.py -v
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

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


# ---------------------------------------------------------------------------
# SSE Route tests
# ---------------------------------------------------------------------------

def _mock_rag_result():
    r = MagicMock()
    r.message = "augmented"
    r.custom_prompt = "prompt"
    r.citations = None
    r.chunk_count = 0
    return r


def _council_result_dict():
    return {
        "response": "Streamed council answer.",
        "model": "council",
        "context": "casual",
        "deep_thinking": True,
        "thinking_process": "Done in 1 round.",
        "citations": None,
        "agent_run_id": "stream-run-1",
        "agent_trace_summary": {"rounds": 1},
    }


def _parse_sse(text: str):
    """Parse SSE text into (event_name, data_dict) tuples."""
    events = []
    lines = text.strip().split("\n")
    current_event = None
    current_data = None
    for line in lines:
        if line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: "):
            current_data = line[6:]
        elif line == "" and current_event and current_data:
            try:
                events.append((current_event, json.loads(current_data)))
            except json.JSONDecodeError:
                events.append((current_event, current_data))
            current_event = None
            current_data = None
    # Catch trailing event without final blank line
    if current_event and current_data:
        try:
            events.append((current_event, json.loads(current_data)))
        except json.JSONDecodeError:
            events.append((current_event, current_data))
    return events


@pytest.fixture
def stream_app():
    from fastapi_app.routers import council_stream as cs_module
    _app = FastAPI()
    _app.add_middleware(SessionMiddleware, secret_key="test-secret")
    _app.include_router(cs_module.router)
    return _app


@pytest.fixture
def stream_client(stream_app):
    return TestClient(stream_app)


class TestCouncilStreamRoute:
    def test_stream_returns_sse(self, stream_client):
        """The route should return SSE events including council_result."""
        async def fake_stream(**kwargs):
            from core.agentic.entrypoint import _sse
            yield _sse("council_event", {"run_id": "r1", "stage": "planning", "role": "planner",
                                          "status": "started", "round": 1, "timestamp": "T",
                                          "short_message": "Planning"})
            yield _sse("council_result", _council_result_dict())

        with patch("fastapi_app.routers.council_stream.run_council_stream", side_effect=fake_stream), \
             patch("fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
                   new_callable=AsyncMock, return_value=_mock_rag_result()):
            resp = stream_client.post("/chat/council/stream", json={
                "message": "Hello",
                "model": "grok",
                "agent_mode": "council",
            })

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]

        events = _parse_sse(resp.text)
        event_names = [e[0] for e in events]
        assert "council_event" in event_names
        assert "council_result" in event_names

        # Verify the result payload
        result_data = [e[1] for e in events if e[0] == "council_result"][0]
        assert result_data["model"] == "council"
        assert result_data["agent_run_id"] == "stream-run-1"

    def test_stream_disabled_returns_disabled_result(self, stream_client):
        """When feature flag is off, should get a single council_result with disabled message."""
        async def fake_disabled_stream(**kwargs):
            from core.agentic.entrypoint import _sse, _disabled_response
            yield _sse("council_result", _disabled_response("casual", None))

        with patch("fastapi_app.routers.council_stream.run_council_stream", side_effect=fake_disabled_stream), \
             patch("fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
                   new_callable=AsyncMock, return_value=_mock_rag_result()):
            resp = stream_client.post("/chat/council/stream", json={
                "message": "Test",
                "model": "grok",
            })

        assert resp.status_code == 200
        events = _parse_sse(resp.text)
        result_data = [e[1] for e in events if e[0] == "council_result"][0]
        assert "not enabled" in result_data["response"]

    def test_stream_event_schema(self, stream_client):
        """Verify each council_event has all required fields."""
        async def fake_stream(**kwargs):
            from core.agentic.entrypoint import _sse
            event = {
                "run_id": "schema-test",
                "stage": "planning",
                "role": "planner",
                "status": "started",
                "round": 1,
                "timestamp": "2026-04-03T00:00:00Z",
                "short_message": "Test",
            }
            yield _sse("council_event", event)
            yield _sse("council_result", _council_result_dict())

        with patch("fastapi_app.routers.council_stream.run_council_stream", side_effect=fake_stream), \
             patch("fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
                   new_callable=AsyncMock, return_value=_mock_rag_result()):
            resp = stream_client.post("/chat/council/stream", json={
                "message": "Hello",
                "model": "grok",
            })

        events = _parse_sse(resp.text)
        council_events = [e[1] for e in events if e[0] == "council_event"]
        assert len(council_events) >= 1

        required_fields = {"run_id", "stage", "role", "status", "round", "timestamp", "short_message"}
        for ce in council_events:
            assert required_fields.issubset(ce.keys()), f"Missing fields: {required_fields - ce.keys()}"
