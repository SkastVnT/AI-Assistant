"""Prompt templates for grounded answer generation.

Separates system instructions, user query, and retrieved evidence
into distinct prompt roles so the LLM can reason over each independently.
"""

# ── System instructions (one per response mode) ───────────────────────────

_BASE_RULES = (
    "Rules you MUST follow:\n"
    "1. Answer ONLY from the evidence chunks provided below. "
    "Do NOT use prior knowledge.\n"
    "2. When you use information from a chunk, cite it inline as [Source N] "
    "where N is the source number shown in the evidence.\n"
    "3. If no evidence chunk answers the question, say explicitly: "
    '"I don\'t have enough evidence to answer this question."\n'
    "4. NEVER fabricate a citation. Only reference [Source N] values "
    "that actually appear in the evidence.\n"
    "5. If only partial evidence exists, answer what you can and state "
    "what is missing."
)

SYSTEM_CONCISE = (
    "You are a precise research assistant. "
    "Give the shortest correct answer (1-3 sentences). "
    "Cite every claim.\n\n" + _BASE_RULES
)

SYSTEM_STANDARD = (
    "You are a knowledgeable research assistant. "
    "Give a clear, well-structured answer in a few paragraphs. "
    "Cite every claim.\n\n" + _BASE_RULES
)

SYSTEM_DETAILED = (
    "You are a thorough research assistant. "
    "Give a comprehensive answer with explanations, examples where "
    "appropriate, and organized sections. Cite every claim.\n\n" + _BASE_RULES
)

SYSTEM_PROMPTS = {
    "concise": SYSTEM_CONCISE,
    "standard": SYSTEM_STANDARD,
    "detailed": SYSTEM_DETAILED,
}


# ── Evidence formatting ───────────────────────────────────────────────────

def format_evidence(
    evidence_blocks: list[dict],
) -> str:
    """Build a numbered evidence section for the prompt.

    Each entry in *evidence_blocks* is a dict with keys:
        source_index (int), filename (str), content (str), score (float).
    """
    if not evidence_blocks:
        return "<no evidence retrieved>"
    parts: list[str] = []
    for e in evidence_blocks:
        idx = e["source_index"]
        fname = e["filename"]
        score = e["score"]
        content = e["content"]
        parts.append(
            f"[Source {idx}] (file: {fname}, relevance: {score:.2f})\n"
            f"{content}"
        )
    return "\n\n---\n\n".join(parts)


# ── User prompt assembly ──────────────────────────────────────────────────

USER_TEMPLATE = (
    "Evidence:\n"
    "{evidence}\n"
    "\n"
    "Question: {query}\n"
    "\n"
    "Answer:"
)


def build_user_prompt(query: str, evidence_text: str) -> str:
    """Compose the user-role prompt from query + pre-formatted evidence."""
    return USER_TEMPLATE.format(evidence=evidence_text, query=query)
