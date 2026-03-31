"""Context relevance metric — evaluates retriever quality.

Measures how relevant the retrieved context is to the user's query.
This is a **retriever** metric: it does NOT evaluate the generated answer.

Scoring:
- 1: Context is completely irrelevant to the query
- 5: Every piece of context is directly useful for answering the query
"""

from __future__ import annotations

from libs.ragops.judge import Judge, JudgeResult

CONTEXT_RELEVANCE_PROMPT = """\
Evaluate how relevant the retrieved context is for answering the given query.

Query: {query}

Context:
{context}

Consider:
1. Does the context contain information needed to answer the query?
2. Is the context focused or does it include excessive noise?
3. Would this context be sufficient for a knowledgeable person to answer?

Respond with ONLY a JSON object:
{{"score": <1-5>, "reasoning": "<brief explanation>"}}
"""


async def eval_context_relevance(
    judge: Judge,
    *,
    query: str,
    context: str,
) -> JudgeResult:
    """Score how relevant the retrieved context is to the query.

    Args:
        judge: Evaluation judge (LLM or heuristic).
        query: The user's original query.
        context: The retrieved context text.

    Returns:
        JudgeResult with 0.0-1.0 score.
    """
    prompt = CONTEXT_RELEVANCE_PROMPT.format(query=query, context=context)
    return await judge.evaluate(prompt)
