"""
image_pipeline.evaluator.experiment_log — Structured benchmark recording.

Records per-case results during benchmark runs and provides aggregation
for suite-level pass/fail, category summaries, and A/B comparisons.

Data flows to storage/metadata/benchmark/<run_id>/<case_id>.json

Usage:
    log = ExperimentLog(run_id="run-001")
    log.record_case(case_id="IA-001", job=job, eval_result=result, ...)
    summary = log.summarize()
    log.save()
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from image_pipeline.job_schema import EvalResult, ImageJob, RunMetadata

logger = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"
_BENCHMARK_YAML = _CONFIGS_DIR / "benchmark_suite.yaml"
_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"
_BENCHMARK_DIR = _STORAGE_DIR / "metadata" / "benchmark"


# ── Data classes ──────────────────────────────────────────────────

@dataclass
class CaseRecord:
    """Single test case result."""
    run_id: str
    case_id: str
    timestamp: str
    stack_version: str

    # Input
    instruction: str = ""
    mode: str = ""
    references: list[str] = field(default_factory=list)
    category: str = ""
    difficulty: str = ""

    # Execution
    models_used: list[str] = field(default_factory=list)
    stages_executed: list[str] = field(default_factory=list)
    stage_timings_ms: dict[str, float] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    execution_locations: dict[str, str] = field(default_factory=dict)
    correction_rounds: int = 0

    # Evaluation
    scores: dict[str, float] = field(default_factory=dict)
    thresholds: dict[str, float] = field(default_factory=dict)
    passed_dimensions: list[str] = field(default_factory=list)
    failed_dimensions: list[str] = field(default_factory=list)
    overall_score: float = 0.0
    case_passed: bool = False
    judge_model: str = ""
    judge_reasoning: dict[str, str] = field(default_factory=dict)

    # Artifacts
    output_image_path: str = ""
    intermediate_images: list[str] = field(default_factory=list)
    prompt_lineage: list[str] = field(default_factory=list)

    # Comparison
    experiment_id: str = ""
    comparison_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CategorySummary:
    """Aggregated results for one evaluation category."""
    category: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    min_score: float = 1.0
    max_score: float = 0.0
    category_passed: bool = False       # vs category_pass_rate threshold
    failed_case_ids: list[str] = field(default_factory=list)


@dataclass
class RunSummary:
    """Suite-level benchmark summary."""
    run_id: str
    timestamp: str
    stack_version: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    overall_pass_rate: float = 0.0
    overall_avg_score: float = 0.0
    categories: dict[str, CategorySummary] = field(default_factory=dict)
    nano_banana_qualified: bool = False     # meets §13 threshold
    critical_failures: list[str] = field(default_factory=list)
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


# ── Experiment log ────────────────────────────────────────────────

class ExperimentLog:
    """
    Records benchmark results and produces suite-level summaries.

    Writes to: storage/metadata/benchmark/<run_id>/
        ├── summary.json
        ├── IA-001.json
        ├── SE-001.json
        └── ...
    """

    def __init__(
        self,
        run_id: str | None = None,
        stack_version: str | None = None,
        output_dir: str | Path | None = None,
        benchmark_cfg_path: str | Path | None = None,
    ):
        self._run_id = run_id or f"run-{int(time.time())}"
        self._stack_version = stack_version or self._detect_git_sha()
        self._output_dir = Path(output_dir or _BENCHMARK_DIR) / self._run_id
        self._records: list[CaseRecord] = []

        # Load pass/fail rules from benchmark config
        cfg = self._load_yaml(Path(benchmark_cfg_path or _BENCHMARK_YAML))
        pf = cfg.get("pass_fail", {})
        self._category_pass_rate: float = float(pf.get("category_pass_rate", 0.70))
        self._nano_threshold: float = float(pf.get("nano_banana_threshold", 0.80))
        self._critical_dims: list[str] = pf.get("critical_dimensions", [])
        self._non_blocking_dims: list[str] = pf.get("non_blocking_dimensions", [])
        self._min_cases_per_cat: int = int(pf.get("min_cases_per_category", 2))

    @property
    def run_id(self) -> str:
        return self._run_id

    # ───────────────────────────────────────────────────────────────
    # Recording
    # ───────────────────────────────────────────────────────────────

    def record_case(
        self,
        case_id: str,
        job: ImageJob,
        eval_result: EvalResult,
        run_metadata: RunMetadata | None = None,
        *,
        category: str = "",
        difficulty: str = "",
        output_image_path: str = "",
        intermediate_images: list[str] | None = None,
        experiment_id: str = "",
        comparison_notes: str = "",
    ) -> CaseRecord:
        """
        Record a single benchmark test case result.

        Args:
            case_id:            Test case ID (e.g. "IA-001")
            job:                The ImageJob that was executed
            eval_result:        The scoring result
            run_metadata:       Optional execution metadata
            category:           Evaluation category
            difficulty:         easy | medium | hard
            output_image_path:  Where the output was saved
        """
        record = CaseRecord(
            run_id=self._run_id,
            case_id=case_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stack_version=self._stack_version,
            instruction=job.user_instruction,
            mode=job.intent or "unknown",
            references=[r.label or r.role.value for r in job.reference_images],
            category=category,
            difficulty=difficulty,
            scores=dict(eval_result.scores),
            thresholds=dict(eval_result.thresholds),
            passed_dimensions=[
                d for d in eval_result.evaluated
                if d not in eval_result.failed_dimensions
            ],
            failed_dimensions=list(eval_result.failed_dimensions),
            overall_score=eval_result.overall_score,
            case_passed=eval_result.passed,
            judge_model=eval_result.judge_model,
            judge_reasoning=dict(eval_result.judge_reasoning),
            output_image_path=output_image_path,
            intermediate_images=intermediate_images or [],
            prompt_lineage=list(job.prompt_spec.prompt_lineage),
            experiment_id=experiment_id,
            comparison_notes=comparison_notes,
        )

        if run_metadata:
            record.models_used = [mu.model for mu in run_metadata.models_used]
            record.stages_executed = list(run_metadata.stage_timings.keys())
            record.stage_timings_ms = dict(run_metadata.stage_timings)
            record.total_latency_ms = run_metadata.total_latency_ms
            record.total_cost_usd = run_metadata.total_cost_usd
            record.execution_locations = dict(run_metadata.execution_map)
            record.correction_rounds = run_metadata.correction_rounds

        self._records.append(record)
        logger.info(
            "Recorded case %s: passed=%s, score=%.3f",
            case_id, record.case_passed, record.overall_score,
        )
        return record

    # ───────────────────────────────────────────────────────────────
    # Summarization
    # ───────────────────────────────────────────────────────────────

    def summarize(self) -> RunSummary:
        """
        Produce a suite-level summary from all recorded cases.

        Applies pass/fail rules from benchmark_suite.yaml:
            - Per-category pass rate must be ≥ category_pass_rate
            - "Nano Banana-like" requires overall ≥ nano_banana_threshold
            - Critical dimension failures are flagged
        """
        summary = RunSummary(
            run_id=self._run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            stack_version=self._stack_version,
            total_cases=len(self._records),
        )

        if not self._records:
            return summary

        # Aggregate per category
        cat_records: dict[str, list[CaseRecord]] = {}
        for rec in self._records:
            cat = rec.category or "uncategorized"
            cat_records.setdefault(cat, []).append(rec)

        for cat, records in cat_records.items():
            cat_summary = CategorySummary(
                category=cat,
                total_cases=len(records),
            )
            scores: list[float] = []
            for rec in records:
                scores.append(rec.overall_score)
                if rec.case_passed:
                    cat_summary.passed_cases += 1
                else:
                    cat_summary.failed_cases += 1
                    cat_summary.failed_case_ids.append(rec.case_id)

            cat_summary.pass_rate = (
                cat_summary.passed_cases / cat_summary.total_cases
                if cat_summary.total_cases > 0
                else 0.0
            )
            cat_summary.avg_score = sum(scores) / len(scores) if scores else 0.0
            cat_summary.min_score = min(scores) if scores else 0.0
            cat_summary.max_score = max(scores) if scores else 0.0
            cat_summary.category_passed = (
                cat_summary.pass_rate >= self._category_pass_rate
                and cat_summary.total_cases >= self._min_cases_per_cat
            )

            summary.categories[cat] = cat_summary

        # Overall stats
        summary.passed_cases = sum(1 for r in self._records if r.case_passed)
        summary.failed_cases = summary.total_cases - summary.passed_cases
        summary.overall_pass_rate = (
            summary.passed_cases / summary.total_cases
            if summary.total_cases > 0
            else 0.0
        )
        all_scores = [r.overall_score for r in self._records]
        summary.overall_avg_score = (
            sum(all_scores) / len(all_scores) if all_scores else 0.0
        )

        # Critical failures
        for rec in self._records:
            for dim in rec.failed_dimensions:
                if dim in self._critical_dims:
                    entry = f"{rec.case_id}:{dim}"
                    if entry not in summary.critical_failures:
                        summary.critical_failures.append(entry)

        # Nano Banana-like qualification
        summary.nano_banana_qualified = (
            summary.overall_pass_rate >= self._nano_threshold
            and len(summary.critical_failures) == 0
        )

        # Costs & latency
        summary.total_cost_usd = sum(r.total_cost_usd for r in self._records)
        summary.total_latency_ms = sum(r.total_latency_ms for r in self._records)

        return summary

    # ───────────────────────────────────────────────────────────────
    # Persistence
    # ───────────────────────────────────────────────────────────────

    def save(self) -> Path:
        """
        Write all case records and the suite summary to disk.

        Returns the output directory path.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Write individual case records
        for rec in self._records:
            case_path = self._output_dir / f"{rec.case_id}.json"
            with open(case_path, "w", encoding="utf-8") as f:
                json.dump(rec.to_dict(), f, indent=2, ensure_ascii=False)

        # Write summary
        summary = self.summarize()
        summary_path = self._output_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(
            "Saved %d case records + summary to %s",
            len(self._records), self._output_dir,
        )
        return self._output_dir

    # ───────────────────────────────────────────────────────────────
    # Comparison
    # ───────────────────────────────────────────────────────────────

    @staticmethod
    def compare_runs(
        run_a_dir: str | Path,
        run_b_dir: str | Path,
    ) -> dict[str, Any]:
        """
        Compare two benchmark runs side-by-side.

        Returns a dict with per-case score deltas and suite-level comparison.
        """
        run_a = Path(run_a_dir)
        run_b = Path(run_b_dir)

        summary_a = ExperimentLog._load_json(run_a / "summary.json")
        summary_b = ExperimentLog._load_json(run_b / "summary.json")

        if not summary_a or not summary_b:
            return {"error": "Could not load one or both summaries"}

        # Collect all case IDs from both runs
        case_ids = set()
        for f in run_a.glob("*.json"):
            if f.name != "summary.json":
                case_ids.add(f.stem)
        for f in run_b.glob("*.json"):
            if f.name != "summary.json":
                case_ids.add(f.stem)

        case_deltas: dict[str, dict[str, Any]] = {}
        for cid in sorted(case_ids):
            rec_a = ExperimentLog._load_json(run_a / f"{cid}.json")
            rec_b = ExperimentLog._load_json(run_b / f"{cid}.json")
            if rec_a and rec_b:
                case_deltas[cid] = {
                    "score_a": rec_a.get("overall_score", 0),
                    "score_b": rec_b.get("overall_score", 0),
                    "delta": rec_b.get("overall_score", 0) - rec_a.get("overall_score", 0),
                    "passed_a": rec_a.get("case_passed", False),
                    "passed_b": rec_b.get("case_passed", False),
                }

        return {
            "run_a": summary_a.get("run_id", "?"),
            "run_b": summary_b.get("run_id", "?"),
            "pass_rate_a": summary_a.get("overall_pass_rate", 0),
            "pass_rate_b": summary_b.get("overall_pass_rate", 0),
            "avg_score_a": summary_a.get("overall_avg_score", 0),
            "avg_score_b": summary_b.get("overall_avg_score", 0),
            "nano_a": summary_a.get("nano_banana_qualified", False),
            "nano_b": summary_b.get("nano_banana_qualified", False),
            "cases": case_deltas,
        }

    # ───────────────────────────────────────────────────────────────
    # Helpers
    # ───────────────────────────────────────────────────────────────

    @staticmethod
    def _detect_git_sha() -> str:
        """Best-effort git SHA detection."""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any] | None:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
