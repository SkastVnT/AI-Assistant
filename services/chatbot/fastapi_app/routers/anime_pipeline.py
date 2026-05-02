"""
FastAPI router — Anime Layered Pipeline.

Mirrors the Flask blueprint at /api/anime-pipeline/*.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/anime-pipeline", tags=["Anime Pipeline"])


@router.get("/images/{filename:path}")
async def serve_pipeline_image(filename: str):
    """Serve saved anime pipeline output images."""
    import os
    from pathlib import Path
    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    safe = os.path.basename(filename)
    if not safe:
        raise HTTPException(status_code=404)

    # Resolve from chatbot service root
    storage_dir = Path(__file__).parent.parent.parent / "Storage" / "Image_Gen"
    file_path = storage_dir / safe
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Image not found: {safe}")
    return FileResponse(str(file_path), media_type="image/png")


@router.get("/health")
async def health():
    """Pre-flight availability check."""
    from core.anime_pipeline_service import check_availability

    result = check_availability()
    status = 200 if result.available else 503
    return JSONResponse(result.to_dict(), status_code=status)


@router.post("/stream")
async def stream_pipeline(request: Request):
    """SSE streaming anime pipeline run."""
    from core.anime_pipeline_service import (
        check_availability,
        validate_request,
        stream_pipeline as _stream,
    )

    avail = check_availability()
    if not avail.available:
        async def _err():
            yield (
                "event: ap_error\ndata: "
                + json.dumps({"error": "; ".join(avail.errors), "recoverable": False})
                + "\n\n"
            )
        return StreamingResponse(
            _err(),
            media_type="text/event-stream",
            status_code=503,
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    req, val_err = validate_request(data)
    if val_err:
        async def _err_val():
            yield "event: ap_error\ndata: " + json.dumps({"error": val_err}) + "\n\n"
        return StreamingResponse(_err_val(), media_type="text/event-stream", status_code=400)

    req.session_id = request.session.get("session_id", request.client.host if request.client else "")
    req.conversation_id = data.get("conversation_id", "")

    async def _wrap():
        for frame in _stream(req):
            yield frame

    return StreamingResponse(
        _wrap(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/generate")
async def generate_pipeline(request: Request):
    """Blocking pipeline run — returns JSON."""
    from core.anime_pipeline_service import (
        check_availability,
        validate_request,
        build_job,
    )

    avail = check_availability()
    if not avail.available:
        return JSONResponse(
            {"error": "; ".join(avail.errors), "availability": avail.to_dict()},
            status_code=503,
        )

    data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    req, val_err = validate_request(data)
    if val_err:
        return JSONResponse({"error": val_err}, status_code=400)

    req.session_id = request.session.get("session_id", request.client.host if request.client else "")

    try:
        from image_pipeline.anime_pipeline import AnimePipelineOrchestrator

        job = build_job(req)
        orchestrator = AnimePipelineOrchestrator()
        orchestrator.run(job)

        result = job.to_dict()
        if job.final_image_b64:
            result["image_b64"] = job.final_image_b64

        return JSONResponse(result)

    except ImportError as e:
        logger.error("[anime_pipeline] Import error: %s", e)
        return JSONResponse({"error": "Anime pipeline modules not available"}, status_code=500)
    except Exception as e:
        logger.error("[anime_pipeline] Failed: %s", e, exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Cancel endpoint ─────────────────────────────────────────────────────────
# Mirror of routes/anime_pipeline.py::cancel_pipeline so the Stop button
# also works under USE_FASTAPI=true. Without this, the JS POST to
# /api/anime-pipeline/cancel returns 404 in FastAPI mode and ComfyUI
# keeps grinding away on the GPU long after the user clicked Stop.

import re as _re

_VALID_JOB_ID_RE = _re.compile(r"^[A-Za-z0-9_\-:.]{1,128}$")


def _interrupt_comfyui() -> None:
    """Best-effort POST /interrupt to the active ComfyUI server."""
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


@router.post("/cancel")
async def cancel_pipeline(request: Request):
    from core.job_queue import get_queue

    try:
        data = await request.json()
    except Exception:
        data = {}
    raw_jid = (data.get("job_id") or "").strip() if isinstance(data, dict) else ""
    if not raw_jid:
        return JSONResponse({"ok": False, "error": "job_id is required"}, status_code=400)
    if not _VALID_JOB_ID_RE.match(raw_jid):
        return JSONResponse({"ok": False, "error": "invalid job_id format"}, status_code=400)

    queue = get_queue()
    rec = queue.get(raw_jid)
    if rec is None:
        return {"ok": True, "was_terminal": True, "job_id": raw_jid}

    accepted = queue.request_cancel(raw_jid)
    was_terminal = not accepted
    if accepted:
        try:
            _interrupt_comfyui()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("[anime_pipeline] /cancel: comfy interrupt failed: %s", exc)
    logger.info(
        "[anime_pipeline] /cancel: job=%s accepted=%s state=%s",
        raw_jid, accepted, rec.state,
    )
    return {"ok": True, "was_terminal": was_terminal, "job_id": raw_jid}


@router.post("/cancel-all")
async def cancel_all_pipelines():
    """Nuclear Stop: cancel every active anime-pipeline job and hit
    ComfyUI ``/interrupt`` once. The frontend Stop button calls this
    as a belt-and-suspenders alongside ``/cancel`` so the server
    always halts — even when ``job_id`` is missing on the client.
    """
    from core.job_queue import get_queue

    accepted = get_queue().request_cancel_all()
    try:
        _interrupt_comfyui()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("[anime_pipeline] /cancel-all: comfy interrupt failed: %s", exc)
    logger.info("[anime_pipeline] /cancel-all: accepted=%d", len(accepted))
    return {"ok": True, "cancelled": accepted, "count": len(accepted)}


# ── Upscale / fix-text mirrors ──────────────────────────────────────────
# Without these, the /api/anime-pipeline/upscale POST from the lightbox
# returns 404 under USE_FASTAPI=true (the Flask blueprint isn't mounted).
# Both routes share the pure helper ``run_upscale_payload`` defined in
# routes/anime_pipeline.py so logic stays in one place.

@router.post("/upscale")
async def upscale_image_fastapi(request: Request):
    from fastapi.concurrency import run_in_threadpool
    from routes.anime_pipeline import run_upscale_payload

    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}

    body, status = await run_in_threadpool(run_upscale_payload, data)
    return JSONResponse(body, status_code=status)


@router.post("/fix-text")
async def fix_text_fastapi(request: Request):
    """Backward-compat alias: forwards to /upscale with factor=1.0
    + denoise=0.40 (text-repair only, no resize)."""
    from fastapi.concurrency import run_in_threadpool
    from routes.anime_pipeline import run_upscale_payload

    try:
        data = await request.json()
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    data["factor"] = 1.0
    data.setdefault("denoise", 0.40)

    body, status = await run_in_threadpool(run_upscale_payload, data)
    return JSONResponse(body, status_code=status)
