"""Tests for the anime-pipeline Stop & Export feature and the
multi-session semaphore-timeout fix.

Scope (verbatim from task):
  * /api/anime-pipeline/cancel calls JobQueue.request_cancel
  * /cancel rejects malformed job_ids
  * /cancel returns ok for unknown jobs (UI can clean up)
  * orchestrator's _is_cancel_requested helper is safe when the
    chatbot job_queue module is unavailable
  * the SSE wrapper recognises ap_cancelled and pins the queue state
  * the semaphore-acquire spin loop honours the timeout env var and
    yields ap_error instead of stalling forever
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.image

_CHATBOT_DIR = Path(__file__).resolve().parents[1]
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


# ---------------------------------------------------------------------------
# Minimal fake JobQueue stand-in.
# ---------------------------------------------------------------------------


class _FakeRecord:
    def __init__(self, job_id, state="running"):
        self.job_id = job_id
        self.state = state
        self.cancel_requested = False


class _FakeQueue:
    def __init__(self, jobs=None):
        self._jobs = dict(jobs or {})
        self.cancel_calls = []
        self.transition_calls = []

    def get(self, job_id):
        return self._jobs.get(job_id)

    def request_cancel(self, job_id):
        self.cancel_calls.append(job_id)
        rec = self._jobs.get(job_id)
        if rec is None:
            return False
        if rec.state in ("completed", "failed", "cancelled"):
            return False
        rec.cancel_requested = True
        return True

    def is_cancel_requested(self, job_id):
        rec = self._jobs.get(job_id)
        return bool(rec and rec.cancel_requested)

    def transition(self, job_id, new_state, **fields):
        self.transition_calls.append((job_id, new_state, dict(fields)))
        rec = self._jobs.get(job_id)
        if rec is not None:
            rec.state = new_state
        return rec

    def update_progress(self, job_id, **kw):
        return self._jobs.get(job_id)

    def create(self, job_id, **kw):
        rec = _FakeRecord(job_id, state="queued")
        self._jobs[job_id] = rec
        return rec


# ---------------------------------------------------------------------------
# /api/anime-pipeline/cancel — endpoint behaviour
# ---------------------------------------------------------------------------


@pytest.fixture()
def cancel_app(monkeypatch):
    """Build a minimal Flask app with just the anime_pipeline blueprint
    mounted, and inject a fake JobQueue into core.job_queue."""
    fake = _FakeQueue()
    fake_module = SimpleNamespace(get_queue=lambda: fake)
    monkeypatch.setitem(sys.modules, "core.job_queue", fake_module)

    # Drop any cached version of routes.anime_pipeline so it re-imports
    # against the fake job_queue. Use monkeypatch.delitem (not a raw pop)
    # so the ORIGINAL module object is restored at teardown — otherwise a
    # divergent duplicate leaks into sys.modules and pollutes later tests.
    monkeypatch.delitem(sys.modules, "routes.anime_pipeline", raising=False)

    from flask import Flask
    from routes.anime_pipeline import anime_pipeline_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test"
    app.register_blueprint(anime_pipeline_bp)
    return app, fake


def test_cancel_endpoint_calls_request_cancel(cancel_app):
    app, fake = cancel_app
    fake._jobs["abc123"] = _FakeRecord("abc123", state="running")
    client = app.test_client()
    resp = client.post("/api/anime-pipeline/cancel", json={"job_id": "abc123"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["was_terminal"] is False
    assert body["job_id"] == "abc123"
    assert fake.cancel_calls == ["abc123"]
    assert fake._jobs["abc123"].cancel_requested is True


def test_cancel_endpoint_unknown_job_returns_ok(cancel_app):
    """Unknown job_id should still return ok=True so the UI cleans up."""
    app, fake = cancel_app
    client = app.test_client()
    resp = client.post("/api/anime-pipeline/cancel", json={"job_id": "ghost"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["was_terminal"] is True
    assert fake.cancel_calls == []  # no real cancel attempted


def test_cancel_endpoint_rejects_malformed_job_id(cancel_app):
    app, _fake = cancel_app
    client = app.test_client()
    # Path traversal / shell-meta payloads must be rejected.
    for bad in ("../etc/passwd", "abc; rm -rf /", "abc xyz", "a" * 100):
        resp = client.post("/api/anime-pipeline/cancel", json={"job_id": bad})
        assert resp.status_code == 400, f"expected 400 for {bad!r}"
        body = resp.get_json()
        assert body["ok"] is False


def test_cancel_endpoint_missing_job_id_400(cancel_app):
    app, _fake = cancel_app
    client = app.test_client()
    resp = client.post("/api/anime-pipeline/cancel", json={})
    assert resp.status_code == 400
    assert resp.get_json()["ok"] is False


def test_cancel_endpoint_terminal_state_returns_was_terminal_true(cancel_app):
    app, fake = cancel_app
    fake._jobs["done1"] = _FakeRecord("done1", state="completed")
    client = app.test_client()
    resp = client.post("/api/anime-pipeline/cancel", json={"job_id": "done1"})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["was_terminal"] is True


# ---------------------------------------------------------------------------
# Orchestrator helper — safe when chatbot service unavailable
# ---------------------------------------------------------------------------


def test_orchestrator_is_cancel_requested_safe_without_queue(monkeypatch):
    """The orchestrator must not crash when imported in a context
    where core.job_queue can't be loaded (e.g. standalone CLI)."""
    # Force the soft import to fail.
    monkeypatch.setitem(sys.modules, "core.job_queue", None)
    from image_pipeline.anime_pipeline.orchestrator import _is_cancel_requested

    assert _is_cancel_requested("any_job") is False
    assert _is_cancel_requested("") is False


def test_orchestrator_is_cancel_requested_reads_queue(monkeypatch):
    fake = _FakeQueue({"jx": _FakeRecord("jx", state="running")})
    fake._jobs["jx"].cancel_requested = True
    monkeypatch.setitem(
        sys.modules,
        "core.job_queue",
        SimpleNamespace(get_queue=lambda: fake),
    )
    from image_pipeline.anime_pipeline.orchestrator import _is_cancel_requested

    assert _is_cancel_requested("jx") is True
    assert _is_cancel_requested("other") is False


# ---------------------------------------------------------------------------
# _wrap_stream_with_queue handles ap_cancelled
# ---------------------------------------------------------------------------


def _sse(event, payload):
    import json as _j

    return f"event: {event}\ndata: {_j.dumps(payload)}\n\n"


def test_wrap_stream_handles_ap_cancelled_keeps_state_cancelled(monkeypatch):
    """After ap_cancelled, a subsequent ap_result must NOT bump the
    queue state back to ``completed`` — it should stay ``cancelled``."""
    fake = _FakeQueue()
    monkeypatch.setitem(
        sys.modules,
        "core.job_queue",
        SimpleNamespace(get_queue=lambda: fake),
    )
    monkeypatch.delitem(sys.modules, "routes.anime_pipeline", raising=False)
    from routes.anime_pipeline import _wrap_stream_with_queue

    def inner():
        yield _sse("ap_status", {"job_id": "j1", "message": "starting"})
        yield _sse("ap_cancelled", {"job_id": "j1", "stage": "beauty_pass"})
        yield _sse("ap_result", {"job_id": "j1", "manifest": {}})
        yield _sse("ap_done", {"job_id": "j1"})

    frames = list(_wrap_stream_with_queue(inner(), prompt_preview="x"))
    assert len(frames) == 4  # all forwarded verbatim
    final_state = fake._jobs["j1"].state
    assert final_state == "cancelled", (
        f"expected cancelled, got {final_state}; transitions={fake.transition_calls}"
    )


# ---------------------------------------------------------------------------
# Semaphore timeout — multi-session stall fix
# ---------------------------------------------------------------------------


def test_semaphore_timeout_yields_ap_error(monkeypatch):
    """When the GPU semaphore can't be acquired within the timeout,
    stream_pipeline must yield ap_error + ap_done and return cleanly
    instead of spinning forever."""
    # Use the ALREADY-imported module — do NOT delitem+reimport it. A fresh
    # import creates a duplicate module object and, critically, rebinds the
    # `core.anime_pipeline_service` attribute on the `core` package to the
    # duplicate. monkeypatch.delitem only restores sys.modules, not that
    # package attribute, so patch("core.anime_pipeline_service.X") (which
    # resolves via the package attribute) would then target the duplicate
    # while routes resolve the original via sys.modules — the divergence
    # that broke test_anime_pipeline_integration in the full suite.
    # The queue timeout is a module global, so patch it directly.
    import core.anime_pipeline_service as svc

    monkeypatch.setattr(svc, "_PIPELINE_QUEUE_TIMEOUT_SEC", 0.5)

    # Drain the semaphore so any acquire(blocking=False) returns False.
    while svc._PIPELINE_SEMAPHORE.acquire(blocking=False):
        pass

    # Build a minimal fake job + req. stream_pipeline yields the very
    # first ap_status frame before hitting the queue gate, so we must
    # let it through.
    fake_job = SimpleNamespace(job_id="qtest1")

    def fake_build_job(_req):
        return fake_job

    monkeypatch.setattr(svc, "build_job", fake_build_job)

    # Stub the orchestrator import inside stream_pipeline.
    import image_pipeline.anime_pipeline as ap_pkg

    monkeypatch.setattr(
        ap_pkg,
        "AnimePipelineOrchestrator",
        lambda: SimpleNamespace(run_stream=lambda j: iter([])),
        raising=False,
    )

    fake_req = SimpleNamespace(
        prompt="hello",
        reference_images=[],
        preset="anime_quality",
        quality_mode="quality",
        debug=False,
        model_base="",
        model_cleanup="",
        model_final="",
        width=0,
        height=0,
        session_id="",
        conversation_id="",
    )

    t0 = time.time()
    frames = []
    try:
        for frame in svc.stream_pipeline(fake_req):
            frames.append(frame)
            if len(frames) > 50:  # safety cap
                break
    finally:
        # Restore semaphore for other tests.
        for _ in range(svc._PIPELINE_MAX_CONCURRENT):
            try:
                svc._PIPELINE_SEMAPHORE.release()
            except ValueError:
                break

    elapsed = time.time() - t0
    # Must finish well under 5s (timeout is 0.5s + initial frames).
    assert elapsed < 5.0, f"stream did not honour timeout ({elapsed:.1f}s)"
    joined = "\n".join(frames)
    assert "event: ap_error" in joined, f"no ap_error frame: {joined!r}"
    assert "queue" in joined.lower()
    assert "event: ap_done" in joined
