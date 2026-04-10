"""LLM-based planner — task decomposition, tool selection, and reflection.

The planner is the "brain" of the agent. It uses structured prompts to:
1. Analyse the task and decompose into sub-goals (PLAN phase)
2. Select the next tool and formulate arguments (ACT phase)
3. Assess whether collected evidence is sufficient (REFLECT phase)
4. Synthesise a final grounded answer (ANSWER phase)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from libs.agent.types import AgentState, ToolCall

if TYPE_CHECKING:
    from libs.agent.memory import ShortTermMemory
    from libs.core.providers.base import LLMProvider

logger = logging.getLogger("rag.agent.planner")


# ═══════════════════════════════════════════════════════════════════════
# System prompts
# ═══════════════════════════════════════════════════════════════════════

PLAN_SYSTEM = """\
You are an expert research planner. Given a user query, decompose it into \
a concise plan of 1-4 sub-questions that need to be answered to fully \
address the query. Each sub-question should be specific and answerable \
by a single tool call.

Respond with valid JSON only:
{
  "plan": "Brief strategy description",
  "sub_queries": ["sub-question 1", "sub-question 2"]
}
"""

ACT_SYSTEM = """\
You are a tool-selection agent. Given the current task state, pick \
the best available tool and provide arguments.

Available tools:
{tool_descriptions}

Rules:
1. Pick exactly ONE tool per turn.
2. Use the "retriever" tool for finding information in the knowledge base.
3. Use "web_search" only if internal search returned no results.
4. Use "python" for calculations or data processing.
5. Use "policy_check" to verify sensitive answers before finalising.
6. Do NOT repeat a query you already ran (check the query history).
7. If you have enough evidence, respond with tool_name "none" to proceed to answering.

Respond with valid JSON only:
{{
  "tool_name": "retriever",
  "arguments": {{"query": "specific search query"}},
  "rationale": "Why this tool and query"
}}
"""

REFLECT_SYSTEM = """\
You are a research quality assessor. Given the original query and \
collected evidence, assess whether we have enough information to \
produce a comprehensive, accurate answer.

Consider:
1. Does the evidence address all parts of the query?
2. Are there contradictions that need resolution?
3. Are there gaps that require additional searches?

Respond with valid JSON only:
{
  "sufficient": true/false,
  "confidence": 0.0-1.0,
  "gaps": ["description of any remaining gaps"],
  "notes": "brief reasoning"
}
"""

ANSWER_SYSTEM = """\
You are a knowledge-base assistant producing a final answer.

RULES:
1. Answer ONLY based on the provided evidence. Do not make up facts.
2. Cite sources using [Evidence N] markers matching the evidence items.
3. If the evidence is insufficient, say so explicitly.
4. Be concise but thorough.
5. Structure the answer clearly with paragraphs or bullet points.
"""


# ═══════════════════════════════════════════════════════════════════════
# Plan phase
# ═══════════════════════════════════════════════════════════════════════


async def plan_task(
    llm: LLMProvider,
    state: AgentState,
    *,
    temperature: float = 0.2,
) -> tuple[str, list[str]]:
    """Decompose the user query into a plan and sub-queries.

    Returns (plan_text, sub_queries).
    """
    prompt = f"User query: {state.query}"
    raw = await llm.complete(prompt, system=PLAN_SYSTEM, temperature=temperature)

    try:
        data = _parse_json(raw)
        plan = str(data.get("plan", ""))
        sub_queries = [str(q) for q in data.get("sub_queries", []) if q]
    except (json.JSONDecodeError, ValueError):
        logger.warning("plan_parse_error: using query as single sub-query")
        plan = "Direct search for the query."
        sub_queries = [state.query]

    if not sub_queries:
        sub_queries = [state.query]

    logger.info("plan: %s sub_queries=%d", plan[:80], len(sub_queries))
    return plan, sub_queries


# ═══════════════════════════════════════════════════════════════════════
# Act phase — tool selection
# ═══════════════════════════════════════════════════════════════════════


async def select_tool(
    llm: LLMProvider,
    state: AgentState,
    memory: ShortTermMemory,
    *,
    tool_descriptions: list[dict],
    temperature: float = 0.1,
) -> ToolCall | None:
    """Select the next tool to call based on current state.

    Returns None if the LLM decides no more tools are needed.
    """
    system = ACT_SYSTEM.format(
        tool_descriptions=json.dumps(tool_descriptions, indent=2),
    )

    context = (
        f"Original query: {state.query}\n\n"
        f"Plan: {state.sub_queries}\n\n"
        f"Iteration: {state.iteration}\n\n"
        f"Evidence collected so far:\n{memory.get_evidence_text()}\n\n"
        f"Queries already run: {memory.query_history}\n\n"
        f"Scratchpad:\n{memory.get_scratchpad_text()}"
    )

    raw = await llm.complete(context, system=system, temperature=temperature)

    try:
        data = _parse_json(raw)
        tool_name = str(data.get("tool_name", "")).strip()
        if not tool_name or tool_name == "none":
            logger.info("act: planner chose no tool, proceeding to answer")
            return None
        arguments = data.get("arguments", {})
        if not isinstance(arguments, dict):
            arguments = {}
        rationale = str(data.get("rationale", ""))
    except (json.JSONDecodeError, ValueError):
        logger.warning("act_parse_error: defaulting to no tool")
        return None

    return ToolCall(
        tool_name=tool_name,
        arguments=arguments,
        rationale=rationale,
    )


# ═══════════════════════════════════════════════════════════════════════
# Reflect phase — self-check
# ═══════════════════════════════════════════════════════════════════════


async def reflect(
    llm: LLMProvider,
    state: AgentState,
    memory: ShortTermMemory,
    *,
    temperature: float = 0.1,
) -> tuple[bool, float, str]:
    """Assess whether collected evidence is sufficient.

    Returns (sufficient, confidence, notes).
    """
    context = (
        f"Original query: {state.query}\n\n"
        f"Evidence collected:\n{memory.get_evidence_text()}\n\n"
        f"Number of evidence items: {memory.evidence_count}\n"
        f"Iteration: {state.iteration}"
    )

    raw = await llm.complete(context, system=REFLECT_SYSTEM, temperature=temperature)

    try:
        data = _parse_json(raw)
        sufficient = bool(data.get("sufficient", False))
        confidence = float(data.get("confidence", 0.0))
        notes = str(data.get("notes", ""))
    except (json.JSONDecodeError, ValueError):
        logger.warning("reflect_parse_error: defaulting to sufficient=False")
        sufficient = False
        confidence = 0.0
        notes = "Failed to parse reflection output."

    logger.info("reflect: sufficient=%s confidence=%.2f", sufficient, confidence)
    return sufficient, confidence, notes


# ═══════════════════════════════════════════════════════════════════════
# Answer phase — final synthesis
# ═══════════════════════════════════════════════════════════════════════


async def synthesise_answer(
    llm: LLMProvider,
    state: AgentState,
    memory: ShortTermMemory,
    *,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> str:
    """Generate the final grounded answer from accumulated evidence.

    Returns the answer text.
    """
    context = (
        f"User query: {state.query}\n\n"
        f"Collected evidence:\n{memory.get_evidence_text()}\n\n"
        f"Scratchpad notes:\n{memory.get_scratchpad_text()}"
    )

    answer = await llm.complete(
        context,
        system=ANSWER_SYSTEM,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return answer.strip()


# ═══════════════════════════════════════════════════════════════════════
# JSON parsing helper
# ═══════════════════════════════════════════════════════════════════════


def _parse_json(raw: str) -> dict:
    """Parse JSON from LLM output, stripping markdown fences if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)
    return json.loads(text)
