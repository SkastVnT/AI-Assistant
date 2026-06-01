"""Run the 48-case LOCAL anime benchmark with real pipeline wiring."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from image_pipeline.evaluator.anime_benchmark_adapter import (
    build_local_anime_benchmark_runner,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--cases", nargs="*", default=None)
    parser.add_argument("--categories", nargs="*", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Exercise suite wiring only; never use dry-run results for parity claims",
    )
    args = parser.parse_args()
    runner = build_local_anime_benchmark_runner()
    asyncio.run(
        runner.run_suite(
            run_id=args.run_id,
            case_ids=args.cases,
            categories=args.categories,
            dry_run=args.dry_run,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

