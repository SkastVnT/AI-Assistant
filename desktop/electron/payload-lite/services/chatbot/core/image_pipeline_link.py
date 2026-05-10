"""Bridge between asset records remembered by the chatbot and the live
local image pipeline (``core.job_queue`` + persisted manifests).

The chatbot frontend stores image records in ``ChatManager.generatedImages``.
For local-pipeline-launched images the frontend usually only knows the
``job_id`` at the moment the SSE result arrives -- ``manifest_path``,
``character_key``, ``preset``, ``final_image_path`` are server-side state
and may even change after the result frame fires (eg. manifest persistence
finishes a beat later).

This module fills that gap: given a record carrying ``job_id``, it looks up
the singleton :class:`core.job_queue.JobQueue` and copies the few
identifying fields back into the record before it goes into the LLM
context block. It also surfaces a short live-state hint ("running",
"completed", "failed") so the assistant does not claim an image is ready
when the job is still in flight.

Hard rules:

* Pure stdlib at import time. JobQueue is imported lazily and any failure
  is swallowed -- this module must not break a chat turn just because the
  queue subsystem is unavailable (eg. in a unit test, or in a deployment
  where the local pipeline is disabled).
* No second dotenv loader.
* Idempotent: caller-provided fields are never overwritten.
* Bounded: we touch at most ``MAX_LOOKUPS`` records per call, mirroring the
  asset-context cap so an attacker cannot force expensive work by sending
  a huge ``generated_images`` array.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)

# Same cap the LLM context uses -- no point enriching records the formatter
# will discard. Defined locally so we do not pull asset_memory at import time.
MAX_LOOKUPS = 5

# Which JobRecord fields we are willing to copy onto an asset record.
# Keep this list small and explicit -- adding more fields means thinking
# about whether they are safe to expose to the LLM.
_COPYABLE_FROM_JOB = (
    "character_key",
    "character_display",
    "series_key",
    "preset",
    "manifest_path",
    "final_image_path",
)

# Map JobQueue states to short tokens we want in the LLM context.
_STATE_HINT = {
    "queued": "queued",
    "running": "running",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}


def _lookup_job(job_id: str) -> Optional[dict]:
    """Look up *job_id* in the JobQueue singleton; return the dict shape or None.

    The import is lazy and any failure (queue module missing, attribute
    error, exception in ``to_dict``) is logged at DEBUG and returns ``None``.
    Callers must treat ``None`` as "no live information available".
    """
    if not job_id or not isinstance(job_id, str):
        return None
    try:
        from core.job_queue import get_queue  # type: ignore
    except Exception as exc:  # pragma: no cover - defensive only
        logger.debug("image_pipeline_link: job_queue unavailable: %s", exc)
        return None
    try:
        rec = get_queue().get(job_id)
    except Exception as exc:  # pragma: no cover - defensive only
        logger.debug("image_pipeline_link: queue.get(%r) failed: %s", job_id, exc)
        return None
    if rec is None:
        return None
    try:
        return rec.to_dict()
    except Exception as exc:  # pragma: no cover - defensive only
        logger.debug("image_pipeline_link: rec.to_dict() failed for %r: %s", job_id, exc)
        return None


def summarize_job(job_id: str) -> Optional[dict]:
    """Return a compact summary of *job_id*, or None if unknown.

    Shape::

        {
            "job_id": str,
            "state": "queued"|"running"|"completed"|"failed"|"cancelled",
            "character_key": str | None,
            "character_display": str | None,
            "series_key": str | None,
            "preset": str | None,
            "progress_stage": str | None,
            "progress_pct": float,
            "manifest_path": str | None,
            "final_image_path": str | None,
            "error": str | None,
        }

    This is intentionally a flat, JSON-serialisable dict so it can also be
    surfaced through future SSE events without re-shaping.
    """
    raw = _lookup_job(job_id)
    if raw is None:
        return None
    return {
        "job_id": raw.get("job_id") or job_id,
        "state": raw.get("state") or "queued",
        "character_key": raw.get("character_key"),
        "character_display": raw.get("character_display"),
        "series_key": raw.get("series_key"),
        "preset": raw.get("preset"),
        "progress_stage": raw.get("progress_stage"),
        "progress_pct": float(raw.get("progress_pct") or 0.0),
        "manifest_path": raw.get("manifest_path"),
        "final_image_path": raw.get("final_image_path"),
        "error": raw.get("error"),
    }


def enrich_records_with_live_state(records: Iterable[Any]) -> list[Any]:
    """Return a *new* list where records carrying ``job_id`` are augmented.

    For each dict-shaped record with a ``job_id`` we did not yet exhaust
    our lookup budget for, we copy any missing field in
    :data:`_COPYABLE_FROM_JOB` from the JobQueue record, and add a small
    ``pipeline`` block::

        record["pipeline"] = {"state": "...", "progress_stage": "...",
                              "progress_pct": float, "error": "..." or None}

    Caller-provided values always win. Non-dict records and records without
    a ``job_id`` are passed through unchanged. The original list is *not*
    mutated -- we return new dicts so downstream code (eg. session
    persistence) is not surprised by extra keys.

    If the JobQueue subsystem is unavailable, this is a no-op (returns the
    records as-is).
    """
    out: list[Any] = []
    used = 0
    for raw in records or []:
        if not isinstance(raw, dict):
            out.append(raw)
            continue
        job_id = raw.get("job_id")
        if not job_id or used >= MAX_LOOKUPS:
            out.append(raw)
            continue
        summary = summarize_job(job_id)
        if summary is None:
            out.append(raw)
            continue
        used += 1
        merged = dict(raw)
        for field in _COPYABLE_FROM_JOB:
            if not merged.get(field) and summary.get(field):
                merged[field] = summary[field]
        # Attach a tiny live-state block. Keep field names short: this
        # ends up serialised into the LLM prompt in some paths.
        state_token = _STATE_HINT.get(summary["state"], summary["state"])
        merged["pipeline"] = {
            "state": state_token,
            "progress_stage": summary.get("progress_stage"),
            "progress_pct": summary.get("progress_pct") or 0.0,
            "error": summary.get("error"),
        }
        out.append(merged)
    return out


def format_pipeline_hint(record: Any) -> Optional[str]:
    """Produce a one-line hint describing the live state of *record*.

    Used by :mod:`core.asset_memory` to extend a context line for records
    that came out of the local pipeline. Returns ``None`` if the record
    has no ``pipeline`` block (the common case for cloud-provider images).
    """
    if not isinstance(record, dict):
        return None
    pipe = record.get("pipeline")
    if not isinstance(pipe, dict):
        return None
    bits: list[str] = []
    state = pipe.get("state")
    if state:
        bits.append(state)
    stage = pipe.get("progress_stage")
    if stage and state in (None, "running", "queued"):
        bits.append(f"stage={stage}")
    pct = pipe.get("progress_pct")
    if isinstance(pct, (int, float)) and 0.0 < float(pct) < 100.0:
        bits.append(f"{float(pct):.0f}%")
    err = pipe.get("error")
    if err:
        bits.append(f"error={str(err)[:80]}")
    if not bits:
        return None
    return "pipeline: " + ", ".join(bits)
