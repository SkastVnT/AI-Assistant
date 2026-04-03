"""
Tests for the agentic blackboard state layer.

Covers:
  • InMemoryBlackboard full lifecycle (create → plan → research → critique → synthesize → trace)
  • Protocol conformance
  • Error paths (missing run_id)
  • JSON round-trip serializability
  • Factory function
"""
import json
import sys
from pathlib import Path

import pytest

# Ensure the chatbot service root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agentic.blackboard import BlackboardStore, create_blackboard
from core.agentic.blackboard_memory import InMemoryBlackboard
from core.agentic.config import CouncilConfig
from core.agentic.contracts import (
    AgentRole,
    CriticOutput,
    CritiqueIssue,
    EvidenceItem,
    FinalAnswer,
    PlannerOutput,
    ResearcherOutput,
    RunStatus,
    SynthesizerOutput,
    TaskNode,
)
from core.agentic.state import AgentRunState, PreContext


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def bb() -> InMemoryBlackboard:
    return InMemoryBlackboard()


@pytest.fixture
def pre_ctx() -> PreContext:
    return PreContext(
        original_message="What is the capital of France?",
        language="en",
        context_type="casual",
    )


@pytest.fixture
def config() -> CouncilConfig:
    return CouncilConfig(max_rounds=3)


# ── Protocol conformance ──────────────────────────────────────────────

def test_in_memory_satisfies_protocol():
    assert isinstance(InMemoryBlackboard(), BlackboardStore)


# ── create_run ─────────────────────────────────────────────────────────

def test_create_run_returns_state(bb: InMemoryBlackboard, pre_ctx: PreContext):
    state = bb.create_run(pre_ctx)
    assert isinstance(state, AgentRunState)
    assert state.status == RunStatus.pending
    assert state.pre_context is not None
    assert state.pre_context.original_message == "What is the capital of France?"


def test_create_run_respects_config(bb: InMemoryBlackboard, pre_ctx: PreContext, config: CouncilConfig):
    state = bb.create_run(pre_ctx, config)
    assert state.max_rounds == 3


def test_create_run_stored(bb: InMemoryBlackboard, pre_ctx: PreContext):
    state = bb.create_run(pre_ctx)
    assert bb.get_run(state.run_id) is state
    assert len(bb) == 1


# ── get_run ────────────────────────────────────────────────────────────

def test_get_run_missing(bb: InMemoryBlackboard):
    assert bb.get_run("nonexistent") is None


# ── update_run_status ──────────────────────────────────────────────────

def test_update_status(bb: InMemoryBlackboard, pre_ctx: PreContext):
    state = bb.create_run(pre_ctx)
    bb.update_run_status(state.run_id, RunStatus.planning)
    assert bb.get_run(state.run_id).status == RunStatus.planning


def test_update_status_missing_raises(bb: InMemoryBlackboard):
    with pytest.raises(KeyError):
        bb.update_run_status("nope", RunStatus.failed)


# ── append_planner_tasks ──────────────────────────────────────────────

def test_append_planner_tasks(bb: InMemoryBlackboard, pre_ctx: PreContext):
    state = bb.create_run(pre_ctx)
    plan = PlannerOutput(
        approach="geographic lookup",
        tasks=[
            TaskNode(question="Identify country", suggested_tools=["web_search"]),
            TaskNode(question="Find capital city", priority=2),
        ],
        estimated_complexity=2,
    )
    bb.append_planner_tasks(state.run_id, plan)
    assert len(state.planner_outputs) == 1
    assert len(state.planner_outputs[0].tasks) == 2


# ── append_research_evidence ──────────────────────────────────────────

def test_append_research_evidence(bb: InMemoryBlackboard, pre_ctx: PreContext):
    state = bb.create_run(pre_ctx)
    research = ResearcherOutput(
        evidence=[
            EvidenceItem(source="web", content="Paris is the capital of France.", relevance=0.95),
            EvidenceItem(source="rag", content="France — capital: Paris", relevance=0.9),
        ],
        summary="Paris is the capital.",
        tools_used=["web_search", "rag_query"],
    )
    bb.append_research_evidence(state.run_id, research)
    assert len(state.researcher_outputs) == 1
    assert state.researcher_outputs[0].evidence[0].content.startswith("Paris")


# ── append_critic_issues ──────────────────────────────────────────────

def test_append_critic_issues(bb: InMemoryBlackboard, pre_ctx: PreContext):
    state = bb.create_run(pre_ctx)
    critique = CriticOutput(
        quality_score=8,
        issues=[
            CritiqueIssue(
                severity="low",
                description="Could mention population",
                suggestion="Add population figure",
            ),
        ],
        verdict="pass",
    )
    bb.append_critic_issues(state.run_id, critique)
    assert len(state.critic_outputs) == 1
    assert state.critic_outputs[0].verdict == "pass"


# ── set_final_answer ──────────────────────────────────────────────────

def test_set_final_answer(bb: InMemoryBlackboard, pre_ctx: PreContext):
    state = bb.create_run(pre_ctx)
    answer = SynthesizerOutput(
        answer=FinalAnswer(
            content="The capital of France is **Paris**.",
            confidence=0.95,
            key_points=["Paris is the capital of France"],
            citations=[{"source": "web", "url": "https://example.com"}],
        ),
    )
    bb.set_final_answer(state.run_id, answer)
    assert state.synthesizer_output is not None
    assert state.status == RunStatus.completed
    assert state.synthesizer_output.answer.confidence == 0.95


# ── summarize_trace ───────────────────────────────────────────────────

def test_summarize_trace_empty(bb: InMemoryBlackboard, pre_ctx: PreContext):
    state = bb.create_run(pre_ctx)
    trace = bb.summarize_trace(state.run_id)
    assert trace["run_id"] == state.run_id
    assert trace["status"] == "pending"
    assert trace["planner_tasks"] == 0
    assert trace["has_final_answer"] is False


def test_summarize_trace_missing_raises(bb: InMemoryBlackboard):
    with pytest.raises(KeyError):
        bb.summarize_trace("bogus")


# ── Full lifecycle test ───────────────────────────────────────────────

def test_full_lifecycle(bb: InMemoryBlackboard, pre_ctx: PreContext):
    """Walk through every stage and assert final trace is correct."""
    # 1. Create
    state = bb.create_run(pre_ctx)
    run_id = state.run_id

    # 2. Plan
    bb.update_run_status(run_id, RunStatus.planning)
    bb.append_planner_tasks(run_id, PlannerOutput(
        approach="lookup",
        tasks=[
            TaskNode(question="What country?", suggested_tools=["web_search"]),
            TaskNode(question="Capital?"),
        ],
        estimated_complexity=2,
    ))

    # 3. Research
    bb.update_run_status(run_id, RunStatus.researching)
    bb.append_research_evidence(run_id, ResearcherOutput(
        evidence=[
            EvidenceItem(source="web", content="Paris", relevance=0.95),
        ],
        summary="Paris",
        tools_used=["web_search"],
    ))

    # 4. Critique
    bb.update_run_status(run_id, RunStatus.critiquing)
    bb.append_critic_issues(run_id, CriticOutput(
        quality_score=9,
        issues=[],
        verdict="pass",
    ))

    # 5. Record some steps for trace
    state.current_round = 1
    state.record_step(AgentRole.planner, output_summary="2 tasks", tokens=150, elapsed_ms=320)
    state.record_step(AgentRole.researcher, output_summary="1 evidence", tokens=200, elapsed_ms=450)
    state.record_step(AgentRole.critic, output_summary="pass", tokens=100, elapsed_ms=210)

    # 6. Synthesize
    bb.update_run_status(run_id, RunStatus.synthesizing)
    bb.set_final_answer(run_id, SynthesizerOutput(
        answer=FinalAnswer(
            content="Paris",
            confidence=0.95,
            key_points=["Paris is the capital of France"],
        ),
    ))
    state.record_step(AgentRole.synthesizer, output_summary="Paris", tokens=80, elapsed_ms=180)

    # 7. Verify trace
    trace = bb.summarize_trace(run_id)
    assert trace["status"] == "completed"
    assert trace["planner_tasks"] == 2
    assert trace["evidence_items"] == 1
    assert trace["critic_issues"] == 0
    assert trace["has_final_answer"] is True
    assert len(trace["steps"]) == 4


# ── JSON serialization round-trip ─────────────────────────────────────

def test_run_state_json_roundtrip(bb: InMemoryBlackboard, pre_ctx: PreContext):
    """AgentRunState must survive JSON serialize → deserialize."""
    state = bb.create_run(pre_ctx)
    bb.append_planner_tasks(state.run_id, PlannerOutput(
        approach="test",
        tasks=[TaskNode(question="Q1")],
    ))
    bb.set_final_answer(state.run_id, SynthesizerOutput(
        answer=FinalAnswer(content="A1", confidence=0.8),
    ))

    json_str = state.model_dump_json()
    restored = AgentRunState.model_validate_json(json_str)

    assert restored.run_id == state.run_id
    assert restored.status == RunStatus.completed
    assert restored.planner_outputs[0].tasks[0].question == "Q1"
    assert restored.synthesizer_output.answer.content == "A1"

    # Also validate the JSON is parseable via stdlib
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)
    assert "run_id" in parsed


def test_summarize_trace_json_serializable(bb: InMemoryBlackboard, pre_ctx: PreContext):
    """summarize_trace() output must be JSON-serializable."""
    state = bb.create_run(pre_ctx)
    trace = bb.summarize_trace(state.run_id)
    json_str = json.dumps(trace)
    assert isinstance(json.loads(json_str), dict)


# ── Factory function ──────────────────────────────────────────────────

def test_factory_default_is_memory():
    bb = create_blackboard()
    assert isinstance(bb, InMemoryBlackboard)


def test_factory_explicit_memory():
    bb = create_blackboard("memory")
    assert isinstance(bb, InMemoryBlackboard)


def test_factory_unknown_falls_back_to_memory():
    bb = create_blackboard("banana")
    assert isinstance(bb, InMemoryBlackboard)


def test_factory_env_override(monkeypatch):
    monkeypatch.setenv("AGENT_BLACKBOARD_BACKEND", "memory")
    bb = create_blackboard()
    assert isinstance(bb, InMemoryBlackboard)


# ── clear helper ──────────────────────────────────────────────────────

def test_clear(bb: InMemoryBlackboard, pre_ctx: PreContext):
    bb.create_run(pre_ctx)
    bb.create_run(pre_ctx)
    assert len(bb) == 2
    bb.clear()
    assert len(bb) == 0
