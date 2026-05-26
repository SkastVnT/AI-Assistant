"""
Video Generation API routes — Flask Blueprint (Sora 2).

Endpoints:
    POST /api/video/generate          → Submit a text-to-video or image-to-video job
    GET  /api/video/status/<job_id>   → Poll job status
    POST /api/video/cancel/<job_id>   → Cancel / delete a job
    GET  /api/video/list              → List recent jobs (?limit=N)
    GET  /api/video/download/<job_id> → Download the completed .mp4
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

logger = logging.getLogger(__name__)

video_bp = Blueprint("video", __name__, url_prefix="/api/video")

_MAX_PROMPT = 4000
_MAX_IMAGES = 5
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_MAX_IMAGE_BYTES = 20 * 1024 * 1024  # 20 MB


def _import_vg():
    from src.video_generation import (
        cancel_video,
        download_video,
        generate_video,
        get_job_status,
        list_jobs,
        poll_video,
    )

    return (
        generate_video,
        poll_video,
        cancel_video,
        download_video,
        get_job_status,
        list_jobs,
    )


# ── Generate ────────────────────────────────────────────────────────────────


@video_bp.route("/generate", methods=["POST"])
def generate():
    """Submit a video generation job. Accepts JSON or multipart/form-data."""
    content_type = request.content_type or ""

    if "multipart/form-data" in content_type:
        # Image-to-video: files uploaded via FormData
        prompt = (request.form.get("prompt") or "").strip()
        size = request.form.get("size") or "1280x720"
        seconds = request.form.get("seconds") or "8"
        model = request.form.get("model") or "sora-2"
        uploaded = request.files.getlist("images")
    else:
        data = request.get_json(force=True, silent=True) or {}
        prompt = (data.get("prompt") or "").strip()
        size = data.get("size") or "1280x720"
        seconds = data.get("seconds") or "8"
        model = data.get("model") or "sora-2"
        uploaded = []

    # Validate prompt
    if not prompt:
        return jsonify({"error": "prompt is required"}), 400
    if len(prompt) > _MAX_PROMPT:
        return jsonify({"error": f"prompt too long (max {_MAX_PROMPT})"}), 400

    # Validate model
    if model not in ("sora-2", "sora-2-pro"):
        return jsonify({"error": "model must be sora-2 or sora-2-pro"}), 400

    # Validate seconds
    try:
        seconds_int = int(seconds)
        if seconds_int not in (4, 8, 12):
            return jsonify({"error": "seconds must be 4, 8, or 12"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "seconds must be an integer"}), 400

    # Save uploaded images to temp files
    temp_paths: list[Path] = []
    try:
        if uploaded:
            if len(uploaded) > _MAX_IMAGES:
                return jsonify({"error": f"max {_MAX_IMAGES} images allowed"}), 400
            for f in uploaded:
                if f.content_type not in _ALLOWED_IMAGE_TYPES:
                    return (
                        jsonify({"error": f"unsupported image type: {f.content_type}"}),
                        400,
                    )
                data_bytes = f.read(_MAX_IMAGE_BYTES + 1)
                if len(data_bytes) > _MAX_IMAGE_BYTES:
                    return (
                        jsonify({"error": f"{f.filename} too large (max 20 MB)"}),
                        400,
                    )
                suffix = Path(f.filename or "img").suffix or ".jpg"
                fd, tmp = tempfile.mkstemp(prefix="vg_upload_", suffix=suffix)
                os.close(fd)
                Path(tmp).write_bytes(data_bytes)
                temp_paths.append(Path(tmp))

        generate_video, *_ = _import_vg()

        if temp_paths:
            result = generate_video(
                prompt,
                size=size,
                seconds=seconds_int,
                model=model,
                image_paths=temp_paths,
            )
        else:
            result = generate_video(
                prompt,
                size=size,
                seconds=seconds_int,
                model=model,
            )
    except RuntimeError as e:
        # e.g. OPENAI_API_KEY not set
        logger.error(f"[VideoGen] generate error: {e}")
        return jsonify({"error": str(e)}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        logger.exception("[VideoGen] unexpected error in generate")
        return jsonify({"error": "Video generation failed"}), 500
    finally:
        for p in temp_paths:
            try:
                p.unlink()
            except OSError:
                pass

    return jsonify(result), 202


# ── Status ──────────────────────────────────────────────────────────────────


@video_bp.route("/status/<job_id>", methods=["GET"])
def status(job_id: str):
    """Poll job status from OpenAI, falling back to local cache."""
    if not job_id or len(job_id) > 128:
        return jsonify({"error": "invalid job_id"}), 400

    _, poll_video, _, _, get_job_status, _ = _import_vg()

    try:
        result = poll_video(job_id)
    except Exception as e:
        logger.warning(f"[VideoGen] poll error for {job_id}: {e}")
        # Fall back to local metadata if API call fails
        cached = get_job_status(job_id)
        if cached:
            return jsonify(cached), 200
        return jsonify({"error": str(e)}), 500

    return jsonify(result), 200


# ── Cancel ──────────────────────────────────────────────────────────────────


@video_bp.route("/cancel/<job_id>", methods=["POST"])
def cancel(job_id: str):
    """Cancel an in-progress or queued video job."""
    if not job_id or len(job_id) > 128:
        return jsonify({"error": "invalid job_id"}), 400

    _, _, cancel_video, *_ = _import_vg()

    try:
        result = cancel_video(job_id)
    except Exception as e:
        logger.error(f"[VideoGen] cancel error for {job_id}: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify(result), 200


# ── List ────────────────────────────────────────────────────────────────────


@video_bp.route("/list", methods=["GET"])
def list_recent():
    """List recent video generation jobs from local metadata."""
    try:
        limit = int(request.args.get("limit", 20))
        limit = max(1, min(100, limit))
    except (ValueError, TypeError):
        limit = 20

    *_, list_jobs = _import_vg()

    try:
        jobs = list_jobs(limit=limit)
    except Exception as e:
        logger.error(f"[VideoGen] list error: {e}")
        return jsonify({"error": str(e)}), 500

    return jsonify({"jobs": jobs}), 200


# ── Download ────────────────────────────────────────────────────────────────


@video_bp.route("/download/<job_id>", methods=["GET"])
def download(job_id: str):
    """Download the completed .mp4 for a video job."""
    if not job_id or len(job_id) > 128:
        return jsonify({"error": "invalid job_id"}), 400

    _, _, _, download_video, get_job_status, _ = _import_vg()

    # Check local cache first to avoid re-download
    try:
        from src.video_generation import VIDEO_STORAGE_DIR

        local = VIDEO_STORAGE_DIR / f"{job_id}.mp4"
        if not local.exists():
            download_video(job_id)
            local = VIDEO_STORAGE_DIR / f"{job_id}.mp4"
        if not local.exists():
            return jsonify({"error": "video file not found after download"}), 404
    except Exception as e:
        logger.error(f"[VideoGen] download error for {job_id}: {e}")
        return jsonify({"error": str(e)}), 500

    return send_file(
        str(local),
        mimetype="video/mp4",
        as_attachment=True,
        download_name=f"sora2_{job_id}.mp4",
    )
