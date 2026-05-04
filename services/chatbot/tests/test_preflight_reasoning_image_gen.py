"""Tests for the preflight risk-assessment branch of
``/api/reasoning-image-gen/generate``.

These tests verify the cheap, GPU-free preflight gate:

* ``preflight_only=true`` returns risk metadata WITHOUT calling
  ``run_pipeline_for_prompt`` / the comfy client.
* ``require_preflight_pass=true`` short-circuits when ``risk_level``
  is ``"high"``.
* Old payloads (no flags) keep current behavior — generation runs.

The real ``image_pipeline.reasoning`` import path is intact; the comfy
client is replaced with a sentinel that fails the test if invoked when
preflight should have blocked.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_CHATBOT_DIR = _ROOT / "services" / "chatbot"
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


# ── Test scaffolding ────────────────────────────────────────────────────────

class _ExplodingComfyClient:
    """Any submit_workflow call fails the test — preflight must NEVER run gen."""

    def submit_workflow(self, workflow, job_id="", pass_name=""):
        raise AssertionError(
            "comfy client must not be called when preflight blocks generation"
        )


def _make_app():
    from flask import Flask
    from routes.reasoning_image_gen import reasoning_image_gen_bp

    app = Flask(__name__)
    app.register_blueprint(reasoning_image_gen_bp)
    return app


# ── preflight_only ──────────────────────────────────────────────────────────


class TestPreflightOnly:
    def test_unknown_iroha_returns_high_risk_and_no_generation(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod
        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "Iroha trong Kaguya Cosmic Princess",
                "preflight_only": True,
            },
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["preflight"] is True
        assert body["would_generate"] is True  # not gated yet
        assert body["risk_level"] == "high"
        assert body["safe_to_attach_lora"] is False
        assert body["needs_review"] is True
        assert body["blocking_reason"] in {
            "unresolved_unknown_no_traits",
            "collision_no_series",
        }
        assert body["suggested_next_action"]
        # Comic / image_b64 must be absent (no generation ran).
        assert "image_b64" not in body
        assert "comic" not in body

    def test_known_character_returns_low_or_medium(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod
        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "hutao đứng trước cổng hư không",
                "preflight_only": True,
            },
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["preflight"] is True
        # hutao resolves via alias table; with no LoRA hint loaded in
        # tests this is "known_no_lora" (medium) rather than "low".
        assert body["risk_level"] in {"low", "medium"}
        assert body["canonical_id"] == "hu_tao@genshin_impact"
        assert body["character_mode"] == "resolved_known"
        assert "image_b64" not in body

    def test_generic_prompt_no_named_character_is_low(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod
        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "a peaceful mountain lake at sunset",
                "preflight_only": True,
            },
        )
        body = res.get_json()
        assert body["preflight"] is True
        assert body["risk_level"] == "low"
        assert body["would_generate"] is True
        assert body["canonical_id"] in (None, "")

    def test_multiple_characters_is_high(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod
        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "Hu Tao và Nahida đứng cạnh nhau",
                "preflight_only": True,
            },
        )
        body = res.get_json()
        assert body["risk_level"] == "high"
        assert body["blocking_reason"] == "multiple_characters"

    def test_explicit_character_hint_pins_low_risk(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod
        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "anything goes here",
                "preflight_only": True,
                "character_hint": {
                    "key": "manual:my_oc@my_world",
                    "display_name": "My OC",
                    "series": "My World",
                },
            },
        )
        body = res.get_json()
        assert body["risk_level"] == "low"
        assert body["safe_to_attach_lora"] is True
        assert body["canonical_id"] == "manual:my_oc@my_world"


# ── require_preflight_pass ──────────────────────────────────────────────────


class TestRequirePreflightPass:
    def test_high_risk_blocks_generation(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod
        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "Iroha trong Kaguya Cosmic Princess",
                "require_preflight_pass": True,
            },
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["preflight"] is True
        assert body["preflight_blocked"] is True
        assert body["success"] is False
        assert body["risk_level"] == "high"
        # Comic / image_b64 must be absent.
        assert "image_b64" not in body

    def test_low_risk_does_not_block(self, monkeypatch):
        # Use a stub comfy client that returns a tiny PNG so generation
        # actually runs to completion when not blocked.
        import base64
        import io
        from PIL import Image

        class _OkResult:
            def __init__(self, b64):
                self.success = True
                self.images_b64 = (b64,)
                self.duration_ms = 1.0
                self.error = ""
                self.cancelled = False

        class _OkClient:
            def __init__(self):
                buf = io.BytesIO()
                Image.new("RGB", (32, 32), (10, 20, 30)).save(buf, format="PNG")
                self._b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                self.calls = 0

            def submit_workflow(self, workflow, job_id="", pass_name=""):
                self.calls += 1
                return _OkResult(self._b64)

        from routes import reasoning_image_gen as route_mod
        stub = _OkClient()
        monkeypatch.setattr(route_mod, "_default_comfy_client", lambda: stub)

        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "a peaceful mountain lake at sunset",
                "require_preflight_pass": True,
            },
        )
        assert res.status_code == 200
        body = res.get_json()
        # Generation ran; preflight passes through as metadata.
        assert body["success"] is True
        assert "image_b64" in body
        assert body["preflight_assessment"]["risk_level"] == "low"
        assert stub.calls >= 1


# ── Backward compatibility ──────────────────────────────────────────────────


class TestBackwardCompatibility:
    def test_old_payload_without_flags_still_generates(self, monkeypatch):
        import base64
        import io
        from PIL import Image

        class _OkResult:
            def __init__(self, b64):
                self.success = True
                self.images_b64 = (b64,)
                self.duration_ms = 1.0
                self.error = ""
                self.cancelled = False

        class _OkClient:
            def __init__(self):
                buf = io.BytesIO()
                Image.new("RGB", (32, 32), (10, 20, 30)).save(buf, format="PNG")
                self._b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                self.calls = 0

            def submit_workflow(self, workflow, job_id="", pass_name=""):
                self.calls += 1
                return _OkResult(self._b64)

        from routes import reasoning_image_gen as route_mod
        stub = _OkClient()
        monkeypatch.setattr(route_mod, "_default_comfy_client", lambda: stub)

        client = _make_app().test_client()
        # Even a HIGH-risk prompt generates when neither flag is set.
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "Iroha trong Kaguya Cosmic Princess",
            },
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True
        assert "image_b64" in body
        # Preflight metadata still surfaced for observability.
        assert "preflight_assessment" in body
        assert body["preflight_assessment"]["risk_level"] == "high"
        assert stub.calls >= 1


# -- provisional_id contract (additive) --------------------------------------


class TestProvisionalId:
    def test_unknown_with_traits_returns_provisional_id(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod
        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        client = _make_app().test_client()
        # The understanding resolver builds an UnknownCharacterProfile
        # for named-but-unresolvable subjects; the preflight payload must
        # surface its ``provisional_id`` even when ``canonical_id`` is null.
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "Iroha trong Kaguya Cosmic Princess",
                "preflight_only": True,
            },
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["canonical_id"] in (None, "")
        assert body["provisional_id"], body
        assert body["provisional_id"].startswith("unknown:")
        assert body["safe_to_attach_lora"] is False
        assert "image_b64" not in body

    def test_low_risk_default_has_no_provisional_id(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod
        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "a peaceful mountain lake at sunset",
                "preflight_only": True,
            },
        )
        body = res.get_json()
        # Field must be present (additive contract) but null for generic prompts.
        assert "provisional_id" in body
        assert body["provisional_id"] in (None, "")
