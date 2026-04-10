"""
Sora 2 Video Generation Module
Uses OpenAI's Videos API (openai>=2.29.0) to generate videos from text prompts.

Models: sora-2 ($0.10/s), sora-2-pro ($0.30/s)
Sizes:  720x1280, 1280x720, 1024x1792, 1792x1024
Durations: 4, 8, or 12 seconds
"""
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI

try:
    from PIL import Image
except ImportError:
    Image = None

logger = logging.getLogger(__name__)

VIDEO_STORAGE_DIR = Path(__file__).resolve().parent.parent / "Storage" / "Video_Gen"
VIDEO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

VALID_SECONDS: set[str] = {"4", "8", "12"}
VALID_SIZES: set[str] = {"720x1280", "1280x720", "1024x1792", "1792x1024"}

# Map user-facing aspect-ratio values to Sora 2 API sizes
ASPECT_RATIO_MAP: dict[str, str] = {
    "1280x720": "1280x720",       # 16:9 landscape
    "720x1280": "720x1280",       # 9:16 portrait
    "1080x1920": "1280x720",      # 1:1 square → use landscape, post-crop later
    "1792x1024": "1792x1024",     # legacy wide
    "1024x1792": "1024x1792",     # legacy tall
}

# Pretty labels for display
ASPECT_LABELS: dict[str, str] = {
    "1280x720": "16:9",
    "720x1280": "9:16",
    "1080x1920": "1:1",
    "1792x1024": "16:9 Wide",
    "1024x1792": "9:16 Tall",
}


def ensure_aspect_ratio_field(job: dict[str, Any]) -> dict[str, Any]:
    """Ensure video metadata has aspect_ratio populated from size when missing."""
    if job.get("aspect_ratio"):
        return job
    size = (job.get("size") or "").lower()
    if size:
        job["aspect_ratio"] = ASPECT_LABELS.get(size, size)
    return job


def _resolve_aspect_ratio(size: str) -> tuple[str, str]:
    """Validate and normalize requested size/aspect into API size + display label."""
    normalized = (size or "").strip().lower()

    # User-facing aspect values from UI
    if normalized in ASPECT_RATIO_MAP:
        api_size = ASPECT_RATIO_MAP[normalized]
        if api_size not in VALID_SIZES:
            raise ValueError(f"Mapped API size is invalid: {api_size}")
        return api_size, ASPECT_LABELS.get(normalized, api_size)

    # Backward-compatible direct API sizes
    if normalized in VALID_SIZES:
        return normalized, ASPECT_LABELS.get(normalized, normalized)

    allowed = sorted(set(ASPECT_RATIO_MAP.keys()) | VALID_SIZES)
    raise ValueError(f"Unsupported video size/aspect ratio '{size}'. Allowed: {', '.join(allowed)}")


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set — required for Sora 2 video generation")
    return OpenAI(api_key=api_key)


def _snap_seconds(duration: int) -> str:
    """Map arbitrary duration to the closest valid bucket (4/8/12)."""
    if duration <= 6:
        return "4"
    if duration <= 10:
        return "8"
    return "12"


def _parse_size(size: str) -> tuple[int, int]:
    """Parse size like '720x1280' to (width, height)."""
    try:
        w_str, h_str = size.lower().split("x", 1)
        return int(w_str), int(h_str)
    except Exception:
        return 1280, 720


def _fit_image_exact(img: "Image.Image", width: int, height: int) -> "Image.Image":
    """Center-crop + resize image so output exactly matches target size."""
    src_w, src_h = img.size
    target_ratio = width / height
    src_ratio = src_w / src_h if src_h else target_ratio

    if src_ratio > target_ratio:
        # Source too wide: crop left-right
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    elif src_ratio < target_ratio:
        # Source too tall: crop top-bottom
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))

    return img.resize((width, height), Image.Resampling.LANCZOS)


def _build_single_reference(image_path: str | Path, size: str) -> Path:
    """Create a temporary single reference image exactly matching requested size."""
    if Image is None:
        return Path(image_path)

    width, height = _parse_size(size)
    src = Image.open(str(image_path)).convert("RGB")
    try:
        fitted = _fit_image_exact(src, width, height)
        fd, out_path = tempfile.mkstemp(prefix="sora2_ref_single_", suffix=".jpg")
        os.close(fd)
        out = Path(out_path)
        fitted.save(out, format="JPEG", quality=95)
        return out
    finally:
        src.close()


def _build_reference_collage(image_paths: list[str | Path], size: str) -> Path:
    """Create a temporary collage from up to 5 images for a single input_reference."""
    if not image_paths:
        raise ValueError("No image paths provided")

    # If Pillow is unavailable, fall back to first image.
    if Image is None:
        return Path(image_paths[0])

    opened = [Image.open(str(p)).convert("RGB") for p in image_paths[:5]]
    try:
        target_w, target_h = _parse_size(size)
        canvas = Image.new("RGB", (target_w, target_h), color=(20, 20, 20))

        # Simple responsive grid for 1..5 images
        layouts = {
            1: [(0, 0, target_w, target_h)],
            2: [(0, 0, target_w // 2, target_h), (target_w // 2, 0, target_w, target_h)],
            3: [(0, 0, target_w // 2, target_h), (target_w // 2, 0, target_w, target_h // 2), (target_w // 2, target_h // 2, target_w, target_h)],
            4: [(0, 0, target_w // 2, target_h // 2), (target_w // 2, 0, target_w, target_h // 2), (0, target_h // 2, target_w // 2, target_h), (target_w // 2, target_h // 2, target_w, target_h)],
            5: [(0, 0, target_w // 2, target_h // 2), (target_w // 2, 0, target_w, target_h // 2), (0, target_h // 2, target_w // 3, target_h), (target_w // 3, target_h // 2, 2 * target_w // 3, target_h), (2 * target_w // 3, target_h // 2, target_w, target_h)],
        }

        slots = layouts[len(opened)]
        for img, slot in zip(opened, slots):
            x1, y1, x2, y2 = slot
            w, h = x2 - x1, y2 - y1
            fitted = _fit_image_exact(img.copy(), w, h)
            px = x1
            py = y1
            canvas.paste(fitted, (px, py))

        fd, out_path = tempfile.mkstemp(prefix="sora2_ref_", suffix=".jpg")
        os.close(fd)
        out = Path(out_path)
        canvas.save(out, format="JPEG", quality=95)
        return out
    finally:
        for img in opened:
            img.close()


def generate_video(
    prompt: str,
    *,
    size: str = "1280x720",
    seconds: int | str = 8,
    model: str = "sora-2",
    image_path: str | Path | None = None,
    image_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    """
    Submit a video generation job via the OpenAI Videos API.

    If *image_path* (single) or *image_paths* (up to 5) is provided
    the API creates image-to-video; otherwise text-to-video.

    Returns a dict with the Video object fields plus local metadata.
    The job may still be in_progress — use poll_video() to wait for completion.
    """
    sec = str(seconds) if str(seconds) in VALID_SECONDS else _snap_seconds(int(seconds))
    api_size, display_label = _resolve_aspect_ratio(size)

    # Consolidate single image_path into the list
    imgs = list(image_paths or [])
    if image_path and not imgs:
        imgs = [image_path]
    imgs = imgs[:5]

    logger.info(
        f"[Sora2] Submitting — prompt={prompt[:80]!r}, "
        f"size={api_size} ({display_label}), seconds={sec}, model={model}, images={len(imgs)}"
    )

    client = _get_client()
    create_kwargs: dict[str, Any] = dict(prompt=prompt, model=model, seconds=sec, size=api_size)
    temp_collage: Path | None = None
    if len(imgs) == 1:
        temp_collage = _build_single_reference(imgs[0], api_size)
        create_kwargs["input_reference"] = temp_collage
    elif len(imgs) > 1:
        temp_collage = _build_reference_collage(imgs, api_size)
        create_kwargs["input_reference"] = temp_collage

    video = client.videos.create(**create_kwargs)

    job = _video_to_dict(video)
    job["aspect_ratio"] = display_label
    if imgs:
        job["source_images"] = [str(p) for p in imgs]
    if temp_collage:
        job["input_reference_mode"] = "collage"
    _save_meta(job)
    if temp_collage and temp_collage.exists():
        try:
            temp_collage.unlink()
        except OSError:
            pass
    return job


def generate_video_sync(
    prompt: str,
    *,
    size: str = "1280x720",
    seconds: int | str = 8,
    model: str = "sora-2",
    image_path: str | Path | None = None,
    image_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    """Submit and block until the video is completed or failed."""
    sec = str(seconds) if str(seconds) in VALID_SECONDS else _snap_seconds(int(seconds))
    api_size, display_label = _resolve_aspect_ratio(size)

    imgs = list(image_paths or [])
    if image_path and not imgs:
        imgs = [image_path]
    imgs = imgs[:5]

    logger.info(
        f"[Sora2] Generating (blocking) — prompt={prompt[:80]!r}, "
        f"size={api_size} ({display_label}), seconds={sec}, model={model}, images={len(imgs)}"
    )

    client = _get_client()
    create_kwargs: dict[str, Any] = dict(prompt=prompt, model=model, seconds=sec, size=api_size)
    temp_collage: Path | None = None
    if len(imgs) == 1:
        temp_collage = _build_single_reference(imgs[0], api_size)
        create_kwargs["input_reference"] = temp_collage
    elif len(imgs) > 1:
        temp_collage = _build_reference_collage(imgs, api_size)
        create_kwargs["input_reference"] = temp_collage

    video = client.videos.create_and_poll(**create_kwargs)

    job = _video_to_dict(video)
    job["aspect_ratio"] = display_label
    if imgs:
        job["source_images"] = [str(p) for p in imgs]
    if temp_collage:
        job["input_reference_mode"] = "collage"
    _save_meta(job)
    if temp_collage and temp_collage.exists():
        try:
            temp_collage.unlink()
        except OSError:
            pass
    return job


def poll_video(video_id: str) -> dict[str, Any]:
    """Poll the API for the current state of a video job."""
    client = _get_client()
    video = client.videos.retrieve(video_id)
    job = _video_to_dict(video)
    # Preserve user-facing aspect ratio and source metadata if it already exists.
    prev = get_job_status(video_id)
    if prev:
        if prev.get("aspect_ratio"):
            job["aspect_ratio"] = prev["aspect_ratio"]
        if prev.get("source_images"):
            job["source_images"] = prev["source_images"]
        if prev.get("input_reference_mode"):
            job["input_reference_mode"] = prev["input_reference_mode"]
    _save_meta(job)
    return job


def download_video(video_id: str) -> Path:
    """Download the completed video file to local storage."""
    client = _get_client()
    content = client.videos.download_content(video_id, variant="video")
    dest = VIDEO_STORAGE_DIR / f"{video_id}.mp4"
    content.stream_to_file(str(dest))
    logger.info(f"[Sora2] Video saved: {dest}")
    try:
        from core.image_storage import archive_legacy_asset
        job_meta = get_job_status(video_id) or {}
        with open(dest, 'rb') as vf:
            legacy_id = archive_legacy_asset(
                asset_type='video',
                asset_id=video_id,
                metadata=job_meta,
                raw_payload={'legacy_format': 'sora2_video_file'},
                file_bytes=vf.read(),
                filename=dest.name,
                mime_type='video/mp4',
            )
        if legacy_id:
            logger.info(f"[Sora2] Video archived to Mongo legacy store: {legacy_id}")
    except Exception as archive_err:
        logger.warning(f"[Sora2] Video archive failed: {archive_err}")
    return dest


def download_thumbnail(video_id: str) -> Path:
    """Download a thumbnail for the video."""
    client = _get_client()
    content = client.videos.download_content(video_id, variant="thumbnail")
    dest = VIDEO_STORAGE_DIR / f"{video_id}_thumb.jpg"
    content.stream_to_file(str(dest))
    try:
        from core.image_storage import archive_legacy_asset
        with open(dest, 'rb') as tf:
            legacy_id = archive_legacy_asset(
                asset_type='video_thumbnail',
                asset_id=f"{video_id}_thumb",
                metadata={'video_id': video_id, 'variant': 'thumbnail'},
                raw_payload={'legacy_format': 'sora2_thumbnail_file'},
                file_bytes=tf.read(),
                filename=dest.name,
                mime_type='image/jpeg',
            )
        if legacy_id:
            logger.info(f"[Sora2] Thumbnail archived to Mongo legacy store: {legacy_id}")
    except Exception as archive_err:
        logger.warning(f"[Sora2] Thumbnail archive failed: {archive_err}")
    return dest


def cancel_video(video_id: str) -> dict[str, Any]:
    """Cancel / delete an in-progress or queued video job."""
    client = _get_client()
    try:
        client.videos.delete(video_id)
        logger.info(f"[Sora2] Cancelled job: {video_id}")
        # Update local metadata
        meta_path = VIDEO_STORAGE_DIR / f"{video_id}.json"
        if meta_path.exists():
            job = json.loads(meta_path.read_text("utf-8"))
            job["status"] = "cancelled"
            meta_path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
            return job
        return {"id": video_id, "status": "cancelled"}
    except Exception as e:
        logger.error(f"[Sora2] Cancel error for {video_id}: {e}")
        raise


def get_job_status(job_id: str) -> dict[str, Any] | None:
    """Get job from local cache (disk)."""
    meta = VIDEO_STORAGE_DIR / f"{job_id}.json"
    if meta.exists():
        return json.loads(meta.read_text("utf-8"))
    return None


def list_jobs(limit: int = 20) -> list[dict[str, Any]]:
    """List recent video generation jobs from local metadata files."""
    jobs: list[dict[str, Any]] = []
    for p in sorted(
        VIDEO_STORAGE_DIR.glob("*.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )[:limit]:
        try:
            job = json.loads(p.read_text("utf-8"))
            jobs.append(ensure_aspect_ratio_field(job))
        except Exception:
            pass
    return jobs


# ── Helpers ────────────────────────────────────────────────────────────

def _video_to_dict(video) -> dict[str, Any]:
    """Convert an openai.types.Video object to a plain dict."""
    cost_per_sec = 0.30 if "pro" in (video.model or "") else 0.10
    secs_int = int(video.seconds) if video.seconds else 0
    size = video.size
    return {
        "id": video.id,
        "status": video.status,
        "prompt": video.prompt,
        "size": size,
        "aspect_ratio": ASPECT_LABELS.get((size or "").lower(), size),
        "seconds": video.seconds,
        "model": video.model,
        "progress": video.progress,
        "error": video.error.message if video.error else None,
        "created_at": _ts(video.created_at),
        "completed_at": _ts(video.completed_at),
        "expires_at": _ts(video.expires_at),
        "cost_estimate": f"${secs_int * cost_per_sec:.2f}",
    }


def _ts(unix: int | None) -> str | None:
    if unix is None:
        return None
    return datetime.fromtimestamp(unix, tz=timezone.utc).isoformat()


def _save_meta(job: dict[str, Any]) -> None:
    path = VIDEO_STORAGE_DIR / f"{job['id']}.json"
    path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from core.image_storage import archive_legacy_asset
        archive_legacy_asset(
            asset_type='video_job',
            asset_id=str(job.get('id', 'unknown')),
            metadata=job,
            raw_payload={'legacy_format': 'sora2_job_json', 'job': job},
            filename=path.name,
            mime_type='application/json',
        )
    except Exception as archive_err:
        logger.warning(f"[Sora2] Job metadata archive failed: {archive_err}")
