"""
src.rag.security — Input sanitisation, policy enforcement and guardrails.

Modules
-------
- policies.py          — central RAGPolicies dataclass with hard caps
- prompt_injection.py  — regex scanner + sanitiser for injection patterns
- (planned) guardrails.py — output-side checks (hallucination flags, toxicity)
- (planned) access.py     — per-collection access control / tenant isolation
"""

from src.rag.security.policies import RAGPolicies, get_rag_policies
from src.rag.security.prompt_injection import (
    InjectionFlag,
    SanitizeResult,
    cap_top_k,
    enforce_query_length,
    sanitize_chunk,
    scan_text,
)

__all__ = [
    "RAGPolicies",
    "get_rag_policies",
    "InjectionFlag",
    "SanitizeResult",
    "cap_top_k",
    "enforce_query_length",
    "sanitize_chunk",
    "scan_text",
]
