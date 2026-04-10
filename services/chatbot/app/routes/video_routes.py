"""
Video Generation Routes (Flask) — /api/video/*
Wraps the Sora 2 module for the Flask new-structure mode.
Supports text-to-video and image-to-video (multipart upload, up to 5 images).
"""
import logging
import os
import tempfile
import uuid

from flask import Blueprint, jsonify, request, send_file
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)
video_bp = Blueprint("video", __name__)

_ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
_MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20 MB
_MAX_IMAGES = 5


def _save_upload(file_storage) -> str | None:
    """Save an uploaded image to a temp file and return its path."""
    if not file_storage or not file_storage.filename:
        return None
    fname = secure_filename(file_storage.filename)
    ext = os.path.splitext(fname)[1].lower()
    if ext not in _ALLOWED_IMAGE_EXT:
        raise ValueError(f"Unsupported image type: {ext}")
    data = file_storage.read()
    if len(data) > _MAX_IMAGE_SIZE:
        raise ValueError("Image too large (max 20 MB)")
    dest = os.path.join(tempfile.gettempdir(), f"sora2_{uuid.uuid4().hex}{ext}")
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def _save_multiple_uploads(file_list) -> list[str]:
    """Save multiple uploaded images, return their temp paths."""
    paths = []
    for fs in file_list[:_MAX_IMAGES]:
        p = _save_upload(fs)
        if p:
            paths.append(p)
    return paths


def _cleanup_temps(paths: list[str]) -> None:
    """Remove temporary image files."""
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.unlink(p)
            except OSError:
                pass


@video_bp.route("/generate", methods=["POST"])
def generate_video():
    """Submit a video generation job.

    Accepts either JSON body or multipart/form-data (when images are attached).
    Supports up to 5 images for image-to-video.
    """
    from src.video_generation import generate_video as _gen

    image_paths: list[str] = []
    try:
        # Multipart form (image upload)
        if request.content_type and "multipart" in request.content_type:
            prompt = (request.form.get("prompt") or "").strip()
            size = request.form.get("size", "1280x720")
            seconds = request.form.get("seconds", "8")
            model = request.form.get("model", "sora-2")
            # Support both single 'image' and multiple 'images' fields
            images = request.files.getlist("images")
            if not images:
                single = request.files.get("image")
                if single:
                    images = [single]
            image_paths = _save_multiple_uploads(images)
        else:
            data = request.get_json(silent=True) or {}
            prompt = (data.get("prompt") or "").strip()
            size = data.get("size", "1280x720")
            seconds = data.get("seconds", "8")
            model = data.get("model", "sora-2")

        if not prompt:
            return jsonify({"error": "prompt is required"}), 400

        result = _gen(
            prompt=prompt,
            size=size,
            seconds=seconds,
            model=model,
            image_paths=image_paths if image_paths else None,
        )
        return jsonify(result)
    except ValueError as e:
        logger.warning("[Video] Validation error: %s", e)
        return jsonify({"error": "Invalid request parameters"}), 400
    except RuntimeError as e:
        logger.error("[Video] Generation runtime error: %s", e)
        return jsonify({"error": "Video generation service unavailable"}), 503
    except Exception as e:
        logger.error("[Video] Generation error: %s", e, exc_info=True)
        return jsonify({"error": f"Video generation failed: {str(e)}"}), 500
    finally:
        _cleanup_temps(image_paths)


@video_bp.route("/cancel/<video_id>", methods=["POST"])
def cancel_video(video_id: str):
    """Cancel/stop an in-progress or queued video job."""
    from src.video_generation import cancel_video as _cancel

    try:
        job = _cancel(video_id)
        return jsonify(job)
    except RuntimeError as e:
        logger.error("[Video] Cancel runtime error: %s", e)
        return jsonify({"error": "Video service unavailable"}), 503
    except Exception as e:
        logger.error("[Video] Cancel error: %s", e)
        return jsonify({"error": "An internal error occurred"}), 500


@video_bp.route("/status/<video_id>", methods=["GET"])
def video_status(video_id: str):
    """Poll OpenAI for current status of a video job."""
    from src.video_generation import poll_video

    try:
        job = poll_video(video_id)
        return jsonify(job)
    except RuntimeError as e:
        logger.error("[Video] Status poll runtime error: %s", e)
        return jsonify({"error": "Video service unavailable"}), 503
    except Exception as e:
        logger.error("[Video] Status poll error: %s", e)
        return jsonify({"error": "An internal error occurred"}), 500


@video_bp.route("/download/<video_id>", methods=["GET"])
def download_video(video_id: str):
    """Download the generated video file (mp4) — full quality, no re-encoding."""
    from src.video_generation import VIDEO_STORAGE_DIR, download_video as _dl

    local_path = VIDEO_STORAGE_DIR / f"{video_id}.mp4"
    if not local_path.exists():
        try:
            local_path = _dl(video_id)
        except RuntimeError as e:
            logger.error("[Video] Download runtime error: %s", e)
            return jsonify({"error": "Video service unavailable"}), 503
        except Exception as e:
            logger.error("[Video] Download error: %s", e)
            return jsonify({"error": "An internal error occurred"}), 500

    file_size = local_path.stat().st_size
    response = send_file(
        str(local_path),
        mimetype="video/mp4",
        download_name=f"{video_id}.mp4",
        as_attachment=True,
        conditional=False,
    )
    response.headers["Content-Length"] = str(file_size)
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Cache-Control"] = "no-transform"
    return response


@video_bp.route("/stream/<video_id>", methods=["GET"])
def stream_video(video_id: str):
    """Stream video for in-browser playback (inline, not attachment)."""
    from src.video_generation import VIDEO_STORAGE_DIR, download_video as _dl

    local_path = VIDEO_STORAGE_DIR / f"{video_id}.mp4"
    if not local_path.exists():
        try:
            local_path = _dl(video_id)
        except RuntimeError as e:
            logger.error("[Video] Stream runtime error: %s", e)
            return jsonify({"error": "Video service unavailable"}), 503
        except Exception as e:
            logger.error("[Video] Stream error: %s", e)
            return jsonify({"error": "An internal error occurred"}), 500

    file_size = local_path.stat().st_size
    response = send_file(
        str(local_path),
        mimetype="video/mp4",
        conditional=False,
    )
    response.headers["Content-Length"] = str(file_size)
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Cache-Control"] = "no-transform"
    response.headers["Content-Disposition"] = "inline"
    return response


@video_bp.route("/list", methods=["GET"])
def list_videos():
    """List recent video generation jobs from local metadata."""
    from src.video_generation import list_jobs

    limit = min(int(request.args.get("limit", 20)), 100)
    return jsonify({"videos": list_jobs(limit=limit)})
