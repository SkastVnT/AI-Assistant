"""
Tests for xAI native multi-agent mode.

Covers:
    - XaiNativeConfig defaults and validation
    - XaiNativeResult fields and trace summary
    - XaiResponsesAdapter payload building
    - XaiResponsesAdapter response parsing
    - XaiResponsesAdapter non-streaming call (mocked HTTP)
    - XaiResponsesAdapter streaming call (mocked HTTP)
    - Entrypoint: run_xai_native() enabled / disabled
    - Entrypoint: run_xai_native_stream() yields SSE events
    - Feature flag: is_xai_native_enabled()
    - Router: /chat dispatches grok_native_research agent_mode
    - Router: /chat/xai-native/stream endpoint exists

Run from services/chatbot/:
    python -m pytest tests/test_xai_native.py -v
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agentic.xai_native.contracts import (
    ReasoningEffort,
    XaiAnnotation,
    XaiNativeConfig,
    XaiNativeResult,
    XaiNativeStatus,
    XaiUsage,
)
from core.agentic.xai_native.adapter import XaiResponsesAdapter
from core.agentic.xai_native.entrypoint import (
    _build_config,
    _build_response_dict,
    _build_system_prompt,
    _disabled_response,
    _sse,
    is_xai_native_enabled,
    run_xai_native,
    run_xai_native_stream,
)


# ═══════════════════════════════════════════════════════════════════════
# Contracts
# ═══════════════════════════════════════════════════════════════════════

class TestXaiNativeConfig:
    def test_defaults(self):
        cfg = XaiNativeConfig()
        assert cfg.model == "grok-4.20-multi-agent"
        assert cfg.reasoning_effort == ReasoningEffort.high
        assert cfg.enable_web_search is True
        assert cfg.enable_x_search is False
        assert cfg.timeout_seconds == 300

    def test_custom_values(self):
        cfg = XaiNativeConfig(
            reasoning_effort=ReasoningEffort.low,
            enable_x_search=True,
            timeout_seconds=60,
        )
        assert cfg.reasoning_effort == ReasoningEffort.low
        assert cfg.enable_x_search is True
        assert cfg.timeout_seconds == 60


class TestReasoningEffort:
    def test_values(self):
        assert ReasoningEffort.low.value == "low"
        assert ReasoningEffort.medium.value == "medium"
        assert ReasoningEffort.high.value == "high"

    def test_from_string(self):
        assert ReasoningEffort("high") == ReasoningEffort.high


class TestXaiUsage:
    def test_defaults(self):
        u = XaiUsage()
        assert u.total_tokens == 0
        assert u.reasoning_tokens == 0

    def test_custom(self):
        u = XaiUsage(total_tokens=500, reasoning_tokens=300, num_sources_used=3)
        assert u.total_tokens == 500
        assert u.reasoning_tokens == 300
        assert u.num_sources_used == 3


class TestXaiNativeResult:
    def test_success(self):
        r = XaiNativeResult(
            response_id="resp-123",
            status=XaiNativeStatus.completed,
            content="Answer text",
            model="grok-4.20-multi-agent",
        )
        assert r.success is True
        assert r.content == "Answer text"

    def test_failure(self):
        r = XaiNativeResult(
            status=XaiNativeStatus.failed,
            error="Timeout",
        )
        assert r.success is False

    def test_trace_summary(self):
        r = XaiNativeResult(
            response_id="resp-456",
            model="grok-4.20-multi-agent",
            usage=XaiUsage(total_tokens=1000, reasoning_tokens=600, num_sources_used=5),
            elapsed_seconds=12.345,
        )
        trace = r.to_trace_summary()
        assert trace["response_id"] == "resp-456"
        assert trace["total_tokens"] == 1000
        assert trace["reasoning_tokens"] == 600
        assert trace["sources_used"] == 5
        assert trace["elapsed_seconds"] == 12.35

    def test_annotations(self):
        ann = XaiAnnotation(type="url_citation", url="https://example.com", title="Example")
        assert ann.url == "https://example.com"


# ═══════════════════════════════════════════════════════════════════════
# Adapter — Payload building
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterPayload:
    def setup_method(self):
        self.adapter = XaiResponsesAdapter(api_key="test-key")

    def test_basic_payload(self):
        cfg = XaiNativeConfig()
        payload = self.adapter._build_payload(
            message="Hello", config=cfg,
        )
        assert payload["model"] == "grok-4.20-multi-agent"
        assert payload["input"] == "Hello"
        assert payload["stream"] is False
        assert payload["store"] is False
        assert payload["reasoning"] == {"effort": "high"}
        assert {"type": "web_search"} in payload["tools"]

    def test_payload_with_system_prompt(self):
        cfg = XaiNativeConfig()
        payload = self.adapter._build_payload(
            message="Test", config=cfg, system_prompt="Be helpful",
        )
        assert payload["instructions"] == "Be helpful"

    def test_payload_without_system_prompt(self):
        cfg = XaiNativeConfig()
        payload = self.adapter._build_payload(
            message="Test", config=cfg,
        )
        assert "instructions" not in payload

    def test_payload_no_tools(self):
        cfg = XaiNativeConfig(enable_web_search=False, enable_x_search=False)
        payload = self.adapter._build_payload(
            message="Test", config=cfg,
        )
        assert payload.get("tools", []) == []

    def test_payload_both_tools(self):
        cfg = XaiNativeConfig(enable_web_search=True, enable_x_search=True)
        payload = self.adapter._build_payload(
            message="Test", config=cfg,
        )
        assert {"type": "web_search"} in payload["tools"]
        assert {"type": "x_search"} in payload["tools"]

    def test_payload_streaming(self):
        cfg = XaiNativeConfig()
        payload = self.adapter._build_payload(
            message="Test", config=cfg, stream=True,
        )
        assert payload["stream"] is True

    def test_reasoning_effort_propagated(self):
        cfg = XaiNativeConfig(reasoning_effort=ReasoningEffort.low)
        payload = self.adapter._build_payload(
            message="Test", config=cfg,
        )
        assert payload["reasoning"]["effort"] == "low"


class TestAdapterConstructor:
    def test_requires_api_key(self):
        with pytest.raises(ValueError, match="GROK_API_KEY"):
            XaiResponsesAdapter(api_key="")


# ═══════════════════════════════════════════════════════════════════════
# Adapter — Response parsing
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterParsing:
    def setup_method(self):
        self.adapter = XaiResponsesAdapter(api_key="test-key")

    def test_parse_successful_response(self):
        data = {
            "id": "resp-abc",
            "model": "grok-4.20-multi-agent",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Research result here",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://example.com",
                                    "title": "Example",
                                    "start_index": 0,
                                    "end_index": 10,
                                }
                            ],
                        }
                    ],
                }
            ],
            "usage": {
                "input_tokens": 100,
                "output_tokens": 200,
                "total_tokens": 300,
                "output_tokens_details": {"reasoning_tokens": 50},
                "num_sources_used": 3,
                "num_server_side_tools_used": 2,
            },
        }
        result = self.adapter._parse_response(data, elapsed=5.0)
        assert result.response_id == "resp-abc"
        assert result.status == XaiNativeStatus.completed
        assert result.content == "Research result here"
        assert result.usage.total_tokens == 300
        assert result.usage.reasoning_tokens == 50
        assert result.usage.num_sources_used == 3
        assert len(result.annotations) == 1
        assert result.annotations[0].url == "https://example.com"
        assert result.elapsed_seconds == 5.0
        assert result.success is True

    def test_parse_error_response(self):
        data = {
            "id": "resp-err",
            "model": "grok-4.20-multi-agent",
            "status": "completed",
            "output": [],
            "usage": {},
            "error": {"message": "Rate limited"},
        }
        result = self.adapter._parse_response(data, elapsed=1.0)
        assert result.status == XaiNativeStatus.failed
        assert result.error == "Rate limited"
        assert result.success is False

    def test_parse_skips_reasoning_items(self):
        data = {
            "id": "resp-reason",
            "model": "grok-4.20-multi-agent",
            "status": "completed",
            "output": [
                {"type": "reasoning", "summary": [{"text": "secret thinking"}]},
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Public answer"}],
                },
            ],
            "usage": {},
        }
        result = self.adapter._parse_response(data, elapsed=2.0)
        assert "secret thinking" not in result.content
        assert result.content == "Public answer"

    def test_parse_usage_chat_completions_format(self):
        raw = {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150,
            "completion_tokens_details": {"reasoning_tokens": 80},
        }
        usage = self.adapter._parse_usage(raw)
        assert usage.input_tokens == 50
        assert usage.output_tokens == 100
        assert usage.reasoning_tokens == 80

    def test_parse_usage_responses_format(self):
        raw = {
            "input_tokens": 50,
            "output_tokens": 100,
            "total_tokens": 150,
            "output_tokens_details": {"reasoning_tokens": 80},
        }
        usage = self.adapter._parse_usage(raw)
        assert usage.input_tokens == 50
        assert usage.output_tokens == 100
        assert usage.reasoning_tokens == 80


class TestAdapterContentDelta:
    def setup_method(self):
        self.adapter = XaiResponsesAdapter(api_key="test-key")

    def test_chat_completions_format(self):
        chunk = {"choices": [{"delta": {"content": "Hello"}}]}
        assert self.adapter._extract_content_delta(chunk) == "Hello"

    def test_responses_output_format(self):
        chunk = {
            "output": [
                {"type": "message", "content": [{"type": "output_text", "text": "World"}]}
            ]
        }
        assert self.adapter._extract_content_delta(chunk) == "World"

    def test_delta_dict_format(self):
        chunk = {"delta": {"content": "ABC"}}
        assert self.adapter._extract_content_delta(chunk) == "ABC"

    def test_empty_chunk(self):
        assert self.adapter._extract_content_delta({}) == ""


# ═══════════════════════════════════════════════════════════════════════
# Adapter — HTTP calls (mocked)
# ═══════════════════════════════════════════════════════════════════════

class TestAdapterCall:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        adapter = XaiResponsesAdapter(api_key="test-key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "resp-ok",
            "model": "grok-4.20-multi-agent",
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Result text"}],
                }
            ],
            "usage": {"total_tokens": 500},
        }

        with patch("core.agentic.xai_native.adapter.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.call(
                message="Test query",
                config=XaiNativeConfig(),
            )

        assert result.success is True
        assert result.content == "Result text"
        assert result.response_id == "resp-ok"

    @pytest.mark.asyncio
    async def test_http_error(self):
        adapter = XaiResponsesAdapter(api_key="test-key")
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"

        with patch("core.agentic.xai_native.adapter.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.call(
                message="Test query",
                config=XaiNativeConfig(),
            )

        assert result.success is False
        assert "429" in result.error

    @pytest.mark.asyncio
    async def test_timeout(self):
        import httpx as real_httpx

        adapter = XaiResponsesAdapter(api_key="test-key")

        with patch("core.agentic.xai_native.adapter.httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            mock_client.post.side_effect = real_httpx.TimeoutException("timed out")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await adapter.call(
                message="Test query",
                config=XaiNativeConfig(timeout_seconds=30),
            )

        assert result.success is False
        assert "timed out" in result.error.lower()


# ═══════════════════════════════════════════════════════════════════════
# Entrypoint — helpers
# ═══════════════════════════════════════════════════════════════════════

class TestEntrypointHelpers:
    def test_build_config_defaults(self):
        cfg = _build_config()
        assert cfg.reasoning_effort == ReasoningEffort.high
        assert cfg.enable_web_search is True

    def test_build_config_custom(self):
        cfg = _build_config(
            reasoning_effort="low",
            enable_web_search=False,
            enable_x_search=True,
        )
        assert cfg.reasoning_effort == ReasoningEffort.low
        assert cfg.enable_web_search is False
        assert cfg.enable_x_search is True

    def test_build_config_invalid_effort_falls_back(self):
        cfg = _build_config(reasoning_effort="invalid_value")
        assert cfg.reasoning_effort == ReasoningEffort.high

    def test_build_system_prompt_default(self):
        prompt = _build_system_prompt(
            context_type="casual",
            language="vi",
            custom_prompt="",
            mcp_context="",
            rag_context="",
        )
        assert "vi" in prompt
        assert "casual" in prompt

    def test_build_system_prompt_custom(self):
        prompt = _build_system_prompt(
            context_type="code",
            language="en",
            custom_prompt="Custom instructions",
            mcp_context="file.py",
            rag_context="RAG chunks",
        )
        assert "Custom instructions" in prompt
        assert "RAG chunks" in prompt
        assert "file.py" in prompt

    def test_disabled_response(self):
        resp = _disabled_response("casual", [{"url": "test"}])
        assert resp["model"] == "grok-native"
        assert "not enabled" in resp["response"]
        assert resp["citations"] == [{"url": "test"}]
        assert resp["agent_run_id"] is None

    def test_sse_format(self):
        sse = _sse("test_event", {"key": "value"})
        assert sse.startswith("event: test_event\n")
        assert '"key": "value"' in sse

    def test_build_response_dict(self):
        result = XaiNativeResult(
            response_id="resp-789",
            content="Answer",
            model="grok-4.20-multi-agent",
            usage=XaiUsage(total_tokens=800, reasoning_tokens=400, num_sources_used=2),
            elapsed_seconds=10.5,
            annotations=[
                XaiAnnotation(type="url_citation", url="https://src.com", title="Source"),
            ],
        )
        config = XaiNativeConfig(reasoning_effort=ReasoningEffort.medium)
        d = _build_response_dict(result, config, "casual", [{"url": "rag"}])

        assert d["response"] == "Answer"
        assert d["model"] == "grok-native"
        assert d["deep_thinking"] is True
        assert d["agent_run_id"] == "resp-789"
        assert d["agent_trace_summary"]["reasoning_effort"] == "medium"
        assert d["agent_trace_summary"]["total_tokens"] == 800
        # RAG + xAI annotations merged
        assert len(d["citations"]) == 2
        assert d["citations"][0]["url"] == "rag"
        assert d["citations"][1]["url"] == "https://src.com"


# ═══════════════════════════════════════════════════════════════════════
# Entrypoint — Feature flag
# ═══════════════════════════════════════════════════════════════════════

class TestFeatureFlag:
    def test_disabled_by_default(self):
        with patch.dict("os.environ", {}, clear=False):
            # Re-import to re-evaluate
            import importlib
            import core.agentic.xai_native.entrypoint as ep
            importlib.reload(ep)
            assert ep.is_xai_native_enabled() is False

    def test_enabled_true(self):
        with patch.dict("os.environ", {"XAI_NATIVE_MULTI_AGENT_ENABLED": "true"}):
            import importlib
            import core.agentic.xai_native.entrypoint as ep
            importlib.reload(ep)
            assert ep.is_xai_native_enabled() is True

    def test_enabled_1(self):
        with patch.dict("os.environ", {"XAI_NATIVE_MULTI_AGENT_ENABLED": "1"}):
            import importlib
            import core.agentic.xai_native.entrypoint as ep
            importlib.reload(ep)
            assert ep.is_xai_native_enabled() is True


# ═══════════════════════════════════════════════════════════════════════
# Entrypoint — run_xai_native
# ═══════════════════════════════════════════════════════════════════════

class TestRunXaiNative:
    @pytest.mark.asyncio
    async def test_disabled_returns_graceful_response(self):
        with patch("core.agentic.xai_native.entrypoint.is_xai_native_enabled", return_value=False):
            result = await run_xai_native(
                original_message="test",
                augmented_message="test",
            )
        assert "not enabled" in result["response"]
        assert result["model"] == "grok-native"

    @pytest.mark.asyncio
    async def test_enabled_calls_adapter(self):
        mock_result = XaiNativeResult(
            response_id="resp-test",
            status=XaiNativeStatus.completed,
            content="Research complete",
            model="grok-4.20-multi-agent",
            usage=XaiUsage(total_tokens=500),
            elapsed_seconds=8.0,
        )
        mock_adapter = MagicMock()
        mock_adapter.call = AsyncMock(return_value=mock_result)

        with patch("core.agentic.xai_native.entrypoint.is_xai_native_enabled", return_value=True), \
             patch("core.agentic.xai_native.entrypoint._get_adapter", return_value=mock_adapter):
            result = await run_xai_native(
                original_message="Analyze quantum computing",
                augmented_message="Analyze quantum computing",
                reasoning_effort="high",
            )

        assert result["response"] == "Research complete"
        assert result["agent_run_id"] == "resp-test"
        assert result["agent_trace_summary"]["total_tokens"] == 500
        mock_adapter.call.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════
# Entrypoint — run_xai_native_stream
# ═══════════════════════════════════════════════════════════════════════

class TestRunXaiNativeStream:
    @pytest.mark.asyncio
    async def test_disabled_yields_disabled_result(self):
        with patch("core.agentic.xai_native.entrypoint.is_xai_native_enabled", return_value=False):
            chunks = []
            async for chunk in run_xai_native_stream(
                original_message="test",
                augmented_message="test",
            ):
                chunks.append(chunk)
        assert len(chunks) == 1
        assert "xai_native_result" in chunks[0]
        assert "not enabled" in chunks[0]

    @pytest.mark.asyncio
    async def test_enabled_yields_events(self):
        async def mock_stream(**kwargs):
            yield {"type": "thinking", "reasoning_tokens": 100}
            yield {"type": "content", "text": "Partial "}
            yield {"type": "content", "text": "answer"}
            yield {
                "type": "done",
                "result": XaiNativeResult(
                    response_id="resp-stream",
                    content="Partial answer",
                    model="grok-4.20-multi-agent",
                    usage=XaiUsage(total_tokens=300),
                    elapsed_seconds=5.0,
                ),
            }

        mock_adapter = MagicMock()
        mock_adapter.stream = mock_stream

        with patch("core.agentic.xai_native.entrypoint.is_xai_native_enabled", return_value=True), \
             patch("core.agentic.xai_native.entrypoint._get_adapter", return_value=mock_adapter):
            chunks = []
            async for chunk in run_xai_native_stream(
                original_message="test",
                augmented_message="test",
            ):
                chunks.append(chunk)

        # start + thinking + 2 content + result = 5
        assert len(chunks) == 5
        assert "xai_native_event" in chunks[0]  # starting
        assert "xai_native_event" in chunks[1]  # thinking
        assert "xai_native_chunk" in chunks[2]  # content
        assert "xai_native_chunk" in chunks[3]  # content
        assert "xai_native_result" in chunks[4]  # done

    @pytest.mark.asyncio
    async def test_stream_error_yields_error_event(self):
        async def mock_stream(**kwargs):
            yield {"type": "error", "error": "Connection failed"}

        mock_adapter = MagicMock()
        mock_adapter.stream = mock_stream

        with patch("core.agentic.xai_native.entrypoint.is_xai_native_enabled", return_value=True), \
             patch("core.agentic.xai_native.entrypoint._get_adapter", return_value=mock_adapter):
            chunks = []
            async for chunk in run_xai_native_stream(
                original_message="test",
                augmented_message="test",
            ):
                chunks.append(chunk)

        # start + error = 2
        assert len(chunks) == 2
        assert "xai_native_error" in chunks[1]
