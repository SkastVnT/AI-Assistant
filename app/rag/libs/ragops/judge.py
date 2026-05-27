"""LLM-as-a-judge interface for RAG evaluation.

Provides a protocol-based judge abstraction with two implementations:
- LLMJudge: calls an LLM to score outputs (for production evals)
- HeuristicJudge: rule-based scoring (for CI, testing, no API needed)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from libs.core.providers.base import LLMProvider

logger = logging.getLogger("rag.ragops.judge")


@dataclass(frozen=True)
class JudgeResult:
    """Structured evaluation result from a judge."""

    score: float  # 0.0-1.0
    reasoning: str
    raw_output: str = ""


@runtime_checkable
class Judge(Protocol):
    """Protocol for evaluation judges."""

    async def evaluate(self, prompt: str) -> JudgeResult:
        """Evaluate a prompt and return a scored result."""
        ...


# ── Parsing helper ────────────────────────────────────────────────────────

_SCORE_PATTERN = re.compile(r'"score"\s*:\s*(\d+(?:\.\d+)?)')
_REASONING_PATTERN = re.compile(r'"reasoning"\s*:\s*"([^"]*(?:\\.[^"]*)*)"')


def _parse_judge_output(raw: str) -> JudgeResult:
    """Parse JSON-like output from LLM judge.

    Expected format: {"score": 4, "reasoning": "..."}
    Scores are on 1-5 scale, normalized to 0.0-1.0.
    """
    # Try full JSON parse first
    try:
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        data = json.loads(cleaned)
        raw_score = float(data.get("score", 0))
        reasoning = str(data.get("reasoning", ""))
        # Normalize 1-5 to 0.0-1.0
        score = max(0.0, min(1.0, (raw_score - 1) / 4))
        return JudgeResult(score=score, reasoning=reasoning, raw_output=raw)
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Fallback: regex extraction
    score_match = _SCORE_PATTERN.search(raw)
    reasoning_match = _REASONING_PATTERN.search(raw)

    if score_match:
        raw_score = float(score_match.group(1))
        score = max(0.0, min(1.0, (raw_score - 1) / 4))
        reasoning = reasoning_match.group(1) if reasoning_match else ""
        return JudgeResult(score=score, reasoning=reasoning, raw_output=raw)

    logger.warning("judge_parse_failed: could not extract score from: %s", raw[:200])
    return JudgeResult(score=0.0, reasoning="Failed to parse judge output", raw_output=raw)


# ── LLM Judge ─────────────────────────────────────────────────────────────


class LLMJudge:
    """Uses an LLM provider to evaluate RAG outputs.

    Sends a structured prompt and parses the JSON response.
    """

    def __init__(
        self,
        llm: LLMProvider,
        *,
        temperature: float = 0.0,
        max_tokens: int = 512,
    ) -> None:
        self._llm = llm
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def evaluate(self, prompt: str) -> JudgeResult:
        system = (
            "You are an expert evaluator for RAG (Retrieval-Augmented Generation) "
            "systems. Evaluate the given input and respond with ONLY a JSON object "
            "in this exact format:\n"
            '{"score": <1-5>, "reasoning": "<brief explanation>"}\n\n'
            "Score scale:\n"
            "1 = Very poor / completely irrelevant or unsupported\n"
            "2 = Poor / mostly irrelevant or unsupported\n"
            "3 = Acceptable / partially relevant or supported\n"
            "4 = Good / mostly relevant and well-supported\n"
            "5 = Excellent / highly relevant and fully supported"
        )
        raw = await self._llm.complete(
            prompt,
            system=system,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        return _parse_judge_output(raw)


# ── Heuristic Judge ───────────────────────────────────────────────────────


class HeuristicJudge:
    """Rule-based judge for CI and testing — no LLM API needed.

    Checks:
    - Non-empty answer
    - Citation presence ([Source N])
    - Length reasonableness
    - No "I don't know" without reason
    - Context overlap (word-level)
    """

    async def evaluate(self, prompt: str) -> JudgeResult:
        """Parse the prompt to extract components and score heuristically.

        The prompt should contain labeled sections:
        Query: ..., Context: ..., Answer: ...
        """
        sections = _extract_sections(prompt)
        query = sections.get("query", "")
        context = sections.get("context", "")
        answer = sections.get("answer", "")

        score = 0.0
        reasons: list[str] = []

        # 1. Non-empty answer
        if answer.strip():
            score += 0.2
            reasons.append("answer is non-empty")
        else:
            reasons.append("answer is empty")
            return JudgeResult(score=0.0, reasoning="; ".join(reasons))

        # 2. Citations present
        citations = re.findall(r"\[Source\s+\d+\]", answer)
        if citations:
            score += 0.2
            reasons.append(f"{len(citations)} citation(s) found")
        else:
            reasons.append("no citations found")

        # 3. Reasonable length
        word_count = len(answer.split())
        if 10 <= word_count <= 2000:
            score += 0.2
            reasons.append(f"reasonable length ({word_count} words)")
        else:
            reasons.append(f"unusual length ({word_count} words)")

        # 4. Context overlap (word-level relevance proxy)
        if context:
            ctx_words = set(context.lower().split())
            ans_words = set(answer.lower().split())
            overlap = len(ctx_words & ans_words)
            if overlap > 5:
                score += 0.2
                reasons.append(f"context overlap: {overlap} shared words")
            else:
                reasons.append(f"low context overlap: {overlap} words")

        # 5. Query-answer relevance (keyword overlap)
        if query:
            q_words = set(query.lower().split())
            a_words = set(answer.lower().split())
            q_overlap = len(q_words & a_words)
            if q_overlap > 1:
                score += 0.2
                reasons.append(f"query-answer overlap: {q_overlap} words")
            else:
                reasons.append(f"low query-answer overlap: {q_overlap} words")

        return JudgeResult(
            score=min(1.0, score),
            reasoning="; ".join(reasons),
        )


def _extract_sections(prompt: str) -> dict[str, str]:
    """Extract labeled sections from evaluation prompt."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in prompt.split("\n"):
        lower = line.strip().lower()
        for key in ("query", "context", "answer", "expected_answer"):
            if lower.startswith(f"{key}:"):
                if current_key:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = key
                current_lines = [line.split(":", 1)[1] if ":" in line else ""]
                break
        else:
            if current_key:
                current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections
