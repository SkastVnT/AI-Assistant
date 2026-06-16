"""Run the 48-case LOCAL anime benchmark with real pipeline wiring."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from image_pipeline.evaluator.anime_benchmark_adapter import (
    build_local_anime_benchmark_runner,
)

PROFILES = ("laptop_6gb", "pc_12gb", "rtx5070", "vps_96gb")


def _configure_benchmark_env(profile: str, suite: str) -> str:
    """Apply benchmark-local env so profile/suite selection is deterministic."""

    selected_suite = "sfw" if suite == "auto" else suite
    os.environ["ANIME_PIPELINE_PROFILE"] = profile
    os.environ.pop("ANIME_PIPELINE_CONFIG", None)
    if selected_suite == "sfw":
        os.environ["ANIME_PIPELINE_ADULT_CONTENT_POLICY"] = "sfw_only"
    return selected_suite


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--cases", nargs="*", default=None)
    parser.add_argument("--categories", nargs="*", default=None)
    parser.add_argument(
        "--profile",
        choices=PROFILES,
        default="pc_12gb",
        help="Named LOCAL anime pipeline profile; defaults to the quality benchmark profile",
    )
    parser.add_argument(
        "--suite",
        choices=("auto", "sfw", "adult_only"),
        default="sfw",
        help="Benchmark suite. auto resolves to sfw; adult_only must be explicit.",
    )
    parser.add_argument(
        "--adult-verified",
        action="store_true",
        help="Confirm that the local adult fixture pack contains verified adults",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Exercise suite wiring only; never use dry-run results for parity claims",
    )
    parser.add_argument(
        "--artifact-root",
        default=None,
        help="Private fixture/output root for adult-only evidence runs",
    )
    parser.add_argument(
        "--parity",
        action="store_true",
        help="Require parity preflight checks; incompatible with --dry-run",
    )
    args = parser.parse_args()
    selected_suite = _configure_benchmark_env(args.profile, args.suite)
    if selected_suite == "adult_only" and not args.adult_verified:
        parser.error("--suite adult_only requires --adult-verified")
    runner = build_local_anime_benchmark_runner(
        suite=selected_suite,
        adult_verified=args.adult_verified,
        artifact_root=args.artifact_root,
    )
    asyncio.run(
        runner.run_suite(
            run_id=args.run_id,
            case_ids=args.cases,
            categories=args.categories,
            dry_run=args.dry_run,
            adult_verified=args.adult_verified,
            parity=args.parity,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
