"""
Agentic Council — Base agent
=============================
Abstract base class for all council agents.

Each concrete agent (Planner, Researcher, Critic, Synthesizer) inherits
from ``BaseAgent`` and implements :meth:`execute`.  The base class owns:

  • The LLM-calling seam (``_call_llm``).
  • Robust JSON extraction from LLM responses (``_parse_json``).
  • Pydantic model validation (``_validate``).

Integration point with existing code:
  • Will use ``core.chatbot_v2.ModelRegistry`` for LLM calls (Phase 2).
"""
from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel, ValidationError

from core.agentic.config import CouncilConfig
from core.agentic.contracts import AgentRole
from core.agentic.state import AgentRunState

if TYPE_CHECKING:
    from core.agentic.llm_adapter import LLMAdapter

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """Abstract base for every council agent.

    Subclasses must set ``role`` and implement :meth:`execute`.

    Parameters
    ----------
    config:
        Council configuration (max rounds, model overrides, etc.).
    llm_adapter:
        Optional ``LLMAdapter`` instance.  When *None* (production),
        a default adapter is created lazily from ``ModelRegistry`` on
        the first ``_call_llm`` call.  Pass an explicit adapter in
        tests to avoid needing real API keys.
    """

    role: AgentRole

    def __init__(
        self,
        config: CouncilConfig,
        llm_adapter: LLMAdapter | None = None,
    ) -> None:
        self.config = config
        self._llm_adapter = llm_adapter

    # ── Public API ─────────────────────────────────────────────────

    @abstractmethod
    async def execute(self, state: AgentRunState) -> None:
        """Run this agent's logic and mutate *state* in-place.

        Contract:
          1. Read whatever prior state you need.
          2. Build messages and call the LLM via :meth:`_call_llm`.
          3. Parse the JSON response via :meth:`_parse_json`.
          4. Validate into a Pydantic model via :meth:`_validate`.
          5. Append output + call ``state.record_step(…)``.

        Must not raise on recoverable errors — catch and return a
        degraded output so the pipeline continues.
        """
        ...

    # ── LLM abstraction seam ──────────────────────────────────────

    @property
    def model_name(self) -> str:
        """LLM model key for this agent (from ``CouncilConfig``)."""
        return self.config.model_for_role(self.role)

    async def _call_llm(
        self,
        *,
        message: str,
        system_prompt: str = "",
        context_type: str = "casual",
        deep_thinking: bool = False,
        language: str = "vi",
    ) -> LLMCallResult:
        """Call the LLM through the adapter and return raw text + metadata.

        On first call (when no adapter was injected), creates one from
        the global ``ModelRegistry``.  If the registry is unavailable
        (e.g. missing API keys in unit tests), returns an empty result
        rather than raising.
        """
        if self._llm_adapter is None:
            try:
                from core.agentic.llm_adapter import LLMAdapter as _Adapter
                self._llm_adapter = _Adapter.from_registry()
            except Exception as exc:
                logger.error("[%s] Cannot create LLMAdapter: %s", self.role.value, exc)
                return LLMCallResult(
                    content="",
                    tokens=0,
                    elapsed_ms=0,
                    model=self.model_name,
                )

        result = self._llm_adapter.call(
            self.model_name,
            message=message,
            system_prompt=system_prompt,
            context_type=context_type,
            deep_thinking=deep_thinking,
            language=language,
        )

        logger.debug(
            "[%s] _call_llm model=%s tokens=%d elapsed=%dms content_len=%d",
            self.role.value,
            result.model,
            result.tokens,
            result.elapsed_ms,
            len(result.content),
        )
        return result

    # ── JSON extraction ───────────────────────────────────────────

    # Matches ```json ... ``` or ``` ... ``` fenced blocks
    _JSON_FENCE_RE = re.compile(
        r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL
    )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Extract a JSON object from an LLM response string.

        Handles three common LLM output patterns:
          1. Clean JSON (the prompt asks for no fences).
          2. Fenced ``json`` code blocks.
          3. JSON embedded in surrounding prose.

        Raises ``ValueError`` if no valid JSON object can be found.
        """
        text = raw.strip()
        if not text:
            raise ValueError("Empty LLM response")

        # 1. Try direct parse
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        # 2. Try fenced code blocks
        for match in BaseAgent._JSON_FENCE_RE.finditer(text):
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

        # 3. Find first { ... last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not extract JSON from LLM response ({len(text)} chars)")

    @staticmethod
    def _validate(data: dict[str, Any], model_cls: type[T]) -> T:
        """Validate a parsed dict against a Pydantic model.

        Raises ``ValidationError`` on schema mismatch.
        """
        return model_cls.model_validate(data)

    # ── Language helper ────────────────────────────────────────────

    @staticmethod
    def _language_name(code: str) -> str:
        """Convert a language code to a display name for prompts."""
        return {
            "vi": "Vietnamese",
            "en": "English",
            "ja": "Japanese",
            "zh": "Chinese",
            "ko": "Korean",
        }.get(code, "English")

    # ── Misc helpers ──────────────────────────────────────────────

    def _truncate(self, text: str, max_len: int = 500) -> str:
        """Truncate *text* for trace summaries."""
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."


class LLMCallResult:
    """Lightweight wrapper around a single LLM call's output."""

    __slots__ = ("content", "tokens", "elapsed_ms", "model")

    def __init__(
        self,
        content: str,
        tokens: int = 0,
        elapsed_ms: int = 0,
        model: str = "",
    ) -> None:
        self.content = content
        self.tokens = tokens
        self.elapsed_ms = elapsed_ms
        self.model = model
