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
