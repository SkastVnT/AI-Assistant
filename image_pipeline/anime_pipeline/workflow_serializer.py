"""
image_pipeline.anime_pipeline.workflow_serializer — Workflow metadata wrapper.

Attaches version, provenance, and debug metadata to ComfyUI workflow JSON.
Used by ComfyClient when saving workflow JSON in debug mode.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

_WORKFLOW_VERSION = "2.0.0"


def serialize_workflow(
    workflow: dict,
    *,
    pass_name: str = "",
    job_id: str = "",
    version: str = _WORKFLOW_VERSION,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap a workflow dict with version and provenance metadata.

    Returns a dict with:
        _meta: version, pass_name, job_id, node_count, timestamp, extras
        workflow: the original workflow dict
    """
    node_classes = sorted({
        n.get("class_type", "unknown")
        for n in workflow.values()
        if isinstance(n, dict)
    })

    return {
        "_meta": {
            "version": version,
            "pass_name": pass_name,
            "job_id": job_id,
            "node_count": len(workflow),
            "node_classes": node_classes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(extra_meta or {}),
        },
        "workflow": workflow,
    }


def get_workflow_version() -> str:
    """Return current workflow schema version."""
    return _WORKFLOW_VERSION
