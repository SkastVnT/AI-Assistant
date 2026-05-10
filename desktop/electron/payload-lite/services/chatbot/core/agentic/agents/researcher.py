"""
Agentic Council — Researcher agent
====================================
Executes the plan produced by the Planner, gathering evidence from
pre-fetched context and (future) tool calls.

This is the only agent with tool-calling capability (Phase 2).
"""
from __future__ import annotations

import logging

from core.agentic.agents.base import BaseAgent
from core.agentic.contracts import (
    AgentRole,
    EvidenceItem,
    PlannerOutput,
    ResearcherOutput,
)
from core.agentic.evidence_gathering import (
    SOURCE_DIRECT,
    SOURCE_MCP,
    SOURCE_RAG,
    SOURCE_UPLOADED_FILE,
    gather_all,
)
from core.agentic.prompts import get_system_prompt
from core.agentic.state import AgentRunState, PreContext

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """Gather evidence for the sub-tasks in the Planner's output.

    Public API:
      ``research(state)`` — investigate the plan and append findings.
      ``execute(state)`` — alias for ``research(state)``.
    """

    role = AgentRole.researcher

    # ── Public methods ─────────────────────────────────────────────

    async def execute(self, state: AgentRunState) -> None:
        """Alias — delegates to :meth:`research`."""
        await self.research(state)

    async def research(self, state: AgentRunState) -> None:
        """Research the plan and append results to ``state.researcher_outputs``.

        Pipeline:
          1. Gather structured evidence from pre-fetched context sources.
          2. Feed plan + pre-gathered evidence to the LLM for synthesis.
          3. Merge pre-gathered evidence with any LLM-discovered items.
          4. Append the combined ``ResearcherOutput`` to state.
        """
        plan = state.latest_plan
        if plan is None:
            logger.warning("[Researcher] No plan available — skipping")
            state.researcher_outputs.append(
                ResearcherOutput(summary="No plan to research.")
            )
            return

        pre = state.pre_context
        lang_code = pre.language if pre else "vi"
        language = self._language_name(lang_code)

        # ── Step 1: gather structured evidence from context sources ──
        pre_evidence = self._gather_pre_evidence(pre)
        tools_used: list[str] = self._tools_from_evidence(pre_evidence)

        # ── Step 2: build LLM input with evidence summary ───────────
        system_prompt = get_system_prompt("researcher", language=language)
        llm_input = self._build_llm_input(plan, pre, pre_evidence)

        result = await self._call_llm(
            message=llm_input,
            system_prompt=system_prompt,
            language=lang_code,
        )

        # ── Step 3: merge pre-gathered + LLM-produced evidence ──────
        output = self._parse_output(result.content, tools_used)
        output = self._merge_evidence(output, pre_evidence)

        state.researcher_outputs.append(output)
        state.record_step(
            self.role,
            input_summary=self._truncate(llm_input),
            output_summary=self._truncate(
                f"{len(output.evidence)} items — {output.summary[:120]}"
            ),
            tool_calls=tools_used or None,
            tokens=result.tokens,
            elapsed_ms=result.elapsed_ms,
        )
        logger.info(
            "[Researcher] run_id=%s | round=%d | model=%s | evidence=%d (pre=%d, llm=%d) | tools=%s",
            state.run_id,
            state.current_round,
            self.model_name,
            len(output.evidence),
            len(pre_evidence),
            len(output.evidence) - len(pre_evidence),
            tools_used or "none",
        )

    # ── Evidence pre-gathering ───────────────────────────────────

    @staticmethod
    def _gather_pre_evidence(pre: PreContext | None) -> list[EvidenceItem]:
        """Extract structured evidence from PreContext using gather_all()."""
        if pre is None:
            return []
        return gather_all(
            rag_chunks=pre.rag_chunks,
            rag_citations=pre.rag_citations,
            mcp_context=pre.mcp_context,
            augmented_message=pre.augmented_message,
            original_message=pre.original_message,
        )

    @staticmethod
    def _tools_from_evidence(evidence: list[EvidenceItem]) -> list[str]:
        """Derive a tools_used list from the evidence sources present."""
        source_to_tool = {
            SOURCE_RAG: "rag_query",
            SOURCE_MCP: "mcp_read",
            SOURCE_UPLOADED_FILE: "file_read",
            SOURCE_DIRECT: "user_context",
        }
        seen: set[str] = set()
        tools: list[str] = []
        for item in evidence:
            tool = source_to_tool.get(item.source)
            if tool and tool not in seen:
                seen.add(tool)
                tools.append(tool)
        return tools

    # ── Input construction ─────────────────────────────────────────

    def _build_llm_input(
        self,
        plan: PlannerOutput,
        pre: PreContext | None,
        pre_evidence: list[EvidenceItem] | None = None,
    ) -> str:
        """Compose the user message sent to the LLM.

        When *pre_evidence* is provided the LLM receives a compact
        summary of already-gathered evidence so it can reason about
        gaps and synthesize rather than re-extract.
        """
        parts: list[str] = []

        if pre:
            parts.append(f"User question:\n{pre.original_message}")

        # Include the plan's tasks
        parts.append(f"\nPlan approach: {plan.approach}")
        for i, task in enumerate(plan.tasks):
            tools_hint = ", ".join(task.suggested_tools) if task.suggested_tools else "none"
            parts.append(f"  Task {i}: {task.question}  [tools: {tools_hint}]")

        # Include pre-gathered evidence summary for LLM reasoning
        if pre_evidence:
            parts.append(self._format_evidence_for_llm(pre_evidence))

        # Include remaining pre-fetched context that wasn't parsed
        if pre and pre.web_search_context:
            parts.append(f"\n--- Pre-fetched web context ---\n{pre.web_search_context[:3000]}")

        return "\n\n".join(parts) or "(no input)"

    @staticmethod
    def _format_evidence_for_llm(evidence: list[EvidenceItem]) -> str:
        """Format pre-gathered evidence into a compact LLM-readable block."""
        if not evidence:
            return ""
        lines = ["\n--- Pre-gathered evidence ---"]
        for i, item in enumerate(evidence):
            label = item.url or item.source
            snippet = item.content[:400]
            if len(item.content) > 400:
                snippet += " ..."
            lines.append(
                f"[{i}] ({item.source}) {label} — relevance {item.relevance:.2f}\n"
                f"    {snippet}"
            )
        lines.append("--- End pre-gathered evidence ---")
        return "\n".join(lines)

    # ── Evidence merging ───────────────────────────────────────────

    @staticmethod
    def _merge_evidence(
        llm_output: ResearcherOutput,
        pre_evidence: list[EvidenceItem],
    ) -> ResearcherOutput:
        """Merge pre-gathered evidence into the LLM's output.

        Pre-gathered items go first (they are grounded facts) followed
        by any *new* items the LLM produced (typically ``source="llm"``).
        Duplicates are skipped based on content prefix matching.
        """
        if not pre_evidence:
            return llm_output

        # Build a set of content prefixes for dedup
        seen_prefixes: set[str] = set()
        for item in pre_evidence:
            seen_prefixes.add(item.content[:80].lower())

        merged = list(pre_evidence)
        for item in llm_output.evidence:
            prefix = item.content[:80].lower()
            if prefix not in seen_prefixes:
                seen_prefixes.add(prefix)
                merged.append(item)

        # Cap total at 15 to avoid context explosion
        merged = merged[:15]

        return ResearcherOutput(
            evidence=merged,
            summary=llm_output.summary,
            tools_used=llm_output.tools_used,
        )

    # ── Output parsing ─────────────────────────────────────────────

    def _parse_output(
        self, raw: str, tools_used: list[str]
    ) -> ResearcherOutput:
        """Parse LLM JSON into ``ResearcherOutput``.

        Falls back to an empty evidence list on parse failure.
        """
        if not raw.strip():
            return self._fallback_output(tools_used)

        try:
            data = self._parse_json(raw)
        except ValueError as exc:
            logger.warning("[Researcher] JSON extraction failed: %s", exc)
            return self._fallback_output(tools_used)

        # Normalise evidence items
        raw_evidence = data.get("evidence", [])
        evidence: list[EvidenceItem] = []
        for item in raw_evidence[:10]:  # cap at 10
            if isinstance(item, dict):
                try:
                    evidence.append(self._validate(item, EvidenceItem))
                except Exception:
                    content = item.get("content", str(item))
                    evidence.append(EvidenceItem(source="llm", content=str(content)))

        summary = str(data.get("summary", "(no summary)"))
        parsed_tools = data.get("tools_used", tools_used)

        return ResearcherOutput(
            evidence=evidence,
            summary=summary,
            tools_used=parsed_tools if isinstance(parsed_tools, list) else tools_used,
        )

    @staticmethod
    def _fallback_output(tools_used: list[str]) -> ResearcherOutput:
        """Return a safe fallback when parsing fails."""
        return ResearcherOutput(
            evidence=[],
            summary="(parse failure — no evidence gathered)",
            tools_used=tools_used,
        )
