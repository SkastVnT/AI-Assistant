"""Unit tests for ``core.character_preview.build_preview``.

Pure function — no GPU, no network, no file writes (the module only
*reads* the optional overrides file and the optional cache directory).
"""

from __future__ import annotations

import json

from core import character_preview as cp
from core.character_preview import PLACEHOLDER_URL, build_preview


def test_no_input_returns_400_caller_responsibility():
    # build_preview itself never raises — empty input degrades to placeholder.
    p = build_preview()
    assert p.preview_url == PLACEHOLDER_URL
    assert p.preview_source == "placeholder"
    assert p.needs_review is True


def test_query_only_unknown_uses_placeholder_and_provisional_id():
    p = build_preview(query="Iroha trong Cosmic Princess")
    assert p.preview_url == PLACEHOLDER_URL
    assert p.preview_source == "placeholder"
    assert p.display_name == "Iroha trong Cosmic Princess"
    assert p.provisional_id and p.provisional_id.startswith("unknown:")
    assert p.needs_review is True
    assert any("preview image" in w.lower() for w in p.warnings)


def test_priority_1_selected_character_thumbnail_wins():
    sel = {
        "key": "hu_tao",
        "display_name": "Hu Tao",
        "series": "Genshin Impact",
        "series_key": "genshin_impact",
        "thumbnail": "/api/characters/hu_tao/thumbnail",
    }
    p = build_preview(selected_character=sel)
    assert p.preview_url == "/api/characters/hu_tao/thumbnail"
    assert p.preview_source == "saa_thumbnail"
    # Tooltip contains identity facts.
    assert any("Hu Tao" in line for line in p.tooltip_lines)
    assert any("safe_to_attach_lora" in line for line in p.tooltip_lines)


def test_priority_2_manual_profile_reference_image_wins_over_overrides():
    sel = {"key": "x", "display_name": "X"}
    profile = {
        "reference_images": ["https://example.com/x.png"],
        "needs_review": True,
    }
    p = build_preview(selected_character=sel, manual_profile=profile)
    assert p.preview_url == "https://example.com/x.png"
    assert p.preview_source == "manual_profile"
    assert p.needs_review is True


def test_priority_3_overrides_file_used_when_present(tmp_path, monkeypatch):
    # Point the loader at a temp overrides file.
    fake_path = tmp_path / "character_overrides.json"
    fake_path.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "canonical_id": "iroha@cosmic_princess",
                        "display_name": "Iroha",
                        "series_name": "Cosmic Princess",
                        "series_slug": "cosmic_princess",
                        "aliases": ["iroha"],
                        "reference_images": ["https://example.com/iroha.png"],
                        "needs_review": True,
                        "lora_hint": None,
                        "safe_to_attach_lora": False,
                        "confidence": 0.7,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cp, "_OVERRIDES_PATH", fake_path)
    p = build_preview(query="Iroha")
    assert p.preview_url == "https://example.com/iroha.png"
    assert p.preview_source == "manual_profile"
    assert p.source == "manual_override"
    assert p.canonical_id == "iroha@cosmic_princess"
    assert p.safe_to_attach_lora is False  # opt-in not satisfied
    assert p.needs_review is True


def test_priority_3_overrides_safe_to_attach_lora_requires_both_flags(
    tmp_path, monkeypatch
):
    fake_path = tmp_path / "character_overrides.json"
    fake_path.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "canonical_id": "ok@series",
                        "display_name": "Ok",
                        "series_slug": "series",
                        "aliases": [],
                        "reference_images": [],
                        "lora_hint": "ok_v1.safetensors",
                        "safe_to_attach_lora": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(cp, "_OVERRIDES_PATH", fake_path)
    p = build_preview(query="Ok")
    assert p.safe_to_attach_lora is True
    assert p.source == "manual_override"


def test_overrides_missing_file_is_silent(monkeypatch, tmp_path):
    monkeypatch.setattr(cp, "_OVERRIDES_PATH", tmp_path / "does_not_exist.json")
    p = build_preview(query="Anything")
    assert p.preview_url == PLACEHOLDER_URL
    # No crash, no warnings about overrides specifically.


def test_overrides_invalid_json_is_silent(monkeypatch, tmp_path):
    bad = tmp_path / "character_overrides.json"
    bad.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(cp, "_OVERRIDES_PATH", bad)
    p = build_preview(query="Anything")
    assert p.preview_url == PLACEHOLDER_URL


def test_priority_5_local_cache_returned_when_file_exists(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    (cache_dir / "hu_tao.png").write_bytes(b"\x89PNG fake")
    monkeypatch.setattr(cp, "_LOCAL_CACHE_DIR", cache_dir)
    monkeypatch.setattr(cp, "_OVERRIDES_PATH", tmp_path / "missing.json")
    # Force registry + SAA misses by using a key the registry won't know.
    monkeypatch.setattr(cp, "_saa_thumbnail_url", lambda key: None)
    p = build_preview(key="hu_tao")
    assert p.preview_source == "local_cache"
    assert p.preview_url.endswith("/character_previews/hu_tao.png")


def test_to_dict_contains_documented_fields():
    p = build_preview(query="Test")
    d = p.to_dict()
    for field in (
        "preview_url",
        "preview_source",
        "source_url",
        "display_name",
        "canonical_id",
        "provisional_id",
        "series_name",
        "series_slug",
        "source",
        "safe_to_attach_lora",
        "needs_review",
        "confidence",
        "tooltip_lines",
        "warnings",
    ):
        assert field in d, f"missing field: {field}"


def test_route_preview_endpoint_returns_json(monkeypatch, tmp_path):
    """Smoke-test the /api/characters/preview route via the Flask test client."""
    monkeypatch.setattr(cp, "_OVERRIDES_PATH", tmp_path / "missing.json")

    from flask import Flask
    from routes.characters import characters_bp

    app = Flask(__name__)
    app.register_blueprint(characters_bp)
    client = app.test_client()

    # Missing both key and q → 400.
    r = client.get("/api/characters/preview")
    assert r.status_code == 400

    # With q only → 200 + placeholder JSON.
    r = client.get("/api/characters/preview?q=Iroha")
    assert r.status_code == 200
    data = r.get_json()
    assert data["display_name"] == "Iroha"
    assert data["preview_source"] == "placeholder"
    assert data["needs_review"] is True
    assert isinstance(data["tooltip_lines"], list)
