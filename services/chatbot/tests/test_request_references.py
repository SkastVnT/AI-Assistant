"""Tests for request-only reference image metadata.

Covers:
* manual_profile.reference_images serializes through the preflight
  payload with reference_scope="request_only" and needs_review=True.
* selected_character.reference_images is picked up when manual_profile
  has none.
* unknown character + provided refs returns provisional_id alongside
  reference metadata.
* Old payloads (no reference_images anywhere) keep working — the
  ``references`` key is OMITTED, not null.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest  # noqa: F401

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_CHATBOT_DIR = _ROOT / "services" / "chatbot"
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


class _ExplodingComfyClient:
    def submit_workflow(self, workflow, job_id="", pass_name=""):
        raise AssertionError("comfy must not run during preflight_only tests")


def _make_app():
    from flask import Flask
    from routes.reasoning_image_gen import reasoning_image_gen_bp

    app = Flask(__name__)
    app.register_blueprint(reasoning_image_gen_bp)
    return app


# ── Helper unit tests (no Flask) ────────────────────────────────────────────


class TestNormalizeReferenceList:
    def test_string_becomes_single_item(self):
        from routes.reasoning_image_gen import _normalize_reference_list

        assert _normalize_reference_list("https://x/y.png") == ["https://x/y.png"]

    def test_list_trims_and_drops_empties(self):
        from routes.reasoning_image_gen import _normalize_reference_list

        out = _normalize_reference_list(["  a ", "", "b", None, 3])
        assert out == ["a", "b"]

    def test_caps_at_max(self):
        from routes.reasoning_image_gen import (
            _MAX_REQUEST_REFERENCES,
            _normalize_reference_list,
        )

        many = [f"u{i}" for i in range(_MAX_REQUEST_REFERENCES + 5)]
        assert len(_normalize_reference_list(many)) == _MAX_REQUEST_REFERENCES

    def test_garbage_returns_empty(self):
        from routes.reasoning_image_gen import _normalize_reference_list

        assert _normalize_reference_list(None) == []
        assert _normalize_reference_list(42) == []
        assert _normalize_reference_list({"k": "v"}) == []


class TestCollectRequestReferences:
    def test_manual_profile_takes_priority(self):
        from routes.reasoning_image_gen import _collect_request_references

        meta = _collect_request_references(
            {
                "manual_profile": {"reference_images": ["a.png"]},
                "selected_character": {"reference_images": ["b.png"]},
                "reference_images": ["c.png"],
            },
            preflight={"canonical_id": None, "provisional_id": "unknown:x@y"},
        )
        assert meta["source"] == "manual_profile"
        assert meta["items"] == ["a.png"]
        assert meta["count"] == 1
        assert meta["reference_scope"] == "request_only"
        assert meta["needs_review"] is True
        assert meta["provisional_id"] == "unknown:x@y"
        assert meta["canonical_id"] is None
        assert meta["supported_by_pipeline"] is False

    def test_falls_back_to_selected_character(self):
        from routes.reasoning_image_gen import _collect_request_references

        meta = _collect_request_references(
            {"selected_character": {"reference_images": ["b.png"]}},
            preflight={"canonical_id": "hu_tao@genshin_impact"},
        )
        assert meta["source"] == "selected_character"
        assert meta["items"] == ["b.png"]
        assert meta["canonical_id"] == "hu_tao@genshin_impact"

    def test_returns_none_when_empty(self):
        from routes.reasoning_image_gen import _collect_request_references

        assert _collect_request_references({}, preflight={}) is None
        assert (
            _collect_request_references(
                {"manual_profile": {"reference_images": []}}, preflight={}
            )
            is None
        )


# ── Route integration ──────────────────────────────────────────────────────


class TestRoutePassthrough:
    def test_manual_profile_refs_serialize_into_preflight(self, monkeypatch):
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
                "manual_profile": {
                    "reference_images": [
                        "https://example.com/a.png",
                        "https://example.com/b.png",
                    ],
                },
            },
        )
        assert res.status_code == 200
        body = res.get_json()
        assert "references" in body
        refs = body["references"]
        assert refs["reference_scope"] == "request_only"
        assert refs["needs_review"] is True
        assert refs["count"] == 2
        assert refs["source"] == "manual_profile"
        assert refs["supported_by_pipeline"] is False
        # Identity correlation: provisional_id is set for unknown chars.
        assert refs["provisional_id"], body
        assert refs["provisional_id"].startswith("unknown:")
        assert "image_b64" not in body  # preflight only

    def test_old_payload_omits_references_key(self, monkeypatch):
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
        assert "references" not in body  # additive contract

    def test_selected_character_refs_when_manual_empty(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod

        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "anything",
                "preflight_only": True,
                "selected_character": {
                    "key": "hu_tao@genshin_impact",
                    "display_name": "Hu Tao",
                    "reference_images": ["ref://hu_tao/1.png"],
                },
            },
        )
        body = res.get_json()
        assert body["references"]["source"] == "selected_character"
        assert body["references"]["items"] == ["ref://hu_tao/1.png"]
        assert body["references"]["reference_scope"] == "request_only"
