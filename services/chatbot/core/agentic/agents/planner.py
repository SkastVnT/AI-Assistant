"""
Agentic Council — Planner agent
================================
Decomposes the user's question into an ordered set of ``TaskNode`` items
and suggests which tools the Researcher should use for each.

This is always the *first* agent to run in every council round.
"""
from __future__ import annotations

import logging

from core.agentic.agents.base import BaseAgent
from core.agentic.contracts import AgentRole, CriticOutput, PlannerOutput, TaskNode
from core.agentic.prompts import get_system_prompt
from core.agentic.state import AgentRunState

logger = logging.getLogger(__name__)


class PlannerAgent(BaseAgent):
    """Plan the investigation strategy for a user query.

    Public API:
      ``plan(state)`` — build a plan and append to ``state.planner_outputs``.
      ``execute(state)`` — alias for ``plan(state)``.
    """

    role = AgentRole.planner

    # ── Public methods ─────────────────────────────────────────────

    async def execute(self, state: AgentRunState) -> None:
        """Alias — delegates to :meth:`plan`."""
        await self.plan(state)

    async def plan(self, state: AgentRunState) -> None:
        """Build a plan and append it to ``state.planner_outputs``."""
        pre = state.pre_context
        lang_code = pre.language if pre else "vi"
        language = self._language_name(lang_code)

        system_prompt = get_system_prompt("planner", language=language)
        llm_input = self._build_llm_input(state)

        result = await self._call_llm(
            message=llm_input,
            system_prompt=system_prompt,
            language=lang_code,
        )

        output = self._parse_output(result.content)

        state.planner_outputs.append(output)
        state.record_step(
            self.role,
            input_summary=self._truncate(llm_input),
            output_summary=self._truncate(
                f"{output.approach} ({len(output.tasks)} tasks, complexity={output.estimated_complexity})"
            ),
            tokens=result.tokens,
            elapsed_ms=result.elapsed_ms,
        )
        logger.info(
            "[Planner] run_id=%s | round=%d | model=%s | tasks=%d complexity=%d",
            state.run_id,
            state.current_round,
            self.model_name,
            len(output.tasks),
            output.estimated_complexity,
        )

    # ── Input construction ─────────────────────────────────────────

    def _build_llm_input(self, state: AgentRunState) -> str:
        """Compose the user message sent to the LLM."""
        parts: list[str] = []

        pre = state.pre_context
        if pre:
            parts.append(f"User question:\n{pre.augmented_message or pre.original_message}")
            if pre.rag_chunks:
                parts.append(f"\nPre-fetched RAG context ({len(pre.rag_chunks)} chunks available)")
            if pre.web_search_context:
                parts.append(f"\nPre-fetched web context available ({len(pre.web_search_context)} chars)")
            if pre.mcp_context:
                parts.append(f"\nMCP file context available ({len(pre.mcp_context)} chars)")

        # Feed back prior critique so the planner adjusts
        critique = state.latest_critique
        if critique:
            parts.append(f"\n--- Prior Critique (quality={critique.quality_score}/10, verdict={critique.verdict}) ---")
            for issue in critique.issues:
                parts.append(f"  [{issue.severity}] {issue.description} → {issue.suggestion}")

        return "\n\n".join(parts) or "(no input)"

    # ── Output parsing ─────────────────────────────────────────────

    def _parse_output(self, raw: str) -> PlannerOutput:
        """Parse LLM JSON into ``PlannerOutput``.

        Falls back to a single generic task on parse failure.
        """
        if not raw.strip():
            return self._fallback_output("(empty LLM response)")

        try:
            data = self._parse_json(raw)
        except ValueError as exc:
            logger.warning("[Planner] JSON extraction failed: %s", exc)
            return self._fallback_output(raw)

        # Normalise tasks
        raw_tasks = data.get("tasks", [])
        tasks: list[TaskNode] = []
        for i, t in enumerate(raw_tasks[:6]):  # cap at 6
            if isinstance(t, dict):
                try:
                    tasks.append(self._validate(t, TaskNode))
                except Exception:
                    # Salvage just the question text
                    q = t.get("question", f"Task {i + 1}")
                    tasks.append(TaskNode(question=str(q)))

        if not tasks:
            tasks = [TaskNode(question="(auto-generated) Investigate the user's question")]

        return PlannerOutput(
            approach=str(data.get("approach", "(no approach stated)")),
            tasks=tasks,
            estimated_complexity=max(1, min(10, int(data.get("estimated_complexity", 3)))),
        )

    @staticmethod
    def _fallback_output(raw: str) -> PlannerOutput:
        """Return a safe fallback when parsing fails."""
        return PlannerOutput(
            approach="(parse failure — fallback plan)",
            tasks=[TaskNode(question="Investigate the user's question")],
            estimated_complexity=3,
        )
