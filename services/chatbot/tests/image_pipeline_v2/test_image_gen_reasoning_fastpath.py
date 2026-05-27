"""
Tests for the Cycle 7 reasoning fast-path inside ``routes.image_gen``.

When the request payload sets ``use_reasoning_pipeline: true`` AND the
``REASONING_PIPELINE_ENABLED`` config flag is true, ``POST /api/image-gen/
generate`` must short-circuit the regular ``ImageGenerationRouter`` and
delegate to ``routes.reasoning_image_gen.run_pipeline_for_prompt`` instead,
returning the standard image-gen response shape so the existing chat UI
renders it without changes.

Coverage:
* Fast-path NOT taken when toggle is off (flag on).
* Fast-path NOT taken when flag is off (toggle on).
* Fast-path taken when both are true → response uses standard
  ``{success, images:[{url, image_id, local_path}], provider, model, ...}``
  shape with ``provider == "reasoning"``.
* Pipeline failure surfaces as ``200 + success=False``.
* Source hygiene: route module references both
  ``REASONING_PIPELINE_ENABLED`` and ``use_reasoning_pipeline`` and uses
  the lazy import pattern (no top-level reasoning import).
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[4]
_CHATBOT_DIR = _ROOT / "services" / "chatbot"
for p in (_ROOT, _CHATBOT_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from PIL import Image  # noqa: E402

ROUTE_FILE = _CHATBOT_DIR / "routes" / "image_gen.py"


def _png_b64() -> str:
    import base64

    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (10, 200, 50)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _make_app():
    """Build a minimal Flask app that registers only ``image_gen_bp``."""
    from flask import Flask
    from routes.image_gen import image_gen_bp

    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(image_gen_bp)
    return app


def _stub_router_returning_failure():
    """Returns a router whose ``.generate()`` always fails — proves the
    fast-path bypassed it when invoked."""
    router = MagicMock()
    result = MagicMock()
    result.success = False
    result.error = "router-should-not-have-been-called"
    result.prompt_used = ""
    router.generate.return_value = result
    return router


def _stub_storage_capture():
    """Returns a fake storage that records save calls and returns a fake URL."""
    storage = MagicMock()
    storage.save.return_value = {
        "image_id": "abc123",
        "url": "/api/image-gen/images/abc123",
        "local_path": "/tmp/abc123.png",
        "file_size": 999,
    }
    return storage


def _patch_common(
    monkeypatch,
    *,
    flag: bool,
    pipeline_result: dict | None,
    router_should_run: bool = False,
):
    """Patch the route module so tests don't touch real ComfyUI / DB."""
    from routes import image_gen as route_mod

    from core import config as core_cfg

    monkeypatch.setattr(core_cfg, "REASONING_PIPELINE_ENABLED", flag, raising=False)

    # Storage + sessions singletons.
    storage = _stub_storage_capture()
    monkeypatch.setattr(route_mod, "_get_storage", lambda: storage)
    sessions = MagicMock()
    sessions.get_or_create.return_value = MagicMock(
        history=[],
        get_context_for_enhancement=lambda: None,
        add_generation=lambda **kw: None,
        active_style=None,
    )
    monkeypatch.setattr(route_mod, "_get_sessions", lambda: sessions)

    router = _stub_router_returning_failure()
    monkeypatch.setattr(route_mod, "_get_router", lambda: router)

    # Patch the lazy import target. The fast-path imports
    # ``routes.reasoning_image_gen.run_pipeline_for_prompt`` inside the
    # function body, so monkeypatching the attribute on that module works.
    if pipeline_result is not None:
        from routes import reasoning_image_gen as r_mod

        monkeypatch.setattr(
            r_mod,
            "run_pipeline_for_prompt",
            lambda *a, **kw: dict(pipeline_result),
        )

    return {"storage": storage, "router": router}


# ---------------------------------------------------------------------------
# Fast-path NOT taken
# ---------------------------------------------------------------------------


class TestFastpathSkipped:
    def test_toggle_off_runs_normal_router(self, monkeypatch):
        ctx = _patch_common(monkeypatch, flag=True, pipeline_result=None)
        app = _make_app()
        client = app.test_client()
        res = client.post(
            "/api/image-gen/generate",
            json={"prompt": "hello", "use_reasoning_pipeline": False},
        )
        # Router was called → its stubbed failure surfaces as 500.
        assert res.status_code == 500
        ctx["router"].generate.assert_called_once()

    def test_flag_off_runs_normal_router(self, monkeypatch):
        ctx = _patch_common(monkeypatch, flag=False, pipeline_result=None)
        app = _make_app()
        client = app.test_client()
        res = client.post(
            "/api/image-gen/generate",
            json={"prompt": "hello", "use_reasoning_pipeline": True},
        )
        assert res.status_code == 500
        ctx["router"].generate.assert_called_once()


# ---------------------------------------------------------------------------
# Fast-path TAKEN
# ---------------------------------------------------------------------------


class TestFastpathTaken:
    def test_success_returns_standard_image_gen_shape(self, monkeypatch):
        pipeline_ok = {
            "success": True,
            "job_id": "reason-deadbeef",
            "image_b64": _png_b64(),
            "comic": {"layout": "single", "panel_count": 1, "image_bytes_size": 9},
            "panels": [{"panel_id": "p0", "success": True}],
            "parse": {},
        }
        ctx = _patch_common(
            monkeypatch,
            flag=True,
            pipeline_result=pipeline_ok,
        )
        app = _make_app()
        client = app.test_client()
        res = client.post(
            "/api/image-gen/generate",
            json={"prompt": "a knight in a forest", "use_reasoning_pipeline": True},
        )
        assert res.status_code == 200, res.get_data(as_text=True)
        body = res.get_json()
        assert body["success"] is True
        assert body["provider"] == "reasoning"
        assert body["model"] == "comic-pipeline"
        # Standard image-gen-v2 contract: top-level images[] with url + image_id.
        assert isinstance(body["images"], list) and len(body["images"]) == 1
        img = body["images"][0]
        assert img["url"] == "/api/image-gen/images/abc123"
        assert img["image_id"] == "abc123"
        # Reasoning metadata preserved alongside.
        assert body["reasoning"]["job_id"] == "reason-deadbeef"
        # Router NOT invoked.
        ctx["router"].generate.assert_not_called()
        # Storage WAS invoked once with the pipeline's base64.
        assert ctx["storage"].save.call_count == 1
        save_kwargs = ctx["storage"].save.call_args.kwargs
        assert save_kwargs["provider"] == "reasoning"
        assert save_kwargs["model"] == "comic-pipeline"
        assert save_kwargs["image_b64"] == pipeline_ok["image_b64"]

    def test_pipeline_failure_returns_success_false(self, monkeypatch):
        pipeline_fail = {
            "success": False,
            "error": "one or more panels failed to render",
            "panels": [{"panel_id": "p0", "success": False, "error": "boom"}],
        }
        ctx = _patch_common(
            monkeypatch,
            flag=True,
            pipeline_result=pipeline_fail,
        )
        app = _make_app()
        client = app.test_client()
        res = client.post(
            "/api/image-gen/generate",
            json={"prompt": "x", "use_reasoning_pipeline": True},
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is False
        assert "panels failed" in body["error"]
        assert body["provider"] == "reasoning"
        ctx["router"].generate.assert_not_called()
        ctx["storage"].save.assert_not_called()


# ---------------------------------------------------------------------------
# Source-level hygiene
# ---------------------------------------------------------------------------


class TestSourceHygiene:
    """The fast-path must keep its dependency on the reasoning module LAZY
    so the regular code path (and the flag-off case) continues to import
    ``routes.image_gen`` without dragging the reasoning library in."""

    def test_route_references_flag_and_payload_key(self):
        text = ROUTE_FILE.read_text(encoding="utf-8")
        assert "REASONING_PIPELINE_ENABLED" in text
        assert "use_reasoning_pipeline" in text
        assert "_run_reasoning_fastpath" in text

    def test_reasoning_import_is_lazy(self):
        text = ROUTE_FILE.read_text(encoding="utf-8")
        # Top-level imports only — no `from routes.reasoning_image_gen` /
        # `import routes.reasoning_image_gen` at column 0.
        for line in text.splitlines():
            if line.startswith(("import ", "from ")):
                assert (
                    "reasoning_image_gen" not in line
                ), f"reasoning_image_gen import must remain lazy; saw: {line}"
        # But the function body MUST contain the lazy import.
        assert "from routes.reasoning_image_gen import run_pipeline_for_prompt" in text


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
