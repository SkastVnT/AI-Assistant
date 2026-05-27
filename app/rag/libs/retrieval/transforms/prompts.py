"""LLM prompt templates for query transformations.

Each template returns a system prompt and a user prompt.
Designed for minimal token usage while maintaining quality.
"""

# ── Query Rewrite ──────────────────────────────────────────────────────────

REWRITE_SYSTEM = (
    "You are a search query optimizer. Rewrite the user's question into a "
    "clear, specific search query that will retrieve the most relevant "
    "documents from a knowledge base. Preserve the original intent. "
    "Output ONLY the rewritten query, nothing else."
)

REWRITE_USER = "Original question: {query}"

# ── HyDE (Hypothetical Document Embeddings) ───────────────────────────────

HYDE_SYSTEM = (
    "You are a knowledgeable assistant. Given a question, write a short "
    "paragraph (3-5 sentences) that would appear in an ideal document "
    "answering this question. Be factual and specific. Do NOT say "
    '"the document says" or "according to" — write as if you ARE the document. '
    "Output ONLY the paragraph, nothing else."
)

HYDE_USER = "Question: {query}"

# ── Query Decomposition ───────────────────────────────────────────────────

DECOMPOSITION_SYSTEM = (
    "You are a question decomposer for a multi-hop retrieval system. "
    "Break the user's complex question into {max_sub_queries} or fewer "
    "simple, self-contained sub-questions that together answer the original. "
    "Each sub-question should be answerable from a single document. "
    "Output one sub-question per line, numbered (1. 2. 3.). "
    "If the question is already simple, output just the original question."
)

DECOMPOSITION_USER = "Complex question: {query}"
