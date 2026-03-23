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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI

logger = logging.getLogger(__name__)

VIDEO_STORAGE_DIR = Path(__file__).resolve().parent.parent / "Storage" / "Video_Gen"
VIDEO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

VALID_SECONDS: set[str] = {"4", "8", "12"}
VALID_SIZES: set[str] = {"720x1280", "1280x720", "1024x1792", "1792x1024"}


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


def generate_video(
    prompt: str,
    *,
    size: str = "1280x720",
    seconds: int | str = 8,
    model: str = "sora-2",
) -> dict[str, Any]:
    """
    Submit a video generation job via the OpenAI Videos API.

    Returns a dict with the Video object fields plus local metadata.
    The job may still be in_progress — use poll_video() to wait for completion.
    """
    sec = str(seconds) if str(seconds) in VALID_SECONDS else _snap_seconds(int(seconds))
    if size not in VALID_SIZES:
        size = "1280x720"

    logger.info(
        f"[Sora2] Submitting — prompt={prompt[:80]!r}, "
        f"size={size}, seconds={sec}, model={model}"
    )

    client = _get_client()
    video = client.videos.create(prompt=prompt, model=model, seconds=sec, size=size)

    job = _video_to_dict(video)
    _save_meta(job)
    return job


def generate_video_sync(
    prompt: str,
    *,
    size: str = "1280x720",
    seconds: int | str = 8,
    model: str = "sora-2",
) -> dict[str, Any]:
    """Submit and block until the video is completed or failed."""
    sec = str(seconds) if str(seconds) in VALID_SECONDS else _snap_seconds(int(seconds))
    if size not in VALID_SIZES:
        size = "1280x720"

    logger.info(
        f"[Sora2] Generating (blocking) — prompt={prompt[:80]!r}, "
        f"size={size}, seconds={sec}, model={model}"
    )

    client = _get_client()
    video = client.videos.create_and_poll(
        prompt=prompt, model=model, seconds=sec, size=size
    )

    job = _video_to_dict(video)
    _save_meta(job)
    return job


def poll_video(video_id: str) -> dict[str, Any]:
    """Poll the API for the current state of a video job."""
    client = _get_client()
    video = client.videos.retrieve(video_id)
    job = _video_to_dict(video)
    _save_meta(job)
    return job


def download_video(video_id: str) -> Path:
    """Download the completed video file to local storage."""
    client = _get_client()
    content = client.videos.download_content(video_id, variant="video")
    dest = VIDEO_STORAGE_DIR / f"{video_id}.mp4"
    content.stream_to_file(str(dest))
    logger.info(f"[Sora2] Video saved: {dest}")
    return dest


def download_thumbnail(video_id: str) -> Path:
    """Download a thumbnail for the video."""
    client = _get_client()
    content = client.videos.download_content(video_id, variant="thumbnail")
    dest = VIDEO_STORAGE_DIR / f"{video_id}_thumb.jpg"
    content.stream_to_file(str(dest))
    return dest


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
            jobs.append(json.loads(p.read_text("utf-8")))
        except Exception:
            pass
    return jobs


# ── Helpers ────────────────────────────────────────────────────────────

def _video_to_dict(video) -> dict[str, Any]:
    """Convert an openai.types.Video object to a plain dict."""
    cost_per_sec = 0.30 if "pro" in (video.model or "") else 0.10
    secs_int = int(video.seconds) if video.seconds else 0
    return {
        "id": video.id,
        "status": video.status,
        "prompt": video.prompt,
        "size": video.size,
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
