"""Tests for the RAGOps observability and evaluation layer.

Covers:
- SpanCollector tracing (span creation, nesting, timing, serialization)
- LLM-as-judge protocol (LLMJudge with mock LLM, HeuristicJudge)
- Judge output parsing (_parse_judge_output edge cases)
- Evaluation metrics (context_relevance, groundedness, answer_relevance)
- Eval harness (EvalDataset loading, evaluate_case, run_evaluation)
- Report generation (JSON and Markdown, save_report)
- EvalRun / EvalResult model instantiation
- RAGOpsSettings defaults and overrides
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from libs.ragops.eval_harness import (
    CaseResult,
    EvalCase,
    EvalDataset,
    EvalRunResult,
    evaluate_case,
    run_evaluation,
)
from libs.ragops.judge import (
    HeuristicJudge,
    JudgeResult,
    LLMJudge,
    _extract_sections,
    _parse_judge_output,
)
from libs.ragops.metrics.answer_relevance import (
    ANSWER_RELEVANCE_PROMPT,
    eval_answer_relevance,
)
from libs.ragops.metrics.context_relevance import (
    CONTEXT_RELEVANCE_PROMPT,
    eval_context_relevance,
)
from libs.ragops.metrics.groundedness import (
    GROUNDEDNESS_PROMPT,
    eval_groundedness,
)
from libs.ragops.report import (
    generate_json_report,
    generate_markdown_report,
    save_report,
)
from libs.ragops.tracing import Span, SpanCollector

# ════════════════════════════════════════════════════════════════════
# SpanCollector tracing
# ════════════════════════════════════════════════════════════════════


class TestSpan:
    def test_basic_span(self):
        s = Span(name="test", start_ns=1_000_000, end_ns=2_000_000)
        assert s.duration_ms == 1
        assert s.name == "test"

    def test_unclosed_span_has_zero_duration(self):
        s = Span(name="open", start_ns=1_000_000)
        assert s.duration_ms == 0

    def test_close_sets_end_ns(self):
        s = Span(name="closeable", start_ns=time.perf_counter_ns())
        time.sleep(0.01)
        s.close()
        assert s.end_ns is not None
        assert s.duration_ms >= 0

    def test_to_dict(self):
        s = Span(
            name="embed",
            start_ns=0,
            end_ns=5_000_000,
            metadata={"model": "text-embedding-3-small"},
        )
        d = s.to_dict()
        assert d["name"] == "embed"
        assert d["duration_ms"] == 5
        assert d["metadata"]["model"] == "text-embedding-3-small"

    def test_to_dict_with_children(self):
        parent = Span(name="parent", start_ns=0, end_ns=10_000_000)
        child = Span(name="child", start_ns=1_000_000, end_ns=5_000_000)
        parent.children.append(child)
        d = parent.to_dict()
        assert len(d["children"]) == 1
        assert d["children"][0]["name"] == "child"

    def test_to_dict_omits_empty_metadata(self):
        s = Span(name="simple", start_ns=0, end_ns=1_000_000)
        d = s.to_dict()
        assert "metadata" not in d

    def test_to_dict_omits_empty_children(self):
        s = Span(name="leaf", start_ns=0, end_ns=1_000_000)
        d = s.to_dict()
        assert "children" not in d


class TestSpanCollector:
    def test_single_span(self):
        c = SpanCollector()
        with c.span("test"):
            pass
        assert len(c.spans) == 1
        assert c.spans[0].name == "test"
        assert c.spans[0].duration_ms >= 0

    def test_nested_spans(self):
        c = SpanCollector()
        with c.span("parent"), c.span("child"):
            pass
        assert len(c.spans) == 1
        parent = c.spans[0]
        assert parent.name == "parent"
        assert len(parent.children) == 1
        assert parent.children[0].name == "child"

    def test_sequential_spans(self):
        c = SpanCollector()
        with c.span("first"):
            pass
        with c.span("second"):
            pass
        assert len(c.spans) == 2
        assert c.spans[0].name == "first"
        assert c.spans[1].name == "second"

    def test_metadata_in_span(self):
        c = SpanCollector()
        with c.span("embed", model="ada-002", dim=1536) as s:
            s.metadata["tokens"] = 42
        assert c.spans[0].metadata == {"model": "ada-002", "dim": 1536, "tokens": 42}

    def test_add_span_post_hoc(self):
        c = SpanCollector()
        c.add_span("retrieval", duration_ms=150, strategy="hybrid")
        assert len(c.spans) == 1
        assert c.spans[0].name == "retrieval"
        assert c.spans[0].metadata["strategy"] == "hybrid"

    def test_add_span_as_child(self):
        c = SpanCollector()
        with c.span("parent"):
            c.add_span("child", duration_ms=50)
        assert len(c.spans) == 1
        assert len(c.spans[0].children) == 1
        assert c.spans[0].children[0].name == "child"

    def test_total_ms(self):
        c = SpanCollector()
        with c.span("a"):
            time.sleep(0.01)
        assert c.total_ms >= 0

    def test_to_dict(self):
        c = SpanCollector()
        c.add_span("step1", duration_ms=100)
        c.add_span("step2", duration_ms=200)
        d = c.to_dict()
        assert "spans" in d
        assert "total_ms" in d
        assert len(d["spans"]) == 2

    def test_summary(self):
        c = SpanCollector()
        c.add_span("embed", duration_ms=50)
        c.add_span("search", duration_ms=100)
        s = c.summary()
        assert s["embed"] == 50
        assert s["search"] == 100

    def test_empty_collector(self):
        c = SpanCollector()
        assert c.spans == []
        assert c.total_ms == 0
        assert c.to_dict() == {"spans": [], "total_ms": 0}


# ════════════════════════════════════════════════════════════════════
# Judge — output parsing
# ════════════════════════════════════════════════════════════════════


class TestParseJudgeOutput:
    def test_clean_json(self):
        raw = '{"score": 4, "reasoning": "Good answer."}'
        result = _parse_judge_output(raw)
        assert result.score == pytest.approx(0.75)  # (4-1)/4
        assert result.reasoning == "Good answer."

    def test_markdown_fenced_json(self):
        raw = '```json\n{"score": 5, "reasoning": "Perfect."}\n```'
        result = _parse_judge_output(raw)
        assert result.score == pytest.approx(1.0)

    def test_score_1_maps_to_zero(self):
        raw = '{"score": 1, "reasoning": "Terrible."}'
        result = _parse_judge_output(raw)
        assert result.score == pytest.approx(0.0)

    def test_score_3_maps_to_half(self):
        raw = '{"score": 3, "reasoning": "Average."}'
        result = _parse_judge_output(raw)
        assert result.score == pytest.approx(0.5)

    def test_score_clamped_above(self):
        raw = '{"score": 10, "reasoning": "Out of bounds."}'
        result = _parse_judge_output(raw)
        assert result.score <= 1.0

    def test_score_clamped_below(self):
        raw = '{"score": 0, "reasoning": "Out of bounds."}'
        result = _parse_judge_output(raw)
        assert result.score >= 0.0

    def test_fallback_regex_extraction(self):
        raw = 'The "score": 4. Reasoning: The answer is relevant.'
        result = _parse_judge_output(raw)
        assert result.score == pytest.approx(0.75)

    def test_invalid_output_returns_zero(self):
        raw = "This is not parseable at all."
        result = _parse_judge_output(raw)
        assert result.score == 0.0


class TestExtractSections:
    def test_extracts_query_and_context(self):
        prompt = "Query: What is RAG?\nContext: RAG is retrieval augmented generation."
        sections = _extract_sections(prompt)
        assert "query" in sections
        assert "context" in sections
        assert "RAG" in sections["query"]

    def test_missing_sections(self):
        sections = _extract_sections("No labeled sections here.")
        assert sections == {}


# ════════════════════════════════════════════════════════════════════
# Judge — LLMJudge
# ════════════════════════════════════════════════════════════════════


class TestLLMJudge:
    @pytest.mark.asyncio
    async def test_llm_judge_evaluates(self):
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(
            return_value='{"score": 4, "reasoning": "Relevant and grounded."}'
        )
        judge = LLMJudge(mock_llm, temperature=0.0, max_tokens=256)
        result = await judge.evaluate("Rate this answer.")
        assert isinstance(result, JudgeResult)
        assert result.score == pytest.approx(0.75)
        assert "Relevant" in result.reasoning

    @pytest.mark.asyncio
    async def test_llm_judge_handles_bad_output(self):
        mock_llm = AsyncMock()
        mock_llm.complete = AsyncMock(return_value="I cannot rate this.")
        judge = LLMJudge(mock_llm)
        result = await judge.evaluate("Rate this answer.")
        assert result.score == 0.0


# ════════════════════════════════════════════════════════════════════
# Judge — HeuristicJudge
# ════════════════════════════════════════════════════════════════════


class TestHeuristicJudge:
    @pytest.mark.asyncio
    async def test_perfect_answer(self):
        judge = HeuristicJudge()
        prompt = (
            "Query: What is chunking?\n"
            "Context: Chunking splits documents into smaller pieces for embedding.\n"
            "Answer: Chunking is the process of splitting documents into smaller "
            "pieces for embedding. This improves retrieval quality by ensuring "
            "each piece is semantically focused. [Source 1]\n"
        )
        result = await judge.evaluate(prompt)
        assert result.score > 0.5

    @pytest.mark.asyncio
    async def test_empty_answer_low_score(self):
        judge = HeuristicJudge()
        prompt = "Query: What?\nContext: Something.\nAnswer:"
        result = await judge.evaluate(prompt)
        assert result.score <= 0.2

    @pytest.mark.asyncio
    async def test_no_sections_still_works(self):
        judge = HeuristicJudge()
        result = await judge.evaluate("Just plain text without sections.")
        assert isinstance(result, JudgeResult)
        assert 0.0 <= result.score <= 1.0


# ════════════════════════════════════════════════════════════════════
# Evaluation metrics
# ════════════════════════════════════════════════════════════════════


class TestContextRelevance:
    @pytest.mark.asyncio
    async def test_calls_judge(self):
        mock_judge = AsyncMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(score=0.8, reasoning="Relevant", raw_output="")
        )
        result = await eval_context_relevance(
            mock_judge, query="What is RAG?", context="RAG is retrieval augmented generation."
        )
        assert result.score == 0.8
        mock_judge.evaluate.assert_called_once()

    def test_prompt_template_exists(self):
        assert "Query:" in CONTEXT_RELEVANCE_PROMPT
        assert "Context:" in CONTEXT_RELEVANCE_PROMPT


class TestGroundedness:
    @pytest.mark.asyncio
    async def test_calls_judge(self):
        mock_judge = AsyncMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(score=0.9, reasoning="Grounded", raw_output="")
        )
        result = await eval_groundedness(
            mock_judge,
            context="RAG uses retrieval to ground answers.",
            answer="RAG grounds answers using retrieval.",
        )
        assert result.score == 0.9

    def test_prompt_template_exists(self):
        assert "Context:" in GROUNDEDNESS_PROMPT
        assert "Answer:" in GROUNDEDNESS_PROMPT


class TestAnswerRelevance:
    @pytest.mark.asyncio
    async def test_calls_judge(self):
        mock_judge = AsyncMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(score=0.7, reasoning="Relevant", raw_output="")
        )
        result = await eval_answer_relevance(
            mock_judge, query="What is RAG?", answer="RAG is a technique."
        )
        assert result.score == 0.7

    def test_prompt_template_exists(self):
        assert "Query:" in ANSWER_RELEVANCE_PROMPT
        assert "Answer:" in ANSWER_RELEVANCE_PROMPT


# ════════════════════════════════════════════════════════════════════
# Eval harness
# ════════════════════════════════════════════════════════════════════


class TestEvalCase:
    def test_minimal_case(self):
        case = EvalCase(id="c1", query="What?")
        assert case.id == "c1"
        assert case.context == ""
        assert case.answer == ""

    def test_full_case(self):
        case = EvalCase(
            id="c2",
            query="What is RAG?",
            context="RAG uses retrieval.",
            answer="RAG is a technique.",
            expected_answer="RAG stands for retrieval augmented generation.",
            tags=["factoid"],
        )
        assert case.tags == ["factoid"]


class TestEvalDataset:
    def test_from_file(self, tmp_path):
        data = {
            "name": "test_dataset",
            "cases": [
                {
                    "id": "t1",
                    "query": "What?",
                    "context": "Something.",
                    "answer": "Something.",
                }
            ],
        }
        p = tmp_path / "test.json"
        p.write_text(json.dumps(data))
        ds = EvalDataset.from_file(p)
        assert ds.name == "test_dataset"
        assert len(ds.cases) == 1

    def test_from_file_with_description(self, tmp_path):
        data = {
            "name": "ds",
            "description": "A test dataset",
            "cases": [{"id": "x", "query": "Q"}],
        }
        p = tmp_path / "ds.json"
        p.write_text(json.dumps(data))
        ds = EvalDataset.from_file(p)
        assert ds.description == "A test dataset"

    def test_sample_dataset_loads(self):
        sample_path = Path(__file__).parent.parent / "eval" / "datasets" / "sample.json"
        if sample_path.exists():
            ds = EvalDataset.from_file(sample_path)
            assert len(ds.cases) == 8


class TestEvaluateCase:
    @pytest.mark.asyncio
    async def test_full_case(self):
        mock_judge = AsyncMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(score=0.8, reasoning="Good", raw_output="")
        )
        case = EvalCase(
            id="c1",
            query="What is RAG?",
            context="RAG uses retrieval.",
            answer="RAG is retrieval augmented generation.",
        )
        result = await evaluate_case(case, mock_judge)
        assert isinstance(result, CaseResult)
        assert result.case_id == "c1"
        assert result.context_relevance is not None
        assert result.groundedness is not None
        assert result.answer_relevance is not None
        assert result.overall_score > 0
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_context_only_case(self):
        mock_judge = AsyncMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(score=0.6, reasoning="OK", raw_output="")
        )
        case = EvalCase(id="c2", query="What?", context="Stuff.")
        result = await evaluate_case(case, mock_judge)
        assert result.context_relevance is not None
        assert result.groundedness is None
        assert result.answer_relevance is None

    @pytest.mark.asyncio
    async def test_answer_only_case(self):
        mock_judge = AsyncMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(score=0.7, reasoning="OK", raw_output="")
        )
        case = EvalCase(id="c3", query="What?", answer="Something.")
        result = await evaluate_case(case, mock_judge)
        assert result.context_relevance is None
        assert result.answer_relevance is not None

    @pytest.mark.asyncio
    async def test_failing_thresholds(self):
        mock_judge = AsyncMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(score=0.1, reasoning="Bad", raw_output="")
        )
        case = EvalCase(
            id="c4", query="Q?", context="C.", answer="A.",
        )
        result = await evaluate_case(
            case, mock_judge,
            min_context_relevance=0.5,
            min_groundedness=0.5,
            min_answer_relevance=0.5,
        )
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_judge_exception_captured(self):
        mock_judge = AsyncMock()
        mock_judge.evaluate = AsyncMock(side_effect=RuntimeError("API down"))
        case = EvalCase(id="c5", query="Q?", context="C.", answer="A.")
        result = await evaluate_case(case, mock_judge)
        assert result.error is not None
        assert "API down" in result.error
        assert result.passed is False


class TestRunEvaluation:
    @pytest.mark.asyncio
    async def test_runs_all_cases(self):
        mock_judge = AsyncMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(score=0.8, reasoning="Good", raw_output="")
        )
        ds = EvalDataset(
            name="test",
            cases=[
                EvalCase(id="a", query="Q1", context="C1", answer="A1"),
                EvalCase(id="b", query="Q2", context="C2", answer="A2"),
            ],
        )
        result = await run_evaluation(ds, mock_judge)
        assert isinstance(result, EvalRunResult)
        assert result.total_cases == 2
        assert result.passed_cases == 2
        assert result.failed_cases == 0
        assert result.avg_overall > 0

    @pytest.mark.asyncio
    async def test_mixed_pass_fail(self):
        call_count = 0

        async def alternating_judge(prompt):
            nonlocal call_count
            call_count += 1
            score = 0.9 if call_count <= 3 else 0.1
            return JudgeResult(score=score, reasoning="", raw_output="")

        mock_judge = AsyncMock()
        mock_judge.evaluate = alternating_judge

        ds = EvalDataset(
            name="mixed",
            cases=[
                EvalCase(id="pass", query="Q1", context="C1", answer="A1"),
                EvalCase(id="fail", query="Q2", context="C2", answer="A2"),
            ],
        )
        result = await run_evaluation(
            ds, mock_judge,
            min_context_relevance=0.5,
            min_groundedness=0.5,
            min_answer_relevance=0.5,
        )
        assert result.total_cases == 2

    @pytest.mark.asyncio
    async def test_to_dict_serializable(self):
        mock_judge = AsyncMock()
        mock_judge.evaluate = AsyncMock(
            return_value=JudgeResult(score=0.7, reasoning="OK", raw_output="")
        )
        ds = EvalDataset(
            name="ser",
            cases=[EvalCase(id="x", query="Q", context="C", answer="A")],
        )
        result = await run_evaluation(ds, mock_judge)
        d = result.to_dict()
        serialized = json.dumps(d)
        assert len(serialized) > 0


# ════════════════════════════════════════════════════════════════════
# Report generation
# ════════════════════════════════════════════════════════════════════


class TestReportGeneration:
    @pytest.fixture
    def eval_result(self):
        return EvalRunResult(
            dataset_name="test_ds",
            case_results=[
                CaseResult(
                    case_id="c1",
                    query="What?",
                    context_relevance=0.8,
                    context_relevance_reasoning="Good context",
                    groundedness=0.9,
                    groundedness_reasoning="Well grounded",
                    answer_relevance=0.7,
                    answer_relevance_reasoning="Relevant",
                    overall_score=0.8,
                    passed=True,
                    latency_ms=100,
                ),
                CaseResult(
                    case_id="c2",
                    query="Why?",
                    context_relevance=0.3,
                    context_relevance_reasoning="Irrelevant",
                    overall_score=0.3,
                    passed=False,
                    latency_ms=50,
                ),
            ],
            total_cases=2,
            passed_cases=1,
            failed_cases=1,
            avg_context_relevance=0.55,
            avg_overall=0.55,
        )

    def test_json_report(self, eval_result):
        report = generate_json_report(eval_result)
        data = json.loads(report)
        assert data["dataset_name"] == "test_ds"
        assert "generated_at" in data
        assert data["total_cases"] == 2

    def test_markdown_report(self, eval_result):
        report = generate_markdown_report(eval_result)
        assert "# RAG Evaluation Report" in report
        assert "test_ds" in report
        assert "PASSED" in report or "FAILED" in report

    def test_markdown_contains_failed_details(self, eval_result):
        report = generate_markdown_report(eval_result)
        assert "c2" in report
        assert "Irrelevant" in report

    def test_save_report(self, eval_result, tmp_path):
        paths = save_report(eval_result, str(tmp_path), formats=("json", "md"))
        assert len(paths) == 2
        for p in paths:
            assert p.exists()
            content = p.read_text()
            assert len(content) > 0

    def test_save_report_json_only(self, eval_result, tmp_path):
        paths = save_report(eval_result, str(tmp_path), formats=("json",))
        assert len(paths) == 1
        assert paths[0].suffix == ".json"


# ════════════════════════════════════════════════════════════════════
# RAGOpsSettings defaults
# ════════════════════════════════════════════════════════════════════


class TestRAGOpsSettings:
    def test_defaults(self):
        from libs.core.settings import RAGOpsSettings

        s = RAGOpsSettings()
        assert s.tracing_enabled is True
        assert s.eval_judge_model == "gpt-4o-mini"
        assert s.eval_judge_temperature == 0.0
        assert s.min_context_relevance == 0.5
        assert s.min_groundedness == 0.5
        assert s.min_answer_relevance == 0.5

    def test_settings_has_ragops(self):
        from libs.core.settings import Settings

        # Settings instantiation may raise due to missing env vars;
        # just verify the field exists in the model
        assert "ragops" in Settings.model_fields


# ════════════════════════════════════════════════════════════════════
# EvalRun / EvalResult models
# ════════════════════════════════════════════════════════════════════


class TestEvalModels:
    def test_eval_run_instantiation(self):
        from libs.core.models import EvalRun

        run = EvalRun(
            tenant_id=uuid4(),
            name="test_run",
            dataset_name="sample",
            status="pending",
            total_cases=10,
        )
        assert run.name == "test_run"
        assert run.status == "pending"

    def test_eval_result_instantiation(self):
        from libs.core.models import EvalResult

        result = EvalResult(
            run_id=uuid4(),
            case_id="c1",
            query="What?",
            context_relevance=0.8,
            groundedness=0.9,
            answer_relevance=0.7,
            overall_score=0.8,
            passed=True,
        )
        assert result.case_id == "c1"
        assert result.passed is True
