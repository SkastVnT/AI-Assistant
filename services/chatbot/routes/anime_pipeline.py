"""
Anime Layered Pipeline API routes — Flask Blueprint.

Endpoints:
    GET  /api/anime-pipeline/health     → Availability check
    POST /api/anime-pipeline/stream     → SSE streaming pipeline run
    POST /api/anime-pipeline/generate   → Blocking pipeline run (returns JSON)
"""

from __future__ import annotations

import json
import logging
import time as _time
from functools import wraps
from flask import Blueprint, request, jsonify, session, Response

logger = logging.getLogger(__name__)

anime_pipeline_bp = Blueprint("anime_pipeline", __name__)

# ── Rate limiting (shared with image-gen pattern) ───────────────────────
_RATE_WINDOW = 120  # wider window — pipeline jobs take longer
_RATE_MAX = 5       # fewer concurrent jobs allowed
_req_log: dict = {}


def _rate_check() -> str | None:
    sid = session.get("session_id", request.remote_addr or "anon")
    now = _time.time()
    log = _req_log.setdefault(sid, [])
    _req_log[sid] = [t for t in log if t > now - _RATE_WINDOW]
    if len(_req_log[sid]) >= _RATE_MAX:
        return f"Rate limited ({_RATE_MAX} pipeline jobs per {_RATE_WINDOW}s)"
    _req_log[sid].append(now)
    return None


# ── Health / availability ───────────────────────────────────────────────

@anime_pipeline_bp.route("/api/anime-pipeline/health", methods=["GET"])
def health():
    """
    Pre-flight check.  Returns:
        { available: bool, feature_flag: bool, comfyui_reachable: bool, errors: [...] }
    """
    from core.anime_pipeline_service import check_availability
    result = check_availability()
    status = 200 if result.available else 503
    return jsonify(result.to_dict()), status


# ── Streaming SSE endpoint ──────────────────────────────────────────────

@anime_pipeline_bp.route("/api/anime-pipeline/stream", methods=["POST"])
def stream_pipeline():
    """
    Run the layered anime pipeline with real-time SSE progress events.

    Body (JSON):
        prompt:              str   — required, max 2 000 chars
        reference_images:    [str] — optional list of base64 images (max 4)
        preset:              str   — anime_quality | anime_speed | anime_balanced
        quality_mode:        str   — auto | fast | quality
        model_base:          str   — optional checkpoint override (composition pass)
        model_cleanup:       str   — optional checkpoint override (cleanup pass)
        model_final:         str   — optional checkpoint override (beauty pass)
        debug:               bool  — if true, stream intermediate previews
        width:               int   — override width (0 = auto from config)
        height:              int   — override height (0 = auto from config)

    SSE events:
        ap_status       — pipeline initialised
        ap_stage_start  — stage begun   { stage, label, stage_num, total_stages }
        ap_stage_done   — stage done    { stage, latency_ms }
        ap_preview      — intermediate  { stage, image_b64 }   (debug only)
        ap_refine       — refine round  { round, previous_score }
        ap_result       — final result  { job_id, image_b64, manifest, ... }
        ap_error        — error         { error, recoverable }
        ap_done         — sentinel      { job_id }
    """
    from core.anime_pipeline_service import (
        check_availability, validate_request, stream_pipeline as _stream,
    )

    # ── Availability gate ───────────────────────────────────────────
    avail = check_availability()
    if not avail.available:
        def _err_unavail():
            yield (
                "event: ap_error\ndata: "
                + json.dumps({
                    "error": "; ".join(avail.errors),
                    "recoverable": False,
                    "availability": avail.to_dict(),
                })
                + "\n\n"
            )
        return Response(
            _err_unavail(),
            mimetype="text/event-stream",
            status=503,
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── Rate check ──────────────────────────────────────────────────
    rate_err = _rate_check()
    if rate_err:
        def _err_rate():
            yield "event: ap_error\ndata: " + json.dumps({"error": rate_err}) + "\n\n"
        return Response(_err_rate(), mimetype="text/event-stream", status=429)

    # ── Validate payload ────────────────────────────────────────────
    data = request.get_json(force=True, silent=True) or {}
    req, val_err = validate_request(data)
    if val_err:
        def _err_val():
            yield "event: ap_error\ndata: " + json.dumps({"error": val_err}) + "\n\n"
        return Response(_err_val(), mimetype="text/event-stream", status=400)

    # Fill session context
    req.session_id = session.get("session_id", request.remote_addr or "")
    req.conversation_id = data.get("conversation_id", session.get("conversation_id", ""))

    return Response(
        _stream(req),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Blocking endpoint (JSON) ───────────────────────────────────────────

@anime_pipeline_bp.route("/api/anime-pipeline/generate", methods=["POST"])
def generate_pipeline():
    """
    Blocking pipeline run.  Returns the full result as JSON.
    Same body as /stream minus the SSE wrapper.
    """
    from core.anime_pipeline_service import (
        check_availability, validate_request, build_job, persist_pipeline_result,
    )

    avail = check_availability()
    if not avail.available:
        return jsonify({"error": "; ".join(avail.errors), "availability": avail.to_dict()}), 503

    rate_err = _rate_check()
    if rate_err:
        return jsonify({"error": rate_err}), 429

    data = request.get_json(force=True, silent=True) or {}
    req, val_err = validate_request(data)
    if val_err:
        return jsonify({"error": val_err}), 400

    req.session_id = session.get("session_id", request.remote_addr or "")
    req.conversation_id = data.get("conversation_id", session.get("conversation_id", ""))

    try:
        from image_pipeline.anime_pipeline import AnimePipelineOrchestrator

        job = build_job(req)
        orchestrator = AnimePipelineOrchestrator()
        orchestrator.run(job)

        result = job.to_dict()
        if job.final_image_b64:
            result["image_b64"] = job.final_image_b64
            result.update(persist_pipeline_result(job, req))

        return jsonify(result)

    except ImportError as e:
        logger.error("[anime_pipeline] Import error: %s", e)
        return jsonify({"error": "Anime pipeline modules not available"}), 500
    except Exception as e:
        logger.error("[anime_pipeline] Failed: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


# ── Upload reference images endpoint ────────────────────────────────────

@anime_pipeline_bp.route("/api/anime-pipeline/upload-refs", methods=["POST"])
def upload_reference_images():
    """
    Upload reference images for character identity.
    Accepts multipart/form-data with 'files' field (max 4 images).
    Optionally includes 'character_tag' to associate with a character.

    Returns:
        { reference_images: [base64_str, ...], count: int }
    """
    import base64

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400
    if len(files) > 4:
        return jsonify({"error": "Maximum 4 reference images allowed"}), 400

    character_tag = request.form.get("character_tag", "").strip()
    refs_b64 = []

    for f in files:
        if not f.content_type or not f.content_type.startswith("image/"):
            continue
        img_data = f.read()
        if len(img_data) > 10_000_000:  # 10MB limit per image
            continue
        if len(img_data) < 1000:  # too small
            continue
        refs_b64.append(base64.b64encode(img_data).decode("ascii"))

    if not refs_b64:
        return jsonify({"error": "No valid image files found"}), 400

    # Optionally save to character reference storage
    if character_tag:
        try:
            from image_pipeline.anime_pipeline.character_research import _REF_DIR
            import hashlib

            ref_dir = _REF_DIR / character_tag / "user"
            ref_dir.mkdir(parents=True, exist_ok=True)
            for i, b64 in enumerate(refs_b64):
                img_bytes = base64.b64decode(b64)
                h = hashlib.md5(img_bytes).hexdigest()[:8]
                path = ref_dir / f"upload_{h}.png"
                path.write_bytes(img_bytes)
                logger.info("[anime_pipeline] Saved user ref: %s", path)
        except Exception as e:
            logger.warning("[anime_pipeline] Could not save user refs: %s", e)

    return jsonify({
        "reference_images": refs_b64,
        "count": len(refs_b64),
        "character_tag": character_tag or None,
    })
