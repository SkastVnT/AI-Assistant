"""
Tests for council mode router integration (Step 9).

Covers:
    - agent_mode="off" → existing chatbot path (backward compat)
    - agent_mode="council" + enabled → run_council called, ChatResponse populated
    - agent_mode="council" + disabled → graceful fallback
    - /chat/upload with agent_mode Form field
    - Council params forwarded correctly

Run from services/chatbot/:
    python -m pytest tests/test_agentic_router.py -v
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from fastapi_app.routers import chat as chat_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def chat_app():
    _app = FastAPI()
    _app.add_middleware(SessionMiddleware, secret_key="test-secret")
    _app.include_router(chat_module.router)
    return _app


@pytest.fixture
def client(chat_app):
    return TestClient(chat_app)


def _mock_chatbot():
    bot = MagicMock()
    bot.chat.return_value = {
        "response": "Normal single-model answer.",
        "thinking_process": None,
    }
    return bot


def _mock_rag_result():
    """Minimal RAGResult-like object."""
    r = MagicMock()
    r.message = "augmented message"
    r.custom_prompt = "augmented prompt"
    r.citations = None
    r.chunk_count = 0
    return r


def _council_result_dict(**overrides):
    base = {
        "response": "Council synthesized answer.",
        "model": "council",
        "context": "casual",
        "deep_thinking": True,
        "thinking_process": "Council completed in 1 round(s).",
        "citations": None,
        "agent_run_id": "run-abc-123",
        "agent_trace_summary": {
            "rounds": 1,
            "agents_used": ["planner", "researcher", "synthesizer", "critic"],
            "total_llm_calls": 4,
            "total_tokens": 1000,
            "elapsed_seconds": 2.5,
            "decision": {"approved": True},
        },
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Common patches for all tests
# ---------------------------------------------------------------------------

def _base_patches():
    """Return a dict of patches that stub out external deps."""
    return {
        "chatbot": patch(
            "fastapi_app.routers.chat.get_chatbot_for_session",
            return_value=_mock_chatbot(),
        ),
        "rag": patch(
            "fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
            new_callable=AsyncMock,
            return_value=_mock_rag_result(),
        ),
    }


# ---------------------------------------------------------------------------
# Backward compatibility: agent_mode="off" (default)
# ---------------------------------------------------------------------------

class TestAgentModeOff:
    """When agent_mode is absent or 'off', council is never invoked."""

    def test_default_request_uses_chatbot(self, client):
        bot = _mock_chatbot()
        patches = _base_patches()
        patches["chatbot"] = patch(
            "fastapi_app.routers.chat.get_chatbot_for_session",
            return_value=bot,
        )

        with patches["chatbot"], patches["rag"], \
             patch("fastapi_app.routers.chat.run_council") as mock_council:
            resp = client.post("/chat", json={
                "message": "Hello",
                "model": "grok",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["model"] == "grok"
        assert body["agent_run_id"] is None
        assert body["agent_trace_summary"] is None
        bot.chat.assert_called_once()
        mock_council.assert_not_called()

    def test_explicit_off_uses_chatbot(self, client):
        bot = _mock_chatbot()
        patches = _base_patches()
        patches["chatbot"] = patch(
            "fastapi_app.routers.chat.get_chatbot_for_session",
            return_value=bot,
        )

        with patches["chatbot"], patches["rag"], \
             patch("fastapi_app.routers.chat.run_council") as mock_council:
            resp = client.post("/chat", json={
                "message": "Hello",
                "model": "grok",
                "agent_mode": "off",
            })

        assert resp.status_code == 200
        bot.chat.assert_called_once()
        mock_council.assert_not_called()


# ---------------------------------------------------------------------------
# Council mode: enabled
# ---------------------------------------------------------------------------

class TestCouncilModeEnabled:
    """When agent_mode="council" and feature flag is on."""

    def test_council_called(self, client):
        council_dict = _council_result_dict()

        with patch("fastapi_app.routers.chat.get_chatbot_for_session") as mock_get_bot, \
             patch("fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
                   new_callable=AsyncMock, return_value=_mock_rag_result()), \
             patch("fastapi_app.routers.chat.run_council",
                   new_callable=AsyncMock, return_value=council_dict) as mock_council:
            resp = client.post("/chat", json={
                "message": "Explain quantum computing",
                "model": "grok",
                "agent_mode": "council",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["model"] == "council"
        assert body["response"] == "Council synthesized answer."
        assert body["agent_run_id"] == "run-abc-123"
        assert body["agent_trace_summary"]["rounds"] == 1
        assert body["deep_thinking"] is True
        mock_council.assert_called_once()
        # Chatbot should NOT be called when council is active
        mock_get_bot.return_value.chat.assert_not_called()

    def test_council_params_forwarded(self, client):
        council_dict = _council_result_dict()

        with patch("fastapi_app.routers.chat.get_chatbot_for_session"), \
             patch("fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
                   new_callable=AsyncMock, return_value=_mock_rag_result()), \
             patch("fastapi_app.routers.chat.run_council",
                   new_callable=AsyncMock, return_value=council_dict) as mock_council:
            resp = client.post("/chat", json={
                "message": "Deep question",
                "model": "grok",
                "agent_mode": "council",
                "max_agent_iterations": 4,
                "preferred_planner_model": "gemini-2.5-pro",
                "preferred_researcher_model": "grok-3",
                "preferred_critic_model": "deepseek-r1",
                "preferred_synthesizer_model": "qwen-plus",
            })

        assert resp.status_code == 200
        call_kwargs = mock_council.call_args.kwargs
        assert call_kwargs["max_agent_iterations"] == 4
        assert call_kwargs["preferred_planner_model"] == "gemini-2.5-pro"
        assert call_kwargs["preferred_researcher_model"] == "grok-3"
        assert call_kwargs["preferred_critic_model"] == "deepseek-r1"
        assert call_kwargs["preferred_synthesizer_model"] == "qwen-plus"

    def test_council_original_message_preserved(self, client):
        council_dict = _council_result_dict()

        with patch("fastapi_app.routers.chat.get_chatbot_for_session"), \
             patch("fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
                   new_callable=AsyncMock, return_value=_mock_rag_result()), \
             patch("fastapi_app.routers.chat.run_council",
                   new_callable=AsyncMock, return_value=council_dict) as mock_council:
            resp = client.post("/chat", json={
                "message": "Original user query",
                "model": "grok",
                "agent_mode": "council",
            })

        assert resp.status_code == 200
        call_kwargs = mock_council.call_args.kwargs
        assert call_kwargs["original_message"] == "Original user query"


# ---------------------------------------------------------------------------
# Council mode: disabled via feature flag
# ---------------------------------------------------------------------------

class TestCouncilModeDisabled:
    """When agent_mode="council" but AGENTIC_V1_ENABLED=false."""

    def test_disabled_returns_graceful_message(self, client):
        disabled_dict = {
            "response": "Council mode is not enabled on this server. "
                        "Set AGENTIC_V1_ENABLED=true to activate it.",
            "model": "council",
            "context": "casual",
            "deep_thinking": False,
            "thinking_process": None,
            "citations": None,
            "agent_run_id": None,
            "agent_trace_summary": None,
        }

        with patch("fastapi_app.routers.chat.get_chatbot_for_session"), \
             patch("fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
                   new_callable=AsyncMock, return_value=_mock_rag_result()), \
             patch("fastapi_app.routers.chat.run_council",
                   new_callable=AsyncMock, return_value=disabled_dict):
            resp = client.post("/chat", json={
                "message": "Test",
                "model": "grok",
                "agent_mode": "council",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert "not enabled" in body["response"]
        assert body["agent_run_id"] is None


# ---------------------------------------------------------------------------
# Upload endpoint with agent_mode
# ---------------------------------------------------------------------------

class TestUploadAgentMode:
    """The /chat/upload multipart endpoint supports agent_mode."""

    def test_upload_default_off(self, client):
        bot = _mock_chatbot()

        with patch("fastapi_app.routers.chat.get_chatbot_for_session", return_value=bot), \
             patch("fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
                   new_callable=AsyncMock, return_value=_mock_rag_result()), \
             patch("fastapi_app.routers.chat.run_council") as mock_council:
            resp = client.post("/chat/upload", data={
                "message": "Hi",
                "model": "grok",
            })

        assert resp.status_code == 200
        bot.chat.assert_called_once()
        mock_council.assert_not_called()

    def test_upload_council_mode(self, client):
        council_dict = _council_result_dict()

        with patch("fastapi_app.routers.chat.get_chatbot_for_session"), \
             patch("fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
                   new_callable=AsyncMock, return_value=_mock_rag_result()), \
             patch("fastapi_app.routers.chat.run_council",
                   new_callable=AsyncMock, return_value=council_dict) as mock_council:
            resp = client.post("/chat/upload", data={
                "message": "Analyze this",
                "model": "grok",
                "agent_mode": "council",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["model"] == "council"
        assert body["agent_run_id"] == "run-abc-123"
        mock_council.assert_called_once()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Boundary and edge-case scenarios."""

    def test_empty_message_still_rejected(self, client):
        """Empty message → 422 (Pydantic validation), regardless of agent_mode."""
        with patch("fastapi_app.routers.chat.get_chatbot_for_session"):
            resp = client.post("/chat", json={
                "message": "",
                "model": "grok",
                "agent_mode": "council",
            })
        assert resp.status_code == 422

    def test_unknown_agent_mode_uses_chatbot(self, client):
        """Unknown agent_mode values fall through to normal chatbot."""
        bot = _mock_chatbot()

        with patch("fastapi_app.routers.chat.get_chatbot_for_session", return_value=bot), \
             patch("fastapi_app.rag_helpers.RAGOrchestrator.retrieve_for_chat",
                   new_callable=AsyncMock, return_value=_mock_rag_result()), \
             patch("fastapi_app.routers.chat.run_council") as mock_council:
            resp = client.post("/chat", json={
                "message": "Hello",
                "model": "grok",
                "agent_mode": "unknown_mode",
            })

        assert resp.status_code == 200
        bot.chat.assert_called_once()
        mock_council.assert_not_called()
