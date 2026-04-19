"""
OutputManifest builder — construct output_manifest.json from a completed job.

The manifest summarises the full pipeline execution: every pass with its
model and timing, critique rounds, the selected final image, runner-up
info (when debug mode is on), and aggregate statistics.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from ..schemas import AnimePipelineJob, RankResult

logger = logging.getLogger(__name__)


def build_output_manifest(
    job: AnimePipelineJob,
    rank_result: Optional[RankResult] = None,
    *,
    debug_mode: bool = False,
    vram_profile: str = "normalvram",
) -> dict[str, Any]:
    """Build a JSON-serialisable manifest dict from a completed job.

    Parameters
    ----------
    job : AnimePipelineJob
        The completed (or failed) pipeline job.
    rank_result : RankResult, optional
        Final ranking data.  When provided, winner and runner-up info
        is included in the manifest.
    debug_mode : bool
        When True, runner-up candidates are included in the manifest.
    vram_profile : str
        VRAM profile used during this run (e.g. "normalvram", "lowvram").

    Returns
    -------
    dict
        The manifest dictionary, ready for ``json.dumps()``.
    """
    passes = _build_pass_list(job)

    manifest: dict[str, Any] = {
        "job_id": job.job_id,
        "status": job.status.value,
        "preset": job.preset,
        "vram_profile": vram_profile,
        "passes": passes,
        "critique_rounds": len(job.critique_results),
        "refine_rounds": job.refine_rounds,
        "models_used": job.models_used,
        "total_latency_ms": round(job.total_latency_ms, 1),
        "selected_final": _selected_final_stage(job, rank_result),
    }

    if rank_result and rank_result.winner:
        manifest["winner"] = rank_result.winner.to_dict()
        manifest["total_candidates"] = rank_result.total_candidates

    if debug_mode and rank_result:
        manifest["runner_ups"] = [r.to_dict() for r in rank_result.runner_ups]
        manifest["stage_timings_ms"] = dict(job.stage_timings_ms)

    if job.error:
        manifest["error"] = job.error

    return manifest


def manifest_to_json(
    job: AnimePipelineJob,
    rank_result: Optional[RankResult] = None,
    *,
    debug_mode: bool = False,
    indent: int = 2,
    vram_profile: str = "normalvram",
) -> str:
    """Build manifest and serialise to a JSON string."""
    data = build_output_manifest(
        job, rank_result, debug_mode=debug_mode, vram_profile=vram_profile,
    )
    return json.dumps(data, ensure_ascii=False, indent=indent)


# ── Internal helpers ──────────────────────────────────────────────

def _build_pass_list(job: AnimePipelineJob) -> list[dict[str, Any]]:
    """Build the ordered pass list from job execution data."""
    passes: list[dict[str, Any]] = []
    for stage in job.stages_executed:
        entry: dict[str, Any] = {
            "name": stage,
            "duration_ms": round(job.stage_timings_ms.get(stage, 0.0), 1),
        }
        # Attach model info if we can find it
        model = _model_for_stage(stage, job)
        if model:
            entry["model"] = model
        # Attach output filename convention
        entry["output"] = _output_filename(stage)
        passes.append(entry)
    return passes


def _model_for_stage(stage: str, job: AnimePipelineJob) -> Optional[str]:
    """Resolve the model used for a given stage from intermediates metadata."""
    for img in job.intermediates:
        if img.stage == stage:
            model = img.metadata.get("model") or img.metadata.get("checkpoint")
            if model:
                return model
    return None


_STAGE_FILENAMES: dict[str, str] = {
    "composition": "01_composition.png",
    "composition_pass": "01_composition.png",
    "structure_lock": "02_structure.png",
    "cleanup": "03_cleanup.png",
    "cleanup_pass": "03_cleanup.png",
    "beauty_pass": "04_beauty.png",
    "refine_beauty": "04_beauty_refined.png",
    "pre_upscale": "04_pre_upscale.png",
    "upscale": "05_upscaled.png",
}


def _output_filename(stage: str) -> str:
    """Map a stage name to its conventional output filename."""
    return _STAGE_FILENAMES.get(stage, f"{stage}.png")


def _selected_final_stage(
    job: AnimePipelineJob, rank_result: Optional[RankResult],
) -> str:
    """Determine which stage produced the selected final image."""
    if rank_result and rank_result.winner:
        return rank_result.winner.stage
    # Fallback: last stage that produced a final image
    if job.final_image_b64:
        for img in reversed(job.intermediates):
            if img.image_b64 == job.final_image_b64:
                return img.stage
    return "unknown"
