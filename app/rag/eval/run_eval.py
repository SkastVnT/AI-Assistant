"""CLI entry point for running RAG evaluations.

Usage:
    python -m eval.run_eval --dataset eval/datasets/sample.json
    python -m eval.run_eval --dataset eval/datasets/sample.json --output eval/reports
    python -m eval.run_eval --dataset eval/datasets/sample.json --judge heuristic
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Ensure project root is on path
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from libs.ragops.eval_harness import EvalDataset, run_evaluation  # noqa: E402
from libs.ragops.judge import HeuristicJudge  # noqa: E402
from libs.ragops.report import save_report  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run RAG evaluation suite")
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to evaluation dataset JSON file",
    )
    parser.add_argument(
        "--output",
        default="eval/reports",
        help="Output directory for reports (default: eval/reports)",
    )
    parser.add_argument(
        "--judge",
        choices=["heuristic", "llm"],
        default="heuristic",
        help="Judge type (default: heuristic for CI)",
    )
    parser.add_argument(
        "--min-context-relevance",
        type=float,
        default=0.5,
        help="Minimum context relevance score to pass",
    )
    parser.add_argument(
        "--min-groundedness",
        type=float,
        default=0.5,
        help="Minimum groundedness score to pass",
    )
    parser.add_argument(
        "--min-answer-relevance",
        type=float,
        default=0.5,
        help="Minimum answer relevance score to pass",
    )
    args = parser.parse_args()

    # Load dataset
    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        print(f"ERROR: Dataset not found: {dataset_path}", file=sys.stderr)
        return 1

    dataset = EvalDataset.from_file(dataset_path)
    print(f"Loaded dataset '{dataset.name}' with {len(dataset.cases)} cases")

    # Create judge
    if args.judge == "heuristic":
        judge = HeuristicJudge()
    else:
        # LLM judge requires API key — import and create
        try:
            # This would need a real LLM provider instance
            print(
                "ERROR: LLM judge requires a configured LLM provider. "
                "Use --judge heuristic for CI.",
                file=sys.stderr,
            )
            return 1
        except Exception as e:
            print(f"ERROR: Failed to create LLM judge: {e}", file=sys.stderr)
            return 1

    # Run evaluation
    result = await run_evaluation(
        dataset,
        judge,
        min_context_relevance=args.min_context_relevance,
        min_groundedness=args.min_groundedness,
        min_answer_relevance=args.min_answer_relevance,
    )

    # Save reports
    paths = save_report(result, args.output)
    for p in paths:
        print(f"Report saved: {p}")

    # Print summary
    print()
    print(f"{'=' * 50}")
    print(f"  Dataset:            {result.dataset_name}")
    print(f"  Total cases:        {result.total_cases}")
    print(f"  Passed:             {result.passed_cases}")
    print(f"  Failed:             {result.failed_cases}")
    print(f"  Avg Context Rel.:   {result.avg_context_relevance:.3f}")
    print(f"  Avg Groundedness:   {result.avg_groundedness:.3f}")
    print(f"  Avg Answer Rel.:    {result.avg_answer_relevance:.3f}")
    print(f"  Avg Overall:        {result.avg_overall:.3f}")
    print(f"  Duration:           {result.total_ms}ms")
    print(f"{'=' * 50}")

    # Exit code: 0 if all passed, 1 if any failed
    return 0 if result.failed_cases == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
