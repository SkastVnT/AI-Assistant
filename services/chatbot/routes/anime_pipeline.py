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
import re
import time as _time
from functools import wraps
from flask import Blueprint, request, jsonify, session, Response

from core.character_registry import get_registry
from core.job_queue import get_queue

logger = logging.getLogger(__name__)

anime_pipeline_bp = Blueprint("anime_pipeline", __name__)

# Job IDs are produced by AnimePipelineJob (uuid-based, plus optional
# alphanumeric suffixes for re-tries). Be conservative and only accept
# safe characters; rejects path traversal / SQL / XSS payloads from
# untrusted POST bodies.
_VALID_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _enrich_with_character(data: dict) -> dict:
    """If payload contains ``character_key``, prepend a fully-qualified
    ``Display Name in Series`` phrase to the prompt so the existing
    character_parser resolves identity reliably. Returns enriched dict.

    Resolution order:
      1. Local hand-curated registry (``storage/character_db/``) — preferred,
         carries display_name + series + LoRA hints.
      2. SAA WAI database (5149 entries from
         ``character_select_stand_alone_app-main/data/wai_characters.csv``)
         — long-tail fallback.

    Backward-compatible: if no character_key (or unresolved), returns input.
    """
    char_key = (data.get("character_key") or "").strip()
    if not char_key:
        return data

    rec = get_registry().get(char_key)

    # Fallback: SAA WAI DB. The picker may surface keys (especially the
    # autocomplete tag entries) that are not present in the curated local
    # registry. Looking them up against SAA keeps the data flow intact.
    if rec is None:
        try:
            from image_pipeline.anime_pipeline.saa_character_db import lookup_character
            saa_hit = lookup_character(char_key)
        except Exception as e:  # pragma: no cover — defensive import guard
            logger.debug("[anime_pipeline] SAA fallback unavailable: %s", e)
            saa_hit = None

        if saa_hit is not None:
            class _SAARecord:  # lightweight stand-in matching the queue contract
                __slots__ = ("key", "display_name", "series", "series_key")
                def __init__(self, key: str, display: str, series: str | None) -> None:
                    self.key = key
                    self.display_name = display
                    self.series = series or ""
                    self.series_key = (series or "").strip().lower().replace(" ", "_") or None
            rec = _SAARecord(char_key, saa_hit.display_name, saa_hit.series_hint)
            logger.info(
                "[anime_pipeline] character_key %s resolved via SAA WAI DB (%s)",
                char_key, saa_hit.display_name,
            )
        else:
            logger.warning("[anime_pipeline] character_key %s not in registry or SAA", char_key)
            return data

    prompt = (data.get("prompt") or "").strip()
    qualified = f"{rec.display_name} in {rec.series}" if rec.series else rec.display_name
    # Only prepend if the qualified phrase isn't already present
    if qualified.lower() not in prompt.lower():
        new_prompt = f"{qualified}, {prompt}" if prompt else qualified
    else:
        new_prompt = prompt
    enriched = dict(data)
    enriched["prompt"] = new_prompt
    enriched["_resolved_character"] = rec
    return enriched


def _wrap_stream_with_queue(inner_gen, character_record=None, preset: str = "",
                             prompt_preview: str = ""):
    """Wrap an SSE generator to mirror lifecycle into the JobQueue.

    Parses ``ap_status``, ``ap_stage_start``, ``ap_stage_done``, ``ap_result``,
    ``ap_error``, ``ap_done`` frames to extract job_id and update queue state.
    Pass-through everything verbatim — never modifies the SSE stream.
    """
    queue = get_queue()
    job_id_seen: dict[str, str] = {}
    cancelled_seen = {"v": False}

    def _ensure_registered(jid: str) -> None:
        if not jid or queue.get(jid) is not None:
            return
        queue.create(
            job_id=jid,
            prompt=prompt_preview[:500],
            character_key=getattr(character_record, "key", None),
            character_display=getattr(character_record, "display_name", None),
            series_key=getattr(character_record, "series_key", None),
            preset=preset or None,
        )

    def _gen():
        try:
            for frame in inner_gen:
                # Frame is an SSE-formatted string: "event: X\ndata: {...}\n\n"
                # Best-effort parse: extract event + first data JSON.
                yield frame
                if not isinstance(frame, str) or "event:" not in frame:
                    continue
                try:
                    lines = frame.split("\n")
                    event_name = ""
                    data_payload = None
                    for ln in lines:
                        if ln.startswith("event:"):
                            event_name = ln.split(":", 1)[1].strip()
                        elif ln.startswith("data:"):
                            raw = ln.split(":", 1)[1].strip()
                            try:
                                data_payload = json.loads(raw)
                            except Exception:
                                data_payload = None
                    if not event_name:
                        continue
                    jid = (data_payload or {}).get("job_id", "") if data_payload else ""
                    if jid and "id" not in job_id_seen:
                        job_id_seen["id"] = jid
                        _ensure_registered(jid)
                    current_jid = job_id_seen.get("id", jid)
                    if not current_jid:
                        continue
                    if event_name == "ap_status":
                        queue.transition(current_jid, "queued")
                    elif event_name in ("ap_stage_start",):
                        stage = (data_payload or {}).get("stage", "")
                        stage_num = (data_payload or {}).get("stage_num", 0)
                        total = (data_payload or {}).get("total_stages", 8) or 8
                        pct = (stage_num / total) * 100 if total else None
                        queue.transition(current_jid, "running",
                                         progress_stage=stage)
                        if pct is not None:
                            queue.update_progress(current_jid, pct=pct)
                    elif event_name == "ap_stage_done":
                        stage = (data_payload or {}).get("stage", "")
                        queue.update_progress(current_jid, stage=stage)
                    elif event_name == "ap_result":
                        manifest = (data_payload or {}).get("manifest") or {}
                        final_path = manifest.get("final_image_path") or manifest.get("filename")
                        # If the user already pressed Stop & Export, keep
                        # the queue state as ``cancelled`` instead of
                        # flipping it back to ``completed`` when the
                        # partial image flushes through.
                        if cancelled_seen["v"]:
                            queue.transition(current_jid, "cancelled",
                                             progress_pct=100.0,
                                             final_image_path=final_path,
                                             manifest_path=manifest.get("manifest_path"))
                        else:
                            queue.transition(current_jid, "completed",
                                             progress_pct=100.0,
                                             final_image_path=final_path,
                                             manifest_path=manifest.get("manifest_path"))
                    elif event_name == "ap_cancelled":
                        cancelled_seen["v"] = True
                        queue.transition(
                            current_jid, "cancelled",
                            progress_stage=(data_payload or {}).get("stage", ""),
                        )
                    elif event_name == "ap_error":
                        err = (data_payload or {}).get("error", "unknown")
                        queue.transition(current_jid, "failed", error=str(err))
                    elif event_name == "ap_done":
                        rec = queue.get(current_jid)
                        if rec and rec.state == "running":
                            queue.transition(current_jid, "completed",
                                             progress_pct=100.0)
                except Exception as parse_exc:
                    logger.debug("[anime_pipeline] queue-wrap parse error: %s", parse_exc)
        except GeneratorExit:
            jid = job_id_seen.get("id")
            if jid:
                rec = queue.get(jid)
                if rec and rec.state in ("queued", "running"):
                    queue.transition(jid, "cancelled", error="client disconnected")
            raise

    return _gen()

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
    data = _enrich_with_character(data)
    resolved_char = data.pop("_resolved_character", None)
    req, val_err = validate_request(data)
    if val_err:
        def _err_val():
            yield "event: ap_error\ndata: " + json.dumps({"error": val_err}) + "\n\n"
        return Response(_err_val(), mimetype="text/event-stream", status=400)

    # Fill session context
    req.session_id = session.get("session_id", request.remote_addr or "")
    req.conversation_id = data.get("conversation_id", session.get("conversation_id", ""))

    inner = _stream(req)
    wrapped = _wrap_stream_with_queue(
        inner, character_record=resolved_char,
        preset=req.preset, prompt_preview=req.prompt,
    )
    return Response(
        wrapped,
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
    data = _enrich_with_character(data)
    resolved_char = data.pop("_resolved_character", None)
    req, val_err = validate_request(data)
    if val_err:
        return jsonify({"error": val_err}), 400

    req.session_id = session.get("session_id", request.remote_addr or "")
    req.conversation_id = data.get("conversation_id", session.get("conversation_id", ""))

    try:
        from image_pipeline.anime_pipeline import AnimePipelineOrchestrator

        job = build_job(req)
        # Register in JobQueue for visibility (sync call — no SSE wrapper)
        get_queue().create(
            job_id=job.job_id,
            prompt=req.prompt[:500],
            character_key=getattr(resolved_char, "key", None),
            character_display=getattr(resolved_char, "display_name", None),
            series_key=getattr(resolved_char, "series_key", None),
            preset=req.preset,
        )
        get_queue().transition(job.job_id, "running")
        orchestrator = AnimePipelineOrchestrator()
        orchestrator.run(job)

        result = job.to_dict()
        if job.final_image_b64:
            result["image_b64"] = job.final_image_b64
            result.update(persist_pipeline_result(job, req))

        get_queue().transition(
            job.job_id, "completed", progress_pct=100.0,
            final_image_path=getattr(job, "final_image_spec_path", None)
            or getattr(job, "final_image_path", None),
        )
        return jsonify(result)

    except ImportError as e:
        logger.error("[anime_pipeline] Import error: %s", e)
        return jsonify({"error": "Anime pipeline modules not available"}), 500
    except Exception as e:
        logger.error("[anime_pipeline] Failed: %s", e, exc_info=True)
        try:
            get_queue().transition(job.job_id, "failed", error=str(e))  # type: ignore[name-defined]
        except Exception:
            pass
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
                h = hashlib.md5(img_bytes, usedforsecurity=False).hexdigest()[:8]
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


# ── Cancel endpoint ─────────────────────────────────────────────────────

@anime_pipeline_bp.route("/api/anime-pipeline/cancel", methods=["POST"])
def cancel_pipeline():
    """Request cancellation of an in-flight anime-pipeline job.

    Body (JSON):
        job_id: str   — the job_id captured from the first ap_status frame

    Sets the JobQueue's ``cancel_requested`` flag. The orchestrator polls
    this flag between major stages (composition_pass, structure_lock,
    beauty_pass) and on the next checkpoint emits ``ap_cancelled`` plus a
    final ``ap_result`` containing the best-so-far image. The SSE stream
    is never killed by this endpoint — the partial image flows through
    the normal chat-bubble code path.

    Returns:
        200 { ok: bool, was_terminal: bool, job_id: str }
        400 { ok: false, error: "..." }  on invalid job_id format
    """
    data = request.get_json(force=True, silent=True) or {}
    raw_jid = (data.get("job_id") or "").strip()
    if not raw_jid:
        return jsonify({"ok": False, "error": "job_id is required"}), 400
    if not _VALID_JOB_ID_RE.match(raw_jid):
        return jsonify({"ok": False, "error": "invalid job_id format"}), 400

    queue = get_queue()
    rec = queue.get(raw_jid)
    if rec is None:
        # Unknown job: nothing to cancel. Return ok so the UI can
        # collapse its progress bubble without showing an error.
        logger.info("[anime_pipeline] /cancel: unknown job %s", raw_jid)
        return jsonify({"ok": True, "was_terminal": True, "job_id": raw_jid})

    accepted = queue.request_cancel(raw_jid)
    was_terminal = not accepted  # request_cancel returns False for terminal states

    # Hard-stop: also POST /interrupt to ComfyUI so the GPU pass that is
    # currently in flight stops too. Without this, the orchestrator only
    # bails between stages — the active KSampler keeps painting on the
    # GPU for another 30-60 s after the user clicked Stop, which is what
    # the user means by "Đã ngưng rồi mà bên ComfyUI còn chạy". Failure
    # is silently swallowed (best-effort) so a missing ComfyUI does not
    # turn the cancel button into a 500.
    if accepted:
        try:
            _interrupt_comfyui()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("[anime_pipeline] /cancel: comfy interrupt failed: %s", exc)

    logger.info(
        "[anime_pipeline] /cancel: job=%s accepted=%s state=%s",
        raw_jid, accepted, rec.state,
    )
    return jsonify({"ok": True, "was_terminal": was_terminal, "job_id": raw_jid})


@anime_pipeline_bp.route("/api/anime-pipeline/cancel-all", methods=["POST"])
def cancel_all_pipelines():
    """Nuclear Stop: cancel every active anime-pipeline job.

    Called by the Stop button as a belt-and-suspenders alongside
    ``/cancel`` so the server always halts even when the client did
    not yet know the ``job_id`` (e.g. Stop pressed before the first
    ``ap_status`` frame landed, or the bubble was recreated and lost
    its ``dataset.jobId``). Also fires ComfyUI ``/interrupt`` once to
    kill the currently running GPU workflow.
    """
    queue = get_queue()
    accepted = queue.request_cancel_all()
    try:
        _interrupt_comfyui()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("[anime_pipeline] /cancel-all: comfy interrupt failed: %s", exc)
    logger.info("[anime_pipeline] /cancel-all: accepted=%d", len(accepted))
    return jsonify({"ok": True, "cancelled": accepted, "count": len(accepted)})


def _interrupt_comfyui() -> None:
    """Best-effort POST /interrupt to the active ComfyUI server.

    Uses the same env vars the pipeline ComfyClient honors so we always
    hit the same instance the orchestrator submitted to.
    """
    import os
    import httpx

    base = (
        os.getenv("ANIME_PIPELINE_COMFYUI_URL")
        or os.getenv("COMFYUI_URL")
        or "http://127.0.0.1:8188"
    ).rstrip("/")
    with httpx.Client(timeout=3.0) as client:
        resp = client.post(f"{base}/interrupt")
        logger.info(
            "[anime_pipeline] /cancel: comfy interrupt -> %s (%s)",
            base, resp.status_code,
        )
