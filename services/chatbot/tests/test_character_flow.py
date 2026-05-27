"""End-to-end character / profile / preflight / preview flow tests.

Covers the 10 spec items from the curator brief, all without invoking
ComfyUI / GPU / vision / network. A sentinel comfy client raises if any
test path tries to start a real generation. Tests touch only:

* ``POST /api/reasoning-image-gen/generate`` (preflight branch)
* ``core.character_understanding.resolve_character`` (pure)
* ``core.character_preview.build_preview`` (pure)

Each test maps 1:1 to a numbered spec item — see the section comment.
This file intentionally consolidates the matrix so a single ``pytest -v``
invocation reports the full coverage list. Lower-level edge cases live
in their dedicated test modules (``test_character_understanding.py``,
``test_character_preview.py``, ``test_preflight_reasoning_image_gen.py``,
``test_reasoning_payload_shape.py``); this file is the integration
checklist, not a duplicate of those.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_CHATBOT_DIR = _ROOT / "services" / "chatbot"
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


# ── Test scaffolding ────────────────────────────────────────────────────────


class _ExplodingComfyClient:
    """Fails the test if generation is attempted."""

    def submit_workflow(self, workflow, job_id="", pass_name=""):
        raise AssertionError(
            "comfy must NOT be invoked — preflight should short-circuit"
        )


@pytest.fixture
def client(monkeypatch):
    from flask import Flask
    from routes import reasoning_image_gen as route_mod

    monkeypatch.setattr(
        route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
    )
    app = Flask(__name__)
    app.register_blueprint(route_mod.reasoning_image_gen_bp)
    return app.test_client()


def _post(client, payload, expect_status=200):
    res = client.post("/api/reasoning-image-gen/generate", json=payload)
    assert res.status_code == expect_status, res.get_data(as_text=True)
    return res.get_json()


def _empty_registry(monkeypatch):
    stub = MagicMock()
    stub.resolve_query.return_value = None
    stub.detect_collisions.return_value = []
    monkeypatch.setattr("core.character_registry.get_registry", lambda: stub)


def _disable_saa(monkeypatch):
    fake = types.ModuleType("image_pipeline.anime_pipeline.saa_character_db")

    def _boom(*a, **kw):
        raise RuntimeError("SAA disabled in this test")

    fake.lookup_character = _boom  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules,
        "image_pipeline.anime_pipeline.saa_character_db",
        fake,
    )


# ── 1. Old prompt-only payload still accepted ──────────────────────────────


def test_01_prompt_only_payload_still_accepted(client):
    body = _post(
        client, {"prompt": "a quiet mountain lake at sunrise", "preflight_only": True}
    )
    assert body["preflight"] is True
    assert "risk_level" in body
    # Old payloads must not require any new keys.
    assert "image_b64" not in body  # no generation


# ── 2. selected_character accepted ─────────────────────────────────────────


def test_02_selected_character_accepted(client):
    body = _post(
        client,
        {
            "prompt": "Kafka in a coffee shop",
            "preflight_only": True,
            "selected_character": {
                "source": "registry",
                "display_name": "Kafka",
                "canonical_id": "kafka@honkai_star_rail",
                "character_slug": "kafka",
                "series_slug": "honkai_star_rail",
            },
        },
    )
    assert body["preflight"] is True


# ── 3. manual_profile accepted ─────────────────────────────────────────────


def test_03_manual_profile_accepted(client):
    body = _post(
        client,
        {
            "prompt": "Aria casting a starlight spell",
            "preflight_only": True,
            "manual_profile": {
                "display_name": "Original Mage Aria",
                "series_slug": "custom_setting",
                "visual_traits": ["silver hair", "violet eyes"],
                "outfit_traits": ["dark robe"],
            },
        },
    )
    assert body["preflight"] is True


# ── 4. preflight_only does not start generation ────────────────────────────


def test_04_preflight_only_does_not_start_generation(client):
    # The fixture's _ExplodingComfyClient is the actual assertion — if
    # generation runs, submit_workflow raises. We also assert no comic /
    # image_b64 appears in the body.
    body = _post(client, {"prompt": "anything", "preflight_only": True})
    assert "image_b64" not in body
    assert "comic" not in body
    assert body["preflight"] is True


# ── 5. require_preflight_pass + high risk blocks ───────────────────────────


def test_05_require_preflight_pass_high_risk_blocks(client):
    body = _post(
        client,
        {
            "prompt": "Iroha trong Kaguya Cosmic Princess",
            "require_preflight_pass": True,
        },
    )
    assert body["preflight"] is True
    assert body["preflight_blocked"] is True
    assert body["success"] is False
    assert body["risk_level"] == "high"


# ── 6. unknown character returns unknown profile ───────────────────────────


def test_06_unknown_character_returns_unknown_profile(monkeypatch):
    from core import character_understanding as cu

    # Strip live registry / SAA so the test is hermetic.
    _empty_registry(monkeypatch)
    _disable_saa(monkeypatch)

    result = cu.resolve_character("Iroha trong Kaguya Cosmic Princess")
    # Must be one of the explicit non-resolved modes — never a silent
    # substitution from a different franchise.
    assert result.mode in {"unresolved_unknown", "low_data_profile"}
    assert result.safe_to_attach_lora is False
    # Provisional id namespaces unknown characters under "unknown:".
    assert result.unknown_profile is not None
    assert (result.unknown_profile.provisional_id or "").startswith("unknown:")


# ── 7. Style-only prompt does not become a character ───────────────────────


def test_07_style_only_prompt_does_not_become_character(monkeypatch):
    from core import character_understanding as cu

    _empty_registry(monkeypatch)
    _disable_saa(monkeypatch)

    # Generic landscape — no character reference at all.
    result = cu.resolve_character("a quiet mountain lake at sunrise")
    assert result.resolved is False
    assert result.best is None
    # Empty mode == no_character_detected (per CHARACTER_PROFILE_FALLBACK).
    assert result.mode == ""
    assert result.safe_to_attach_lora is False


# ── 8. Preview placeholder works ───────────────────────────────────────────


def test_08_preview_placeholder_works(monkeypatch, tmp_path):
    from core import character_preview as cp

    # Point overrides + cache at empty dirs so every priority misses.
    monkeypatch.setattr(cp, "_OVERRIDES_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(cp, "_LOCAL_CACHE_DIR", tmp_path / "cache")

    preview = cp.build_preview(query="totally_unknown_character_xyz")
    assert preview.preview_url == cp.PLACEHOLDER_URL
    assert preview.preview_source == "placeholder"
    assert (preview.provisional_id or "").startswith("unknown:")
    assert preview.safe_to_attach_lora is False
    assert preview.needs_review is True


# ── 9. Preview metadata does not enable LoRA ───────────────────────────────


def test_09_preview_metadata_alone_does_not_enable_lora(monkeypatch, tmp_path):
    """Manual override text alone must NOT flip ``safe_to_attach_lora``.

    Per IDENTITY_COLLISION_POLICY rule 3: an override needs BOTH
    ``lora_hint`` AND ``safe_to_attach_lora: true`` to opt in. A profile
    with neither stays unsafe even when the preview happily renders.
    """
    from core import character_preview as cp

    overrides_file = tmp_path / "character_overrides.json"
    overrides_file.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "canonical_id": "test_char@test_series",
                        "display_name": "Test Char",
                        "series_slug": "test_series",
                        "visual_traits": ["red hair"],
                        "reference_images": ["https://example.com/a.png"],
                        # NOTE: no lora_hint, no safe_to_attach_lora.
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cp, "_OVERRIDES_PATH", overrides_file)
    monkeypatch.setattr(cp, "_LOCAL_CACHE_DIR", tmp_path / "cache")

    preview = cp.build_preview(query="Test Char")
    # Reference image flows through, but LoRA stays disabled.
    assert preview.preview_url == "https://example.com/a.png"
    assert preview.safe_to_attach_lora is False


# ── 10. Result JSON-serializable ───────────────────────────────────────────


def test_10_result_json_serializable(client, monkeypatch, tmp_path):
    """Every surface a frontend touches must round-trip through json."""
    # 10a. Route response.
    body = _post(client, {"prompt": "Kafka", "preflight_only": True})
    json.dumps(body)  # raises TypeError if anything is non-serializable

    # 10b. CharacterUnderstandingResult.
    from core import character_understanding as cu

    _empty_registry(monkeypatch)
    _disable_saa(monkeypatch)
    result = cu.resolve_character("zzz_unknown")
    if hasattr(result, "to_dict"):
        json.dumps(result.to_dict())
    else:
        json.dumps(
            {
                "resolved": result.resolved,
                "ambiguous": result.ambiguous,
                "mode": result.mode,
                "safe_to_attach_lora": result.safe_to_attach_lora,
                "candidates": (
                    [c.to_dict() for c in result.candidates]
                    if hasattr(result, "candidates")
                    else []
                ),
            }
        )

    # 10c. CharacterPreview.
    from core import character_preview as cp

    monkeypatch.setattr(cp, "_OVERRIDES_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(cp, "_LOCAL_CACHE_DIR", tmp_path / "cache")
    preview = cp.build_preview(query="unknown_xyz")
    json.dumps(preview.to_dict())
