"""Tests for ``core.mongo_store`` — the fail-safe MongoDB persistence layer.

Covers:

1. Disabled mode (no env / no client) — all save/update functions no-op.
2. Mocked client — documents are inserted with the expected shape.
3. Identity-safety clamp on ``upsert_character_profile``.
4. Image asset ``base64``/``bytes`` keys are stripped before insert.
5. Route integration — preflight branch saves a job; generation route
   continues even when the Mongo save raises.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_CHATBOT_DIR = _ROOT / "services" / "chatbot"
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


# ── Fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_mongo_store():
    from core import mongo_store

    mongo_store._reset_for_tests()
    yield
    mongo_store._reset_for_tests()


@pytest.fixture
def disabled_mongo(monkeypatch):
    """Force mongo_store to disabled (no env vars)."""
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.delenv("MONGODB_DB_NAME", raising=False)


@pytest.fixture
def fake_db(monkeypatch):
    """Inject a MagicMock DB and mark mongo_store as initialized+enabled."""
    from core import mongo_store

    db = MagicMock(name="fake_db")
    # Each collection is itself a MagicMock with the methods we use.
    monkeypatch.setattr(mongo_store._state, "initialized", True)
    monkeypatch.setattr(mongo_store._state, "db", db)
    monkeypatch.setattr(mongo_store._state, "indexes_ensured", True)  # skip ensure
    return db


# ── 1. Disabled mode ───────────────────────────────────────────────────


class TestDisabled:
    def test_is_mongo_enabled_false_without_env(self, disabled_mongo):
        from core import mongo_store

        assert mongo_store.is_mongo_enabled() is False

    def test_save_generation_job_noop(self, disabled_mongo):
        from core import mongo_store

        out = mongo_store.save_generation_job({"job_id": "j1"})
        assert out["ok"] is False
        assert out["disabled"] is True

    def test_update_generation_job_noop(self, disabled_mongo):
        from core import mongo_store

        out = mongo_store.update_generation_job("j1", {"status": "completed"})
        assert out["ok"] is False
        assert out["disabled"] is True

    def test_save_image_asset_noop(self, disabled_mongo):
        from core import mongo_store

        out = mongo_store.save_image_asset({"image_id": "i1"})
        assert out["ok"] is False
        assert out["disabled"] is True

    def test_upsert_character_profile_noop(self, disabled_mongo):
        from core import mongo_store

        out = mongo_store.upsert_character_profile({"canonical_id": "c1"})
        assert out["ok"] is False
        assert out["disabled"] is True

    def test_get_character_profile_returns_none(self, disabled_mongo):
        from core import mongo_store

        assert mongo_store.get_character_profile("c1") is None


# ── 2. Mocked client ───────────────────────────────────────────────────


class TestMockedClient:
    def test_save_generation_job_inserts_expected_document(self, fake_db):
        from core import mongo_store

        out = mongo_store.save_generation_job(
            {
                "job_id": "j1",
                "raw_prompt": "Furina dancing",
                "character_result": {"canonical_id": "furina@genshin_impact"},
                "preflight": {"risk_level": "low"},
            }
        )
        assert out["ok"] is True
        assert out["job_id"] == "j1"
        # update_one called with upsert=True on generation_jobs
        call = fake_db["generation_jobs"].update_one.call_args
        assert call.kwargs.get("upsert") is True
        filter_arg, update_arg = call.args[0], call.args[1]
        assert filter_arg == {"job_id": "j1"}
        doc = update_arg["$setOnInsert"]
        assert doc["job_id"] == "j1"
        assert doc["raw_prompt"] == "Furina dancing"
        assert doc["status"] == "preflight_only"  # default
        assert doc["provider"] == "reasoning_image_gen"
        assert "created_at" in doc
        assert "updated_at" in doc

    def test_update_generation_job_patches_status(self, fake_db):
        from core import mongo_store

        # Pretend the update matched.
        fake_db["generation_jobs"].update_one.return_value = MagicMock(
            matched_count=1, modified_count=1
        )
        out = mongo_store.update_generation_job("j1", {"status": "completed"})
        assert out["ok"] is True
        call = fake_db["generation_jobs"].update_one.call_args
        assert call.args[0] == {"job_id": "j1"}
        assert call.args[1]["$set"]["status"] == "completed"
        assert "updated_at" in call.args[1]["$set"]

    def test_save_image_asset_strips_binary_keys(self, fake_db):
        from core import mongo_store

        out = mongo_store.save_image_asset(
            {
                "image_id": "img1",
                "job_id": "j1",
                "local_path": "storage/outputs/img1.png",
                "sha256": "abc",
                "image_b64": "AAAA",  # forbidden
                "data": b"\x89PNG",  # forbidden
            }
        )
        assert out["ok"] is True
        call = fake_db["image_assets"].update_one.call_args
        doc = call.args[1]["$setOnInsert"]
        assert doc["local_path"] == "storage/outputs/img1.png"
        assert doc["sha256"] == "abc"
        assert "image_b64" not in doc
        assert "data" not in doc
        assert doc["role"] == "output"
        assert doc["scope"] == "job_output"

    def test_upsert_character_profile_stores_canonical_id(self, fake_db):
        from core import mongo_store

        out = mongo_store.upsert_character_profile(
            {
                "canonical_id": "furina@genshin_impact",
                "display_name": "Furina",
                "series_slug": "genshin_impact",
                "data_status": "known",
                "safe_to_attach_lora": True,
            }
        )
        assert out["ok"] is True
        call = fake_db["character_profiles"].update_one.call_args
        assert call.args[0] == {"canonical_id": "furina@genshin_impact"}
        doc = call.args[1]["$set"]
        assert doc["canonical_id"] == "furina@genshin_impact"
        assert doc["display_name"] == "Furina"
        assert doc["safe_to_attach_lora"] is True

    def test_upsert_character_profile_clamps_unsafe_when_unknown(self, fake_db):
        from core import mongo_store

        out = mongo_store.upsert_character_profile(
            {
                "canonical_id": "unknown:aria@custom",
                "data_status": "unknown",
                "safe_to_attach_lora": True,  # caller asks True — must be clamped
            }
        )
        assert out["ok"] is True
        doc = fake_db["character_profiles"].update_one.call_args.args[1]["$set"]
        assert doc["safe_to_attach_lora"] is False

    def test_save_generation_job_missing_job_id_rejected(self, fake_db):
        from core import mongo_store

        out = mongo_store.save_generation_job({"raw_prompt": "x"})
        assert out["ok"] is False
        assert "job_id" in out["error"]
        fake_db["generation_jobs"].update_one.assert_not_called()


# ── 3. Route / preflight integration ───────────────────────────────────


class _ExplodingComfyClient:
    def submit_workflow(self, workflow, job_id="", pass_name=""):
        raise AssertionError("comfy must not be called when preflight blocks")


def _make_app():
    from flask import Flask
    from routes.reasoning_image_gen import reasoning_image_gen_bp

    app = Flask(__name__)
    app.register_blueprint(reasoning_image_gen_bp)
    return app


class TestRouteIntegration:
    def test_high_risk_preflight_saves_blocked_job(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod

        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        saved: list[dict] = []

        def _fake_save(doc):
            saved.append(dict(doc))
            return {"ok": True, "job_id": doc.get("job_id")}

        monkeypatch.setattr(route_mod.mongo_store, "save_generation_job", _fake_save)
        monkeypatch.setattr(
            route_mod.mongo_store,
            "upsert_character_profile",
            lambda *_a, **_k: {"ok": True},
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
        assert body.get("preflight_blocked") is True
        # Exactly one save — for the blocked job — with status mapped.
        assert len(saved) == 1
        doc = saved[0]
        assert doc["status"] == "blocked_by_preflight"
        assert doc["preflight"]["risk_level"] == "high"
        assert doc["job_id"].startswith("reason-")
        # And the route surfaces the same job_id.
        assert body["job_id"] == doc["job_id"]

    def test_generation_continues_when_mongo_save_raises(self, monkeypatch):
        """If mongo_store.save_generation_job raises, the request must still
        return a normal preflight-only response (fail-safe)."""
        from routes import reasoning_image_gen as route_mod

        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )

        def _boom(_doc):
            raise RuntimeError("simulated mongo outage")

        monkeypatch.setattr(route_mod.mongo_store, "save_generation_job", _boom)

        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "a calm landscape, no characters",
                "preflight_only": True,
            },
        )
        # Route must NOT crash — preflight body still returned.
        assert res.status_code == 200
        body = res.get_json()
        assert body["preflight"] is True
        assert "risk_level" in body
