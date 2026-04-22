"""FastAPI router — Local image-job queue tracker.

Mirrors the Flask blueprint at /api/jobs/* so the topbar
"Job Queue" panel works under both ``USE_FASTAPI=true`` and the
Flask legacy app. Routes are kept verbatim with the Flask version
so the frontend (services/chatbot/static/js/modules/job-queue-panel.js)
needs zero changes.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from core.job_queue import JOB_STATES, get_queue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("")
@router.get("/")
def list_jobs(
    state: Optional[str] = Query(None, description="Filter by job state"),
    limit: int = Query(50, ge=1, le=200),
):
    if state and state not in JOB_STATES:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_state", "valid": list(JOB_STATES)},
        )
    q = get_queue()
    items = q.list(state=state, limit=limit)
    return {
        "jobs": [r.to_dict() for r in items],
        "count": len(items),
        "stats": q.stats(),
    }


@router.get("/stats")
def stats():
    return get_queue().stats()


@router.get("/{job_id}")
def get_job(job_id: str):
    q = get_queue()
    rec = q.get(job_id)
    if rec is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "job_id": job_id},
        )
    return {"job": rec.to_dict()}


@router.get("/{job_id}/manifest")
def get_manifest(job_id: str):
    """Return the manifest JSON written by ResultStore, if available."""
    repo_root = Path(__file__).resolve().parents[4]
    candidate = (repo_root / "storage" / "metadata" / f"{job_id}.json").resolve()
    try:
        candidate.relative_to(repo_root)
    except ValueError:
        raise HTTPException(status_code=403)

    if not candidate.exists():
        # Fall back to in-memory job record if the manifest file was not
        # written yet (e.g. job still running, or ResultStore disabled).
        rec = get_queue().get(job_id)
        if rec is None:
            return JSONResponse(
                status_code=404,
                content={"error": "not_found", "job_id": job_id},
            )
        return {"job": rec.to_dict(), "manifest_source": "memory"}
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("jobs.get_manifest: failed to read %s: %s", candidate, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "manifest_unreadable"},
        )
    return {
        "manifest": data,
        "manifest_source": "file",
        "path": str(candidate),
    }


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str):
    q = get_queue()
    ok = q.request_cancel(job_id)
    if not ok:
        return JSONResponse(
            status_code=404,
            content={"cancelled": False, "reason": "not_found_or_terminal"},
        )
    return {"cancelled": True, "job_id": job_id}
