"""Phase 2 — error_class → ap_error recoverable mapping in the service layer.

Verifies that the 3-class error taxonomy threaded from the orchestrator events
(stage_error / pipeline_error with an `error_class`) is mapped onto the SSE
`ap_error` frame's `recoverable` flag as intended, while unclassified frames
keep their legacy per-event default (backward compatible).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.image

_CHATBOT_DIR = Path(__file__).resolve().parents[1]
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


class TestDeriveRecoverable:
    def test_pure_mapping(self):
        from core.anime_pipeline_service import _derive_recoverable

        # Classified errors override the default.
        assert _derive_recoverable("retryable", default=False) is True
        assert _derive_recoverable("resource", default=True) is False
        assert _derive_recoverable("config_or_workflow", default=True) is False
        # Unknown / missing class falls back to the caller's default.
        assert _derive_recoverable(None, default=True) is True
        assert _derive_recoverable(None, default=False) is False
        assert _derive_recoverable("weird", default=True) is True


def _drive_one_event(monkeypatch, event_type: str, data: dict) -> list[str]:
    """Run _run_pipeline_inner against a fake orchestrator that yields exactly
    one event, collecting frames until (and including) the ap_error frame."""
    import core.anime_pipeline_service as svc

    fake_job = SimpleNamespace(job_id="ec-test", to_dict=lambda: {})

    class _FakeOrch:
        def run_stream(self, _job):
            yield {"event": event_type, "data": data}

    frames: list[str] = []
    gen = svc._run_pipeline_inner(_FakeOrch(), fake_job, SimpleNamespace())
    try:
        for frame in gen:
            frames.append(frame)
            if "event: ap_error" in frame:
                break
    finally:
        gen.close()
    return frames


class TestApErrorMapping:
    def test_stage_error_resource_is_terminal(self, monkeypatch):
        frames = _drive_one_event(
            monkeypatch,
            "anime_pipeline_stage_error",
            {"stage": "beauty", "error": "CUDA OOM", "error_class": "resource"},
        )
        body = "".join(frames)
        assert "event: ap_error" in body
        assert '"error_class": "resource"' in body
        assert '"recoverable": false' in body

    def test_stage_error_unclassified_stays_recoverable(self, monkeypatch):
        frames = _drive_one_event(
            monkeypatch,
            "anime_pipeline_stage_error",
            {"stage": "beauty", "error": "transient blip"},
        )
        body = "".join(frames)
        assert "event: ap_error" in body
        assert '"recoverable": true' in body

    def test_stage_error_retryable_is_recoverable(self, monkeypatch):
        frames = _drive_one_event(
            monkeypatch,
            "anime_pipeline_stage_error",
            {"stage": "beauty", "error": "connect fail", "error_class": "retryable"},
        )
        body = "".join(frames)
        assert '"recoverable": true' in body
        assert '"error_class": "retryable"' in body

    def test_pipeline_error_passthrough(self, monkeypatch):
        frames = _drive_one_event(
            monkeypatch,
            "anime_pipeline_pipeline_error",
            {"error": "bad workflow", "error_class": "config_or_workflow"},
        )
        body = "".join(frames)
        assert '"error_class": "config_or_workflow"' in body
        assert '"recoverable": false' in body
