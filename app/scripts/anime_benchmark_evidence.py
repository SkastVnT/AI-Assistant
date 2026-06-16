"""Manage private anime benchmark evidence and sanitized public reports."""

from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import Counter
from pathlib import Path
from typing import Any

APP_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_ROOT = APP_ROOT / "docs" / "benchmark-reports"
PROVIDER_LABELS = {
    "chatgpt_images": "ChatGPT Images 2.0 with thinking",
    "nano_banana_2": "Nano Banana 2 (Gemini 3.1 Flash Image)",
    "nano_banana_pro": "Nano Banana Pro",
}
PROVIDER_ALIASES = {
    "chatgpt_images": "chatgpt_images",
    "chatgpt_images_2": "chatgpt_images",
    "chatgpt_pro": "chatgpt_images",
    "nano_banana_2": "nano_banana_2",
    "gemini_nano_banana_2": "nano_banana_2",
    "gemini_nano_banana": "nano_banana_2",
    "nano_banana_pro": "nano_banana_pro",
    "gemini_nano_banana_pro": "nano_banana_pro",
}
PROVIDERS = set(PROVIDER_LABELS)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _run_dir(artifact_root: str, run_id: str) -> Path:
    return Path(artifact_root).expanduser().resolve() / run_id


def _provider_id(value: str) -> str:
    key = str(value or "").strip().lower().replace("-", "_")
    try:
        return PROVIDER_ALIASES[key]
    except KeyError as exc:
        raise ValueError(f"Unknown comparator provider: {value}") from exc


def _provider_dirs(run_dir: Path, provider: str) -> list[Path]:
    aliases = [
        alias
        for alias, canonical in PROVIDER_ALIASES.items()
        if canonical == provider
    ]
    dirs = [run_dir / "comparators" / name for name in [provider, *aliases]]
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in dirs:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def import_comparator(args: argparse.Namespace) -> int:
    provider = _provider_id(args.provider)
    source = Path(args.capture_dir).expanduser().resolve()
    if not source.is_dir():
        raise FileNotFoundError(f"Comparator capture directory not found: {source}")
    target = _run_dir(args.artifact_root, args.run_id) / "comparators" / provider
    target.mkdir(parents=True, exist_ok=True)
    copied = 0
    for path in sorted(source.iterdir()):
        if path.is_file():
            shutil.copy2(path, target / path.name)
            copied += 1
    print(f"Imported {copied} {provider} captures into {target}")
    return 0


def _case_records(run_dir: Path) -> list[dict[str, Any]]:
    records = []
    for path in sorted(run_dir.glob("*.json")):
        if path.name in {
            "summary.json",
            "review_packet.json",
            "randomization_map.json",
            "comparator_verdicts.json",
        }:
            continue
        value = _read_json(path)
        if isinstance(value, dict) and value.get("case_id"):
            records.append(value)
    return records


def build_review(args: argparse.Namespace) -> int:
    run_dir = _run_dir(args.artifact_root, args.run_id)
    rng = random.Random(args.seed)
    packet: list[dict[str, Any]] = []
    private_map: dict[str, dict[str, str]] = {}
    for record in _case_records(run_dir):
        case_id = str(record["case_id"])
        candidates: dict[str, str] = {}
        local = str(record.get("output_image_path", ""))
        if local and Path(local).is_file():
            candidates["local"] = local
        for provider in sorted(PROVIDERS):
            matches = [
                match
                for capture_dir in _provider_dirs(run_dir, provider)
                for match in sorted(capture_dir.glob(f"{case_id}.*"))
            ]
            if matches:
                candidates[provider] = str(matches[0])
        if len(candidates) < 2:
            continue
        sources = sorted(candidates)
        rng.shuffle(sources)
        labels = [chr(ord("A") + index) for index in range(len(sources))]
        mapping = dict(zip(labels, sources, strict=False))
        private_map[case_id] = mapping
        packet.append(
            {
                "case_id": case_id,
                "category": record.get("category", ""),
                "candidates": [
                    {"label": label, "path": candidates[source]}
                    for label, source in mapping.items()
                ],
            }
        )
    _write_json(run_dir / "review_packet.json", {"cases": packet})
    _write_json(run_dir / "randomization_map.json", private_map)
    print(f"Built blind review packet with {len(packet)} cases in {run_dir}")
    return 0


def _capture_case_ids(run_dir: Path, provider: str) -> set[str]:
    case_ids: set[str] = set()
    for capture_dir in _provider_dirs(run_dir, provider):
        if not capture_dir.is_dir():
            continue
        for path in capture_dir.iterdir():
            if path.is_file():
                case_ids.add(path.stem)
    return case_ids


def _review_packet_case_ids(run_dir: Path) -> set[str]:
    path = run_dir / "review_packet.json"
    if not path.is_file():
        return set()
    packet = _read_json(path)
    cases = packet.get("cases", []) if isinstance(packet, dict) else []
    return {
        str(case.get("case_id"))
        for case in cases
        if isinstance(case, dict) and case.get("case_id")
    }


def _review_coverage(
    run_dir: Path,
    records: list[dict[str, Any]],
    verdicts: Any,
) -> dict[str, Any]:
    case_ids = {
        str(record.get("case_id"))
        for record in records
        if record.get("case_id")
    }
    review_case_ids = _review_packet_case_ids(run_dir)
    capture_counts = {
        provider: len(_capture_case_ids(run_dir, provider) & case_ids)
        for provider in sorted(PROVIDERS)
    }
    capture_complete = {
        provider: count == len(case_ids) and bool(case_ids)
        for provider, count in capture_counts.items()
    }
    comparator_captures_complete = all(capture_complete.values()) and bool(
        capture_complete
    )
    verdict_case_ids: set[str] = set()
    normalized_verdicts = verdicts if isinstance(verdicts, list) else []
    for verdict in normalized_verdicts:
        if isinstance(verdict, dict) and verdict.get("case_id"):
            verdict_case_ids.add(str(verdict["case_id"]))
    review_packet_complete = review_case_ids == case_ids and bool(case_ids)
    verdict_complete = verdict_case_ids == case_ids and bool(case_ids)
    return {
        "local_case_count": len(case_ids),
        "review_packet_case_count": len(review_case_ids),
        "review_packet_complete": review_packet_complete,
        "comparator_capture_case_counts": capture_counts,
        "comparator_capture_complete": capture_complete,
        "comparator_captures_complete": comparator_captures_complete,
        "verdict_case_count": len(verdict_case_ids),
        "verdict_complete": verdict_complete,
        "complete": (
            review_packet_complete
            and comparator_captures_complete
            and verdict_complete
        ),
    }


def summarize(args: argparse.Namespace) -> int:
    run_dir = _run_dir(args.artifact_root, args.run_id)
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"Benchmark summary not found: {summary_path}")
    summary = _read_json(summary_path)
    records = _case_records(run_dir)
    public_dir = Path(args.report_root).expanduser().resolve() / args.run_id

    sanitized_cases = [
        {
            "case_id": record.get("case_id"),
            "category": record.get("category"),
            "difficulty": record.get("difficulty"),
            "scores": record.get("scores", {}),
            "thresholds": record.get("thresholds", {}),
            "overall_score": record.get("overall_score", 0.0),
            "case_passed": record.get("case_passed", False),
            "judge_model": record.get("judge_model", ""),
        }
        for record in records
    ]
    verdict_path = run_dir / "comparator_verdicts.json"
    verdicts = _read_json(verdict_path) if verdict_path.is_file() else []
    counts: Counter[tuple[str, str]] = Counter()
    for verdict in verdicts if isinstance(verdicts, list) else []:
        try:
            provider = _provider_id(str(verdict.get("provider", "unknown")))
        except ValueError:
            provider = "unknown"
        outcome = str(verdict.get("verdict", "unknown"))
        counts[(provider, outcome)] += 1
    comparator = {
        provider: {
            outcome: count
            for (item_provider, outcome), count in sorted(counts.items())
            if item_provider == provider
        }
        for provider in sorted({provider for provider, _ in counts})
    }

    public_summary = {
        key: value
        for key, value in summary.items()
        if key
        not in {
            "judge_reasoning",
            "output_image_path",
            "intermediate_images",
            "prompt_lineage",
            "execution_errors",
            "nano_banana_qualified",
        }
    }
    public_summary["execution_error_count"] = len(summary.get("execution_errors", []))
    coverage = _review_coverage(run_dir, records, verdicts)
    local_gate = bool(
        summary.get(
            "local_quality_gate_passed",
            summary.get("nano_banana_qualified", False),
        )
    )
    public_summary["local_quality_gate_passed"] = local_gate
    public_summary["comparator_review_complete"] = coverage["complete"]
    public_summary["parity_evidence_complete"] = local_gate and coverage["complete"]
    _write_json(public_dir / "summary.json", public_summary)
    _write_json(public_dir / "case_scores.json", sanitized_cases)
    _write_json(
        public_dir / "provenance.json",
        {
            "run_id": args.run_id,
            "stack_version": summary.get("stack_version", "unknown"),
            "private_artifacts_stored": True,
            "raw_artifacts_published": False,
        },
    )
    _write_json(public_dir / "comparator_verdict.json", comparator)
    _write_json(public_dir / "comparator_coverage.json", coverage)
    print(f"Wrote sanitized report to {public_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    importer = subparsers.add_parser("import-comparator")
    importer.add_argument("--artifact-root", required=True)
    importer.add_argument("--run-id", required=True)
    importer.add_argument(
        "--provider",
        required=True,
        choices=sorted(PROVIDER_ALIASES),
        help="Comparator provider ID; legacy aliases are normalized",
    )
    importer.add_argument("--capture-dir", required=True)
    importer.set_defaults(handler=import_comparator)

    review = subparsers.add_parser("build-review")
    review.add_argument("--artifact-root", required=True)
    review.add_argument("--run-id", required=True)
    review.add_argument("--seed", type=int, required=True)
    review.set_defaults(handler=build_review)

    summary = subparsers.add_parser("summarize")
    summary.add_argument("--artifact-root", required=True)
    summary.add_argument("--run-id", required=True)
    summary.add_argument("--report-root", default=str(DEFAULT_REPORT_ROOT))
    summary.set_defaults(handler=summarize)

    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
