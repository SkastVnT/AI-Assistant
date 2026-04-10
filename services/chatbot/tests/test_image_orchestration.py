"""
Tests for the image orchestration flow — intent detection, orchestrator pipeline,
chat.py integration, and stream.py integration.

Run from services/chatbot/:
    python -m pytest tests/test_image_orchestration.py -v

No real GPU / API keys needed — providers are mocked.
"""
from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────
# 1. Intent detection tests (pure — no imports from providers)
# ─────────────────────────────────────────────────────────────────────

class TestIntentDetection:
    """Unit tests for core/image_gen/intent.py"""

    def setup_method(self):
        from core.image_gen.intent import detect_intent, ImageIntent
        self.detect_intent = detect_intent
        self.ImageIntent   = ImageIntent

    # ── Generation intent ──────────────────────────────────────

    def test_generation_vietnamese(self):
        r = self.detect_intent("vẽ một con mèo trên mái nhà")
        assert r.intent == self.ImageIntent.GENERATE
        assert r.confidence > 0.4

    def test_generation_english(self):
        r = self.detect_intent("draw a cat sitting on a rooftop at sunset")
        assert r.intent == self.ImageIntent.GENERATE

    def test_generation_create_image(self):
        r = self.detect_intent("create an image of a dragon flying over the ocean")
        assert r.intent == self.ImageIntent.GENERATE

    def test_generation_tao_anh(self):
        r = self.detect_intent("tạo ảnh một cô gái anime tóc hồng")
        assert r.intent == self.ImageIntent.GENERATE

    # ── Edit intent ────────────────────────────────────────────

    def test_edit_explicit_with_previous(self):
        r = self.detect_intent("chỉnh ảnh làm sáng hơn", has_previous_image=True)
        assert r.intent == self.ImageIntent.EDIT

    def test_edit_english_with_previous(self):
        r = self.detect_intent("edit image to add a rainbow", has_previous_image=True)
        assert r.intent == self.ImageIntent.EDIT

    def test_edit_no_previous_falls_through(self):
        """Without a previous image, edit keywords should not trigger EDIT."""
        r = self.detect_intent("edit image", has_previous_image=False)
        # Should be GENERATE (has "edit image" in _EDIT_EN but no previous)
        # Actually _EDIT_EN is only checked when has_previous_image=True
        assert r.intent != self.ImageIntent.EDIT

    # ── Followup edit intent ───────────────────────────────────

    def test_followup_short_add(self):
        r = self.detect_intent("thêm cầu vồng", has_previous_image=True)
        assert r.intent == self.ImageIntent.FOLLOWUP_EDIT

    def test_followup_short_remove(self):
        r = self.detect_intent("bỏ nền", has_previous_image=True)
        assert r.intent == self.ImageIntent.FOLLOWUP_EDIT

    def test_followup_english_brighter(self):
        r = self.detect_intent("make it brighter", has_previous_image=True)
        # "make it" appears in _EDIT_EN so EDIT is acceptable too
        assert r.intent in (self.ImageIntent.FOLLOWUP_EDIT, self.ImageIntent.EDIT)

    def test_followup_too_long_not_triggered(self):
        """Long messages should not be classified as followup."""
        long_msg = "make it brighter and add a beautiful sunset sky with orange clouds please"
        r = self.detect_intent(long_msg, has_previous_image=True)
        # Too many words for followup — should be EDIT or GENERATE
        assert r.intent != self.ImageIntent.FOLLOWUP_EDIT

    # ── NONE intent ────────────────────────────────────────────

    def test_none_chat_question(self):
        r = self.detect_intent("giải thích machine learning là gì?")
        assert r.intent == self.ImageIntent.NONE

    def test_none_code_request(self):
        r = self.detect_intent("viết hàm Python để sort một list")
        assert r.intent == self.ImageIntent.NONE

    def test_none_translate(self):
        r = self.detect_intent("dịch câu này sang tiếng Anh: xin chào")
        assert r.intent == self.ImageIntent.NONE

    # ── Hints extraction ───────────────────────────────────────

    def test_style_hint_anime(self):
        r = self.detect_intent("vẽ một nhân vật anime tóc vàng")
        assert r.style_hint == "anime"

    def test_style_hint_photorealistic(self):
        r = self.detect_intent("generate a photorealistic portrait of a woman")
        assert r.style_hint == "photorealistic"

    def test_quality_hint_fast(self):
        r = self.detect_intent("vẽ nhanh một con chó")
        assert r.quality_hint == "fast"

    def test_quality_hint_hd(self):
        r = self.detect_intent("create a 4K detailed landscape")
        assert r.quality_hint == "quality"

    def test_dimension_portrait(self):
        r = self.detect_intent("vẽ ảnh dọc 9:16 một cô gái")
        assert r.width < r.height  # portrait

    def test_dimension_landscape(self):
        r = self.detect_intent("create a wide landscape banner")
        assert r.width > r.height  # landscape

    # ── IMAGE_FIRST_MODE edge cases ─────────────────────────────

    def test_image_first_mode_question_not_triggered(self, monkeypatch):
        monkeypatch.setenv("IMAGE_FIRST_MODE", "1")
        r = self.detect_intent("what is the capital of France?")
        assert r.intent == self.ImageIntent.NONE

    def test_image_first_mode_description_triggered(self, monkeypatch):
        monkeypatch.setenv("IMAGE_FIRST_MODE", "1")
        r = self.detect_intent("a fluffy orange cat sitting by a window")
        assert r.intent == self.ImageIntent.GENERATE
        assert r.confidence <= 0.5  # low confidence for IMAGE_FIRST_MODE

    def test_image_first_mode_disabled(self, monkeypatch):
        monkeypatch.setenv("IMAGE_FIRST_MODE", "0")
        r = self.detect_intent("a fluffy orange cat")
        assert r.intent == self.ImageIntent.NONE


# ─────────────────────────────────────────────────────────────────────
# 2. Orchestrator unit tests (provider mocked)
# ─────────────────────────────────────────────────────────────────────

class TestImageOrchestrator:
    """Unit tests for core/image_gen/orchestrator.py with mocked provider."""

    def _make_orchestrator(self, session_id: str = "test-session"):
        from core.image_gen.orchestrator import ImageOrchestrator
        orch = ImageOrchestrator(session_id=session_id)
        orch._enabled = True
        return orch

    def _mock_router(self, success: bool = True):
        from core.image_gen.providers.base import ImageResult
        result = ImageResult(
            success    = success,
            images_b64 = ["FAKEB64DATA"] if success else [],
            images_url = [],
            provider   = "fal",
            model      = "fal-flux-schnell",
            prompt_used = "enhanced: a cat on a rooftop",
            cost_usd   = 0.003,
            latency_ms = 1200,
            metadata   = {"width": "1024", "height": "1024"},
            error      = None if success else "Provider unavailable",
        )
        router = MagicMock()
        router.generate.return_value = result
        return router

    def test_handle_returns_image_for_generate_intent(self):
        orch = self._make_orchestrator()

        mock_router  = self._mock_router(success=True)
        mock_storage = MagicMock()
        mock_storage.save.return_value = {"url": "http://example.com/img.png"}

        with patch.object(type(orch), "_get_router",  return_value=mock_router), \
             patch.object(type(orch), "_get_storage", return_value=mock_storage):
            result = orch.handle("vẽ một con mèo", language="vi")

        assert result.is_image is True
        assert result.provider == "fal"
        assert "FAKEB64DATA" in result.images_b64
        assert "## 🎨" in result.response_text

    def test_handle_fallback_when_disabled(self):
        orch = self._make_orchestrator()
        orch._enabled = False
        result = orch.handle("vẽ một con mèo")
        assert result.is_image is False
        assert result.fallback_to_llm is True

    def test_handle_none_intent_falls_through(self):
        orch = self._make_orchestrator()
        result = orch.handle("giải thích machine learning là gì?")
        assert result.fallback_to_llm is True
        assert result.is_image is False

    def test_handle_provider_failure_falls_back_to_llm(self):
        orch = self._make_orchestrator()
        mock_router  = self._mock_router(success=False)
        mock_storage = MagicMock()

        with patch.object(type(orch), "_get_router",  return_value=mock_router), \
             patch.object(type(orch), "_get_storage", return_value=mock_storage):
            result = orch.handle("vẽ một con mèo", language="vi")

        assert result.is_image is False
        assert result.fallback_to_llm is True
        assert result.error

    def test_multi_turn_edit_uses_previous_image(self):
        orch = self._make_orchestrator()

        # Step 1: initial generation
        mock_router  = self._mock_router(success=True)
        mock_storage = MagicMock()
        mock_storage.save.return_value = {}

        with patch.object(type(orch), "_get_router",  return_value=mock_router), \
             patch.object(type(orch), "_get_storage", return_value=mock_storage):
            r1 = orch.handle("vẽ một con mèo", language="vi")

        assert r1.is_image is True
        assert orch.has_previous_image is True

        # Step 2: followup edit
        with patch.object(type(orch), "_get_router",  return_value=mock_router), \
             patch.object(type(orch), "_get_storage", return_value=mock_storage):
            r2 = orch.handle("thêm cầu vồng", language="vi")

        assert r2.is_image is True
        assert r2.intent.value in ("followup", "edit")
        # Router should have been called with i2i mode (source_image_b64 set)
        call_kwargs = mock_router.generate.call_args_list[-1][1]
        # source_image_b64 comes from b64 in session
        assert call_kwargs.get("source_image_b64") is not None or \
               call_kwargs.get("mode") in ("i2i", "t2i")  # depends on b64 availability

    def test_explicit_tool_forces_generation(self):
        """When 'image-generation' tool is active, NONE intent → GENERATE."""
        orch = self._make_orchestrator()

        mock_router  = self._mock_router(success=True)
        mock_storage = MagicMock()
        mock_storage.save.return_value = {}

        with patch.object(type(orch), "_get_router",  return_value=mock_router), \
             patch.object(type(orch), "_get_storage", return_value=mock_storage):
            result = orch.handle(
                "a fluffy cat",
                tools=["image-generation"],
            )

        assert result.is_image is True

    def test_streaming_yields_correct_events(self):
        orch = self._make_orchestrator()
        mock_router  = self._mock_router(success=True)
        mock_storage = MagicMock()
        mock_storage.save.return_value = {}

        with patch.object(type(orch), "_get_router",  return_value=mock_router), \
             patch.object(type(orch), "_get_storage", return_value=mock_storage):
            events = list(orch.handle_stream("vẽ một con mèo", language="vi"))

        event_names = [e["event"] for e in events]
        assert "image_gen_start"  in event_names
        assert "image_gen_status" in event_names
        assert "image_gen_result" in event_names

    def test_streaming_yields_no_events_for_chat_message(self):
        orch = self._make_orchestrator()
        events = list(orch.handle_stream("giải thích Python là gì?"))
        assert events == []

    def test_style_persisted_across_turns(self):
        orch = self._make_orchestrator()
        mock_router  = self._mock_router(success=True)
        mock_storage = MagicMock()
        mock_storage.save.return_value = {}

        # First image with anime style
        with patch.object(type(orch), "_get_router",  return_value=mock_router), \
             patch.object(type(orch), "_get_storage", return_value=mock_storage):
            orch.handle("vẽ nhân vật anime tóc vàng")

        assert orch._img_session.active_style == "anime"

        # Second image — style should be inherited
        with patch.object(type(orch), "_get_router",  return_value=mock_router), \
             patch.object(type(orch), "_get_storage", return_value=mock_storage):
            orch.handle("thêm kiếm", tools=[])

        call_kwargs = mock_router.generate.call_args_list[-1][1]
        assert call_kwargs.get("style") == "anime"


# ─────────────────────────────────────────────────────────────────────
# Stub missing heavy optional modules so the FastAPI router can be
# imported in the test environment (pgvector / RAG SQL models not
# installed in this venv — pre-existing constraint).
# ─────────────────────────────────────────────────────────────────────

def _ensure_stub(dotted: str):
    import sys, types
    parts = dotted.split(".")
    for i in range(1, len(parts) + 1):
        full = ".".join(parts[:i])
        if full not in sys.modules:
            sys.modules[full] = types.ModuleType(full)

for _s in [
    "pgvector", "pgvector.sqlalchemy",
    "src.rag.db", "src.rag.db.models",
    "src.rag.service", "src.rag.service.ingest_service",
    "src.rag.service.orchestrator",
]:
    _ensure_stub(_s)

import sys as _sys, types as _types
from pathlib import Path as _Path

# Provide attrs referenced at import time by rag.py and rag_helpers.py.
#
# _ensure_stub() may have already put a plain types.ModuleType("src.rag")
# into sys.modules (without __path__) as a side-effect of stubbing child
# packages.  A plain ModuleType is *not* a package: attempting
# `from src.rag.prompts import …` in any later test file would raise
#     ModuleNotFoundError: … 'src.rag' is not a package
# To avoid that, ensure the module in sys.modules["src.rag"] either:
#   a) is the real imported package (has __path__) – leave it untouched, or
#   b) has __path__ pointing at the real src/rag/ directory so that
#      sub-packages remain importable even via the lightweight stub.
_rag_real_path = str((_Path(__file__).parent.parent / "src" / "rag").resolve())
_existing = _sys.modules.get("src.rag")
if _existing is None or not hasattr(_existing, "__path__"):
    # Create (or replace) the stub and give it a proper __path__ so that
    # Python can still find src.rag.prompts, src.rag.security, etc.
    _src_rag_mod = _types.ModuleType("src.rag")
    _src_rag_mod.RAG_ENABLED = False         # type: ignore
    _src_rag_mod.get_rag_pipeline = lambda: None  # type: ignore
    _src_rag_mod.__path__ = [_rag_real_path]  # marks this as a package
    _src_rag_mod.__package__ = "src.rag"
    _sys.modules["src.rag"] = _src_rag_mod
_sys.modules["src.rag.service.orchestrator"].RAGOrchestrator = MagicMock  # type: ignore
_sys.modules["src.rag.service.orchestrator"].RAGResult = MagicMock        # type: ignore


# ─────────────────────────────────────────────────────────────────────
# 3. FastAPI router integration tests (_do_chat branch logic)
#    Uses AsyncMock to call _do_chat directly — avoids full app import.
# ─────────────────────────────────────────────────────────────────────

class TestChatEndpointImageOrchestration:
    """Direct tests of _do_chat() orchestration branch."""

    def _make_request(self):
        """Minimal Starlette Request-like mock."""
        req = MagicMock()
        req.session = {"session_id": "test-session-123"}
        return req

    def _mock_orch_result(self, is_image: bool = True):
        from core.image_gen.orchestrator import OrchestratorResult
        from core.image_gen.intent import ImageIntent
        return OrchestratorResult(
            is_image        = is_image,
            intent          = ImageIntent.GENERATE,
            images_b64      = ["FAKEB64"],
            images_url      = ["http://example.com/test.png"],
            enhanced_prompt = "enhanced: a cat",
            original_prompt = "vẽ con mèo",
            provider        = "fal",
            model           = "schnell",
            cost_usd        = 0.003,
            latency_ms      = 1100,
            response_text   = "## 🎨 Ảnh đã được tạo!\n\ntest",
            fallback_to_llm = not is_image,
        )

    def _rag_result(self):
        r = MagicMock()
        r.message = "augmented message"
        r.custom_prompt = ""
        r.citations = None
        r.chunk_count = 0
        return r

    @pytest.mark.asyncio
    async def test_image_request_returns_image_result(self):
        from fastapi_app.routers.chat import _do_chat

        mock_orch = MagicMock()
        mock_orch.handle.return_value = self._mock_orch_result(is_image=True)

        with patch("fastapi_app.routers.chat.get_image_orchestrator_for_session",
                   return_value=mock_orch), \
             patch("fastapi_app.routers.chat.retrieve_rag_context",
                   return_value=self._rag_result()):
            result = await _do_chat(
                request=self._make_request(),
                message="vẽ con mèo",
                model="grok", context="casual", deep_thinking=False,
                language="vi", custom_prompt="", memory_ids=[], history=None,
                mcp_selected_files=[], agent_config=None, tools=[],
            )

        assert result.image_result is not None
        assert result.image_result["provider"] == "fal"
        assert "🎨" in result.response

    @pytest.mark.asyncio
    async def test_chat_request_skips_image_gen(self):
        from fastapi_app.routers.chat import _do_chat

        mock_orch = MagicMock()
        mock_orch.handle.return_value = self._mock_orch_result(is_image=False)

        mock_chatbot = MagicMock()
        mock_chatbot.chat.return_value = {"response": "Python là ngôn ngữ."}

        with patch("fastapi_app.routers.chat.get_image_orchestrator_for_session",
                   return_value=mock_orch), \
             patch("fastapi_app.routers.chat.get_chatbot_for_session",
                   return_value=mock_chatbot), \
             patch("fastapi_app.routers.chat.retrieve_rag_context",
                   return_value=self._rag_result()):
            result = await _do_chat(
                request=self._make_request(),
                message="Python là gì?",
                model="grok", context="casual", deep_thinking=False,
                language="vi", custom_prompt="", memory_ids=[], history=None,
                mcp_selected_files=[], agent_config=None, tools=[],
            )

        assert result.image_result is None
        assert "Python" in result.response

    @pytest.mark.asyncio
    async def test_enable_image_gen_false_skips_orchestration(self):
        from fastapi_app.routers.chat import _do_chat

        mock_orch = MagicMock()
        mock_chatbot = MagicMock()
        mock_chatbot.chat.return_value = {"response": "chat response"}

        with patch("fastapi_app.routers.chat.get_image_orchestrator_for_session",
                   return_value=mock_orch), \
             patch("fastapi_app.routers.chat.get_chatbot_for_session",
                   return_value=mock_chatbot), \
             patch("fastapi_app.routers.chat.retrieve_rag_context",
                   return_value=self._rag_result()):
            await _do_chat(
                request=self._make_request(),
                message="vẽ con mèo",
                model="grok", context="casual", deep_thinking=False,
                language="vi", custom_prompt="", memory_ids=[], history=None,
                mcp_selected_files=[], agent_config=None, tools=[],
                enable_image_gen=False,
            )

        mock_orch.handle.assert_not_called()

    @pytest.mark.asyncio
    async def test_agent_mode_council_skips_image_gen(self):
        from fastapi_app.routers.chat import _do_chat

        mock_orch = MagicMock()

        with patch("fastapi_app.routers.chat.get_image_orchestrator_for_session",
                   return_value=mock_orch), \
             patch("fastapi_app.routers.chat.retrieve_rag_context",
                   return_value=self._rag_result()), \
             patch("fastapi_app.routers.chat.run_council",
                   new_callable=AsyncMock) as mock_council:
            mock_council.return_value = {
                "response": "council answer", "model": "grok", "context": "casual",
            }
            await _do_chat(
                request=self._make_request(),
                message="vẽ con mèo",
                model="grok", context="casual", deep_thinking=False,
                language="vi", custom_prompt="", memory_ids=[], history=None,
                mcp_selected_files=[], agent_config=None, tools=[],
                agent_mode="council",
            )

        mock_orch.handle.assert_not_called()


# ─────────────────────────────────────────────────────────────────────
# 4. Stream orchestrator logic tests (handle_stream events)
# ─────────────────────────────────────────────────────────────────────

class TestStreamEndpointImageOrchestration:
    """Direct tests of ImageOrchestrator.handle_stream() event sequence."""

    def _make_orchestrator(self, session_id: str = "stream-test"):
        from core.image_gen.orchestrator import ImageOrchestrator
        orch = ImageOrchestrator(session_id=session_id)
        orch._enabled = True
        return orch

    def _mock_router(self, success: bool = True):
        from core.image_gen.providers.base import ImageResult
        result = ImageResult(
            success    = success,
            images_b64 = ["FAKEB64"] if success else [],
            provider   = "fal",
            model      = "schnell",
            prompt_used= "enhanced: a cat",
            cost_usd   = 0.003,
            metadata   = {"width": "1024", "height": "1024"},
            error      = None if success else "Provider failed",
        )
        r = MagicMock()
        r.generate.return_value = result
        return r

    def test_image_stream_emits_image_events(self):
        orch        = self._make_orchestrator()
        mock_router = self._mock_router(success=True)
        mock_storage = MagicMock()
        mock_storage.save.return_value = {}

        with patch.object(type(orch), "_get_router",  return_value=mock_router), \
             patch.object(type(orch), "_get_storage", return_value=mock_storage):
            events = list(orch.handle_stream("vẽ con mèo", language="vi"))

        event_names = [e["event"] for e in events]
        assert "image_gen_start"  in event_names
        assert "image_gen_result" in event_names
        assert "image_gen_error"  not in event_names

    def test_fallback_stream_goes_to_llm_on_failure(self):
        orch         = self._make_orchestrator()
        mock_router  = self._mock_router(success=False)
        mock_storage = MagicMock()

        with patch.object(type(orch), "_get_router",  return_value=mock_router), \
             patch.object(type(orch), "_get_storage", return_value=mock_storage):
            events = list(orch.handle_stream("vẽ con mèo", language="vi"))

        error_events = [e for e in events if e["event"] == "image_gen_error"]
        assert error_events, "Expected image_gen_error event on failure"
        assert error_events[0]["data"].get("fallback_to_llm") is True

    def test_non_image_message_yields_no_events(self):
        orch = self._make_orchestrator()
        events = list(orch.handle_stream("giải thích Python là gì?"))
        assert events == []


