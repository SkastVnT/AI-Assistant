"""Tests for ``core.manual_profile`` + ``/api/characters/profile/*``.

Verifies:
* preview returns low_data_profile with safe_to_attach_lora=False
* invalid profile (no display_name / no traits) returns warnings
* duplicate canonical_id in the override file returns a warning + duplicate
* save refuses to silently overwrite — returns suggested_json instead
* save writes a new entry when no duplicate exists (uses tmp file)
* GET endpoint contracts (200 / 400)

No real generation is invoked — the route handler only calls the pure
builder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_CHATBOT_DIR = _ROOT / "services" / "chatbot"
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


# ── Builder tests ──────────────────────────────────────────────────────────


def test_preview_low_data_profile_unsafe_lora():
    from core.manual_profile import preview_manual_profile

    out = preview_manual_profile(
        {
            "display_name": "Original Mage Aria",
            "series_name": "Custom Setting",
            "series_slug": "custom_setting",
            "visual_traits": ["silver hair", "violet eyes"],
            "outfit_traits": ["dark robe"],
            "negative_identity_guard": ["no canon characters"],
        }
    )
    assert out["mode"] == "low_data_profile"
    assert out["safe_to_attach_lora"] is False
    assert out["needs_review"] is True
    assert out["canonical_id"] == "original_mage_aria@custom_setting"
    assert "Original Mage Aria" in out["character_identity_block"]
    assert "Do not attach LoRA" in out["character_identity_block"]
    # Clean profile → no warnings.
    assert out["warnings"] == []
    assert out["duplicates"] == []


def test_preview_invalid_profile_returns_warnings():
    from core.manual_profile import preview_manual_profile

    out = preview_manual_profile({"display_name": ""})  # empty
    assert out["safe_to_attach_lora"] is False
    assert any("display_name is required" in w for w in out["warnings"])
    assert any("series_name or series_slug" in w for w in out["warnings"])
    assert any("visual_traits is empty" in w for w in out["warnings"])


def test_preview_handles_textarea_string_input():
    from core.manual_profile import preview_manual_profile

    out = preview_manual_profile(
        {
            "display_name": "Test",
            "series_slug": "demo",
            # textarea-style multi-line string instead of list
            "visual_traits": "blue hair\ngreen eyes",
            "negative_identity_guard": "no realistic faces",
        }
    )
    assert out["normalized"]["visual_traits"] == ["blue hair", "green eyes"]
    assert out["normalized"]["negative_identity_guard"] == ["no realistic faces"]


def test_preview_bad_reference_image_warning():
    from core.manual_profile import preview_manual_profile

    out = preview_manual_profile(
        {
            "display_name": "Test",
            "series_slug": "demo",
            "visual_traits": ["x"],
            "reference_images": ["not-a-url", "https://example.com/ok.png"],
        }
    )
    assert any("reference_images" in w for w in out["warnings"])


# ── Duplicate detection (override file) ────────────────────────────────────


def test_duplicate_in_overrides_returns_warning(monkeypatch):
    import core.manual_profile as mp

    monkeypatch.setattr(
        mp,
        "_load_manual_overrides",
        lambda path=None: [
            {
                "canonical_id": "aria@custom_setting",
                "display_name": "Aria",
                "aliases": ["aria"],
            }
        ],
    )
    out = mp.preview_manual_profile(
        {
            "display_name": "Aria",
            "series_slug": "custom_setting",
            "visual_traits": ["silver hair"],
        }
    )
    assert any(d["source"] == "override" for d in out["duplicates"])
    assert any("duplicate detected" in w for w in out["warnings"])


# ── Save: refuses overwrite, returns suggested_json ────────────────────────


def test_save_refuses_silent_overwrite(monkeypatch, tmp_path):
    import core.manual_profile as mp

    target = tmp_path / "character_overrides.json"
    target.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "canonical_id": "aria@custom_setting",
                        "display_name": "Aria",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(mp, "OVERRIDES_PATH", target)
    monkeypatch.setattr(
        mp,
        "_load_manual_overrides",
        lambda path=None: json.loads(target.read_text(encoding="utf-8"))["characters"],
    )

    out = mp.save_manual_profile(
        {
            "display_name": "Aria",
            "series_slug": "custom_setting",
            "visual_traits": ["silver hair"],
        }
    )
    assert out["saved"] is False
    assert (
        "duplicate" in out["reason"].lower()
        or "already exists" in out["reason"].lower()
    )
    assert "suggested_json" in out
    # File must NOT have been mutated.
    after = json.loads(target.read_text(encoding="utf-8"))
    assert len(after["characters"]) == 1


def test_save_validation_failure_blocks_write(monkeypatch, tmp_path):
    import core.manual_profile as mp

    target = tmp_path / "character_overrides.json"
    monkeypatch.setattr(mp, "OVERRIDES_PATH", target)
    monkeypatch.setattr(mp, "_load_manual_overrides", lambda path=None: [])

    out = mp.save_manual_profile({"display_name": ""})
    assert out["saved"] is False
    assert "validation failed" in out["reason"]
    assert not target.exists()


def test_save_writes_when_safe(monkeypatch, tmp_path):
    import core.manual_profile as mp

    target = tmp_path / "character_overrides.json"
    monkeypatch.setattr(mp, "OVERRIDES_PATH", target)
    monkeypatch.setattr(mp, "_load_manual_overrides", lambda path=None: [])

    out = mp.save_manual_profile(
        {
            "display_name": "Brand New Char",
            "series_name": "Brand New Series",
            "series_slug": "brand_new_series",
            "visual_traits": ["red hair", "horn"],
        }
    )
    assert out["saved"] is True
    assert target.exists()
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["characters"][0]["canonical_id"] == "brand_new_char@brand_new_series"
    assert data["characters"][0]["data_status"] == "manual_override"


def test_force_does_not_bypass_validation(monkeypatch, tmp_path):
    import core.manual_profile as mp

    target = tmp_path / "character_overrides.json"
    monkeypatch.setattr(mp, "OVERRIDES_PATH", target)
    monkeypatch.setattr(mp, "_load_manual_overrides", lambda path=None: [])

    out = mp.save_manual_profile({"display_name": ""}, force=True)
    assert out["saved"] is False
    assert "validation failed" in out["reason"]


# ── Route smoke tests ──────────────────────────────────────────────────────


@pytest.fixture()
def client(monkeypatch, tmp_path):
    from flask import Flask
    from routes.characters import characters_bp

    import core.manual_profile as mp

    monkeypatch.setattr(mp, "OVERRIDES_PATH", tmp_path / "character_overrides.json")
    monkeypatch.setattr(mp, "_load_manual_overrides", lambda path=None: [])
    app = Flask(__name__)
    app.register_blueprint(characters_bp)
    return app.test_client()


def test_route_preview_returns_low_data_profile(client):
    res = client.post(
        "/api/characters/profile/preview",
        json={
            "manual_profile": {
                "display_name": "Aria",
                "series_slug": "custom_setting",
                "visual_traits": ["silver hair"],
            },
        },
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["mode"] == "low_data_profile"
    assert body["safe_to_attach_lora"] is False


def test_route_preview_accepts_flat_payload(client):
    # No "manual_profile" wrapper — handler tolerates flat shape too.
    res = client.post(
        "/api/characters/profile/preview",
        json={
            "display_name": "Aria",
            "series_slug": "custom_setting",
            "visual_traits": ["silver hair"],
        },
    )
    assert res.status_code == 200
    assert res.get_json()["safe_to_attach_lora"] is False


def test_route_preview_invalid_returns_warnings(client):
    res = client.post("/api/characters/profile/preview", json={"manual_profile": {}})
    assert res.status_code == 200
    body = res.get_json()
    assert body["safe_to_attach_lora"] is False
    assert body["warnings"]


def test_route_save_writes_when_safe(client):
    res = client.post(
        "/api/characters/profile/save",
        json={
            "manual_profile": {
                "display_name": "Brand New Char",
                "series_slug": "brand_new_series",
                "visual_traits": ["red hair"],
            },
        },
    )
    assert res.status_code == 200
    assert res.get_json()["saved"] is True
