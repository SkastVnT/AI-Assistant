"""
image_pipeline.anime_pipeline.result_store — Save intermediates, metadata, and final outputs.

Handles:
  - Saving intermediate images per stage
  - Writing output_manifest.json
  - Storing final image to configured location
  - File naming convention per SKILL spec
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from .schemas import AnimePipelineJob

logger = logging.getLogger(__name__)

# ── File naming convention ────────────────────────────────────────────
_STAGE_FILE_PREFIX = {
    "composition": "01_composition",
    "structure_lock": "02",
    "cleanup": "03_cleanup",
    "beauty": "04_beauty",
    "upscale": "05_upscaled",
}

_HINT_FILE_NAMES = {
    "lineart_anime": "02_lineart",
    "lineart": "02_lineart",
    "depth": "02_depth",
    "canny": "02_canny",
}


# ── Spec §7: canonical filename helper ───────────────────────────────
# Format: <session>_<feature>_<char>_<series>_<ts>.<ext>
#   session = first 8 chars of job.job_id  (short but unique per run)
#   feature = stage / purpose tag (e.g. "final", "beauty", "composition",
#             "ref", "plan", "manifest")
#   char    = job.character_tag (danbooru) or "unknown"
#   series  = job.series_tag             or "unknown"
#   ts      = int(time.time())  (epoch seconds, monotonic within a run)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(value: str, *, fallback: str = "unknown") -> str:
    if not value:
        return fallback
    s = _SLUG_RE.sub("_", value.lower()).strip("_")
    return s or fallback


def spec_filename(
    job: AnimePipelineJob,
    feature: str,
    ext: str = "png",
    *,
    ts: int | None = None,
) -> str:
    """Build a spec-compliant filename for job artifacts.

    Example::

        a1b2c3d4_final_raiden_shogun_genshin_impact_1713912345.png
    """
    session = (getattr(job, "job_id", "") or "").replace("-", "")[:8] or "session"
    feature_slug = _slug(feature, fallback="artifact")
    char_slug = _slug(getattr(job, "character_tag", ""), fallback="unknown")
    series_slug = _slug(getattr(job, "series_tag", ""), fallback="unknown")
    stamp = ts if ts is not None else int(time.time())
    clean_ext = ext.lstrip(".").lower() or "png"
    return (
        f"{session}_{feature_slug}_{char_slug}_{series_slug}_{stamp}.{clean_ext}"
    )


class ResultStore:
    """Persist pipeline intermediates, final images, and manifests.

    Each job gets a directory: <base_dir>/<job_id>/
    """

    def __init__(self, base_dir: str = "storage/intermediate"):
        self._base_dir = Path(base_dir)

    def save_intermediate(
        self,
        job: AnimePipelineJob,
        stage: str,
        image_b64: str,
        suffix: str = "",
    ) -> str:
        """Save a single intermediate image. Returns file path."""
        job_dir = self._job_dir(job.job_id)
        prefix = _STAGE_FILE_PREFIX.get(stage, stage)
        filename = f"{prefix}{('_' + suffix) if suffix else ''}.png"
        filepath = job_dir / filename

        self._write_b64(filepath, image_b64)
        return str(filepath)

    def save_hint_layer(
        self,
        job: AnimePipelineJob,
        layer_type: str,
        image_b64: str,
    ) -> str:
        """Save a structure hint layer. Returns file path."""
        job_dir = self._job_dir(job.job_id)
        filename = f"{_HINT_FILE_NAMES.get(layer_type, '02_' + layer_type)}.png"
        filepath = job_dir / filename
        self._write_b64(filepath, image_b64)
        return str(filepath)

    def save_final(self, job: AnimePipelineJob) -> str:
        """Save the final output image. Returns file path."""
        if not job.final_image_b64:
            return ""
        job_dir = self._job_dir(job.job_id)
        filepath = job_dir / "final_output.png"
        self._write_b64(filepath, job.final_image_b64)
        job.final_image_path = str(filepath)

        # Spec §7: also emit a spec-named copy so downstream consumers
        # can attribute artifacts back to a (char, series) identity.
        try:
            spec_name = spec_filename(job, feature="final", ext="png")
            spec_path = job_dir / spec_name
            # Hard-link when possible (fast, same inode), else copy bytes.
            if not spec_path.exists():
                try:
                    import os as _os
                    _os.link(filepath, spec_path)
                except Exception:
                    spec_path.write_bytes(filepath.read_bytes())
            job.final_image_spec_path = str(spec_path)
        except Exception as e:
            logger.warning("[ResultStore] Spec-named final copy failed: %s", e)

        return str(filepath)

    def save_manifest(self, job: AnimePipelineJob, rank_result: Any = None) -> str:
        """Write output_manifest.json summarizing the entire job.

        When ``rank_result`` is provided, the manifest is built via the
        shared ``build_output_manifest`` helper so winner / runner-up
        metadata is included.  The legacy structure is preserved when
        ``rank_result`` is ``None`` (backward compatible).
        """
        job_dir = self._job_dir(job.job_id)
        filepath = job_dir / "output_manifest.json"

        if rank_result is not None:
            try:
                from .agents.output_manifest import build_output_manifest

                vram_profile = "normalvram"
                # Best-effort: pull the live VRAM profile from config if accessible
                try:
                    from .config import load_config

                    vram_profile = load_config().vram.profile.value
                except Exception:
                    pass

                manifest = build_output_manifest(
                    job,
                    rank_result,
                    debug_mode=False,
                    vram_profile=vram_profile,
                )
                # Preserve fields historically written by this store that
                # build_output_manifest does not emit.
                manifest.setdefault("created_at", job.created_at)
                manifest.setdefault("completed_at", job.completed_at)
                manifest.setdefault("user_prompt", job.user_prompt)
                if job.critique_results:
                    manifest.setdefault(
                        "critique_reports",
                        [c.to_dict() for c in job.critique_results],
                    )
                if job.layer_plan:
                    manifest.setdefault("layer_plan", job.layer_plan.to_dict())
                try:
                    filepath.write_text(
                        json.dumps(manifest, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    logger.info("[ResultStore] Manifest (ranked) written: %s", filepath)
                except Exception as e:
                    logger.error("[ResultStore] Failed to write ranked manifest: %s", e)
                return str(filepath)
            except Exception as e:
                logger.warning(
                    "[ResultStore] Ranked manifest build failed (%s); falling back to legacy manifest",
                    e,
                )

        manifest: dict[str, Any] = {
            "job_id": job.job_id,
            "preset": job.preset,
            "status": job.status.value,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
            "user_prompt": job.user_prompt,
            "passes": [],
            "critique_rounds": len(job.critique_results),
            "refine_rounds": job.refine_rounds,
            "models_used": job.models_used,
            "stage_timings_ms": job.stage_timings_ms,
            "total_latency_ms": job.total_latency_ms,
            "selected_final": "final_output.png" if job.final_image_b64 else None,
            "error": job.error,
        }

        # Build pass list from intermediates
        for img in job.intermediates:
            prefix = _STAGE_FILE_PREFIX.get(img.stage, img.stage)
            manifest["passes"].append({
                "name": img.stage,
                "model": img.metadata.get("checkpoint") or img.metadata.get("model", ""),
                "duration_ms": job.stage_timings_ms.get(img.stage, 0.0),
                "output": f"{prefix}.png",
            })

        # Add critique summaries
        if job.critique_results:
            manifest["critique_reports"] = [c.to_dict() for c in job.critique_results]

        # Add plan if available
        if job.layer_plan:
            manifest["layer_plan"] = job.layer_plan.to_dict()

        try:
            filepath.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.info("[ResultStore] Manifest written: %s", filepath)
        except Exception as e:
            logger.error("[ResultStore] Failed to write manifest: %s", e)

        return str(filepath)

    def save_all(self, job: AnimePipelineJob, rank_result: Any = None) -> dict[str, str]:
        """Save all intermediates, final image, and manifest. Returns paths."""
        paths: dict[str, str] = {}

        for i, img in enumerate(job.intermediates):
            if img.image_b64:
                path = self.save_intermediate(job, img.stage, img.image_b64)
                img.file_path = path
                paths[f"intermediate_{i}_{img.stage}"] = path

        # Structure layers
        for layer in job.structure_layers:
            if layer.image_b64:
                path = self.save_hint_layer(job, layer.layer_type.value if hasattr(layer.layer_type, 'value') else str(layer.layer_type), layer.image_b64)
                paths[f"hint_{layer.layer_type}"] = path

        if job.final_image_b64:
            paths["final"] = self.save_final(job)

        paths["manifest"] = self.save_manifest(job, rank_result=rank_result)
        return paths

    # ── Helpers ────────────────────────────────────────────────────────

    def _job_dir(self, job_id: str) -> Path:
        d = self._base_dir / job_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _write_b64(filepath: Path, image_b64: str) -> None:
        """Decode base64 and write PNG."""
        try:
            raw = image_b64.split(",", 1)[-1] if "," in image_b64 else image_b64
            filepath.write_bytes(base64.b64decode(raw))
        except Exception as e:
            logger.error("[ResultStore] Failed to write %s: %s", filepath, e)
