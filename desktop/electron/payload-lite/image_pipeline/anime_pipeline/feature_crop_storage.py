"""Feature crop-as-layer storage.

Spec verbatim (2026-04-23 user request):
  "dung YOLO detection lay tat ca dac trung (mat, moi, mi mat, long
   may, mieng, mui, hinh dang khuon mat, dong tu, iris, nach, co, tay,
   ban tay, mong tay, toc, long nach, nguc, bung, ron, dui, chan, ban
   chan,... va mau sac) ... cat ra thanh cac tam nho coi no lam mot
   layer va luu no tai nhu la <ten session chat><dac trung><nhan vat>
   <game/?><ts(HH/DD/MM/YYYY)>.<file_extension>"

This module runs AFTER the detection_inpaint stage.  It reuses the
existing DetectionResult (no second YOLO inference) plus the latest
finalised image to:

  1. Crop each detected region to a stand-alone PNG (with padding so
     downstream consumers can re-mask without bleed).
  2. Compute mean RGB + dominant-channel for the crop via PIL.ImageStat
     so the layer manifest carries colour metadata too.
  3. Persist to
       storage/feature_layers/<session>/<char>__<series>__<feature>__
         <HH-MM_DD-MM-YYYY>__<idx>.png
     with every path component sanitised.
  4. Return a list[dict] manifest the orchestrator stores at
     job.metadata["feature_crops"].

The function is a no-op when:
  * detection_inpaint produced no regions, OR
  * the source image is missing / un-decodable, OR
  * Pillow is unavailable (we degrade silently — pipeline must never
    fail because of crop persistence).
"""
from __future__ import annotations

import base64
import io
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # avoid runtime import cycles
    from .schemas import AnimePipelineJob
    from .agents.detection_detail import DetectedRegion, DetectionResult


# ── Path / filename sanitisation ────────────────────────────────────

_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _slug(value: str, *, fallback: str = "unknown", max_len: int = 48) -> str:
    """Make a string filesystem-safe and bounded."""
    if not value:
        return fallback
    cleaned = _SAFE_RE.sub("_", value.strip()).strip("._-")
    if not cleaned:
        return fallback
    return cleaned[:max_len]


def _resolve_storage_root() -> Path:
    """Where to drop feature crops.

    Honours $FEATURE_LAYER_DIR for tests / ops overrides.  Defaults to
    <repo>/storage/feature_layers (sibling of the existing Image_Gen
    storage dir used by anime_pipeline_service.py)."""
    override = os.getenv("FEATURE_LAYER_DIR")
    if override:
        return Path(override).expanduser().resolve()
    # repo root = three parents up from this file
    return (Path(__file__).resolve().parents[2] / "storage" / "feature_layers").resolve()


def _resolve_job_subdir(job: "AnimePipelineJob") -> str:
    """Per-generation folder name under ``<session>/``.

    User spec (2026-04-27): every distinct generation must land in its
    own subdirectory so crops from different prompts never collide.
    Folder name embeds character + series + job-id prefix for human
    browsability:

        ``<char>__<series>__<job_id_prefix>``

    The job_id is truncated to 12 chars (uuid4 hex prefix) which keeps
    the path short while staying unique within a session.
    """
    char = _slug(getattr(job, "character_name", "") or "character")
    series = _slug(getattr(job, "series_name", "") or "unknown_series")
    raw_id = str(getattr(job, "job_id", "") or "").strip()
    job_id = _slug(raw_id, fallback="job", max_len=16)[:16] or "job"
    return f"{char}__{series}__{job_id}"


# ── Image decoding / colour stats ───────────────────────────────────

def _decode_b64_png(b64: str):
    """Return a PIL.Image or None.  Pillow import is local so the
    pipeline still runs in environments without it."""
    try:
        from PIL import Image  # type: ignore
    except Exception:  # pragma: no cover
        logger.debug("Pillow unavailable — feature crop disabled")
        return None
    try:
        if "," in b64 and b64.startswith("data:"):
            b64 = b64.split(",", 1)[1]
        raw = base64.b64decode(b64)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:  # noqa: BLE001 — defensive
        logger.warning("feature_crop: cannot decode source image: %s", exc)
        return None


def _color_stats(crop) -> dict[str, Any]:
    """Mean RGB + hex code for a crop.  Empty dict on any failure."""
    try:
        from PIL import ImageStat  # type: ignore
    except Exception:  # pragma: no cover
        return {}
    try:
        stat = ImageStat.Stat(crop)
        r, g, b = (int(round(c)) for c in stat.mean[:3])
        return {
            "mean_rgb": [r, g, b],
            "hex": f"#{r:02x}{g:02x}{b:02x}",
        }
    except Exception as exc:  # noqa: BLE001
        logger.debug("feature_crop: color stat failed: %s", exc)
        return {}


# ── Public entry point ──────────────────────────────────────────────

def persist_feature_crops(
    job: "AnimePipelineJob",
    detection: Optional["DetectionResult"],
    *,
    source_b64: Optional[str] = None,
    padding_px: int = 8,
    source: str = "generated",
    ref_index: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Crop every detected region and write it to disk.

    Returns a manifest list.  Always returns a list (possibly empty);
    never raises.  The orchestrator should assign the result to
    ``job.metadata["feature_crops"]``.

    Parameters
    ----------
    job: AnimePipelineJob
        Source of session_id / character_name / series_name and the
        canonical final image fallback.
    detection: DetectionResult | None
        Latest YOLO detection (typically ``DetectionInpaintAgent.last_result``).
    source_b64: str | None
        Base64 PNG to crop from.  Defaults to ``job.final_image_b64`` so
        crops reflect the inpainted output, not the raw beauty pass.
    padding_px: int
        Extra context kept around each bbox.  Defaults to 8 px.
    source: str
        Either ``"generated"`` (AI output) or ``"reference"`` (SAA / cached
        ref images).  Crops are written to
        ``storage/feature_layers/<session>/<original|ai_gen>/`` so the
        reference vs generated layers can be diffed downstream.
    ref_index: int | None
        For ``source='reference'`` only — index of the reference image so
        crops from different refs don't clobber each other.
    """
    if detection is None or getattr(detection, "total_regions", 0) == 0:
        return []

    img_b64 = source_b64 or job.final_image_b64
    if not img_b64:
        logger.info("feature_crop: no source image, skipping")
        return []

    img = _decode_b64_png(img_b64)
    if img is None:
        return []

    session = _slug(getattr(job, "session_id", "") or job.job_id, fallback="default")
    char = _slug(job.character_name or "character")
    series = _slug(job.series_name or "unknown_series")
    ts = datetime.now().strftime("%H-%M_%d-%m-%Y")

    # 2026-04-26 user spec: split into original/ (reference layers) and
    # ai_gen/ (generated layers).  Existing flat-layout files remain
    # readable but new writes always go through the source-aware subdir.
    # 2026-04-27 user spec: each generation also gets its own job-id
    # subdirectory under <session>/ so crops from different prompts no
    # longer pile up in a single flat folder.
    sub = "original" if source == "reference" else "ai_gen"
    job_subdir = _resolve_job_subdir(job)
    storage_root = _resolve_storage_root() / session / job_subdir / sub
    try:
        storage_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("feature_crop: cannot create %s: %s", storage_root, exc)
        return []

    width, height = img.size
    manifest: list[dict[str, Any]] = []

    for region_type, regions in detection.regions.items():
        feat = _slug(region_type, fallback="region")
        for idx, region in enumerate(regions):
            try:
                x1 = max(0, int(region.x1) - padding_px)
                y1 = max(0, int(region.y1) - padding_px)
                x2 = min(width, int(region.x2) + padding_px)
                y2 = min(height, int(region.y2) + padding_px)
                if x2 <= x1 or y2 <= y1:
                    continue
                crop = img.crop((x1, y1, x2, y2))

                ref_part = f"__ref{ref_index:02d}" if ref_index is not None else ""
                fname = f"{char}__{series}__{feat}__{ts}{ref_part}__{idx:02d}.png"
                fpath = storage_root / fname
                crop.save(fpath, format="PNG", optimize=True)

                entry: dict[str, Any] = {
                    "feature": region_type,
                    "index": idx,
                    "source": source,  # "reference" | "generated"
                    "ref_index": ref_index,
                    "path": str(fpath),
                    "rel_path": str(fpath.relative_to(_resolve_storage_root().parent))
                        if fpath.is_relative_to(_resolve_storage_root().parent)
                        else str(fpath),
                    "bbox": [x1, y1, x2, y2],
                    "width": x2 - x1,
                    "height": y2 - y1,
                    "confidence": round(float(getattr(region, "confidence", 0.0)), 3),
                    "session_id": session,
                    "character": char,
                    "series": series,
                    "timestamp": ts,
                }
                entry.update(_color_stats(crop))
                manifest.append(entry)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "feature_crop: failed for %s[%d]: %s", region_type, idx, exc
                )

    if manifest:
        logger.info(
            "feature_crop[%s]: persisted %d crops across %d feature types under %s",
            source,
            len(manifest),
            len({m["feature"] for m in manifest}),
            storage_root,
        )
    return manifest


# ── Reference vs generated evaluator ────────────────────────────────

def evaluate_reference_vs_generated(
    job: "AnimePipelineJob",
    *,
    feature_priority: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Compare ``original/`` (reference) vs ``ai_gen/`` crops feature-by-feature.

    User spec (2026-04-26): "thuc hien detection ref danh gia tu tat ca
    dac trung tren co the chu yeu nhat la khuon mat" — face is highest
    priority, then eyes, then the rest.

    Comparison metric is mean-RGB Euclidean distance per feature type
    (cheap, no LLM).  Lower delta = better preservation of the reference
    appearance.  Always returns a dict; never raises.
    """
    feature_priority = feature_priority or [
        "face", "full_face", "eyes", "full_eyes", "hair", "mouth", "nose",
    ]

    session = _slug(getattr(job, "session_id", "") or job.job_id, fallback="default")
    job_subdir = _resolve_job_subdir(job)
    base = _resolve_storage_root() / session / job_subdir
    orig_dir = base / "original"
    gen_dir = base / "ai_gen"

    if not orig_dir.exists() or not gen_dir.exists():
        # Backwards-compat: fall back to the legacy flat layout from
        # before the per-job subdirectory split.
        legacy = _resolve_storage_root() / session
        legacy_orig = legacy / "original"
        legacy_gen = legacy / "ai_gen"
        if legacy_orig.exists() and legacy_gen.exists():
            orig_dir, gen_dir = legacy_orig, legacy_gen
        else:
            return {"compared": 0, "reason": "missing_subdir"}

    try:
        from PIL import Image, ImageStat  # type: ignore
    except Exception:
        return {"compared": 0, "reason": "pillow_unavailable"}

    def _mean_rgb_for(dir_: Path, feat: str) -> Optional[tuple[float, float, float]]:
        # Filename pattern: <char>__<series>__<feat>__<ts>...
        rs, gs, bs = [], [], []
        for p in dir_.glob(f"*__{feat}__*.png"):
            try:
                with Image.open(p) as im:
                    s = ImageStat.Stat(im.convert("RGB")).mean
                rs.append(s[0]); gs.append(s[1]); bs.append(s[2])
            except Exception:
                continue
        if not rs:
            return None
        return (sum(rs) / len(rs), sum(gs) / len(gs), sum(bs) / len(bs))

    per_feature: list[dict[str, Any]] = []
    weighted_sum = 0.0
    weight_total = 0.0
    for i, feat in enumerate(feature_priority):
        weight = 1.0 / (i + 1)  # face heaviest
        ref = _mean_rgb_for(orig_dir, feat)
        gen = _mean_rgb_for(gen_dir, feat)
        if ref is None or gen is None:
            continue
        delta = (
            (ref[0] - gen[0]) ** 2
            + (ref[1] - gen[1]) ** 2
            + (ref[2] - gen[2]) ** 2
        ) ** 0.5
        per_feature.append({
            "feature": feat,
            "weight": round(weight, 3),
            "ref_mean_rgb": [round(c, 1) for c in ref],
            "gen_mean_rgb": [round(c, 1) for c in gen],
            "delta_rgb": round(delta, 2),
        })
        weighted_sum += weight * delta
        weight_total += weight

    if not per_feature:
        return {"compared": 0, "reason": "no_overlap"}

    avg_delta = weighted_sum / weight_total if weight_total else 0.0
    # Map delta (0..441 max for full-RGB swing) to 0..10 quality score.
    score = max(0.0, min(10.0, 10.0 - (avg_delta / 441.0) * 10.0))
    result = {
        "compared": len(per_feature),
        "weighted_avg_delta_rgb": round(avg_delta, 2),
        "score": round(score, 2),  # 10 = identical, 0 = max divergence
        "per_feature": per_feature,
        "face_priority": feature_priority[:3],
    }
    logger.info(
        "feature_crop: ref-vs-gen evaluation score=%.2f (%d features compared, face-priority)",
        score, len(per_feature),
    )
    return result
