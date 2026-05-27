"""Answer relevance metric — evaluates end-to-end quality.

Measures whether the generated answer actually addresses the user's query.
This is a **generator** metric that focuses on the query-answer relationship.

Scoring:
- 1: Answer does not address the query at all
- 5: Answer directly and completely addresses the query
"""

from __future__ import annotations

from libs.ragops.judge import Judge, JudgeResult

ANSWER_RELEVANCE_PROMPT = """\
Evaluate how well the generated answer addresses the user's query.

Query: {query}

Answer:
{answer}

Consider:
1. Does the answer directly address what was asked?
2. Is the answer complete, or does it miss key aspects of the query?
3. Is the answer concise and focused, or does it ramble?
4. Would the user be satisfied with this answer?

Respond with ONLY a JSON object:
{{"score": <1-5>, "reasoning": "<brief explanation>"}}
"""


async def eval_answer_relevance(
    judge: Judge,
    *,
    query: str,
    answer: str,
) -> JudgeResult:
    """Score how well the answer addresses the query.

    Args:
        judge: Evaluation judge (LLM or heuristic).
        query: The user's original query.
        answer: The generated answer.

    Returns:
        JudgeResult with 0.0-1.0 score.
    """
    prompt = ANSWER_RELEVANCE_PROMPT.format(query=query, answer=answer)
    return await judge.evaluate(prompt)
