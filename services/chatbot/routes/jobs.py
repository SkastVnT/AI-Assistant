"""Routes for the local image-job queue tracker."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request

from core.job_queue import JOB_STATES, get_queue

logger = logging.getLogger(__name__)

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")
_REPO_ROOT = Path(__file__).resolve().parents[3]


@jobs_bp.get("")
@jobs_bp.get("/")
def list_jobs():
    state = request.args.get("state", type=str) or None
    if state and state not in JOB_STATES:
        return jsonify({"error": "invalid_state", "valid": list(JOB_STATES)}), 400
    limit = min(max(request.args.get("limit", 50, type=int), 1), 200)
    q = get_queue()
    items = q.list(state=state, limit=limit)
    return jsonify(
        {
            "jobs": [r.to_dict() for r in items],
            "count": len(items),
            "stats": q.stats(),
        }
    )


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
    rec = get_queue().get(job_id)
    candidate = _find_manifest_file(job_id, rec.manifest_path if rec else None)
    if candidate is None:
        # Fall back to in-memory job record if manifest file not written
        if rec is None:
            return jsonify({"error": "not_found", "job_id": job_id}), 404
        return jsonify({"job": rec.to_dict(), "manifest_source": "memory"})
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("jobs.get_manifest: failed to read %s: %s", candidate, exc)
        return jsonify({"error": "manifest_unreadable"}), 500
    return jsonify(
        {"manifest": data, "manifest_source": "file", "path": str(candidate)}
    )


def _find_manifest_file(job_id: str, recorded_path: str | None = None) -> Path | None:
    """Resolve a manifest only from approved app storage locations."""

    repo_root = _REPO_ROOT
    storage_root = (repo_root / "app" / "storage").resolve()
    approved_roots = (
        (storage_root / "metadata").resolve(),
        (storage_root / "intermediate").resolve(),
    )
    candidates: list[Path] = []
    if recorded_path:
        recorded = Path(recorded_path)
        if not recorded.is_absolute():
            recorded = repo_root / recorded
        candidates.append(recorded.resolve())
    candidates.extend(
        [
            (approved_roots[0] / f"{job_id}.json").resolve(),
            (approved_roots[1] / job_id / "output_manifest.json").resolve(),
        ]
    )

    candidate = None
    for path in candidates:
        try:
            if any(path.is_relative_to(root) for root in approved_roots):
                if path.is_file():
                    candidate = path
                    break
            else:
                logger.warning("jobs.get_manifest: rejected unsafe path %s", path)
        except ValueError:
            logger.warning("jobs.get_manifest: rejected unsafe path %s", path)

    return candidate


@jobs_bp.post("/<job_id>/cancel")
def cancel_job(job_id: str):
    q = get_queue()
    ok = q.request_cancel(job_id)
    if not ok:
        return jsonify({"cancelled": False, "reason": "not_found_or_terminal"}), 404
    return jsonify({"cancelled": True, "job_id": job_id})
