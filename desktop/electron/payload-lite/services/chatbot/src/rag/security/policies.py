"""
RAG policy limits — hard caps enforced across ingest, retrieval and chat.

All limits live in one place so they can be tuned centrally.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RAGPolicies:
    """Immutable policy configuration for the RAG subsystem."""

    # ── Ingest limits ─────────────────────────────────────────────────
    max_file_bytes: int = 50 * 1024 * 1024          # 50 MB
    max_chunks_per_document: int = 2_000
    max_chunk_chars: int = 4_000                     # individual chunk text
    max_documents_per_tenant: int = 200              # dev tier

    # ── Retrieval / chat limits ───────────────────────────────────────
    max_top_k: int = 20
    max_context_chars: int = 60_000                  # total RAG block injected
    max_query_chars: int = 4_000                     # user query length

    # ── Prompt-injection scanning ─────────────────────────────────────
    block_on_injection: bool = False                  # if True, drop the chunk entirely
    flag_on_injection: bool = True                    # add [⚠ FLAGGED] marker


# Singleton — importable everywhere
_DEFAULT = RAGPolicies()


def get_rag_policies() -> RAGPolicies:
    """Return the active policy set (singleton)."""
    return _DEFAULT
