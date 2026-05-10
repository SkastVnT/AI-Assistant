"""In-memory job queue for local image generation jobs.

Thread-safe singleton tracking job lifecycle:
``queued → running → completed | failed | cancelled``.

This is **state tracking only** — the pipeline orchestrator still runs
synchronously inside the request that creates the job. The queue gives the
UI visibility into job history, in-flight jobs, manifest links, and a
best-effort cancellation flag.

Persistence: jobs are kept in memory with a bounded history (default 200).
For durable manifests use the existing ``ResultStore`` which writes to
``storage/metadata/<job_id>.json``.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from pymongo import MongoClient
except Exception:  # optional dependency
    MongoClient = None


JOB_STATES = ("queued", "running", "completed", "failed", "cancelled")
DEFAULT_HISTORY_LIMIT = 200


@dataclass
class JobRecord:
    job_id: str
    state: str = "queued"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    prompt: str = ""
    character_key: Optional[str] = None
    character_display: Optional[str] = None
    series_key: Optional[str] = None
    preset: Optional[str] = None
    model_slot: Optional[str] = None
    progress_stage: Optional[str] = None
    progress_pct: float = 0.0
    error: Optional[str] = None
    final_image_path: Optional[str] = None
    manifest_path: Optional[str] = None
    cancel_requested: bool = False
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class JobQueue:
    """Thread-safe in-memory job tracker."""

    _instance: Optional["JobQueue"] = None
    _instance_lock = threading.Lock()

    def __init__(self, history_limit: int = DEFAULT_HISTORY_LIMIT) -> None:
        self._lock = threading.RLock()
        self._jobs: OrderedDict[str, JobRecord] = OrderedDict()
        self._history_limit = history_limit
        self._mongo_collection = self._try_init_mongo()

    @classmethod
    def get_instance(cls) -> "JobQueue":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # --- mutations -----------------------------------------------------

    def create(
        self,
        job_id: str,
        prompt: str = "",
        character_key: Optional[str] = None,
        character_display: Optional[str] = None,
        series_key: Optional[str] = None,
        preset: Optional[str] = None,
        model_slot: Optional[str] = None,
        extra: Optional[dict] = None,
    ) -> JobRecord:
        with self._lock:
            rec = JobRecord(
                job_id=job_id,
                state="queued",
                prompt=prompt,
                character_key=character_key,
                character_display=character_display,
                series_key=series_key,
                preset=preset,
                model_slot=model_slot,
                extra=dict(extra or {}),
            )
            self._jobs[job_id] = rec
            self._jobs.move_to_end(job_id)
            self._evict_locked()
            logger.info("job_queue: create %s preset=%s char=%s", job_id, preset, character_key)
            self._persist(rec)
            return rec

    def transition(self, job_id: str, new_state: str, **fields) -> Optional[JobRecord]:
        if new_state not in JOB_STATES:
            raise ValueError(f"invalid job state: {new_state}")
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                logger.warning("job_queue: transition unknown job %s -> %s", job_id, new_state)
                return None
            rec.state = new_state
            now = time.time()
            if new_state == "running" and rec.started_at is None:
                rec.started_at = now
            if new_state in ("completed", "failed", "cancelled") and rec.completed_at is None:
                rec.completed_at = now
            for k, v in fields.items():
                if hasattr(rec, k):
                    setattr(rec, k, v)
                else:
                    rec.extra[k] = v
            self._persist(rec)
            return rec

    def update_progress(self, job_id: str, stage: Optional[str] = None,
                        pct: Optional[float] = None) -> Optional[JobRecord]:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return None
            if stage is not None:
                rec.progress_stage = stage
            if pct is not None:
                rec.progress_pct = max(0.0, min(100.0, float(pct)))
            self._persist(rec)
            return rec

    def request_cancel(self, job_id: str) -> bool:
        with self._lock:
            rec = self._jobs.get(job_id)
            if rec is None:
                return False
            if rec.state in ("completed", "failed", "cancelled"):
                return False
            rec.cancel_requested = True
            logger.info("job_queue: cancel requested for %s", job_id)
            self._persist(rec)
            return True

    def request_cancel_all(self) -> list[str]:
        """Nuclear option: mark every non-terminal job as cancel-requested.

        Returns the list of job IDs that were accepted for cancellation.
        Used by the anime-pipeline ``/cancel-all`` endpoint so the Stop
        button works even when the frontend does not know the job_id
        (e.g. Stop pressed before the first ``ap_status`` frame lands,
        or the bubble was recreated and lost ``dataset.jobId``).
        """
        accepted: list[str] = []
        with self._lock:
            for jid, rec in self._jobs.items():
                if rec.state in ("completed", "failed", "cancelled"):
                    continue
                rec.cancel_requested = True
                accepted.append(jid)
        if accepted:
            logger.info("job_queue: cancel-all requested for %d job(s): %s",
                        len(accepted), accepted)
        return accepted

    def is_cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            rec = self._jobs.get(job_id)
            return bool(rec and rec.cancel_requested)

    # --- queries -------------------------------------------------------

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, state: Optional[str] = None, limit: int = 50) -> list[JobRecord]:
        with self._lock:
            items = list(self._jobs.values())
        items.reverse()  # newest first
        if state:
            items = [r for r in items if r.state == state]
        return items[:limit]

    def stats(self) -> dict:
        counts = {s: 0 for s in JOB_STATES}
        with self._lock:
            for rec in self._jobs.values():
                counts[rec.state] = counts.get(rec.state, 0) + 1
            total = len(self._jobs)
        return {"total": total, "by_state": counts, "history_limit": self._history_limit}

    def _persist(self, rec: JobRecord) -> None:
        if self._mongo_collection is None:
            return
        try:
            self._mongo_collection.update_one({"job_id": rec.job_id}, {"$set": rec.to_dict()}, upsert=True)
        except Exception as exc:
            logger.warning("job_queue: mongo persist failed for %s: %s", rec.job_id, exc)

    def _try_init_mongo(self):
        if MongoClient is None:
            return None
        uri = os.getenv("MONGODB_URI") or os.getenv("MONGO_URI")
        db_name = os.getenv("JOB_QUEUE_DB", "ai_assistant")
        coll = os.getenv("JOB_QUEUE_COLLECTION", "jobs")
        if not uri:
            return None
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=500)
            collection = client[db_name][coll]
            client.admin.command("ping")
            logger.info("job_queue: mongo persistence enabled (%s.%s)", db_name, coll)
            return collection
        except Exception as exc:
            logger.warning("job_queue: mongo disabled (%s)", exc)
            return None

    # --- internal ------------------------------------------------------

    def _evict_locked(self) -> None:
        while len(self._jobs) > self._history_limit:
            evicted_id, _ = self._jobs.popitem(last=False)
            logger.debug("job_queue: evicted %s", evicted_id)


def get_queue() -> JobQueue:
    return JobQueue.get_instance()


__all__ = ["JobQueue", "JobRecord", "JOB_STATES", "get_queue"]
