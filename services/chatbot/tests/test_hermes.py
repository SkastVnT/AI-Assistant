"""
Tests for Hermes Agent integration — adapter + Flask route.

All tests use mocks. No real HTTP calls to Hermes sidecar.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

# Ensure chatbot root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def _enable_hermes(monkeypatch):
    """Enable Hermes feature flag."""
    monkeypatch.setattr("core.hermes_adapter.HERMES_ENABLED", True)
    monkeypatch.setattr("core.hermes_adapter.HERMES_API_URL", "http://fake-hermes:8080")
    monkeypatch.setattr("core.hermes_adapter.HERMES_API_KEY", "test-key")
    monkeypatch.setattr("core.hermes_adapter.HERMES_TIMEOUT", 30)


@pytest.fixture
def mock_hermes_success(monkeypatch):
    """Mock requests.post to return a successful Hermes response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": "Hermes says hello!"}
    mock_resp.text = '{"response": "Hermes says hello!"}'
    monkeypatch.setattr("core.hermes_adapter.requests.post", lambda *a, **kw: mock_resp)
    return mock_resp


# ---------------------------------------------------------------------------
# Adapter tests
# ---------------------------------------------------------------------------

class TestHermesChat:
    """Tests for core.hermes_adapter.hermes_chat."""

    def test_disabled_returns_error(self, monkeypatch):
        monkeypatch.setattr("core.hermes_adapter.HERMES_ENABLED", False)
        from core.hermes_adapter import hermes_chat
        result = hermes_chat("hello")
        assert result["success"] is False
        assert "HERMES_ENABLED" in result["error"]

    def test_empty_message_returns_error(self, _enable_hermes):
        from core.hermes_adapter import hermes_chat
        result = hermes_chat("")
        assert result["success"] is False
        assert "message" in result["error"].lower()

    def test_message_too_long(self, _enable_hermes):
        from core.hermes_adapter import hermes_chat
        result = hermes_chat("x" * 11_000)
        assert result["success"] is False
        assert "dài" in result["error"]

    def test_successful_chat(self, _enable_hermes, mock_hermes_success):
        from core.hermes_adapter import hermes_chat
        result = hermes_chat("hello world")
        assert result["success"] is True
        assert "Hermes says hello" in result["result"]
        assert result["elapsed_s"] >= 0

    def test_connection_error(self, _enable_hermes, monkeypatch):
        def raise_conn(*a, **kw):
            raise requests.ConnectionError("refused")
        monkeypatch.setattr("core.hermes_adapter.requests.post", raise_conn)
        from core.hermes_adapter import hermes_chat
        result = hermes_chat("hello")
        assert result["success"] is False
        assert "kết nối" in result["error"]

    def test_timeout_error(self, _enable_hermes, monkeypatch):
        def raise_timeout(*a, **kw):
            raise requests.Timeout("timed out")
        monkeypatch.setattr("core.hermes_adapter.requests.post", raise_timeout)
        from core.hermes_adapter import hermes_chat
        result = hermes_chat("hello")
        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    def test_non_200_response(self, _enable_hermes, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        monkeypatch.setattr("core.hermes_adapter.requests.post", lambda *a, **kw: mock_resp)
        from core.hermes_adapter import hermes_chat
        result = hermes_chat("hello")
        assert result["success"] is False
        # Adapter returns a generic message; status code appears in the log not the error field
        assert "unavailable" in result["error"].lower()

    def test_non_json_response(self, _enable_hermes, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("not json")
        mock_resp.text = "plain text response"
        monkeypatch.setattr("core.hermes_adapter.requests.post", lambda *a, **kw: mock_resp)
        from core.hermes_adapter import hermes_chat
        result = hermes_chat("hello")
        assert result["success"] is True
        assert "plain text response" in result["result"]

    def test_auth_header_sent(self, _enable_hermes, monkeypatch):
        """Verify Authorization header is included when API key is set."""
        captured = {}
        def capture_post(url, json=None, headers=None, timeout=None):
            captured['headers'] = headers
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"response": "ok"}
            return mock_resp
        monkeypatch.setattr("core.hermes_adapter.requests.post", capture_post)
        from core.hermes_adapter import hermes_chat
        hermes_chat("test")
        assert "Authorization" in captured["headers"]
        assert "Bearer test-key" == captured["headers"]["Authorization"]

    def test_conversation_history_forwarded(self, _enable_hermes, monkeypatch):
        captured = {}
        def capture_post(url, json=None, headers=None, timeout=None):
            captured['payload'] = json
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"response": "ok"}
            return mock_resp
        monkeypatch.setattr("core.hermes_adapter.requests.post", capture_post)
        from core.hermes_adapter import hermes_chat
        history = [{"role": "user", "content": "hi"}]
        hermes_chat("follow up", conversation_history=history)
        assert captured['payload']['conversation_history'] == history


# ---------------------------------------------------------------------------
# Flask route tests
# ---------------------------------------------------------------------------

class TestHermesRoute:
    """Tests for routes/hermes.py Flask blueprint."""

    @pytest.fixture
    def client(self):
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        from routes.hermes import hermes_bp
        app.register_blueprint(hermes_bp)
        return app.test_client()

    def test_missing_message_returns_400(self, client):
        resp = client.post(
            '/api/hermes/chat',
            json={},
            content_type='application/json',
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_successful_request(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.hermes_adapter.hermes_chat",
            lambda msg, **kw: {"success": True, "result": "answer", "error": None, "elapsed_s": 1.0},
        )
        resp = client.post(
            '/api/hermes/chat',
            json={'message': 'hello'},
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['result'] == 'answer'

    def test_adapter_error_returns_422(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.hermes_adapter.hermes_chat",
            lambda msg, **kw: {
                "success": False, "result": "", "error": "sidecar down", "elapsed_s": 0,
            },
        )
        resp = client.post(
            '/api/hermes/chat',
            json={'message': 'test'},
            content_type='application/json',
        )
        assert resp.status_code == 422

    def test_internal_exception_returns_500(self, client, monkeypatch):
        def boom(*a, **kw):
            raise RuntimeError("unexpected")
        monkeypatch.setattr("core.hermes_adapter.hermes_chat", boom)
        resp = client.post(
            '/api/hermes/chat',
            json={'message': 'test'},
            content_type='application/json',
        )
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Bridge tests — keyword guard + reasoning-pipeline redirect
# ---------------------------------------------------------------------------

class TestHermesReasoningBridge:
    """Tests for the Hermes → reasoning-pipeline bridge in routes/hermes.py."""

    @pytest.fixture
    def client(self):
        from flask import Flask
        app = Flask(__name__)
        app.config['TESTING'] = True
        from routes.hermes import hermes_bp
        app.register_blueprint(hermes_bp)
        return app.test_client()

    @pytest.fixture
    def hermes_called(self, monkeypatch):
        """Spy: records calls to hermes_chat and returns a stock success."""
        calls = {"count": 0, "last_msg": None}

        def fake_hermes(msg, **kw):
            calls["count"] += 1
            calls["last_msg"] = msg
            return {"success": True, "result": "hermes-answer", "error": None, "elapsed_s": 0.1}

        monkeypatch.setattr("core.hermes_adapter.hermes_chat", fake_hermes)
        return calls

    def test_keyword_helper_rejects_normal_chat(self):
        from routes.hermes import _has_image_keyword
        assert not _has_image_keyword("giải thích đoạn mã này giúp tôi")
        assert not _has_image_keyword("summarize the README")
        assert not _has_image_keyword("ảnh hưởng của thuế quan là gì")  # 'ảnh' as substring
        assert not _has_image_keyword("show me the logs")

    def test_keyword_helper_accepts_image_requests(self):
        from routes.hermes import _has_image_keyword
        assert _has_image_keyword("vẽ một con mèo dễ thương")
        assert _has_image_keyword("tạo ảnh phong cảnh núi rừng")
        assert _has_image_keyword("generate an image of a sunset")
        assert _has_image_keyword("draw a 4-panel comic")
        assert _has_image_keyword("create a manga page about samurai")

    def test_normal_chat_does_not_redirect(self, client, hermes_called, monkeypatch):
        """Even with REASONING_PIPELINE on, plain chat must hit Hermes."""
        monkeypatch.setattr("core.image_intent.is_reasoning_pipeline_enabled", lambda: True)
        # Classifier should never even be called; if it is, return None.
        monkeypatch.setattr("core.image_intent.detect_image_intent", lambda *a, **kw: None)

        resp = client.post(
            '/api/hermes/chat',
            json={'message': 'giải thích file này giúp tôi'},
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert hermes_called["count"] == 1
        assert resp.get_json()["result"] == "hermes-answer"

    def test_image_request_redirects_to_pipeline(self, client, hermes_called, monkeypatch):
        """Explicit image keyword + high-confidence classifier → pipeline."""
        from image_pipeline.reasoning.capability_router import (
            CapabilityDecision, RequestKind,
        )

        monkeypatch.setattr("core.image_intent.is_reasoning_pipeline_enabled", lambda: True)
        monkeypatch.setattr(
            "core.image_intent.detect_image_intent",
            lambda *a, **kw: CapabilityDecision(
                kind=RequestKind.TEXT_TO_IMAGE,
                confidence=0.9,
                reasons=("test",),
            ),
        )

        # Stub the pipeline so we don't run ComfyUI.
        def fake_pipeline(prompt_text, **kw):
            return {
                "success": True,
                "job_id": "job-123",
                "image_b64": "AAAA",
                "comic": None,
                "parse": {},
                "panels": [],
                "status_code": 200,
            }
        import sys, types
        fake_mod = types.ModuleType("routes.reasoning_image_gen")
        fake_mod.run_pipeline_for_prompt = fake_pipeline
        monkeypatch.setitem(sys.modules, "routes.reasoning_image_gen", fake_mod)

        resp = client.post(
            '/api/hermes/chat',
            json={'message': 'vẽ một con mèo'},
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["source"] == "reasoning_pipeline"
        assert data["image_b64"] == "AAAA"
        assert data["job_id"] == "job-123"
        assert "data:image/png;base64,AAAA" in data["result"]
        assert hermes_called["count"] == 0  # Hermes was NOT called

    def test_low_confidence_falls_through(self, client, hermes_called, monkeypatch):
        """Image keyword present but classifier < 0.75 → Hermes, not pipeline."""
        from image_pipeline.reasoning.capability_router import (
            CapabilityDecision, RequestKind,
        )
        monkeypatch.setattr("core.image_intent.is_reasoning_pipeline_enabled", lambda: True)
        monkeypatch.setattr(
            "core.image_intent.detect_image_intent",
            lambda *a, **kw: CapabilityDecision(
                kind=RequestKind.TEXT_TO_IMAGE,
                confidence=0.4,
                reasons=("low",),
            ),
        )

        resp = client.post(
            '/api/hermes/chat',
            json={'message': 'draw a cat'},
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert hermes_called["count"] == 1

    def test_pipeline_exception_falls_back_to_hermes(self, client, hermes_called, monkeypatch):
        """Bridge runtime error must fall through to Hermes."""
        from image_pipeline.reasoning.capability_router import (
            CapabilityDecision, RequestKind,
        )
        monkeypatch.setattr("core.image_intent.is_reasoning_pipeline_enabled", lambda: True)
        monkeypatch.setattr(
            "core.image_intent.detect_image_intent",
            lambda *a, **kw: CapabilityDecision(
                kind=RequestKind.TEXT_TO_IMAGE, confidence=0.95, reasons=(),
            ),
        )

        def boom(prompt_text, **kw):
            raise RuntimeError("comfy down")
        import sys, types
        fake_mod = types.ModuleType("routes.reasoning_image_gen")
        fake_mod.run_pipeline_for_prompt = boom
        monkeypatch.setitem(sys.modules, "routes.reasoning_image_gen", fake_mod)

        resp = client.post(
            '/api/hermes/chat',
            json={'message': 'vẽ ảnh hoàng hôn'},
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert hermes_called["count"] == 1  # Fell back to Hermes
        assert resp.get_json()["result"] == "hermes-answer"

    def test_pipeline_disabled_no_classifier_call(self, client, hermes_called, monkeypatch):
        """When REASONING_PIPELINE=false, classifier must not run."""
        monkeypatch.setattr("core.image_intent.is_reasoning_pipeline_enabled", lambda: False)

        called = {"n": 0}
        def spy(*a, **kw):
            called["n"] += 1
            return None
        monkeypatch.setattr("core.image_intent.detect_image_intent", spy)

        resp = client.post(
            '/api/hermes/chat',
            json={'message': 'vẽ một con mèo'},
            content_type='application/json',
        )
        assert resp.status_code == 200
        assert called["n"] == 0
        assert hermes_called["count"] == 1
