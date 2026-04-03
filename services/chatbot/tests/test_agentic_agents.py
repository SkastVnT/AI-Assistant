"""
Tests for the 4 agent workers and their shared infrastructure.

Covers:
  • BaseAgent._parse_json — clean JSON, fenced, embedded, failures
  • BaseAgent._validate — Pydantic model validation
  • Prompts — all 4 roles resolve, language substitution
  • PlannerAgent._parse_output — valid JSON, malformed, empty
  • ResearcherAgent._parse_output — valid JSON, malformed, no-plan guard
  • CriticAgent._parse_output — valid JSON, severity normalisation
  • SynthesizerAgent._parse_output — valid JSON, raw-text fallback
  • Full orchestrator smoke test through all 4 agents
"""
import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agentic.agents.base import BaseAgent, LLMCallResult
from core.agentic.agents.planner import PlannerAgent
from core.agentic.agents.researcher import ResearcherAgent
from core.agentic.agents.critic import CriticAgent
from core.agentic.agents.synthesizer import SynthesizerAgent
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
from core.agentic.prompts import get_system_prompt
from core.agentic.state import AgentRunState, PreContext


# ── Fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def config() -> CouncilConfig:
    return CouncilConfig()


@pytest.fixture
def pre_ctx() -> PreContext:
    return PreContext(
        original_message="What are the best practices for Python async?",
        language="en",
        context_type="casual",
    )


@pytest.fixture
def state(pre_ctx: PreContext) -> AgentRunState:
    return AgentRunState(pre_context=pre_ctx, current_round=1)


# ── BaseAgent._parse_json ─────────────────────────────────────────────

class TestParseJson:
    """Test the JSON extraction logic on the base class."""

    def test_clean_json(self):
        raw = '{"approach": "test", "tasks": []}'
        result = BaseAgent._parse_json(raw)
        assert result["approach"] == "test"

    def test_fenced_json(self):
        raw = 'Here is my plan:\n```json\n{"approach": "fenced"}\n```\nDone.'
        result = BaseAgent._parse_json(raw)
        assert result["approach"] == "fenced"

    def test_fenced_no_lang(self):
        raw = '```\n{"key": "value"}\n```'
        result = BaseAgent._parse_json(raw)
        assert result["key"] == "value"

    def test_embedded_json(self):
        raw = 'Sure, here is the output: {"score": 8} — hope that helps!'
        result = BaseAgent._parse_json(raw)
        assert result["score"] == 8

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="Empty"):
            BaseAgent._parse_json("")

    def test_garbage_raises(self):
        with pytest.raises(ValueError, match="Could not extract"):
            BaseAgent._parse_json("This is plain text with no JSON at all.")

    def test_whitespace_around_json(self):
        raw = '  \n  {"x": 1}  \n  '
        assert BaseAgent._parse_json(raw) == {"x": 1}


# ── BaseAgent._validate ──────────────────────────────────────────────

class TestValidate:
    def test_valid_task_node(self):
        data = {"question": "What is X?", "priority": 2}
        node = BaseAgent._validate(data, TaskNode)
        assert isinstance(node, TaskNode)
        assert node.priority == 2

    def test_invalid_raises(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BaseAgent._validate({"priority": "not_a_number"}, TaskNode)


# ── Prompts ───────────────────────────────────────────────────────────

class TestPrompts:
    @pytest.mark.parametrize("role", ["planner", "researcher", "critic", "synthesizer"])
    def test_all_roles_resolve(self, role: str):
        prompt = get_system_prompt(role, language="English")
        assert len(prompt) > 100
        assert "English" in prompt

    def test_language_substitution(self):
        prompt = get_system_prompt("planner", language="Vietnamese")
        assert "Vietnamese" in prompt

    def test_unknown_role_raises(self):
        with pytest.raises(KeyError):
            get_system_prompt("wizard")


# ── PlannerAgent ──────────────────────────────────────────────────────

class TestPlannerAgent:
    def _agent(self, config: CouncilConfig) -> PlannerAgent:
        return PlannerAgent(config)

    def test_parse_valid_json(self, config: CouncilConfig):
        agent = self._agent(config)
        raw = json.dumps({
            "approach": "Split into geography sub-questions",
            "tasks": [
                {"question": "What country is it in?", "suggested_tools": ["web_search"], "priority": 1},
                {"question": "What is the capital?", "priority": 2},
            ],
            "estimated_complexity": 3,
        })
        output = agent._parse_output(raw)
        assert isinstance(output, PlannerOutput)
        assert output.approach == "Split into geography sub-questions"
        assert len(output.tasks) == 2
        assert output.tasks[0].suggested_tools == ["web_search"]
        assert output.estimated_complexity == 3

    def test_parse_empty_fallback(self, config: CouncilConfig):
        output = self._agent(config)._parse_output("")
        assert isinstance(output, PlannerOutput)
        assert len(output.tasks) == 1
        assert "fallback" in output.approach.lower() or "empty" in output.approach.lower()

    def test_parse_garbage_fallback(self, config: CouncilConfig):
        output = self._agent(config)._parse_output("This isn't JSON at all!")
        assert isinstance(output, PlannerOutput)
        assert len(output.tasks) >= 1

    def test_parse_caps_tasks_at_6(self, config: CouncilConfig):
        tasks = [{"question": f"Task {i}"} for i in range(10)]
        raw = json.dumps({"approach": "many", "tasks": tasks, "estimated_complexity": 5})
        output = self._agent(config)._parse_output(raw)
        assert len(output.tasks) <= 6

    def test_parse_clamps_complexity(self, config: CouncilConfig):
        raw = json.dumps({"approach": "x", "tasks": [{"question": "q"}], "estimated_complexity": 99})
        output = self._agent(config)._parse_output(raw)
        assert output.estimated_complexity == 10

    def test_execute_async(self, config: CouncilConfig, state: AgentRunState):
        """Smoke test: execute runs without error (LLM returns empty)."""
        agent = self._agent(config)
        asyncio.get_event_loop().run_until_complete(agent.plan(state))
        assert len(state.planner_outputs) == 1
        assert len(state.steps) == 1
        assert state.steps[0].agent == AgentRole.planner


# ── ResearcherAgent ───────────────────────────────────────────────────

class TestResearcherAgent:
    def _agent(self, config: CouncilConfig) -> ResearcherAgent:
        return ResearcherAgent(config)

    def test_parse_valid_json(self, config: CouncilConfig):
        agent = self._agent(config)
        raw = json.dumps({
            "evidence": [
                {"source": "web", "content": "Paris is the capital.", "relevance": 0.95},
                {"source": "rag", "content": "France info.", "url": "http://example.com", "relevance": 0.8},
            ],
            "summary": "Paris is the capital of France.",
            "tools_used": ["web_search"],
        })
        output = agent._parse_output(raw, ["web_search"])
        assert isinstance(output, ResearcherOutput)
        assert len(output.evidence) == 2
        assert output.evidence[0].source == "web"
        assert output.summary == "Paris is the capital of France."

    def test_parse_empty_fallback(self, config: CouncilConfig):
        output = self._agent(config)._parse_output("", [])
        assert output.evidence == []
        assert "fallback" in output.summary.lower() or "failure" in output.summary.lower()

    def test_no_plan_guard(self, config: CouncilConfig, state: AgentRunState):
        """Researcher with no plan should produce a degraded output, not crash."""
        agent = self._agent(config)
        asyncio.get_event_loop().run_until_complete(agent.research(state))
        assert len(state.researcher_outputs) == 1
        assert "No plan" in state.researcher_outputs[0].summary

    def test_execute_with_plan(self, config: CouncilConfig, state: AgentRunState):
        """After adding a plan, researcher should run and record a step."""
        state.planner_outputs.append(PlannerOutput(
            approach="test", tasks=[TaskNode(question="Q1")],
        ))
        agent = self._agent(config)
        asyncio.get_event_loop().run_until_complete(agent.research(state))
        assert len(state.researcher_outputs) == 1
        assert len(state.steps) == 1
        assert state.steps[0].agent == AgentRole.researcher

    def test_caps_evidence_at_10(self, config: CouncilConfig):
        evidence = [{"source": "llm", "content": f"Fact {i}", "relevance": 0.5} for i in range(15)]
        raw = json.dumps({"evidence": evidence, "summary": "lots", "tools_used": []})
        output = self._agent(config)._parse_output(raw, [])
        assert len(output.evidence) <= 10


# ── CriticAgent ───────────────────────────────────────────────────────

class TestCriticAgent:
    def _agent(self, config: CouncilConfig) -> CriticAgent:
        return CriticAgent(config)

    def test_parse_valid_pass(self, config: CouncilConfig):
        raw = json.dumps({
            "quality_score": 9,
            "issues": [],
            "verdict": "pass",
        })
        output = self._agent(config)._parse_output(raw)
        assert isinstance(output, CriticOutput)
        assert output.quality_score == 9
        assert output.verdict == "pass"

    def test_parse_valid_needs_work(self, config: CouncilConfig):
        raw = json.dumps({
            "quality_score": 4,
            "issues": [
                {"severity": "high", "description": "Missing key evidence", "suggestion": "Search more"},
                {"severity": "low", "description": "Minor formatting", "suggestion": "Fix bullets"},
            ],
            "verdict": "needs_work",
        })
        output = self._agent(config)._parse_output(raw)
        assert output.quality_score == 4
        assert output.verdict == "needs_work"
        assert len(output.issues) == 2
        assert output.issues[0].severity == "high"

    def test_severity_normalisation(self, config: CouncilConfig):
        raw = json.dumps({
            "quality_score": 5,
            "issues": [{"severity": "CRITICAL", "description": "bad"}],
            "verdict": "needs_work",
        })
        output = self._agent(config)._parse_output(raw)
        # Invalid severity gets normalised to "medium"
        assert output.issues[0].severity == "medium"

    def test_verdict_auto_derived(self, config: CouncilConfig):
        """If verdict is invalid, it's derived from score."""
        raw = json.dumps({"quality_score": 4, "issues": [], "verdict": "banana"})
        output = self._agent(config)._parse_output(raw)
        assert output.verdict == "needs_work"  # score < 7

        raw2 = json.dumps({"quality_score": 8, "issues": [], "verdict": "banana"})
        output2 = self._agent(config)._parse_output(raw2)
        assert output2.verdict == "pass"  # score >= 7

    def test_score_clamp(self, config: CouncilConfig):
        raw = json.dumps({"quality_score": 99, "issues": [], "verdict": "pass"})
        output = self._agent(config)._parse_output(raw)
        assert output.quality_score == 10

    def test_empty_fallback(self, config: CouncilConfig):
        output = self._agent(config)._parse_output("")
        assert output.verdict == "pass"  # fallback is conservative

    def test_execute_async(self, config: CouncilConfig, state: AgentRunState):
        agent = self._agent(config)
        asyncio.get_event_loop().run_until_complete(agent.critique(state))
        assert len(state.critic_outputs) == 1
        assert len(state.steps) == 1
        assert state.steps[0].agent == AgentRole.critic


# ── SynthesizerAgent ──────────────────────────────────────────────────

class TestSynthesizerAgent:
    def _agent(self, config: CouncilConfig) -> SynthesizerAgent:
        return SynthesizerAgent(config)

    def test_parse_valid_json(self, config: CouncilConfig):
        raw = json.dumps({
            "content": "## Answer\nParis is the capital of France.",
            "confidence": 0.92,
            "key_points": ["Paris is the capital", "France is in Europe"],
            "citations": [
                {"source": "web", "url": "https://example.com", "title": "Wiki"},
            ],
        })
        output = self._agent(config)._parse_output(raw)
        assert isinstance(output, SynthesizerOutput)
        assert output.answer.confidence == 0.92
        assert len(output.answer.key_points) == 2
        assert len(output.answer.citations) == 1
        assert "Paris" in output.answer.content

    def test_parse_raw_text_fallback(self, config: CouncilConfig):
        """If LLM returns plain text, it becomes the content."""
        output = self._agent(config)._parse_output("Just a plain answer with no JSON.")
        assert isinstance(output, SynthesizerOutput)
        assert "plain answer" in output.answer.content
        assert output.answer.confidence == 0.0

    def test_confidence_clamp(self, config: CouncilConfig):
        raw = json.dumps({"content": "x", "confidence": 5.0})
        output = self._agent(config)._parse_output(raw)
        assert output.answer.confidence == 1.0

    def test_empty_fallback(self, config: CouncilConfig):
        output = self._agent(config)._parse_output("")
        assert "empty" in output.answer.content.lower()

    def test_execute_async(self, config: CouncilConfig, state: AgentRunState):
        agent = self._agent(config)
        asyncio.get_event_loop().run_until_complete(agent.synthesize(state))
        assert state.synthesizer_output is not None
        assert len(state.steps) == 1
        assert state.steps[0].agent == AgentRole.synthesizer


# ── Full orchestrator smoke test ──────────────────────────────────────

class TestOrchestrator:
    def test_full_pipeline_smoke(self, config: CouncilConfig, pre_ctx: PreContext):
        """Run all 4 agents end-to-end through the orchestrator."""
        from core.agentic.orchestrator import CouncilOrchestrator

        orch = CouncilOrchestrator(config)
        result = asyncio.get_event_loop().run_until_complete(orch.run(pre_ctx))
        assert result.status == RunStatus.completed
        assert result.answer is not None
        assert result.trace.run_id
        assert len(result.trace.steps) >= 4  # at least P+R+C+S


# ── Structured output serializability ─────────────────────────────────

class TestOutputSerialization:
    """All agent outputs must be JSON-serializable."""

    def test_planner_output(self):
        o = PlannerOutput(
            approach="geo lookup",
            tasks=[TaskNode(question="Q1", suggested_tools=["web_search"])],
            estimated_complexity=3,
        )
        d = json.loads(o.model_dump_json())
        assert d["tasks"][0]["question"] == "Q1"

    def test_researcher_output(self):
        o = ResearcherOutput(
            evidence=[EvidenceItem(source="web", content="fact", relevance=0.9)],
            summary="summary",
            tools_used=["web_search"],
        )
        d = json.loads(o.model_dump_json())
        assert d["evidence"][0]["source"] == "web"

    def test_critic_output(self):
        o = CriticOutput(
            quality_score=8,
            issues=[CritiqueIssue(severity="low", description="minor")],
            verdict="pass",
        )
        d = json.loads(o.model_dump_json())
        assert d["verdict"] == "pass"

    def test_synthesizer_output(self):
        o = SynthesizerOutput(answer=FinalAnswer(
            content="Answer", confidence=0.9,
            key_points=["p1"], citations=[{"source": "web"}],
        ))
        d = json.loads(o.model_dump_json())
        assert d["answer"]["confidence"] == 0.9
