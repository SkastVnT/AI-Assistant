"""Payload-shape tests for ``/api/reasoning-image-gen/generate``.

Verifies that the route accepts the structured character metadata produced
by `static/js/modules/character-chip.js` without invoking ComfyUI:

* prompt-only payload still works (preflight_only)
* selected_character is accepted
* manual_profile is accepted
* require_preflight_pass + max_cost_level are accepted

All three rich payloads are sent with ``preflight_only=true`` so no real
generation happens. A sentinel comfy client fails the test if any code
path tries to submit a workflow.
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


class _ExplodingComfyClient:
    def submit_workflow(self, workflow, job_id="", pass_name=""):
        raise AssertionError("comfy client must not be called for preflight-only")


def _client(monkeypatch):
    from flask import Flask
    from routes import reasoning_image_gen as route_mod

    monkeypatch.setattr(
        route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
    )
    app = Flask(__name__)
    app.register_blueprint(route_mod.reasoning_image_gen_bp)
    return app.test_client()


def _post(client, payload):
    res = client.post("/api/reasoning-image-gen/generate", json=payload)
    assert res.status_code == 200, res.get_data(as_text=True)
    return res.get_json()


def test_prompt_only_still_works(monkeypatch):
    body = _post(
        _client(monkeypatch),
        {"prompt": "a cat sitting on a fence", "preflight_only": True},
    )
    assert body.get("preflight") is True
    assert "risk_level" in body


def test_selected_character_accepted(monkeypatch):
    selected = {
        "source": "registry",
        "display_name": "Kafka",
        "canonical_id": "kafka@honkai_star_rail",
        "character_slug": "kafka",
        "series_name": "Honkai Star Rail",
        "series_slug": "honkai_star_rail",
        "tag": "kafka",
        "thumbnail": "/api/characters/kafka/thumbnail",
        "preview_url": "/api/characters/kafka/thumbnail",
        "preview_source": "saa_thumbnail",
    }
    body = _post(
        _client(monkeypatch),
        {
            "prompt": "Kafka in a coffee shop",
            "preflight_only": True,
            "selected_character": selected,
        },
    )
    assert body.get("preflight") is True


def test_manual_profile_accepted(monkeypatch):
    manual = {
        "display_name": "Original Mage Aria",
        "series_name": "Custom Setting",
        "series_slug": "custom_setting",
        "visual_traits": ["silver hair", "violet eyes", "small build"],
        "outfit_traits": ["dark robe", "gold trim"],
        "personality_traits": ["calm"],
        "negative_identity_guard": ["no canon characters"],
        "reference_images": ["https://example.com/aria.png"],
    }
    body = _post(
        _client(monkeypatch),
        {
            "prompt": "Aria casting a spell",
            "preflight_only": True,
            "manual_profile": manual,
        },
    )
    assert body.get("preflight") is True


def test_full_payload_with_budget_caps(monkeypatch):
    body = _post(
        _client(monkeypatch),
        {
            "prompt": "Kafka in a coffee shop",
            "preflight_only": True,
            "require_preflight_pass": True,
            "budget_mode": "fast",
            "max_cost_level": "low",
            "selected_character": {
                "source": "registry",
                "display_name": "Kafka",
                "canonical_id": "kafka@honkai_star_rail",
                "character_slug": "kafka",
                "series_slug": "honkai_star_rail",
            },
            "manual_profile": {"display_name": "ignored when selected_character set"},
        },
    )
    assert body.get("preflight") is True
    # cost block is included in preflight responses
    assert "cost" in body
