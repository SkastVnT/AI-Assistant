"""Report generator — produces Markdown and JSON evaluation reports.

Generates a readable summary of an evaluation run for CI artifacts,
PR comments, or dashboards.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from libs.ragops.eval_harness import EvalRunResult


def generate_json_report(result: EvalRunResult) -> str:
    """Generate a JSON report string."""
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        **result.to_dict(),
    }
    return json.dumps(report, indent=2, ensure_ascii=False)


def generate_markdown_report(result: EvalRunResult) -> str:
    """Generate a human-readable Markdown report."""
    status = "PASSED" if result.failed_cases == 0 else "FAILED"
    status_icon = "&#x2705;" if status == "PASSED" else "&#x274C;"

    lines = [
        f"# RAG Evaluation Report {status_icon}",
        "",
        f"**Dataset:** {result.dataset_name}",
        f"**Status:** {status}",
        f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Summary",
        "",
        "| Metric | Score |",
        "|--------|-------|",
        f"| Context Relevance (avg) | {result.avg_context_relevance:.3f} |",
        f"| Groundedness (avg) | {result.avg_groundedness:.3f} |",
        f"| Answer Relevance (avg) | {result.avg_answer_relevance:.3f} |",
        f"| Overall (avg) | {result.avg_overall:.3f} |",
        "",
        f"**Cases:** {result.total_cases} total, "
        f"{result.passed_cases} passed, {result.failed_cases} failed",
        f"**Duration:** {result.total_ms}ms",
        "",
        "## Per-Case Results",
        "",
        "| Case | Context Rel. | Groundedness | Answer Rel. "
        "| Overall | Status |",
        "|------|-------------|-------------|-------------|"
        "---------|--------|",
    ]

    for c in result.case_results:
        cr = f"{c.context_relevance:.2f}" if c.context_relevance is not None else "-"
        gr = f"{c.groundedness:.2f}" if c.groundedness is not None else "-"
        ar = f"{c.answer_relevance:.2f}" if c.answer_relevance is not None else "-"
        ov = f"{c.overall_score:.2f}" if c.overall_score is not None else "-"
        st = "PASS" if c.passed else "FAIL"
        lines.append(
            f"| {c.case_id} | {cr} | {gr} | {ar} | {ov} | {st} |"
        )

    # ── Failed case details ───────────────────────────────────────
    failed = [c for c in result.case_results if not c.passed]
    if failed:
        lines.extend(["", "## Failed Cases", ""])
        for c in failed:
            lines.append(f"### {c.case_id}")
            lines.append(f"**Query:** {c.query}")
            if c.error:
                lines.append(f"**Error:** {c.error}")
            if c.context_relevance_reasoning:
                lines.append(
                    f"**Context Relevance ({c.context_relevance:.2f}):** "
                    f"{c.context_relevance_reasoning}"
                )
            if c.groundedness_reasoning:
                lines.append(
                    f"**Groundedness ({c.groundedness:.2f}):** "
                    f"{c.groundedness_reasoning}"
                )
            if c.answer_relevance_reasoning:
                lines.append(
                    f"**Answer Relevance ({c.answer_relevance:.2f}):** "
                    f"{c.answer_relevance_reasoning}"
                )
            lines.append("")

    return "\n".join(lines)


def save_report(
    result: EvalRunResult,
    output_dir: str | Path,
    *,
    formats: tuple[str, ...] = ("json", "md"),
) -> list[Path]:
    """Save report to disk in specified formats.

    Returns list of paths written.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    if "json" in formats:
        json_path = out / "eval_report.json"
        json_path.write_text(generate_json_report(result), encoding="utf-8")
        paths.append(json_path)

    if "md" in formats:
        md_path = out / "eval_report.md"
        md_path.write_text(generate_markdown_report(result), encoding="utf-8")
        paths.append(md_path)

    return paths
