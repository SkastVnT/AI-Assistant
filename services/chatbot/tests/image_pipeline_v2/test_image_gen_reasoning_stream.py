"""
Tests for the Cycle 7.5 streaming reasoning fast-path inside
``routes.image_gen``'s ``POST /api/image-gen/stream`` SSE endpoint.

The /stream endpoint is the real chat-typed entry point: when the chat UI
detects a draw-prompt and dispatches via ``ImageGenV2.generateFromChatStream``,
the request lands here. Cycle 7 wired the JSON ``/generate`` endpoint;
Cycle 7.5 closes the parity gap by routing the SSE endpoint through the
same gating (payload + env flag).
"""

from __future__ import annotations

import base64
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock

_ROOT = Path(__file__).resolve().parents[4]
_CHATBOT_DIR = _ROOT / "services" / "chatbot"
for p in (_ROOT, _CHATBOT_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from PIL import Image  # noqa: E402

ROUTE_FILE = _CHATBOT_DIR / "routes" / "image_gen.py"


def _png_b64() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (200, 100, 50)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _make_app():
    from flask import Flask
    from routes.image_gen import image_gen_bp

    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(image_gen_bp)
    return app


def _patch(monkeypatch, *, flag: bool, pipeline_result: dict | None):
    from routes import image_gen as route_mod

    from core import config as core_cfg

    monkeypatch.setattr(core_cfg, "REASONING_PIPELINE_ENABLED", flag, raising=False)

    storage = MagicMock()
    storage.save.return_value = {
        "image_id": "stream123",
        "url": "/api/image-gen/images/stream123",
        "local_path": "/tmp/stream123.png",
        "file_size": 1234,
    }
    monkeypatch.setattr(route_mod, "_get_storage", lambda: storage)

    sessions = MagicMock()
    sessions.get_or_create.return_value = MagicMock(
        history=[],
        get_context_for_enhancement=lambda: None,
        add_generation=lambda **kw: None,
        active_style=None,
    )
    monkeypatch.setattr(route_mod, "_get_sessions", lambda: sessions)

    # Router stub: streaming generator that yields a result event so we can
    # detect when the regular path runs (which we DO NOT want for fast-path
    # cases — its presence in the SSE output proves the bypass succeeded
    # OR failed).
    router = MagicMock()

    def _yield_router(*a, **kw):
        yield {
            "event": "result",
            "data": {
                "success": False,
                "error": "router-ran",
                "provider": "router",
                "model": "x",
                "images_b64": [],
                "images_url": [],
                "prompt_used": "",
                "metadata": {},
            },
        }

    router.generate_stream.side_effect = _yield_router
    monkeypatch.setattr(route_mod, "_get_router", lambda: router)

    if pipeline_result is not None:
        from routes import reasoning_image_gen as r_mod

        monkeypatch.setattr(
            r_mod,
            "run_pipeline_for_prompt",
            lambda *a, **kw: dict(pipeline_result),
        )

    return {"storage": storage, "router": router}


def _read_sse_body(resp) -> str:
    return resp.get_data(as_text=True)


# ---------------------------------------------------------------------------
# Fast-path NOT taken — proves chat-typed flow keeps working
# ---------------------------------------------------------------------------


class TestStreamFastpathSkipped:
    def test_toggle_off_runs_router_stream(self, monkeypatch):
        ctx = _patch(monkeypatch, flag=True, pipeline_result=None)
        app = _make_app()
        client = app.test_client()
        resp = client.post(
            "/api/image-gen/stream",
            json={"prompt": "hi", "use_reasoning_pipeline": False},
        )
        assert resp.status_code == 200
        body = _read_sse_body(resp)
        assert '"router-ran"' in body  # Regular router path executed.
        ctx["router"].generate_stream.assert_called_once()

    def test_flag_off_runs_router_stream(self, monkeypatch):
        ctx = _patch(monkeypatch, flag=False, pipeline_result=None)
        app = _make_app()
        client = app.test_client()
        resp = client.post(
            "/api/image-gen/stream",
            json={"prompt": "hi", "use_reasoning_pipeline": True},
        )
        assert resp.status_code == 200
        body = _read_sse_body(resp)
        assert '"router-ran"' in body
        ctx["router"].generate_stream.assert_called_once()


# ---------------------------------------------------------------------------
# Fast-path TAKEN
# ---------------------------------------------------------------------------


class TestStreamFastpathTaken:
    def test_success_emits_required_sse_events(self, monkeypatch):
        pipeline_ok = {
            "success": True,
            "job_id": "reason-stream-1",
            "image_b64": _png_b64(),
            "comic": {"layout": "single", "panel_count": 1, "image_bytes_size": 9},
            "panels": [{"panel_id": "p0", "success": True}],
            "parse": {},
        }
        ctx = _patch(monkeypatch, flag=True, pipeline_result=pipeline_ok)
        app = _make_app()
        client = app.test_client()
        resp = client.post(
            "/api/image-gen/stream",
            json={"prompt": "draw a knight", "use_reasoning_pipeline": True},
        )
        assert resp.status_code == 200
        body = _read_sse_body(resp)
        # SSE event vocabulary the chat UI relies on.
        assert "event: status" in body
        assert "event: provider_try" in body
        assert "event: provider_success" in body
        assert "event: result" in body
        assert "event: saved" in body
        # Reasoning identity survives intact.
        assert '"provider": "reasoning"' in body
        assert '"model": "comic-pipeline"' in body
        assert '"reason-stream-1"' in body
        assert "/api/image-gen/images/stream123" in body
        # Router was bypassed.
        ctx["router"].generate_stream.assert_not_called()
        # Storage was hit with the pipeline base64.
        assert ctx["storage"].save.call_count == 1
        kw = ctx["storage"].save.call_args.kwargs
        assert kw["provider"] == "reasoning"
        assert kw["image_b64"] == pipeline_ok["image_b64"]

    def test_pipeline_failure_emits_sse_error(self, monkeypatch):
        pipeline_fail = {
            "success": False,
            "error": "pipeline blew up",
            "panels": [{"panel_id": "p0", "success": False, "error": "boom"}],
        }
        ctx = _patch(monkeypatch, flag=True, pipeline_result=pipeline_fail)
        app = _make_app()
        client = app.test_client()
        resp = client.post(
            "/api/image-gen/stream",
            json={"prompt": "x", "use_reasoning_pipeline": True},
        )
        assert resp.status_code == 200
        body = _read_sse_body(resp)
        assert "event: error" in body
        assert "pipeline blew up" in body
        ctx["router"].generate_stream.assert_not_called()
        ctx["storage"].save.assert_not_called()


# ---------------------------------------------------------------------------
# Source hygiene
# ---------------------------------------------------------------------------


class TestStreamSourceHygiene:
    def test_route_defines_stream_helper(self):
        text = ROUTE_FILE.read_text(encoding="utf-8")
        assert "_stream_reasoning_fastpath" in text
        # The /stream endpoint must reference the helper AND the flag.
        assert "REASONING_PIPELINE_ENABLED" in text
        # Lazy import is preserved (tested in detail by the JSON fast-path
        # test); just sanity-check the helper lives in the same module.
        assert "def _stream_reasoning_fastpath" in text
