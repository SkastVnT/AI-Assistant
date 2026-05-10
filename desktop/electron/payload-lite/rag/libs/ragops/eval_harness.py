"""Evaluation harness — runs eval datasets and collects scored results.

Supports two modes:
1. **Offline evaluation**: evaluates pre-recorded query/context/answer triples
   (no live DB or LLM generation needed — only the judge LLM).
2. **Live evaluation**: runs queries through the full pipeline and evaluates
   the actual retrieval + generation output.

The offline mode is used for CI; live mode for full regression testing.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from libs.ragops.judge import Judge
from libs.ragops.metrics.answer_relevance import eval_answer_relevance
from libs.ragops.metrics.context_relevance import eval_context_relevance
from libs.ragops.metrics.groundedness import eval_groundedness

logger = logging.getLogger("rag.ragops.eval_harness")


# ── Dataset schema ─────────────────────────────────────────────────────────


@dataclass
class EvalCase:
    """A single test case from an evaluation dataset."""

    id: str
    query: str
    context: str = ""
    expected_answer: str = ""
    answer: str = ""  # pre-recorded or will be filled by live eval
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class EvalDataset:
    """Collection of evaluation cases."""

    name: str
    cases: list[EvalCase]
    description: str = ""

    @classmethod
    def from_file(cls, path: str | Path) -> EvalDataset:
        """Load dataset from a JSON file."""
        p = Path(path)
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        cases = [
            EvalCase(
                id=c["id"],
                query=c["query"],
                context=c.get("context", ""),
                expected_answer=c.get("expected_answer", ""),
                answer=c.get("answer", ""),
                tags=c.get("tags", []),
                metadata=c.get("metadata", {}),
            )
            for c in data.get("cases", [])
        ]
        return cls(
            name=data.get("name", p.stem),
            cases=cases,
            description=data.get("description", ""),
        )


# ── Evaluation result ──────────────────────────────────────────────────────


@dataclass
class CaseResult:
    """Scored result for a single evaluation case."""

    case_id: str
    query: str
    # Retriever metric
    context_relevance: float | None = None
    context_relevance_reasoning: str = ""
    # Generator metrics
    groundedness: float | None = None
    groundedness_reasoning: str = ""
    answer_relevance: float | None = None
    answer_relevance_reasoning: str = ""
    # Aggregate
    overall_score: float | None = None
    passed: bool = True
    latency_ms: int = 0
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "query": self.query,
            "context_relevance": self.context_relevance,
            "context_relevance_reasoning": self.context_relevance_reasoning,
            "groundedness": self.groundedness,
            "groundedness_reasoning": self.groundedness_reasoning,
            "answer_relevance": self.answer_relevance,
            "answer_relevance_reasoning": self.answer_relevance_reasoning,
            "overall_score": self.overall_score,
            "passed": self.passed,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass
class EvalRunResult:
    """Aggregate result for a full evaluation run."""

    dataset_name: str
    case_results: list[CaseResult]
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    avg_context_relevance: float = 0.0
    avg_groundedness: float = 0.0
    avg_answer_relevance: float = 0.0
    avg_overall: float = 0.0
    total_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "dataset_name": self.dataset_name,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "avg_context_relevance": round(self.avg_context_relevance, 3),
            "avg_groundedness": round(self.avg_groundedness, 3),
            "avg_answer_relevance": round(self.avg_answer_relevance, 3),
            "avg_overall": round(self.avg_overall, 3),
            "total_ms": self.total_ms,
            "cases": [c.to_dict() for c in self.case_results],
        }


# ── Evaluation runner ──────────────────────────────────────────────────────


async def evaluate_case(
    case: EvalCase,
    judge: Judge,
    *,
    min_context_relevance: float = 0.5,
    min_groundedness: float = 0.5,
    min_answer_relevance: float = 0.5,
) -> CaseResult:
    """Evaluate a single case using all applicable metrics.

    - If context is provided: scores context_relevance (retriever eval)
    - If answer is provided: scores groundedness + answer_relevance (generator eval)
    """
    t_start = time.perf_counter()
    result = CaseResult(case_id=case.id, query=case.query)

    try:
        # ── Retriever evaluation ──────────────────────────────────
        if case.context:
            cr = await eval_context_relevance(
                judge, query=case.query, context=case.context,
            )
            result.context_relevance = cr.score
            result.context_relevance_reasoning = cr.reasoning

        # ── Generator evaluation ──────────────────────────────────
        if case.answer and case.context:
            gr = await eval_groundedness(
                judge, context=case.context, answer=case.answer,
            )
            result.groundedness = gr.score
            result.groundedness_reasoning = gr.reasoning

        if case.answer:
            ar = await eval_answer_relevance(
                judge, query=case.query, answer=case.answer,
            )
            result.answer_relevance = ar.score
            result.answer_relevance_reasoning = ar.reasoning

        # ── Aggregate ─────────────────────────────────────────────
        scores = [
            s for s in [
                result.context_relevance,
                result.groundedness,
                result.answer_relevance,
            ] if s is not None
        ]
        if scores:
            result.overall_score = sum(scores) / len(scores)

        # ── Pass/fail ─────────────────────────────────────────────
        result.passed = True
        if (
            result.context_relevance is not None
            and result.context_relevance < min_context_relevance
        ):
            result.passed = False
        if result.groundedness is not None and result.groundedness < min_groundedness:
            result.passed = False
        if result.answer_relevance is not None and result.answer_relevance < min_answer_relevance:
            result.passed = False
    except Exception as exc:
        logger.exception("eval_case_error case=%s: %s", case.id, exc)
        result.error = str(exc)
        result.passed = False

    result.latency_ms = int((time.perf_counter() - t_start) * 1000)
    return result


async def run_evaluation(
    dataset: EvalDataset,
    judge: Judge,
    *,
    min_context_relevance: float = 0.5,
    min_groundedness: float = 0.5,
    min_answer_relevance: float = 0.5,
) -> EvalRunResult:
    """Run evaluation over an entire dataset.

    Evaluates each case sequentially (to respect LLM rate limits)
    and aggregates results.
    """
    t_start = time.perf_counter()
    case_results: list[CaseResult] = []

    for case in dataset.cases:
        cr = await evaluate_case(
            case,
            judge,
            min_context_relevance=min_context_relevance,
            min_groundedness=min_groundedness,
            min_answer_relevance=min_answer_relevance,
        )
        case_results.append(cr)
        logger.info(
            "eval_case id=%s overall=%.2f passed=%s latency=%dms",
            cr.case_id,
            cr.overall_score or 0,
            cr.passed,
            cr.latency_ms,
        )

    # ── Aggregate ─────────────────────────────────────────────────
    total = len(case_results)
    passed = sum(1 for c in case_results if c.passed)
    failed = total - passed

    def _avg(attr: str) -> float:
        vals = [getattr(c, attr) for c in case_results if getattr(c, attr) is not None]
        return sum(vals) / len(vals) if vals else 0.0

    result = EvalRunResult(
        dataset_name=dataset.name,
        case_results=case_results,
        total_cases=total,
        passed_cases=passed,
        failed_cases=failed,
        avg_context_relevance=_avg("context_relevance"),
        avg_groundedness=_avg("groundedness"),
        avg_answer_relevance=_avg("answer_relevance"),
        avg_overall=_avg("overall_score"),
        total_ms=int((time.perf_counter() - t_start) * 1000),
    )

    logger.info(
        "eval_run dataset=%s total=%d passed=%d failed=%d "
        "avg_cr=%.2f avg_gr=%.2f avg_ar=%.2f",
        dataset.name, total, passed, failed,
        result.avg_context_relevance,
        result.avg_groundedness,
        result.avg_answer_relevance,
    )

    return result
