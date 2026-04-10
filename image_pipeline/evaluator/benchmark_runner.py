"""
image_pipeline.evaluator.benchmark_runner — CLI/programmatic benchmark executor.

Loads test cases from configs/benchmark_suite.yaml, runs them through the
pipeline, scores each with the Scorer, records results via ExperimentLog,
and prints a suite summary.

Usage (CLI):
    python -m image_pipeline.evaluator.benchmark_runner --run-id run-001 --dry-run
    python -m image_pipeline.evaluator.benchmark_runner --cases IA-001 SE-002

Usage (programmatic):
    runner = BenchmarkRunner()
    summary = await runner.run_suite(case_ids=["IA-001", "SE-002"])
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

from image_pipeline.evaluator.experiment_log import ExperimentLog, RunSummary
from image_pipeline.evaluator.scorer import Scorer
from image_pipeline.job_schema import (
    EvalResult,
    ImageJob,
    PromptSpec,
    ReferenceImage,
    ReferenceRole,
    GenerationParams,
)

logger = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"
_BENCHMARK_YAML = _CONFIGS_DIR / "benchmark_suite.yaml"


class BenchmarkRunner:
    """
    Executes benchmark test cases and records results.

    In dry-run mode, produces stub results without calling any model.
    In live mode, integrates with the full pipeline.
    """

    def __init__(
        self,
        benchmark_path: str | Path | None = None,
        scorer: Scorer | None = None,
        pipeline_fn: Any = None,   # async (ImageJob) -> (output_path, RunMetadata)
    ):
        self._benchmark_path = Path(benchmark_path or _BENCHMARK_YAML)
        self._test_cases = self._load_test_cases()
        self._scorer = scorer
        self._pipeline_fn = pipeline_fn

        logger.info(
            "BenchmarkRunner: %d test cases loaded",
            len(self._test_cases),
        )

    # ───────────────────────────────────────────────────────────────
    # Public API
    # ───────────────────────────────────────────────────────────────

    async def run_suite(
        self,
        run_id: str | None = None,
        case_ids: list[str] | None = None,
        categories: list[str] | None = None,
        dry_run: bool = False,
    ) -> RunSummary:
        """
        Run the full benchmark suite or a filtered subset.

        Args:
            run_id:     Identifier for this benchmark run.
            case_ids:   Specific case IDs to run (None = all).
            categories: Filter by category (None = all).
            dry_run:    Generate stub scores without calling models.

        Returns:
            RunSummary with all aggregated results.
        """
        experiment = ExperimentLog(run_id=run_id)

        # Filter cases
        cases = self._filter_cases(case_ids, categories)
        logger.info(
            "Running %d/%d test cases (run_id=%s, dry_run=%s)",
            len(cases), len(self._test_cases),
            experiment.run_id, dry_run,
        )

        for case in cases:
            case_id = case["id"]
            logger.info("── Case %s (%s, %s) ──", case_id, case.get("category"), case.get("difficulty"))

            try:
                job = self._case_to_job(case)

                if dry_run:
                    eval_result = self._stub_eval(job, case)
                    output_path = ""
                    run_meta = None
                elif self._pipeline_fn and self._scorer:
                    output_path, run_meta = await self._pipeline_fn(job)
                    eval_result = await self._scorer.score(job, output_path)
                else:
                    logger.warning(
                        "No pipeline or scorer configured; using stub for %s",
                        case_id,
                    )
                    eval_result = self._stub_eval(job, case)
                    output_path = ""
                    run_meta = None

                experiment.record_case(
                    case_id=case_id,
                    job=job,
                    eval_result=eval_result,
                    run_metadata=run_meta,
                    category=case.get("category", ""),
                    difficulty=case.get("difficulty", ""),
                    output_image_path=str(output_path),
                )

            except Exception as e:
                logger.error("Case %s failed: %s", case_id, str(e)[:500])
                # Record failure with zero scores
                job = self._case_to_job(case)
                dims = case.get("dimensions", ["instruction_adherence"])
                fail_result = EvalResult(
                    scores={d: 0.0 for d in dims},
                    evaluated=dims,
                    judge_model="error",
                )
                fail_result.evaluate()
                experiment.record_case(
                    case_id=case_id,
                    job=job,
                    eval_result=fail_result,
                    category=case.get("category", ""),
                    difficulty=case.get("difficulty", ""),
                )

        # Save results
        output_dir = experiment.save()
        summary = experiment.summarize()

        self._print_summary(summary)
        logger.info("Results saved to: %s", output_dir)

        return summary

    # ───────────────────────────────────────────────────────────────
    # Case loading / filtering
    # ───────────────────────────────────────────────────────────────

    def _load_test_cases(self) -> list[dict[str, Any]]:
        if not self._benchmark_path.exists():
            logger.warning("Benchmark file not found: %s", self._benchmark_path)
            return []
        with open(self._benchmark_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("test_cases", [])

    def _filter_cases(
        self,
        case_ids: list[str] | None = None,
        categories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        cases = self._test_cases
        if case_ids:
            cases = [c for c in cases if c["id"] in case_ids]
        if categories:
            cases = [c for c in cases if c.get("category") in categories]
        return cases

    # ───────────────────────────────────────────────────────────────
    # Case → ImageJob conversion
    # ───────────────────────────────────────────────────────────────

    @staticmethod
    def _case_to_job(case: dict[str, Any]) -> ImageJob:
        """Convert a benchmark test case dict into an ImageJob."""
        setup = case.get("setup", {})

        # Handle multi-turn: use the last instruction
        instruction = case.get("instruction", "")
        turns = case.get("turns")
        if turns and isinstance(turns, list):
            instruction = turns[-1].get("instruction", instruction)

        job = ImageJob(
            user_instruction=instruction,
            intent=setup.get("mode", "t2i"),
            language=setup.get("language", "en"),
        )

        # Source image for edit modes
        source = setup.get("source_image")
        if source:
            job.source_image_url = source
            # Set intent to semantic_edit if not already an edit-like mode
            if job.intent and "edit" not in job.intent and "correction" not in job.intent:
                pass  # Keep the setup-provided mode

        # Reference images
        for ref_cfg in setup.get("references", []):
            role_str = ref_cfg.get("role", "full")
            try:
                role = ReferenceRole(role_str)
            except ValueError:
                role = ReferenceRole.FULL
            job.reference_images.append(ReferenceImage(
                role=role,
                image_url=ref_cfg.get("image", ""),
                label=ref_cfg.get("note", ""),
            ))

        # Expected constraints
        expected = case.get("expected", {})
        job.must_keep = expected.get("must_preserve", [])
        if isinstance(job.must_keep, str):
            job.must_keep = [job.must_keep]

        return job

    # ───────────────────────────────────────────────────────────────
    # Dry-run stub
    # ───────────────────────────────────────────────────────────────

    @staticmethod
    def _stub_eval(job: ImageJob, case: dict[str, Any]) -> EvalResult:
        """
        Generate a deterministic stub EvalResult for dry-run mode.

        Scores are based on difficulty:
            easy   → 0.85
            medium → 0.72
            hard   → 0.58
        """
        difficulty_scores = {"easy": 0.85, "medium": 0.72, "hard": 0.58}
        base = difficulty_scores.get(case.get("difficulty", "medium"), 0.72)

        dims = case.get("dimensions", ["instruction_adherence"])
        result = EvalResult(
            scores={dim: base for dim in dims},
            evaluated=dims,
            judge_model="dry-run-stub",
            judge_reasoning={dim: f"Stub score for {case.get('difficulty', 'medium')} difficulty" for dim in dims},
        )
        result.evaluate()
        return result

    # ───────────────────────────────────────────────────────────────
    # Output formatting
    # ───────────────────────────────────────────────────────────────

    @staticmethod
    def _print_summary(summary: RunSummary) -> None:
        """Print a formatted summary to stdout."""
        print("\n" + "=" * 70)
        print(f"  BENCHMARK SUMMARY — {summary.run_id}")
        print("=" * 70)
        print(f"  Timestamp:    {summary.timestamp}")
        print(f"  Stack:        {summary.stack_version}")
        print(f"  Cases:        {summary.passed_cases}/{summary.total_cases} passed")
        print(f"  Pass rate:    {summary.overall_pass_rate:.1%}")
        print(f"  Avg score:    {summary.overall_avg_score:.3f}")
        print(f"  Total cost:   ${summary.total_cost_usd:.3f}")

        if summary.categories:
            print("\n  Category breakdown:")
            for cat, cs in sorted(summary.categories.items()):
                status = "PASS" if cs.category_passed else "FAIL"
                print(
                    f"    {cat:30s}  {cs.passed_cases}/{cs.total_cases} "
                    f"({cs.pass_rate:.0%})  avg={cs.avg_score:.3f}  [{status}]"
                )
                if cs.failed_case_ids:
                    print(f"      Failed: {', '.join(cs.failed_case_ids)}")

        if summary.critical_failures:
            print(f"\n  CRITICAL FAILURES: {', '.join(summary.critical_failures)}")

        nano_label = "YES" if summary.nano_banana_qualified else "NO"
        print(f"\n  Nano Banana-like qualified: {nano_label}")
        print("=" * 70 + "\n")


# ── CLI entry point ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Run image pipeline benchmark suite",
    )
    parser.add_argument("--run-id", default=None, help="Run identifier")
    parser.add_argument(
        "--cases", nargs="*", default=None,
        help="Specific case IDs to run (e.g. IA-001 SE-002)",
    )
    parser.add_argument(
        "--categories", nargs="*", default=None,
        help="Filter by category",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Generate stub scores without calling models",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    runner = BenchmarkRunner()

    summary = asyncio.run(runner.run_suite(
        run_id=args.run_id,
        case_ids=args.cases,
        categories=args.categories,
        dry_run=args.dry_run,
    ))

    sys.exit(0 if summary.nano_banana_qualified else 1)


if __name__ == "__main__":
    main()
