"""
Tests for ``services.chatbot.routes.reasoning_image_gen`` — Cycle 6.

Coverage:
* Flag-off scenario: blueprint is NOT registered when the flag is false
  (verified by emulating the conditional in ``chatbot_main.py``).
* Flag-on scenario: blueprint registers; ``GET /status`` returns 200 with
  ``enabled=True``; ``POST /generate`` returns 200 with a base64 image
  when the comfy client + scorer + inpaint runner are monkeypatched.
* ``POST /generate`` rejects empty prompts with 400.
* Cross-layer hygiene: route module does not call ``load_dotenv`` /
  ``import dotenv`` / ``import services.chatbot`` / ``import core.`` …
  scan limited to lines starting with ``import`` or ``from`` so docstring
  mentions never self-fail the test.
* The route file imports ``core.config`` (the chatbot config namespace)
  but explicitly: ``from core.config import REASONING_PIPELINE_*``. This
  is allowed — only ``import core.X`` / ``from core.X import`` style
  imports of OTHER core modules are forbidden by hygiene scanning.

Run from ``services/chatbot/`` so ``core.*`` and ``routes.*`` are import
roots, e.g.::

    cd services/chatbot
    pytest tests/image_pipeline_v2/test_reasoning_image_gen_route.py -v
"""

from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

import pytest

# Repo root for image_pipeline.* imports (matches sibling test files).
_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# services/chatbot must be on sys.path so ``core.*`` and ``routes.*``
# resolve the same way the live Flask app sees them. When pytest is run
# from services/chatbot the cwd already provides this; the explicit
# insert keeps the test runnable from the repo root too.
_CHATBOT_DIR = _ROOT / "services" / "chatbot"
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))

from PIL import Image  # noqa: E402

ROUTE_FILE = _CHATBOT_DIR / "routes" / "reasoning_image_gen.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _png_bytes(color=(40, 90, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color).save(buf, format="PNG")
    return buf.getvalue()


class _StubComfyResult:
    def __init__(self, b64: str, ok: bool = True, err: str = "") -> None:
        self.success = ok
        self.images_b64 = (b64,) if b64 else ()
        self.duration_ms = 12.5
        self.error = err
        self.cancelled = False


class _StubComfyClient:
    """Records every call so the test can assert one panel == one submit."""

    def __init__(self, image_bytes: bytes) -> None:
        self._b64 = base64.b64encode(image_bytes).decode("ascii")
        self.calls: list[tuple[str, str]] = []

    def submit_workflow(self, workflow, job_id="", pass_name=""):
        self.calls.append((job_id, pass_name))
        return _StubComfyResult(self._b64)


def _make_flask_app(register: bool):
    """Build a fresh Flask app, optionally registering the reasoning bp.

    Mirrors the conditional block in ``chatbot_main.py`` so the test
    doubles as a contract check on the registration pattern.
    """
    from flask import Flask

    app = Flask(__name__)
    if register:
        from routes.reasoning_image_gen import reasoning_image_gen_bp
        app.register_blueprint(reasoning_image_gen_bp)
    return app


# ---------------------------------------------------------------------------
# Flag-off contract
# ---------------------------------------------------------------------------


class TestFlagOff:
    def test_blueprint_not_registered_when_flag_off(self):
        app = _make_flask_app(register=False)
        rules = {r.rule for r in app.url_map.iter_rules()}
        assert not any("reasoning-image-gen" in rule for rule in rules)

    def test_status_returns_404_when_flag_off(self):
        app = _make_flask_app(register=False)
        client = app.test_client()
        res = client.get("/api/reasoning-image-gen/status")
        assert res.status_code == 404


# ---------------------------------------------------------------------------
# Flag-on behavior
# ---------------------------------------------------------------------------


class TestFlagOn:
    def test_status_returns_enabled_payload(self):
        app = _make_flask_app(register=True)
        client = app.test_client()
        res = client.get("/api/reasoning-image-gen/status")
        assert res.status_code == 200
        body = res.get_json()
        assert body["enabled"] is True
        assert "comfy_url" in body
        assert isinstance(body["max_panels"], int)

    def test_generate_rejects_empty_prompt(self):
        app = _make_flask_app(register=True)
        client = app.test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={"prompt": "   "},
        )
        assert res.status_code == 400
        body = res.get_json()
        assert body["success"] is False

    def test_generate_returns_assembled_image(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod

        stub = _StubComfyClient(_png_bytes())
        monkeypatch.setattr(route_mod, "_default_comfy_client", lambda: stub)

        app = _make_flask_app(register=True)
        client = app.test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={"prompt": "a cat sitting in a sunny window"},
        )
        assert res.status_code == 200, res.get_data(as_text=True)
        body = res.get_json()
        assert body["success"] is True
        assert body["job_id"].startswith("reason-")
        assert body["image_b64"]
        assert body["comic"]["panel_count"] >= 1
        assert body["comic"]["image_bytes_size"] > 0
        # At least one panel was rendered.
        assert len(body["panels"]) == body["comic"]["panel_count"]
        # Image bytes round-trip through Pillow.
        decoded = Image.open(io.BytesIO(base64.b64decode(body["image_b64"])))
        decoded.load()
        assert decoded.size[0] > 0 and decoded.size[1] > 0
        # Comfy stub was invoked exactly once per panel.
        assert len(stub.calls) == body["comic"]["panel_count"]

    def test_generate_surfaces_render_failure(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod

        class _FailingClient:
            def submit_workflow(self, workflow, job_id="", pass_name=""):
                return _StubComfyResult("", ok=False, err="boom")

        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _FailingClient()
        )
        app = _make_flask_app(register=True)
        client = app.test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={"prompt": "a portrait of a knight"},
        )
        # Render failures surface as 200 + success=False per the contract.
        assert res.status_code == 200
        body = res.get_json()
        assert body["success"] is False
        assert "panels" in body
        assert any(p["success"] is False for p in body["panels"])


# ---------------------------------------------------------------------------
# Cross-layer hygiene — same convention as Cycle 4/5 tests
# ---------------------------------------------------------------------------


class TestRouteHygiene:
    """The route file is the integration boundary. It MAY import from
    ``core.config``, ``image_pipeline.reasoning.*``, ``flask``, and the
    in-tree ``src.utils.comfyui_client`` (lazy). It must NOT call
    ``load_dotenv`` or pull in ``services.chatbot.*`` / ``dotenv`` /
    ``image_pipeline.evaluator`` — the env loading contract owns that.
    """

    FORBIDDEN = (
        "load_dotenv",
        "from dotenv",
        "import dotenv",
        "services.chatbot",
        "image_pipeline.evaluator",
    )

    def _import_lines(self) -> list[str]:
        text = ROUTE_FILE.read_text(encoding="utf-8")
        out: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                out.append(stripped)
        return out

    def test_route_module_avoids_forbidden_imports(self):
        lines = self._import_lines()
        joined = "\n".join(lines)
        for needle in self.FORBIDDEN:
            assert needle not in joined, (
                f"reasoning_image_gen.py must not contain {needle!r} in imports; "
                f"saw line(s) referencing it."
            )

    def test_route_module_imports_config_flag(self):
        # Positive presence checks scan the entire module text — the multi-line
        # ``from core.config import (...)`` style splits each symbol onto its
        # own line which the import-line filter would drop.
        text = ROUTE_FILE.read_text(encoding="utf-8")
        assert "REASONING_PIPELINE_COMFY_URL" in text
        assert "REASONING_PIPELINE_MAX_PANELS" in text
        assert "from core.config import" in text

    def test_chatbot_main_registers_only_under_flag(self):
        main_text = (_CHATBOT_DIR / "chatbot_main.py").read_text(encoding="utf-8")
        # The conditional registration block must exist and key off the flag.
        assert "REASONING_PIPELINE_ENABLED" in main_text
        assert "from routes.reasoning_image_gen import reasoning_image_gen_bp" in main_text
        # And the import must sit INSIDE an `if REASONING_PIPELINE_ENABLED:` block.
        idx_flag = main_text.find("if REASONING_PIPELINE_ENABLED:")
        idx_import = main_text.find(
            "from routes.reasoning_image_gen import reasoning_image_gen_bp"
        )
        assert idx_flag != -1 and idx_import != -1
        assert idx_flag < idx_import, (
            "reasoning_image_gen import must appear AFTER the if-flag guard "
            "so flag-off runtime is byte-identical."
        )


# ---------------------------------------------------------------------------
# Character-understanding wiring (Phase 2)
# ---------------------------------------------------------------------------


class TestCharacterUnderstandingWiring:
    """Verify the understanding layer is called and its result is reflected
    in metadata WITHOUT changing the existing pipeline contract.

    The pipeline call itself is short-circuited — we monkeypatch
    ``run_pipeline_for_prompt`` to capture the ``character_hint`` that the
    route would have passed in. This keeps the test fast and free of
    ComfyUI dependencies.
    """

    def _patch_pipeline(self, monkeypatch):
        """Replace the pipeline function with a capture stub."""
        captured: dict = {}

        def fake_run(prompt_text, *, layout=None, attached_images=0, character_hint=None):
            captured["prompt"] = prompt_text
            captured["character_hint"] = character_hint
            return {
                "success": True,
                "job_id": "reason-test",
                "parse": {},
                "panels": [],
                "comic": {},
                "image_b64": "",
                "status_code": 200,
            }

        from routes import reasoning_image_gen as route_mod
        monkeypatch.setattr(route_mod, "run_pipeline_for_prompt", fake_run)
        return captured

    def test_unambiguous_alias_auto_fills_hint(self, monkeypatch):
        captured = self._patch_pipeline(monkeypatch)
        app = _make_flask_app(register=True)
        res = app.test_client().post(
            "/api/reasoning-image-gen/generate",
            json={"prompt": "tạo ảnh Hutao mặc áo dài"},
        )
        assert res.status_code == 200
        body = res.get_json()
        # understanding block is always echoed.
        assert "understanding" in body
        assert body["understanding"]["resolved"] is True
        assert body["understanding"]["ambiguous"] is False
        ids = {c["canonical_id"] for c in body["understanding"]["candidates"]}
        assert "hu_tao@genshin_impact" in ids
        # And character_hint reaches the pipeline auto-filled.
        assert captured["character_hint"] is not None
        assert captured["character_hint"]["key"] == "hu_tao@genshin_impact"
        assert captured["character_hint"]["source"].startswith("understanding:")

    def test_ambiguous_name_does_not_auto_fill(self, monkeypatch):
        captured = self._patch_pipeline(monkeypatch)
        app = _make_flask_app(register=True)
        res = app.test_client().post(
            "/api/reasoning-image-gen/generate",
            json={"prompt": "tạo ảnh Miko trong vườn hoa"},
        )
        assert res.status_code == 200
        body = res.get_json()
        # Ambiguous → flagged in metadata, multiple candidates returned.
        assert body["understanding"]["ambiguous"] is True
        assert len(body["understanding"]["candidates"]) >= 2
        # Pipeline gets NO character_hint — caller must ask the user.
        assert captured["character_hint"] is None

    def test_explicit_character_key_wins_over_understanding(self, monkeypatch):
        """A picker-supplied character_key must NOT be overwritten by the
        understanding result, even when both would resolve."""
        captured = self._patch_pipeline(monkeypatch)
        # Force the registry to find the picker key.
        from unittest.mock import MagicMock
        rec = MagicMock()
        rec.key = "raiden_shogun_genshin_impact"
        rec.display_name = "Raiden Shogun"
        rec.series = "Genshin Impact"
        rec.series_key = "genshin_impact"
        rec.character_tag = "raiden_shogun"
        stub = MagicMock()
        stub.get.return_value = rec
        monkeypatch.setattr("core.character_registry.get_registry", lambda: stub)

        app = _make_flask_app(register=True)
        res = app.test_client().post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "vẽ Hutao",
                "character_key": "raiden_shogun_genshin_impact",
            },
        )
        assert res.status_code == 200
        # Hint comes from the picker (registry source), not understanding.
        assert captured["character_hint"]["key"] == "raiden_shogun_genshin_impact"

    def test_selected_character_payload_wins(self, monkeypatch):
        captured = self._patch_pipeline(monkeypatch)
        app = _make_flask_app(register=True)
        res = app.test_client().post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "draw Rem in the garden",  # ambiguous on its own
                "selected_character": {
                    "character_slug": "rem",
                    "series_slug": "rezero",
                    "display_name": "Rem",
                    "series_name": "Re:Zero",
                },
            },
        )
        assert res.status_code == 200
        body = res.get_json()
        assert body["understanding"]["resolved"] is True
        assert body["understanding"]["ambiguous"] is False
        assert body["understanding"]["candidates"][0]["canonical_id"] == "rem@rezero"
        # And the pipeline receives the auto-filled hint.
        assert captured["character_hint"]["key"] == "rem@rezero"

    def test_understanding_failure_does_not_break_route(self, monkeypatch):
        captured = self._patch_pipeline(monkeypatch)

        def boom(*a, **kw):
            raise RuntimeError("understanding crashed")

        monkeypatch.setattr(
            "core.character_understanding.resolve_character_intent", boom
        )
        app = _make_flask_app(register=True)
        res = app.test_client().post(
            "/api/reasoning-image-gen/generate",
            json={"prompt": "a quiet forest at dusk"},
        )
        assert res.status_code == 200
        body = res.get_json()
        # Route still succeeds; understanding block is omitted.
        assert body["success"] is True
        assert "understanding" not in body
        assert captured["character_hint"] is None


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
