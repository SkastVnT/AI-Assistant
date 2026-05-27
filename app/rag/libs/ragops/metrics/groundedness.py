"""Groundedness / faithfulness metric — evaluates generator quality.

Measures whether the generated answer is faithfully grounded in the
retrieved context. Penalizes hallucinated claims not supported by context.

This is a **generator** metric.

Scoring:
- 1: Answer contains mostly fabricated claims not in the context
- 5: Every claim in the answer is directly supported by the context
"""

from __future__ import annotations

from libs.ragops.judge import Judge, JudgeResult

GROUNDEDNESS_PROMPT = """\
Evaluate whether the generated answer is faithfully grounded in the provided \
context. Penalize any claims, facts, or details NOT supported by the context.

Context:
{context}

Answer:
{answer}

Consider:
1. Is every factual claim in the answer supported by the context?
2. Does the answer fabricate information not present in the context?
3. Does the answer correctly attribute information to sources?
4. If the answer says "I don't have enough evidence", is that appropriate?

Respond with ONLY a JSON object:
{{"score": <1-5>, "reasoning": "<brief explanation>"}}
"""


async def eval_groundedness(
    judge: Judge,
    *,
    context: str,
    answer: str,
) -> JudgeResult:
    """Score how well the answer is grounded in the retrieved context.

    Args:
        judge: Evaluation judge (LLM or heuristic).
        context: The retrieved context text.
        answer: The generated answer.

    Returns:
        JudgeResult with 0.0-1.0 score.
    """
    prompt = GROUNDEDNESS_PROMPT.format(context=context, answer=answer)
    return await judge.evaluate(prompt)
