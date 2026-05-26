"""Tests for ``core.image_gen.cost_estimator.estimate_image_request_cost``
and the route-level budget gate added to
``/api/reasoning-image-gen/generate``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_CHATBOT_DIR = _ROOT / "services" / "chatbot"
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))

from core.image_gen.cost_estimator import estimate_image_request_cost  # noqa: E402

# ── Pure-function tests ─────────────────────────────────────────────────────


class TestEstimator:
    def test_generic_single_image_is_low(self):
        out = estimate_image_request_cost({"prompt": "a quiet forest path"})
        assert out["estimated_cost_level"] == "low"
        assert out["recommended_mode"] == "normal"
        assert out["should_require_confirmation"] is False

    def test_multi_panel_layout_is_high(self):
        out = estimate_image_request_cost({"layout": "grid_2x2"})
        assert out["estimated_cost_level"] == "high"
        assert "multi_panel_layout" in out["reasons"]
        assert out["recommended_mode"] == "ask_confirmation"

    def test_panel_count_above_one_is_high(self):
        out = estimate_image_request_cost({"num_panels": 4})
        assert out["estimated_cost_level"] == "high"
        assert "multi_panel_layout" in out["reasons"]

    def test_unknown_character_exact_request_is_high(self):
        preflight = {
            "risk_level": "high",
            "blocking_reason": "unresolved_unknown_no_traits",
            "character_mode": "unresolved_unknown",
            "signals": {"multiple_characters": False},
        }
        out = estimate_image_request_cost({"prompt": "Iroha"}, preflight)
        assert out["estimated_cost_level"] == "high"
        assert any(r.startswith("character_risk_high") for r in out["reasons"])

    def test_multiple_characters_signal_is_high(self):
        preflight = {
            "risk_level": "high",
            "blocking_reason": "multiple_characters",
            "signals": {"multiple_characters": True},
        }
        out = estimate_image_request_cost({"prompt": "A and B"}, preflight)
        assert out["estimated_cost_level"] == "high"
        assert "multiple_characters" in out["reasons"]

    def test_high_resolution_is_high(self):
        out = estimate_image_request_cost({"width": 2048, "height": 2048})
        assert out["estimated_cost_level"] == "high"
        assert "high_resolution_or_upscale" in out["reasons"]

    def test_upscale_flag_is_high(self):
        out = estimate_image_request_cost({"upscale": True})
        assert out["estimated_cost_level"] == "high"
        assert "high_resolution_or_upscale" in out["reasons"]

    def test_many_attached_references_is_high(self):
        out = estimate_image_request_cost({"attached_images": 4})
        assert out["estimated_cost_level"] == "high"

    def test_correction_loop_is_high(self):
        out = estimate_image_request_cost({"max_correction_passes": 3})
        assert out["estimated_cost_level"] == "high"
        assert "correction_loop" in out["reasons"]

    def test_known_no_lora_is_medium(self):
        preflight = {
            "risk_level": "medium",
            "blocking_reason": "known_no_lora",
            "character_mode": "resolved_known",
            "signals": {"multiple_characters": False},
        }
        out = estimate_image_request_cost({"prompt": "hutao"}, preflight)
        assert out["estimated_cost_level"] == "medium"
        assert any(r.startswith("character_risk_medium") for r in out["reasons"])

    def test_low_data_profile_is_medium(self):
        preflight = {
            "risk_level": "low",
            "blocking_reason": "",
            "character_mode": "low_data_profile",
            "signals": {"multiple_characters": False},
        }
        out = estimate_image_request_cost({}, preflight)
        assert out["estimated_cost_level"] == "medium"
        assert "low_data_profile" in out["reasons"]

    def test_max_cost_medium_blocks_high(self):
        out = estimate_image_request_cost(
            {
                "layout": "grid_2x2",
                "max_cost_level": "medium",
            }
        )
        assert out["estimated_cost_level"] == "high"
        assert out["should_require_confirmation"] is True
        assert out["recommended_mode"] == "ask_confirmation"

    def test_max_cost_high_does_not_block(self):
        out = estimate_image_request_cost(
            {
                "layout": "grid_2x2",
                "max_cost_level": "high",
            }
        )
        assert out["estimated_cost_level"] == "high"
        assert out["should_require_confirmation"] is False

    def test_budget_mode_fast_yields_fast_recommendation(self):
        out = estimate_image_request_cost({"budget_mode": "fast"})
        assert out["recommended_mode"] == "fast"

    def test_old_payload_has_no_budget_keys_still_returns_low(self):
        out = estimate_image_request_cost({"prompt": "cat"})
        assert out["estimated_cost_level"] == "low"
        assert out["should_require_confirmation"] is False
        assert out["recommended_mode"] == "normal"


# ── Route-level integration ─────────────────────────────────────────────────


class _ExplodingComfyClient:
    def submit_workflow(self, workflow, job_id="", pass_name=""):
        raise AssertionError("comfy client must not be called when budget gate fires")


def _make_app():
    from flask import Flask
    from routes.reasoning_image_gen import reasoning_image_gen_bp

    app = Flask(__name__)
    app.register_blueprint(reasoning_image_gen_bp)
    return app


class TestRouteBudgetGate:
    def test_max_cost_medium_blocks_high_cost_request(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod

        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "a quiet forest path",
                "layout": "grid_2x2",
                "max_cost_level": "medium",
            },
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["needs_confirmation"] is True
        assert body["cost"]["estimated_cost_level"] == "high"
        assert "image_b64" not in body

    def test_old_payload_still_generates(self, monkeypatch):
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
                Image.new("RGB", (32, 32), (1, 2, 3)).save(buf, format="PNG")
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
            json={"prompt": "a peaceful mountain lake at sunset"},
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is True
        assert "image_b64" in body
        # Cost metadata is attached for observability.
        assert body["cost"]["estimated_cost_level"] == "low"
        assert stub.calls >= 1

    def test_preflight_only_includes_cost(self, monkeypatch):
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
        assert res.status_code == 200
        body = res.get_json()
        assert body["preflight"] is True
        assert body["cost"]["estimated_cost_level"] in {"low", "medium", "high"}
