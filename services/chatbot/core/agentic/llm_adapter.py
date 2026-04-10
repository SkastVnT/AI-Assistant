"""
Agentic Council — LLM adapter
===============================
Thin bridge between the new agentic workers and the existing
``ModelRegistry`` / handler stack in ``core.chatbot_v2``.

This adapter:
  • Imports ``ModelRegistry`` lazily (only when ``call()`` is invoked).
  • Builds a ``ChatContext`` from plain parameters.
  • Returns a normalized ``LLMCallResult`` usable by ``BaseAgent``.
  • Never touches MongoDB, session state, or conversation history.
  • Respects the ``model_resolver`` fallback policy.

Usage inside an agent::

    adapter = LLMAdapter.from_registry()
    result = adapter.call(
        model="grok",
        message="What is X?",
        system_prompt="You are ...",
    )
    # result.content, result.tokens, result.elapsed_ms
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable

from core.agentic.agents.base import LLMCallResult

logger = logging.getLogger(__name__)


class LLMAdapter:
    """Lightweight bridge to the existing model handler stack.

    Parameters
    ----------
    registry:
        An instance of ``core.chatbot_v2.ModelRegistry`` (or any object
        that implements ``.get_handler(name)``, ``.get_config(name)``,
        and ``.is_available(name)``).
    """

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    # ── Factory ────────────────────────────────────────────────────

    @classmethod
    def from_registry(cls) -> LLMAdapter:
        """Create an adapter using the global ``ModelRegistry`` singleton.

        Import is deferred so the module can be loaded without API keys
        during testing.
        """
        from core.chatbot_v2 import get_model_registry

        return cls(get_model_registry())

    # ── Availability check (for model_resolver) ───────────────────

    def is_available(self, model: str) -> bool:
        """Return ``True`` if *model* has a configured handler."""
        return self._registry.is_available(model)

    # ── Core call ──────────────────────────────────────────────────

    def call(
        self,
        model: str,
        *,
        message: str,
        system_prompt: str = "",
        context_type: str = "casual",
        deep_thinking: bool = False,
        language: str = "vi",
    ) -> LLMCallResult:
        """Call an LLM model through the existing handler stack.

        This is a **synchronous** call (matching the existing handler
        contract).  The orchestrator can wrap it in
        ``asyncio.to_thread()`` if needed.

        Returns
        -------
        LLMCallResult
            Always returned — never raises for recoverable errors.
        """
        start = time.monotonic()

        handler = self._registry.get_handler(model)
        if handler is None:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error("[LLMAdapter] No handler for model=%s", model)
            return LLMCallResult(
                content="",
                tokens=0,
                elapsed_ms=elapsed_ms,
                model=model,
            )

        try:
            # Build a ChatContext — import here to keep module-level clean
            from core.base_chat import ChatContext
            from core.config import get_system_prompts

            ctx = ChatContext(
                message=message,
                context=context_type,
                deep_thinking=deep_thinking,
                language=language,
                custom_prompt=system_prompt,
                # No history / memories / images — agents are stateless
                history=[],
                memories=None,
                conversation_history=[],
            )

            response = handler.chat(ctx, get_system_prompts, stream=False)

            elapsed_ms = int((time.monotonic() - start) * 1000)

            # The handler returns ChatResponse (dataclass with .content, .success, .error)
            if hasattr(response, "success") and not response.success:
                logger.warning(
                    "[LLMAdapter] model=%s returned error: %s",
                    model, getattr(response, "error", "unknown"),
                )
                return LLMCallResult(
                    content="",
                    tokens=0,
                    elapsed_ms=elapsed_ms,
                    model=model,
                )

            content = getattr(response, "content", "") or ""

            # Rough token estimate (the existing stack doesn't expose usage)
            tokens = max(1, len(content) // 4)

            return LLMCallResult(
                content=content,
                tokens=tokens,
                elapsed_ms=elapsed_ms,
                model=model,
            )

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error("[LLMAdapter] model=%s call failed: %s", model, exc)
            return LLMCallResult(
                content="",
                tokens=0,
                elapsed_ms=elapsed_ms,
                model=model,
            )
