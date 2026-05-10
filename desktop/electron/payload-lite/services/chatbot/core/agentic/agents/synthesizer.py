"""
Agentic Council — Synthesizer agent
=====================================
Produces the final user-facing answer from the accumulated evidence
and critique.  This is always the *last* agent to run.
"""
from __future__ import annotations

import logging
from typing import Any

from core.agentic.agents.base import BaseAgent
from core.agentic.contracts import AgentRole, FinalAnswer, SynthesizerOutput
from core.agentic.prompts import get_system_prompt
from core.agentic.state import AgentRunState

logger = logging.getLogger(__name__)


class SynthesizerAgent(BaseAgent):
    """Compose the final answer from all prior agent outputs.

    Public API:
      ``synthesize(state)`` — build and set ``state.synthesizer_output``.
      ``execute(state)`` — alias for ``synthesize(state)``.
    """

    role = AgentRole.synthesizer

    # ── Public methods ─────────────────────────────────────────────

    async def execute(self, state: AgentRunState) -> None:
        """Alias — delegates to :meth:`synthesize`."""
        await self.synthesize(state)

    async def synthesize(self, state: AgentRunState) -> None:
        """Synthesize the final answer and set ``state.synthesizer_output``."""
        pre = state.pre_context
        lang_code = pre.language if pre else "vi"
        language = self._language_name(lang_code)

        system_prompt = get_system_prompt("synthesizer", language=language)
        llm_input = self._build_llm_input(state)

        result = await self._call_llm(
            message=llm_input,
            system_prompt=system_prompt,
            deep_thinking=True,
            language=lang_code,
        )

        output = self._parse_output(result.content)
        state.synthesizer_output = output

        state.record_step(
            self.role,
            input_summary=self._truncate(llm_input),
            output_summary=self._truncate(
                f"confidence={output.answer.confidence:.2f} "
                f"points={len(output.answer.key_points)} "
                f"citations={len(output.answer.citations)}"
            ),
            tokens=result.tokens,
            elapsed_ms=result.elapsed_ms,
        )
        logger.info(
            "[Synthesizer] run_id=%s | model=%s | chars=%d confidence=%.2f",
            state.run_id,
            self.model_name,
            len(output.answer.content),
            output.answer.confidence,
        )

    # ── Input construction ─────────────────────────────────────────

    def _build_llm_input(self, state: AgentRunState) -> str:
        """Compose the full context for synthesis."""
        parts: list[str] = []

        pre = state.pre_context
        if pre is not None:
            parts.append(f"Original question:\n{pre.original_message}")

        for i, plan in enumerate(state.planner_outputs):
            parts.append(f"\n--- Plan (round {i + 1}): {plan.approach} ---")
            for j, t in enumerate(plan.tasks):
                parts.append(f"  Task {j}: {t.question}")

        for i, research in enumerate(state.researcher_outputs):
            parts.append(f"\n--- Research (round {i + 1}) ---\n{research.summary}")
            for j, ev in enumerate(research.evidence):
                cite = f" [{ev.url}]" if ev.url else ""
                parts.append(f"  [{ev.source}] {ev.content[:300]}{cite}")

        for i, critique in enumerate(state.critic_outputs):
            parts.append(
                f"\n--- Critique (round {i + 1}) — "
                f"score={critique.quality_score}/10, verdict={critique.verdict} ---"
            )
            for issue in critique.issues:
                parts.append(f"  [{issue.severity}] {issue.description}")
                if issue.suggestion:
                    parts.append(f"    → {issue.suggestion}")

        return "\n\n".join(parts) or "(no context)"

    # ── Output parsing ─────────────────────────────────────────────

    def _parse_output(self, raw: str) -> SynthesizerOutput:
        """Parse LLM JSON into ``SynthesizerOutput``.

        Falls back to wrapping raw text as the content on parse failure.
        """
        if not raw.strip():
            return self._fallback_output("(empty LLM response)")

        try:
            data = self._parse_json(raw)
        except ValueError as exc:
            logger.warning("[Synthesizer] JSON extraction failed: %s — using raw text", exc)
            return self._fallback_output(raw)

        # Normalise content
        content = str(data.get("content", raw))

        # Normalise confidence
        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5

        # Normalise key_points
        raw_points = data.get("key_points", [])
        key_points = [str(p) for p in raw_points[:6]] if isinstance(raw_points, list) else []

        # Normalise citations
        raw_citations = data.get("citations", [])
        citations: list[dict[str, Any]] = []
        if isinstance(raw_citations, list):
            for c in raw_citations[:10]:
                if isinstance(c, dict):
                    citations.append({
                        "source": str(c.get("source", "llm")),
                        "url": c.get("url"),
                        "title": str(c.get("title", "")),
                    })

        return SynthesizerOutput(
            answer=FinalAnswer(
                content=content,
                confidence=confidence,
                key_points=key_points,
                citations=citations,
            )
        )

    @staticmethod
    def _fallback_output(raw: str) -> SynthesizerOutput:
        """Return a safe fallback — wraps raw text as the final answer."""
        return SynthesizerOutput(
            answer=FinalAnswer(
                content=raw or "(no answer generated)",
                confidence=0.0,
                key_points=[],
                citations=[],
            )
        )
