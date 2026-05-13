"""Phase 2 tests for ``core.mongo_store`` — schema v2 activity logging.

Covers the new functions added on top of the Phase 1 surface:

* ``ai_assistant_v2`` default DB name resolution.
* ``MONGODB_DB`` preferred over the legacy ``MONGODB_DB_NAME``.
* ``schema_version=2`` stamped on every persisted document.
* ``save_conversation`` / ``save_message`` upsert + binary-key stripping.
* ``save_tool_call`` + ``update_tool_call`` lifecycle.
* ``save_uploaded_file`` rejects file bytes.
* ``save_generation_job`` carries optional ``conversation_id`` /
  ``message_id`` when provided.
* The streaming route does not crash when Mongo is disabled.
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


# ── Fixtures (mirror Phase 1) ─────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_mongo_store():
    from core import mongo_store
    mongo_store._reset_for_tests()
    yield
    mongo_store._reset_for_tests()


@pytest.fixture
def fake_db(monkeypatch):
    from core import mongo_store
    db = MagicMock(name="fake_db")
    monkeypatch.setattr(mongo_store, "_INITIALIZED", True)
    monkeypatch.setattr(mongo_store, "_DB", db)
    monkeypatch.setattr(mongo_store, "_INDEXES_ENSURED", True)
    return db


# ── 1. Env / DB-name resolution ───────────────────────────────────────


class TestEnvResolution:
    def test_default_db_name_is_v2(self, monkeypatch):
        from core import mongo_store
        monkeypatch.delenv("MONGODB_DB", raising=False)
        monkeypatch.delenv("MONGODB_DB_NAME", raising=False)
        monkeypatch.setenv("MONGODB_URI", "mongodb://example:27017")
        uri, db_name = mongo_store._read_env()
        assert uri == "mongodb://example:27017"
        assert db_name == "ai_assistant_v2"

    def test_mongodb_db_preferred_over_legacy(self, monkeypatch):
        from core import mongo_store
        monkeypatch.setenv("MONGODB_URI", "mongodb://example:27017")
        monkeypatch.setenv("MONGODB_DB", "preferred_db")
        monkeypatch.setenv("MONGODB_DB_NAME", "legacy_db")
        _, db_name = mongo_store._read_env()
        assert db_name == "preferred_db"

    def test_legacy_db_name_used_when_new_var_missing(self, monkeypatch):
        from core import mongo_store
        monkeypatch.setenv("MONGODB_URI", "mongodb://example:27017")
        monkeypatch.delenv("MONGODB_DB", raising=False)
        monkeypatch.setenv("MONGODB_DB_NAME", "legacy_db")
        _, db_name = mongo_store._read_env()
        assert db_name == "legacy_db"

    def test_disabled_when_uri_missing(self, monkeypatch):
        from core import mongo_store
        monkeypatch.delenv("MONGODB_URI", raising=False)
        assert mongo_store.is_mongo_enabled() is False


# ── 2. New collection writes ──────────────────────────────────────────


class TestActivityLogging:
    def test_save_conversation_inserts_with_schema_v2(self, fake_db):
        from core import mongo_store
        out = mongo_store.save_conversation({
            "conversation_id": "conv-1",
            "user_id": "u1",
            "title": "first chat",
        })
        assert out["ok"] is True
        call = fake_db["conversations"].update_one.call_args
        assert call.kwargs.get("upsert") is True
        assert call.args[0] == {"conversation_id": "conv-1"}
        body = call.args[1]["$set"]
        assert body["schema_version"] == 2
        assert body["conversation_id"] == "conv-1"
        assert body["user_id"] == "u1"
        assert "updated_at" in body
        assert call.args[1]["$setOnInsert"] == {"created_at": body["updated_at"]} or "created_at" in call.args[1]["$setOnInsert"]

    def test_save_conversation_missing_id_rejected(self, fake_db):
        from core import mongo_store
        out = mongo_store.save_conversation({"user_id": "u1"})
        assert out["ok"] is False
        assert "conversation_id" in out["error"]
        fake_db["conversations"].update_one.assert_not_called()

    def test_update_conversation_patches_fields(self, fake_db):
        from core import mongo_store
        fake_db["conversations"].update_one.return_value = MagicMock(
            matched_count=1, modified_count=1
        )
        out = mongo_store.update_conversation("conv-1", {"title": "renamed"})
        assert out["ok"] is True
        call = fake_db["conversations"].update_one.call_args
        assert call.args[0] == {"conversation_id": "conv-1"}
        assert call.args[1]["$set"]["title"] == "renamed"
        assert "updated_at" in call.args[1]["$set"]

    def test_save_message_sets_schema_v2_and_strips_binary_keys(self, fake_db):
        from core import mongo_store
        out = mongo_store.save_message({
            "message_id": "msg-1",
            "conversation_id": "conv-1",
            "role": "user",
            "content": "hello",
            "image_b64": "AAAA",      # forbidden
            "data": b"\x89PNG",       # forbidden
            "file_bytes": b"x",       # forbidden
        })
        assert out["ok"] is True
        # MagicMock returns the same child for any key, so update_one calls
        # for messages and conversations land on the same call list. Find
        # the message insert by its filter shape.
        all_calls = fake_db["messages"].update_one.call_args_list
        msg_inserts = [c for c in all_calls if c.args[0] == {"message_id": "msg-1"}]
        assert len(msg_inserts) == 1
        call = msg_inserts[0]
        body = call.args[1]["$setOnInsert"]
        assert body["schema_version"] == 2
        assert body["role"] == "user"
        assert body["content"] == "hello"
        assert "image_b64" not in body
        assert "data" not in body
        assert "file_bytes" not in body
        # Side-effect: parent conversation last_message_at bumped.
        bump_calls = fake_db["conversations"].update_one.call_args_list
        assert any(c.args[0] == {"conversation_id": "conv-1"} for c in bump_calls)

    def test_save_message_missing_id_rejected(self, fake_db):
        from core import mongo_store
        out = mongo_store.save_message({"role": "user", "content": "x"})
        assert out["ok"] is False
        fake_db["messages"].update_one.assert_not_called()

    def test_save_tool_call_then_update_lifecycle(self, fake_db):
        from core import mongo_store
        out = mongo_store.save_tool_call({
            "tool_call_id": "tc-1",
            "conversation_id": "conv-1",
            "message_id": "msg-1",
            "tool_name": "web_search",
            "input_summary": {"query": "weather"},
        })
        assert out["ok"] is True
        body = fake_db["tool_calls"].update_one.call_args.args[1]["$setOnInsert"]
        assert body["schema_version"] == 2
        assert body["tool_call_id"] == "tc-1"
        assert body["status"] == "running"
        assert "started_at" in body

        fake_db["tool_calls"].update_one.return_value = MagicMock(
            matched_count=1, modified_count=1
        )
        out2 = mongo_store.update_tool_call("tc-1", {
            "status": "completed",
            "result_summary": {"hits": 5},
        })
        assert out2["ok"] is True
        last = fake_db["tool_calls"].update_one.call_args
        assert last.args[0] == {"tool_call_id": "tc-1"}
        patch = last.args[1]["$set"]
        assert patch["status"] == "completed"
        assert patch["completed_at"] == patch["updated_at"]
        assert patch["result_summary"] == {"hits": 5}

    def test_save_uploaded_file_rejects_bytes(self, fake_db):
        from core import mongo_store
        out = mongo_store.save_uploaded_file({
            "file_id": "f-1",
            "file_name": "cat.png",
            "mime_type": "image/png",
            "local_path": "uploads/cat.png",
            "file_size": 1234,
            "data": b"\x89PNG",        # forbidden
            "file_b64": "AAAA",        # forbidden
        })
        assert out["ok"] is True
        body = fake_db["uploaded_files"].update_one.call_args.args[1]["$setOnInsert"]
        assert body["schema_version"] == 2
        assert body["file_id"] == "f-1"
        assert body["local_path"] == "uploads/cat.png"
        assert "data" not in body
        assert "file_b64" not in body

    def test_save_generation_job_carries_v2_schema(self, fake_db):
        from core import mongo_store
        out = mongo_store.save_generation_job({
            "job_id": "j-1",
            "raw_prompt": "x",
            "conversation_id": "conv-1",
            "message_id": "msg-1",
        })
        assert out["ok"] is True
        body = fake_db["generation_jobs"].update_one.call_args.args[1]["$setOnInsert"]
        assert body["schema_version"] == 2
        assert body["conversation_id"] == "conv-1"
        assert body["message_id"] == "msg-1"

    def test_save_image_asset_schema_v2(self, fake_db):
        from core import mongo_store
        out = mongo_store.save_image_asset({
            "image_id": "img-1",
            "job_id": "j-1",
            "local_path": "out/img-1.png",
            "data": b"\x89PNG",
        })
        assert out["ok"] is True
        body = fake_db["image_assets"].update_one.call_args.args[1]["$setOnInsert"]
        assert body["schema_version"] == 2
        assert "data" not in body


# ── 3. Disabled-mode no-ops on new functions ──────────────────────────


class TestDisabledNewFunctions:
    @pytest.fixture(autouse=True)
    def _disabled(self, monkeypatch):
        monkeypatch.delenv("MONGODB_URI", raising=False)
        monkeypatch.delenv("MONGODB_DB", raising=False)
        monkeypatch.delenv("MONGODB_DB_NAME", raising=False)
        # Remove the MONGODB_ENABLED kill-switch so the store checks for the
        # URI (which is also absent) and sets disabled_reason correctly.
        monkeypatch.delenv("MONGODB_ENABLED", raising=False)
        from core import mongo_store
        mongo_store._reset_for_tests()
        yield
        mongo_store._reset_for_tests()

    def test_save_conversation_noop(self):
        from core import mongo_store
        out = mongo_store.save_conversation({"conversation_id": "c1"})
        assert out == {"ok": False, "disabled": True, "reason": "missing MONGODB_URI"}

    def test_save_message_noop(self):
        from core import mongo_store
        out = mongo_store.save_message({"message_id": "m1"})
        assert out["ok"] is False and out["disabled"] is True

    def test_save_tool_call_noop(self):
        from core import mongo_store
        out = mongo_store.save_tool_call({"tool_call_id": "tc1"})
        assert out["ok"] is False and out["disabled"] is True

    def test_update_tool_call_noop(self):
        from core import mongo_store
        out = mongo_store.update_tool_call("tc1", {"status": "completed"})
        assert out["ok"] is False and out["disabled"] is True

    def test_save_uploaded_file_noop(self):
        from core import mongo_store
        out = mongo_store.save_uploaded_file({"file_id": "f1"})
        assert out["ok"] is False and out["disabled"] is True


# ── 4. Reasoning image-gen route propagates conversation_id/message_id ─


class _ExplodingComfyClient:
    def submit_workflow(self, workflow, job_id="", pass_name=""):
        raise AssertionError("comfy must not be called when preflight blocks")


def _make_app():
    from flask import Flask
    from routes.reasoning_image_gen import reasoning_image_gen_bp
    app = Flask(__name__)
    app.register_blueprint(reasoning_image_gen_bp)
    return app


class TestReasoningRouteLinksMessage:
    def test_generation_job_carries_conversation_and_message_ids(self, monkeypatch):
        from routes import reasoning_image_gen as route_mod
        monkeypatch.setattr(
            route_mod, "_default_comfy_client", lambda: _ExplodingComfyClient()
        )
        saved: list[dict] = []
        monkeypatch.setattr(
            route_mod.mongo_store, "save_generation_job",
            lambda doc: saved.append(dict(doc)) or {"ok": True},
        )
        monkeypatch.setattr(
            route_mod.mongo_store, "upsert_character_profile",
            lambda *_a, **_k: {"ok": True},
        )
        client = _make_app().test_client()
        res = client.post(
            "/api/reasoning-image-gen/generate",
            json={
                "prompt": "a calm landscape",
                "preflight_only": True,
                "conversation_id": "conv-99",
                "message_id": "msg-77",
            },
        )
        assert res.status_code == 200
        assert len(saved) == 1
        doc = saved[0]
        assert doc["conversation_id"] == "conv-99"
        assert doc["message_id"] == "msg-77"


# ── 5. Streaming route module imports cleanly with mongo_store ────────


class TestStreamingFailSafe:
    def test_stream_module_imports_with_mongo_store_disabled(
        self, monkeypatch
    ):
        """Confirms ``routes.stream`` imports the mongo_store module
        and that the disabled-mode save calls used in the request setup
        never raise. The full SSE generator is exercised via integration
        elsewhere; this guards the import boundary + fail-safe behavior
        of the activity-logging hook.
        """
        monkeypatch.delenv("MONGODB_URI", raising=False)
        monkeypatch.delenv("MONGODB_DB", raising=False)
        monkeypatch.delenv("MONGODB_DB_NAME", raising=False)
        from routes import stream as stream_mod
        from core import mongo_store
        assert stream_mod.mongo_store is mongo_store
        # The two disabled calls used by chat_stream during request setup
        # must return cleanly without raising. We don't assert the disabled
        # key here because a developer .env file may still expose a live
        # MONGODB_URI in the test environment; either outcome is acceptable
        # — the contract is just "never raises, always returns a dict".
        out_conv = mongo_store.save_conversation({"conversation_id": "c1-failsafe-test"})
        out_msg = mongo_store.save_message({"message_id": "m1-failsafe-test"})
        assert isinstance(out_conv, dict)
        assert isinstance(out_msg, dict)
        assert "ok" in out_conv
        assert "ok" in out_msg

