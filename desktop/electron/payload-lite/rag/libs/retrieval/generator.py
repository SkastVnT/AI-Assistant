"""RAG generation — combines retrieval results with LLM completion."""

from libs.core.providers.base import LLMProvider
from libs.retrieval.search import SearchResult

RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions based on the provided context.\n"
    "Rules:\n"
    "- Answer ONLY based on the context provided below.\n"
    "- If the context does not contain enough information, say so clearly.\n"
    "- Cite the source filename when possible.\n"
    "- Be concise and accurate."
)


def _build_context(results: list[SearchResult]) -> str:
    """Format search results into a context string for the LLM."""
    if not results:
        return "No relevant documents found."

    parts: list[str] = []
    for i, r in enumerate(results, 1):
        parts.append(
            f"[Source {i}: {r.filename} (relevance: {r.score:.2f})]\n{r.content}"
        )
    return "\n\n---\n\n".join(parts)


async def generate_answer(
    llm: LLMProvider,
    query: str,
    results: list[SearchResult],
    *,
    system_prompt: str | None = None,
) -> str:
    """Generate an answer using retrieved context + LLM."""
    context = _build_context(results)
    prompt = f"""Context:
{context}

Question: {query}

Answer:"""

    return await llm.complete(
        prompt,
        system=system_prompt or RAG_SYSTEM_PROMPT,
        temperature=0.1,
    )
