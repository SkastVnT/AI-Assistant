"""
Agentic Council — Critic agent
================================
Reviews the Planner's strategy and the Researcher's findings, then
produces a quality score and a list of issues.

The Critic's ``verdict`` drives the orchestrator's loop decision:
  • ``"pass"``       → proceed directly to Synthesis.
  • ``"needs_work"`` → run another Planner → Researcher → Critic round.
"""
from __future__ import annotations

import logging

from core.agentic.agents.base import BaseAgent
from core.agentic.contracts import (
    AgentRole,
    CriticOutput,
    CritiqueIssue,
    PlannerOutput,
    ResearcherOutput,
    RetryTarget,
)
from core.agentic.prompts import get_system_prompt
from core.agentic.state import AgentRunState

logger = logging.getLogger(__name__)

_VALID_SEVERITIES = {"low", "medium", "high"}
_VALID_VERDICTS = {"pass", "needs_work"}
_VALID_RETRY_TARGETS = {t.value for t in RetryTarget}


class CriticAgent(BaseAgent):
    """Evaluate quality of the current plan + research.

    Public API:
      ``critique(state)`` — evaluate and append to ``state.critic_outputs``.
      ``execute(state)`` — alias for ``critique(state)``.
    """

    role = AgentRole.critic

    # ── Public methods ─────────────────────────────────────────────

    async def execute(self, state: AgentRunState) -> None:
        """Alias — delegates to :meth:`critique`."""
        await self.critique(state)

    async def critique(self, state: AgentRunState) -> None:
        """Critique the current round and append to ``state.critic_outputs``."""
        plan = state.latest_plan
        research = state.latest_research
        synth = state.synthesizer_output
        pre = state.pre_context
        lang_code = pre.language if pre else "vi"
        language = self._language_name(lang_code)

        system_prompt = get_system_prompt("critic", language=language)
        llm_input = self._build_llm_input(plan, research, pre, synth)

        result = await self._call_llm(
            message=llm_input,
            system_prompt=system_prompt,
            language=lang_code,
        )

        output = self._parse_output(result.content)

        state.critic_outputs.append(output)
        state.record_step(
            self.role,
            input_summary=self._truncate(llm_input),
            output_summary=f"score={output.quality_score} verdict={output.verdict} issues={len(output.issues)}",
            tokens=result.tokens,
            elapsed_ms=result.elapsed_ms,
        )
        logger.info(
            "[Critic] run_id=%s | round=%d | model=%s | quality=%d verdict=%s issues=%d",
            state.run_id,
            state.current_round,
            self.model_name,
            output.quality_score,
            output.verdict,
            len(output.issues),
        )

    # ── Input construction ─────────────────────────────────────────

    def _build_llm_input(
        self,
        plan: PlannerOutput | None,
        research: ResearcherOutput | None,
        pre: object | None,
        synth: object | None = None,
    ) -> str:
        """Compose the user message sent to the LLM."""
        parts: list[str] = []

        if pre is not None and hasattr(pre, "original_message"):
            parts.append(f"Original question:\n{pre.original_message}")

        if plan is not None:
            parts.append(f"\n--- Plan (approach: {plan.approach}) ---")
            for i, t in enumerate(plan.tasks):
                parts.append(f"  Task {i}: {t.question}  [priority={t.priority}]")

        if research is not None:
            parts.append(f"\n--- Research summary ---\n{research.summary}")
            for j, ev in enumerate(research.evidence):
                parts.append(
                    f"  Evidence {j} [{ev.source}] (relevance={ev.relevance:.2f}): "
                    f"{ev.content[:200]}"
                )

        if synth is not None and hasattr(synth, "answer"):
            answer = synth.answer
            parts.append(f"\n--- Draft answer (confidence={answer.confidence:.2f}) ---")
            parts.append(answer.content[:2000])
            if answer.key_points:
                parts.append("  Key points: " + "; ".join(answer.key_points[:5]))

        return "\n\n".join(parts) or "(no input)"

    # ── Output parsing ─────────────────────────────────────────────

    def _parse_output(self, raw: str) -> CriticOutput:
        """Parse LLM JSON into ``CriticOutput``.

        Falls back to a passing score on parse failure so the pipeline
        can still complete (conservative: don't loop forever).
        """
        if not raw.strip():
            return self._fallback_output()

        try:
            data = self._parse_json(raw)
        except ValueError as exc:
            logger.warning("[Critic] JSON extraction failed: %s", exc)
            return self._fallback_output()

        # Normalise quality_score
        try:
            score = max(1, min(10, int(data.get("quality_score", 5))))
        except (TypeError, ValueError):
            score = 5

        # Normalise verdict
        verdict_raw = str(data.get("verdict", "")).lower().strip()
        if verdict_raw not in _VALID_VERDICTS:
            verdict = "needs_work" if score < 7 else "pass"
        else:
            verdict = verdict_raw

        # Normalise issues
        raw_issues = data.get("issues", [])
        issues: list[CritiqueIssue] = []
        for item in raw_issues[:5]:  # cap at 5
            if isinstance(item, dict):
                severity = str(item.get("severity", "medium")).lower()
                if severity not in _VALID_SEVERITIES:
                    severity = "medium"
                issues.append(CritiqueIssue(
                    severity=severity,
                    description=str(item.get("description", "(no description)")),
                    suggestion=str(item.get("suggestion", "")),
                    task_id=item.get("task_id"),
                ))

        # Normalise retry_target
        retry_raw = str(data.get("retry_target", "")).lower().strip()
        if retry_raw in _VALID_RETRY_TARGETS:
            retry_target = RetryTarget(retry_raw)
        else:
            retry_target = self._infer_retry_target(issues)

        # Extract focused feedback
        focused_feedback = str(data.get("focused_feedback", "")).strip()
        if not focused_feedback and issues:
            # Auto-generate from high-severity issues
            focused_feedback = "; ".join(
                i.suggestion or i.description
                for i in issues
                if i.severity in ("high", "medium")
            )[:500]

        return CriticOutput(
            quality_score=score,
            issues=issues,
            verdict=verdict,
            retry_target=retry_target,
            focused_feedback=focused_feedback,
        )

    @staticmethod
    def _infer_retry_target(issues: list[CritiqueIssue]) -> RetryTarget:
        """Infer which stage to retry based on issue descriptions.

        Heuristic:
          - Keywords like 'evidence', 'missing', 'source', 'grounding'
            → researcher
          - Keywords like 'answer', 'format', 'synthesis', 'incomplete'
            → synthesizer
          - Mixed or unclear → both
        """
        research_kw = {"evidence", "missing", "source", "grounding", "data", "search", "fact"}
        synth_kw = {"answer", "format", "synthesis", "incomplete", "clarity", "coherent", "draft"}

        r_hits = 0
        s_hits = 0
        for issue in issues:
            words = set(issue.description.lower().split())
            r_hits += len(words & research_kw)
            s_hits += len(words & synth_kw)

        if r_hits > 0 and s_hits == 0:
            return RetryTarget.researcher
        if s_hits > 0 and r_hits == 0:
            return RetryTarget.synthesizer
        return RetryTarget.both

    @staticmethod
    def _fallback_output() -> CriticOutput:
        """Return a safe fallback — defaults to pass so the pipeline terminates."""
        return CriticOutput(
            quality_score=7,
            issues=[],
            verdict="pass",
        )
