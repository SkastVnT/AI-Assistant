"""Routes for the local image-job queue tracker."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request, abort

from core.job_queue import get_queue, JOB_STATES

logger = logging.getLogger(__name__)

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")


@jobs_bp.get("")
@jobs_bp.get("/")
def list_jobs():
    state = request.args.get("state", type=str) or None
    if state and state not in JOB_STATES:
        return jsonify({"error": "invalid_state", "valid": list(JOB_STATES)}), 400
    limit = min(max(request.args.get("limit", 50, type=int), 1), 200)
    q = get_queue()
    items = q.list(state=state, limit=limit)
    return jsonify({
        "jobs": [r.to_dict() for r in items],
        "count": len(items),
        "stats": q.stats(),
    })


@jobs_bp.get("/stats")
def stats():
    return jsonify(get_queue().stats())


@jobs_bp.get("/<job_id>")
def get_job(job_id: str):
    q = get_queue()
    rec = q.get(job_id)
    if rec is None:
        return jsonify({"error": "not_found", "job_id": job_id}), 404
    return jsonify({"job": rec.to_dict()})


@jobs_bp.get("/<job_id>/manifest")
def get_manifest(job_id: str):
    """Return the manifest JSON written by ResultStore, if available."""
    repo_root = Path(__file__).resolve().parents[3]
    candidate = (repo_root / "storage" / "metadata" / f"{job_id}.json").resolve()
    try:
        candidate.relative_to(repo_root)
    except ValueError:
        abort(403)
    if not candidate.exists():
        # Fall back to in-memory job record if manifest file not written
        rec = get_queue().get(job_id)
        if rec is None:
            return jsonify({"error": "not_found", "job_id": job_id}), 404
        return jsonify({"job": rec.to_dict(), "manifest_source": "memory"})
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("jobs.get_manifest: failed to read %s: %s", candidate, exc)
        return jsonify({"error": "manifest_unreadable"}), 500
    return jsonify({"manifest": data, "manifest_source": "file", "path": str(candidate)})


@jobs_bp.post("/<job_id>/cancel")
def cancel_job(job_id: str):
    q = get_queue()
    ok = q.request_cancel(job_id)
    if not ok:
        return jsonify({"cancelled": False, "reason": "not_found_or_terminal"}), 404
    return jsonify({"cancelled": True, "job_id": job_id})
