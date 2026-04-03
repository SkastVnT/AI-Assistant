"""
Agentic Council — Model resolver
==================================
Maps agent roles to available LLM models using a priority-ordered
fallback policy.  Respects ``preferred_*_model`` overrides from the
API contract and gracefully degrades when models are unavailable.

This module is **pure logic** — it does not import ModelRegistry at
module level, so it can be tested without API keys or network access.
"""
from __future__ import annotations

import logging
from typing import Callable, Sequence

from core.agentic.contracts import AgentRole

logger = logging.getLogger(__name__)


# ── Role → model fallback chains ──────────────────────────────────────
#
# Each chain is tried left-to-right; the first available model wins.
# These reflect the requirements:
#   planner:      openai → deepseek → grok
#   researcher:   gemini → grok → openai
#   critic:       grok → deepseek → openai
#   synthesizer:  stepfun → step-flash → openai → grok

ROLE_FALLBACK_CHAINS: dict[AgentRole, list[str]] = {
    AgentRole.planner: ["openai", "deepseek", "grok", "gemini"],
    AgentRole.researcher: ["gemini", "grok", "openai", "deepseek"],
    AgentRole.critic: ["grok", "deepseek", "openai", "gemini"],
    AgentRole.synthesizer: ["stepfun", "step-flash", "openai", "grok", "gemini"],
}

# Exhaustive last-resort chain if the role-specific one is empty
_GLOBAL_FALLBACK: list[str] = [
    "grok", "openai", "deepseek", "gemini", "step-flash", "stepfun", "qwen",
]


def resolve_model(
    role: AgentRole,
    *,
    preferred: str | None = None,
    is_available: Callable[[str], bool] | None = None,
) -> str:
    """Pick the best available model for *role*.

    Resolution order:
      1. ``preferred`` (client override) — used if available.
      2. Role-specific fallback chain (``ROLE_FALLBACK_CHAINS``).
      3. Global fallback chain.
      4. Literal ``"grok"`` as absolute last resort.

    Parameters
    ----------
    role:
        The agent role requesting a model.
    preferred:
        Optional client-specified model name (from ``preferred_*_model``
        fields on ``ChatRequest``).  If set and available, it wins.
    is_available:
        Callable that returns ``True`` when a model name is registered
        and has a valid API key.  When *None* (unit-test mode) every
        model is assumed available.
    """
    check = is_available or _always_available

    # 1. Client override
    if preferred and check(preferred):
        logger.debug("[resolve] role=%s → preferred=%s (override)", role.value, preferred)
        return preferred
    if preferred:
        logger.info(
            "[resolve] role=%s — preferred=%s not available, falling back",
            role.value, preferred,
        )

    # 2. Role-specific chain
    chain = ROLE_FALLBACK_CHAINS.get(role, [])
    for model in chain:
        if check(model):
            logger.debug("[resolve] role=%s → %s (chain)", role.value, model)
            return model

    # 3. Global fallback
    for model in _GLOBAL_FALLBACK:
        if check(model):
            logger.warning("[resolve] role=%s → %s (global fallback)", role.value, model)
            return model

    # 4. Absolute last resort
    logger.error("[resolve] role=%s — no model available, returning 'grok'", role.value)
    return "grok"


def resolve_all_roles(
    *,
    preferred_planner: str | None = None,
    preferred_researcher: str | None = None,
    preferred_critic: str | None = None,
    preferred_synthesizer: str | None = None,
    is_available: Callable[[str], bool] | None = None,
) -> dict[AgentRole, str]:
    """Resolve models for all four roles in one call.

    Convenience wrapper used by the orchestrator during init.
    """
    return {
        AgentRole.planner: resolve_model(
            AgentRole.planner, preferred=preferred_planner, is_available=is_available,
        ),
        AgentRole.researcher: resolve_model(
            AgentRole.researcher, preferred=preferred_researcher, is_available=is_available,
        ),
        AgentRole.critic: resolve_model(
            AgentRole.critic, preferred=preferred_critic, is_available=is_available,
        ),
        AgentRole.synthesizer: resolve_model(
            AgentRole.synthesizer, preferred=preferred_synthesizer, is_available=is_available,
        ),
    }


def _always_available(model: str) -> bool:
    """Default availability check — always returns True."""
    return True
