"""Agent controller — the state machine that drives the agentic loop.

Implements the PLAN → ACT → OBSERVE → REFLECT → ANSWER cycle.
Each phase delegates to the planner, tool executor, or safety module.
The controller is stateless itself — all state lives in AgentState.

State machine diagram:

    ┌──────┐
    │ PLAN │──────────────────────────────────┐
    └──┬───┘                                  │
       │ sub_queries                          │ (budget exceeded)
       ▼                                      ▼
    ┌──────┐     ┌─────────┐     ┌─────────┐    ┌───────┐
    │ ACT  │────►│ OBSERVE │────►│ REFLECT │───►│ ERROR │
    └──┬───┘     └────┬────┘     └────┬────┘    └───────┘
       │              │               │
       │ (none)       │ evidence      │ sufficient=true
       │              │               ▼
       │              │          ┌────────┐    ┌──────┐
       │              │          │ ANSWER │───►│ DONE │
       │              │          └────────┘    └──────┘
       │              │               │
       │              │               │ sufficient=false
       │              └───────────────┤
       │                              │
       └────── (loop back) ◄──────────┘
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from libs.agent.memory import ShortTermMemory
from libs.agent.planner import plan_task, reflect, select_tool, synthesise_answer
from libs.agent.safety import (
    check_budget,
    create_delegated_auth,
    get_stop_reason_for_budget,
    is_tool_allowed,
    screen_task,
)
from libs.agent.types import (
    AgentConfig,
    AgentPhase,
    AgentState,
    StopReason,
    Turn,
)

if TYPE_CHECKING:
    from libs.agent.tools import ToolRegistry
    from libs.auth.context import AuthContext
    from libs.core.providers.base import LLMProvider
    from libs.ragops.tracing import SpanCollector

logger = logging.getLogger("rag.agent.controller")


class AgentController:
    """Drives the agentic RAG loop from PLAN through DONE/ERROR.

    Parameters
    ----------
    llm:
        LLM provider for planning, reflection, and answer generation.
    tool_registry:
        Registry of available tools.
    config:
        Agent runtime configuration (limits, thresholds, toggles).
    span_collector:
        Optional tracing collector for observability.
    """

    def __init__(
        self,
        llm: LLMProvider,
        tool_registry: ToolRegistry,
        config: AgentConfig | None = None,
        span_collector: SpanCollector | None = None,
    ) -> None:
        self._llm = llm
        self._tools = tool_registry
        self._config = config or AgentConfig()
        self._spans = span_collector

    async def run(
        self,
        query: str,
        auth: AuthContext,
    ) -> AgentState:
        """Execute the full agentic loop for a query.

        Returns the terminal AgentState with answer or error.
        """
        state = AgentState(
            query=query,
            tenant_id=auth.tenant_id,
            user_id=auth.user_id,
        )
        memory = ShortTermMemory(
            max_evidence=self._config.max_evidence_items,
        )
        delegated = create_delegated_auth(auth)

        # ── Pre-flight: task screening ─────────────────────────────
        screening = screen_task(query)
        if not screening.allowed:
            state.phase = AgentPhase.ERROR
            state.stop_reason = StopReason.POLICY_BLOCKED
            state.answer = f"Task rejected: {screening.blocked_reason}"
            return state

        # ── Phase 1: PLAN ──────────────────────────────────────────
        state.phase = AgentPhase.PLAN
        if self._spans:
            ctx = self._spans.span("agent_plan")
            ctx.__enter__()

        plan_text, sub_queries = await plan_task(
            self._llm, state,
            temperature=self._config.planning_temperature,
        )
        state.sub_queries = sub_queries

        turn = Turn(index=0, phase=AgentPhase.PLAN, plan=plan_text)
        state.turns.append(turn)

        if self._spans:
            ctx.__exit__(None, None, None)

        # ── Main loop: ACT → OBSERVE → REFLECT ────────────────────
        while not state.is_terminal():
            state.iteration += 1

            # Budget check
            budget = check_budget(state, self._config)
            if not budget.allowed:
                logger.warning("budget_exceeded: %s", budget.reason)
                state.phase = AgentPhase.ERROR
                state.stop_reason = get_stop_reason_for_budget(state, self._config)
                # Still try to produce a best-effort answer
                state.answer = await self._best_effort_answer(state, memory)
                break

            # ── ACT: select a tool ─────────────────────────────────
            state.phase = AgentPhase.ACT
            if self._spans:
                act_ctx = self._spans.span("agent_act", iteration=state.iteration)
                act_ctx.__enter__()

            tool_call = await select_tool(
                self._llm, state, memory,
                tool_descriptions=self._tools.available_tools(),
                temperature=self._config.planning_temperature,
            )

            if tool_call is None:
                # Planner says we have enough — go to ANSWER
                if self._spans:
                    act_ctx.__exit__(None, None, None)
                break

            # Authorization check
            if not is_tool_allowed(delegated, tool_call.tool_name):
                logger.warning(
                    "tool_blocked: %s not in allowlist for role=%s",
                    tool_call.tool_name, delegated.role,
                )
                memory.add_note(
                    f"Tool '{tool_call.tool_name}' is not permitted for your role."
                )
                if self._spans:
                    act_ctx.__exit__(None, None, None)
                continue

            tool = self._tools.get(tool_call.tool_name)
            if tool is None:
                logger.warning("tool_not_found: %s", tool_call.tool_name)
                memory.add_note(f"Tool '{tool_call.tool_name}' not found.")
                if self._spans:
                    act_ctx.__exit__(None, None, None)
                continue

            # Execute the tool
            tool_result = await tool.execute(tool_call, auth)
            state.total_tool_calls += 1

            if self._spans:
                act_ctx.__exit__(None, None, None)

            # ── OBSERVE: process the result ────────────────────────
            state.phase = AgentPhase.OBSERVE
            if tool_result.success and tool_result.output:
                memory.add_evidence(
                    tool_result.output,
                    source=tool_result.tool_name,
                    query=tool_call.arguments.get("query", ""),
                    turn_index=state.iteration,
                )
                memory.record_query(tool_call.arguments.get("query", ""))
            state.evidence = [e.content for e in memory.evidence]

            turn = Turn(
                index=state.iteration,
                phase=AgentPhase.ACT,
                tool_call=tool_call,
                tool_result=tool_result,
            )

            # ── REFLECT: self-check ────────────────────────────────
            state.phase = AgentPhase.REFLECT
            if self._spans:
                ref_ctx = self._spans.span("agent_reflect", iteration=state.iteration)
                ref_ctx.__enter__()

            sufficient, confidence, notes = await reflect(
                self._llm, state, memory,
            )
            turn.reflection = notes
            state.turns.append(turn)

            if self._spans:
                ref_ctx.__exit__(None, None, None)

            if sufficient and confidence >= self._config.reflection_threshold:
                memory.add_note(f"Sufficient evidence (confidence={confidence:.2f})")
                break

        # ── ANSWER phase ───────────────────────────────────────────
        if not state.is_terminal():
            state.phase = AgentPhase.ANSWER
            if self._spans:
                ans_ctx = self._spans.span("agent_answer")
                ans_ctx.__enter__()

            state.answer = await synthesise_answer(
                self._llm, state, memory,
                temperature=self._config.answer_temperature,
            )
            state.stop_reason = StopReason.ANSWERED
            state.phase = AgentPhase.DONE

            answer_turn = Turn(
                index=state.iteration + 1,
                phase=AgentPhase.ANSWER,
                is_final=True,
            )
            state.turns.append(answer_turn)

            if self._spans:
                ans_ctx.__exit__(None, None, None)

        logger.info(
            "agent_done: task=%s iterations=%d tools=%d reason=%s",
            state.task_id, state.iteration,
            state.total_tool_calls, state.stop_reason,
        )
        return state

    async def _best_effort_answer(
        self, state: AgentState, memory: ShortTermMemory,
    ) -> str:
        """Generate a best-effort answer when budget is exceeded."""
        if memory.evidence_count == 0:
            return (
                "I was unable to gather sufficient evidence within the "
                "allowed budget. Please try a simpler query."
            )
        return await synthesise_answer(
            self._llm, state, memory,
            temperature=self._config.answer_temperature,
        )
