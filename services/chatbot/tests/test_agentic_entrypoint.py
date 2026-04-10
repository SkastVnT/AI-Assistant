"""
Tests for the council entrypoint (run_council / run_council_stream).

Covers:
    - run_council() builds correct config and pre_context
    - run_council() returns ChatResponse-compatible dict
    - run_council() disabled returns graceful message
    - run_council_stream() yields SSE events
    - run_council_stream() disabled yields disabled result
    - _build_config() model override logic
    - _build_response_dict() field mapping

Run from services/chatbot/:
    python -m pytest tests/test_agentic_entrypoint.py -v
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agentic.contracts import (
    CouncilResult,
    CouncilTrace,
    FinalAnswer,
    FinalDecision,
    RunStatus,
)
from core.agentic.entrypoint import (
    _build_config,
    _build_pre_context,
    _build_response_dict,
    _disabled_response,
    _sse,
    is_council_enabled,
    run_council,
    run_council_stream,
)


# ── Helpers ────────────────────────────────────────────────────────────

def _mock_council_result(
    content: str = "Final answer",
    score: int = 8,
    approved: bool = True,
) -> CouncilResult:
    return CouncilResult(
        answer=FinalAnswer(content=content, confidence=0.85, key_points=["Point 1"]),
        trace=CouncilTrace(
            run_id="test-run-123",
            rounds=1,
            agents_used=["planner", "researcher", "synthesizer", "critic"],
            total_llm_calls=4,
            total_tokens=1200,
            elapsed_seconds=3.2,
        ),
        decision=FinalDecision(
            approved=approved,
            iterations_used=1,
            iterations_max=2,
            final_quality_score=score,
            exit_reason="approved" if approved else "budget_exhausted",
        ),
        status=RunStatus.completed,
    )


# ═══════════════════════════════════════════════════════════════════════
# Feature flag
# ═══════════════════════════════════════════════════════════════════════

class TestFeatureFlag:
    def test_default_is_disabled(self):
        with patch.dict(os.environ, {}, clear=False):
            # The module-level constant is already evaluated, so test the function
            # by patching the constant
            with patch("core.agentic.entrypoint.AGENTIC_V1_ENABLED", False):
                assert is_council_enabled() is False

    def test_enabled_when_true(self):
        with patch("core.agentic.entrypoint.AGENTIC_V1_ENABLED", True):
            assert is_council_enabled() is True


# ═══════════════════════════════════════════════════════════════════════
# _disabled_response
# ═══════════════════════════════════════════════════════════════════════

class TestDisabledResponse:
    def test_contains_message(self):
        r = _disabled_response("casual", None)
        assert "not enabled" in r["response"]
        assert r["model"] == "council"
        assert r["deep_thinking"] is False
        assert r["agent_run_id"] is None

    def test_passes_through_citations(self):
        cites = [{"url": "http://example.com", "title": "Test"}]
        r = _disabled_response("knowledge", cites)
        assert r["citations"] == cites
        assert r["context"] == "knowledge"


# ═══════════════════════════════════════════════════════════════════════
# _build_config
# ═══════════════════════════════════════════════════════════════════════

class TestBuildConfig:
    def test_default_config(self):
        cfg = _build_config(
            max_agent_iterations=2,
            preferred_planner_model=None,
            preferred_researcher_model=None,
            preferred_critic_model=None,
            preferred_synthesizer_model=None,
        )
        assert cfg.max_rounds == 2
        # Defaults come from ROLE_FALLBACK_CHAINS[0]
        assert cfg.planner_model  # not empty
        assert cfg.researcher_model

    def test_override_models(self):
        cfg = _build_config(
            max_agent_iterations=3,
            preferred_planner_model="gemini-2.5-pro",
            preferred_researcher_model="grok-3",
            preferred_critic_model="deepseek-r1",
            preferred_synthesizer_model="qwen-plus",
        )
        assert cfg.max_rounds == 3
        assert cfg.planner_model == "gemini-2.5-pro"
        assert cfg.researcher_model == "grok-3"
        assert cfg.critic_model == "deepseek-r1"
        assert cfg.synthesizer_model == "qwen-plus"


# ═══════════════════════════════════════════════════════════════════════
# _build_pre_context
# ═══════════════════════════════════════════════════════════════════════

class TestBuildPreContext:
    def test_basic(self):
        pre = _build_pre_context(
            original_message="Hello",
            augmented_message="Hello + context",
            rag_chunks=None,
            rag_citations=None,
            mcp_context="",
            language="en",
            context_type="casual",
            custom_prompt="",
        )
        assert pre.original_message == "Hello"
        assert pre.augmented_message == "Hello + context"
        assert pre.rag_chunks == []
        assert pre.language == "en"

    def test_with_rag_data(self):
        chunks = [{"text": "chunk1", "score": 0.9}]
        cites = [{"url": "http://example.com"}]
        pre = _build_pre_context(
            original_message="Q",
            augmented_message="Q+",
            rag_chunks=chunks,
            rag_citations=cites,
            mcp_context="file content",
            language="vi",
            context_type="knowledge",
            custom_prompt="Be precise",
        )
        assert len(pre.rag_chunks) == 1
        assert len(pre.rag_citations) == 1
        assert pre.mcp_context == "file content"
        assert pre.custom_prompt == "Be precise"


# ═══════════════════════════════════════════════════════════════════════
# _build_response_dict
# ═══════════════════════════════════════════════════════════════════════

class TestBuildResponseDict:
    def test_contains_required_fields(self):
        result = _mock_council_result()
        d = _build_response_dict(result, "casual", None)

        assert d["response"] == "Final answer"
        assert d["model"] == "council"
        assert d["context"] == "casual"
        assert d["deep_thinking"] is True
        assert d["agent_run_id"] == "test-run-123"
        assert d["agent_trace_summary"]["rounds"] == 1

    def test_thinking_process_populated(self):
        result = _mock_council_result()
        d = _build_response_dict(result, "casual", None)

        assert "1 round" in d["thinking_process"]
        assert "4 LLM calls" in d["thinking_process"]
        assert "approved" in d["thinking_process"]

    def test_warnings_included(self):
        result = _mock_council_result(approved=False)
        result.decision.warnings = ["[high] Data gap"]
        d = _build_response_dict(result, "casual", None)

        assert "Data gap" in d["thinking_process"]


# ═══════════════════════════════════════════════════════════════════════
# _sse helper
# ═══════════════════════════════════════════════════════════════════════

class TestSSEHelper:
    def test_dict_serialization(self):
        s = _sse("test_event", {"key": "value"})
        assert s.startswith("event: test_event\n")
        assert '"key": "value"' in s
        assert s.endswith("\n\n")

    def test_string_passthrough(self):
        s = _sse("raw", "hello world")
        assert "data: hello world\n\n" in s

    def test_unicode_preserved(self):
        s = _sse("event", {"text": "xin chào"})
        assert "xin chào" in s  # ensure_ascii=False


# ═══════════════════════════════════════════════════════════════════════
# run_council (non-streaming)
# ═══════════════════════════════════════════════════════════════════════

class TestRunCouncil:
    @pytest.mark.asyncio
    async def test_disabled_returns_graceful_dict(self):
        with patch("core.agentic.entrypoint.AGENTIC_V1_ENABLED", False):
            result = await run_council(
                original_message="Test",
                augmented_message="Test+",
            )
        assert "not enabled" in result["response"]
        assert result["agent_run_id"] is None

    @pytest.mark.asyncio
    async def test_enabled_runs_orchestrator(self):
        mock_result = _mock_council_result()

        with patch("core.agentic.entrypoint.AGENTIC_V1_ENABLED", True), \
             patch("core.agentic.entrypoint.CouncilOrchestrator") as MockOrch:
            MockOrch.return_value.run = AsyncMock(return_value=mock_result)

            result = await run_council(
                original_message="What is AI?",
                augmented_message="What is AI? + context",
                language="en",
            )

        assert result["response"] == "Final answer"
        assert result["model"] == "council"
        assert result["agent_run_id"] == "test-run-123"
        MockOrch.return_value.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_rag_citations_through(self):
        mock_result = _mock_council_result()
        cites = [{"url": "http://example.com"}]

        with patch("core.agentic.entrypoint.AGENTIC_V1_ENABLED", True), \
             patch("core.agentic.entrypoint.CouncilOrchestrator") as MockOrch:
            MockOrch.return_value.run = AsyncMock(return_value=mock_result)

            result = await run_council(
                original_message="Q",
                augmented_message="Q+",
                rag_citations=cites,
            )

        assert result["citations"] == cites


# ═══════════════════════════════════════════════════════════════════════
# run_council_stream
# ═══════════════════════════════════════════════════════════════════════

class TestRunCouncilStream:
    @pytest.mark.asyncio
    async def test_disabled_yields_single_event(self):
        with patch("core.agentic.entrypoint.AGENTIC_V1_ENABLED", False):
            events = []
            async for chunk in run_council_stream(
                original_message="Test",
                augmented_message="Test+",
            ):
                events.append(chunk)

        assert len(events) == 1
        assert "council_result" in events[0]
        assert "not enabled" in events[0]

    @pytest.mark.asyncio
    async def test_enabled_yields_events_and_result(self):
        mock_result = _mock_council_result()

        with patch("core.agentic.entrypoint.AGENTIC_V1_ENABLED", True), \
             patch("core.agentic.entrypoint.CouncilOrchestrator") as MockOrch:
            MockOrch.return_value.run = AsyncMock(return_value=mock_result)

            events = []
            async for chunk in run_council_stream(
                original_message="What is AI?",
                augmented_message="What is AI? + context",
            ):
                events.append(chunk)

        # Should have at least the council_result event
        assert any("council_result" in e for e in events)
        # The final event should contain the answer
        result_events = [e for e in events if "council_result" in e]
        assert len(result_events) >= 1
