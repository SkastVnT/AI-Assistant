"""
Tests for model_resolver and llm_adapter integration.

Covers:
  • resolve_model — preferred override, role-specific chain, global fallback
  • resolve_all_roles — convenience wrapper
  • DEFAULT_AGENT_MODELS — derived from resolver chains
  • CouncilConfig — defaults match resolver chains
  • LLMAdapter — call routing, missing handler, error handling
  • BaseAgent._call_llm — adapter injection and lazy creation
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agentic.agents.base import BaseAgent, LLMCallResult
from core.agentic.config import CouncilConfig, DEFAULT_AGENT_MODELS
from core.agentic.contracts import AgentRole
from core.agentic.llm_adapter import LLMAdapter
from core.agentic.model_resolver import (
    ROLE_FALLBACK_CHAINS,
    _GLOBAL_FALLBACK,
    resolve_all_roles,
    resolve_model,
)


# ═══════════════════════════════════════════════════════════════════════
# model_resolver tests
# ═══════════════════════════════════════════════════════════════════════


class TestResolveModel:
    """Tests for resolve_model()."""

    def test_preferred_override(self):
        """Client override wins when available."""
        result = resolve_model(AgentRole.planner, preferred="qwen")
        assert result == "qwen"

    def test_preferred_unavailable_falls_to_chain(self):
        """When preferred is unavailable, fall to role chain."""
        result = resolve_model(
            AgentRole.planner,
            preferred="nonexistent",
            is_available=lambda m: m in {"deepseek", "grok"},
        )
        # planner chain: openai → deepseek → grok → gemini
        # openai unavailable, deepseek available → deepseek
        assert result == "deepseek"

    def test_role_chain_first_available(self):
        """Role chain picks the first available model."""
        result = resolve_model(
            AgentRole.researcher,
            is_available=lambda m: m in {"grok", "openai"},
        )
        # researcher chain: gemini → grok → openai → deepseek
        # gemini unavailable, grok available → grok
        assert result == "grok"

    def test_role_chain_fully_unavailable_falls_to_global(self):
        """If entire role chain is unavailable, try global fallback."""
        # Synthesizer chain: stepfun, step-flash, openai, grok, gemini
        available = {"qwen"}
        result = resolve_model(
            AgentRole.synthesizer,
            is_available=lambda m: m in available,
        )
        assert result == "qwen"  # from _GLOBAL_FALLBACK

    def test_all_unavailable_returns_grok(self):
        """Absolute last resort returns 'grok'."""
        result = resolve_model(
            AgentRole.critic,
            is_available=lambda _: False,
        )
        assert result == "grok"

    def test_no_availability_check_assumes_all_available(self):
        """Without is_available, first in chain wins."""
        result = resolve_model(AgentRole.planner)
        assert result == ROLE_FALLBACK_CHAINS[AgentRole.planner][0]

    def test_all_four_roles_have_chains(self):
        """Every AgentRole has a non-empty fallback chain."""
        for role in AgentRole:
            assert role in ROLE_FALLBACK_CHAINS
            assert len(ROLE_FALLBACK_CHAINS[role]) >= 2


class TestResolveAllRoles:
    """Tests for resolve_all_roles()."""

    def test_returns_all_four_roles(self):
        result = resolve_all_roles()
        assert set(result.keys()) == {r for r in AgentRole}

    def test_preferred_overrides_applied(self):
        result = resolve_all_roles(preferred_planner="qwen", preferred_critic="gemini")
        assert result[AgentRole.planner] == "qwen"
        assert result[AgentRole.critic] == "gemini"

    def test_availability_propagated(self):
        available = {"deepseek", "openai"}
        result = resolve_all_roles(is_available=lambda m: m in available)
        # All results should be from the available set
        for role, model in result.items():
            assert model in available, f"{role.value} got {model}, not in {available}"


# ═══════════════════════════════════════════════════════════════════════
# Config defaults tests
# ═══════════════════════════════════════════════════════════════════════


class TestConfigDefaults:
    """Tests that CouncilConfig defaults align with the resolver."""

    def test_default_models_derived_from_chains(self):
        """DEFAULT_AGENT_MODELS should match the first entry in each chain."""
        for role, chain in ROLE_FALLBACK_CHAINS.items():
            assert DEFAULT_AGENT_MODELS[role] == chain[0]

    def test_council_config_defaults(self):
        """CouncilConfig fields should use resolver-derived defaults."""
        cfg = CouncilConfig()
        assert cfg.planner_model == ROLE_FALLBACK_CHAINS[AgentRole.planner][0]
        assert cfg.researcher_model == ROLE_FALLBACK_CHAINS[AgentRole.researcher][0]
        assert cfg.critic_model == ROLE_FALLBACK_CHAINS[AgentRole.critic][0]
        assert cfg.synthesizer_model == ROLE_FALLBACK_CHAINS[AgentRole.synthesizer][0]

    def test_model_for_role(self):
        cfg = CouncilConfig()
        assert cfg.model_for_role(AgentRole.planner) == cfg.planner_model
        assert cfg.model_for_role(AgentRole.researcher) == cfg.researcher_model
        assert cfg.model_for_role(AgentRole.critic) == cfg.critic_model
        assert cfg.model_for_role(AgentRole.synthesizer) == cfg.synthesizer_model

    def test_model_for_role_override(self):
        cfg = CouncilConfig(planner_model="deepseek")
        assert cfg.model_for_role(AgentRole.planner) == "deepseek"


# ═══════════════════════════════════════════════════════════════════════
# LLMAdapter tests
# ═══════════════════════════════════════════════════════════════════════


def _make_mock_registry(*, available=None, response_content="Hello"):
    """Build a mock ModelRegistry with configurable behavior."""
    registry = MagicMock()

    available_set = available or {"openai", "grok", "deepseek", "gemini"}
    registry.is_available.side_effect = lambda m: m in available_set

    # Mock handler + ChatResponse
    mock_response = MagicMock()
    mock_response.success = True
    mock_response.content = response_content

    mock_handler = MagicMock()
    mock_handler.chat.return_value = mock_response

    registry.get_handler.return_value = mock_handler

    return registry, mock_handler, mock_response


class TestLLMAdapter:
    """Tests for LLMAdapter."""

    def test_call_success(self):
        registry, handler, _ = _make_mock_registry(response_content="Test answer")
        adapter = LLMAdapter(registry)

        result = adapter.call(
            "grok",
            message="Hello",
            system_prompt="Be helpful",
        )

        assert isinstance(result, LLMCallResult)
        assert result.content == "Test answer"
        assert result.model == "grok"
        assert result.tokens > 0
        assert result.elapsed_ms >= 0

        # Verify handler was called
        registry.get_handler.assert_called_once_with("grok")
        handler.chat.assert_called_once()

    def test_call_no_handler(self):
        registry = MagicMock()
        registry.get_handler.return_value = None
        adapter = LLMAdapter(registry)

        result = adapter.call("missing_model", message="Hello")

        assert result.content == ""
        assert result.model == "missing_model"

    def test_call_handler_error(self):
        registry = MagicMock()
        mock_handler = MagicMock()
        mock_handler.chat.side_effect = RuntimeError("API down")
        registry.get_handler.return_value = mock_handler
        adapter = LLMAdapter(registry)

        result = adapter.call("grok", message="Hello")

        assert result.content == ""
        assert result.model == "grok"

    def test_call_unsuccessful_response(self):
        registry, handler, mock_response = _make_mock_registry()
        mock_response.success = False
        mock_response.error = "rate limited"
        adapter = LLMAdapter(registry)

        result = adapter.call("grok", message="Hello")

        assert result.content == ""

    def test_is_available(self):
        registry, _, _ = _make_mock_registry(available={"grok", "openai"})
        adapter = LLMAdapter(registry)

        assert adapter.is_available("grok") is True
        assert adapter.is_available("openai") is True
        assert adapter.is_available("nonexistent") is False


# ═══════════════════════════════════════════════════════════════════════
# BaseAgent._call_llm integration tests
# ═══════════════════════════════════════════════════════════════════════

class _StubAgent(BaseAgent):
    """Minimal concrete agent for testing _call_llm."""
    role = AgentRole.planner

    async def execute(self, state):
        pass


class TestBaseAgentCallLLM:
    """Tests for the adapter wiring in BaseAgent._call_llm."""

    @pytest.mark.asyncio
    async def test_injected_adapter_is_used(self):
        """When an adapter is injected, _call_llm uses it directly."""
        registry, _, _ = _make_mock_registry(response_content='{"plan": "ok"}')
        adapter = LLMAdapter(registry)

        agent = _StubAgent(CouncilConfig(), llm_adapter=adapter)
        result = await agent._call_llm(message="test")

        assert result.content == '{"plan": "ok"}'
        assert isinstance(result, LLMCallResult)

    @pytest.mark.asyncio
    async def test_adapter_not_injected_lazy_creation_fails_gracefully(self):
        """When no adapter is injected and registry import fails, returns empty."""
        agent = _StubAgent(CouncilConfig())
        # Patch from_registry to raise
        with patch(
            "core.agentic.llm_adapter.LLMAdapter.from_registry",
            side_effect=ImportError("no keys"),
        ):
            result = await agent._call_llm(message="test")
            assert result.content == ""

    @pytest.mark.asyncio
    async def test_adapter_cached_after_first_call(self):
        """The adapter is created once and reused across calls."""
        registry, _, _ = _make_mock_registry(response_content="cached")
        adapter = LLMAdapter(registry)

        agent = _StubAgent(CouncilConfig(), llm_adapter=adapter)
        r1 = await agent._call_llm(message="first")
        r2 = await agent._call_llm(message="second")

        assert r1.content == "cached"
        assert r2.content == "cached"
        assert agent._llm_adapter is adapter


# ═══════════════════════════════════════════════════════════════════════
# End-to-end: resolver → adapter → agent
# ═══════════════════════════════════════════════════════════════════════


class TestEndToEnd:
    """Verify the full chain: resolver picks model → adapter calls it."""

    def test_resolver_to_adapter(self):
        available = {"grok", "deepseek"}
        registry, handler, _ = _make_mock_registry(
            available=available, response_content="e2e answer",
        )
        adapter = LLMAdapter(registry)

        # Resolver picks the best model
        model = resolve_model(
            AgentRole.planner,
            is_available=adapter.is_available,
        )
        # planner chain: openai → deepseek → grok → gemini
        # available: grok, deepseek → deepseek wins
        assert model == "deepseek"

        result = adapter.call(model, message="e2e test")
        assert result.content == "e2e answer"
        registry.get_handler.assert_called_with("deepseek")
