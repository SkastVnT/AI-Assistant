"""
src.rag.prompts — Prompt templates and citation building.

Responsibility:
    Build the context block injected into the LLM prompt when RAG is active.
    Produce structured citation metadata returned alongside the chat response.

Future additions:
    - Per-language prompt variants
    - Confidence-gated templates (high/low confidence)
    - System-prompt vs user-message injection strategies
"""
from .templates import (
    RAG_CONTEXT_TEMPLATE,
    RAG_GROUNDED_SYSTEM_INSTRUCTION,
    build_grounded_rag_context,
    build_rag_context,
    get_grounded_system_instruction,
)

__all__ = [
    "RAG_CONTEXT_TEMPLATE",
    "RAG_GROUNDED_SYSTEM_INSTRUCTION",
    "build_grounded_rag_context",
    "build_rag_context",
    "get_grounded_system_instruction",
]
