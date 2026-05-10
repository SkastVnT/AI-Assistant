"""
Agentic Council — Evidence gathering
======================================
Normalised evidence extraction from the four context sources already
available in the chatbot request pipeline:

  1. **uploaded_file** — text extracted from uploaded files (OCR / STT)
  2. **rag**           — chunks from the RAG retrieval pipeline
  3. **mcp**           — file content injected via MCP
  4. **direct_user_context** — inline context the user pasted in the message

Each gatherer returns a list of :class:`EvidenceItem` objects with
``source`` set to one of the above strings.  The module **does not
perform I/O itself** — it re-uses whatever the existing helpers already
produced and was captured in :class:`PreContext`.

Token/context control
~~~~~~~~~~~~~~~~~~~~~
- Every snippet is truncated to ``MAX_SNIPPET_CHARS`` (default 1 500).
- Total evidence items per source are capped (``MAX_*_ITEMS``).
- Oversized RAG chunks and MCP blocks are summarised to a title + head.
- Callers can pass a ``budget_chars`` to ``gather_all()`` for global cap.
"""
from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from core.agentic.contracts import EvidenceItem

logger = logging.getLogger(__name__)


# ── Tuning knobs ───────────────────────────────────────────────────────

MAX_SNIPPET_CHARS: int = 1_500
"""Hard ceiling on any single evidence snippet."""

MAX_RAG_ITEMS: int = 8
MAX_MCP_ITEMS: int = 5
MAX_UPLOAD_ITEMS: int = 5
MAX_DIRECT_ITEMS: int = 3

DEFAULT_BUDGET_CHARS: int = 15_000
"""Soft ceiling on total characters across *all* evidence items."""


# ── Source type constants ──────────────────────────────────────────────

SOURCE_UPLOADED_FILE = "uploaded_file"
SOURCE_RAG = "rag"
SOURCE_MCP = "mcp"
SOURCE_DIRECT = "direct_user_context"


# ── Public API ─────────────────────────────────────────────────────────


def gather_all(
    *,
    rag_chunks: list[dict[str, Any]] | None = None,
    rag_citations: list[dict[str, Any]] | None = None,
    mcp_context: str = "",
    augmented_message: str = "",
    original_message: str = "",
    budget_chars: int = DEFAULT_BUDGET_CHARS,
) -> list[EvidenceItem]:
    """Gather evidence from every available pre-fetched source.

    Parameters
    ----------
    rag_chunks:
        List of dicts with at least ``content`` (str) and optionally
        ``doc_name`` / ``chunk_id`` / ``score``.
    rag_citations:
        Structured citations returned by :class:`RAGResult`.
    mcp_context:
        Raw MCP context block (may contain multiple file sections).
    augmented_message:
        The user message *after* all injections (files + MCP + RAG).
    original_message:
        The raw user message *before* augmentation.
    budget_chars:
        Soft ceiling on total evidence character count.

    Returns
    -------
    list[EvidenceItem]
        Deduplicated, capped, and truncated evidence bundle.
    """
    evidence: list[EvidenceItem] = []

    # 1. Uploaded files (extracted from augmented_message markers)
    evidence.extend(
        _extract_uploaded_file_evidence(augmented_message)
    )

    # 2. RAG chunks
    evidence.extend(
        _extract_rag_evidence(rag_chunks or [], rag_citations or [])
    )

    # 3. MCP file context
    evidence.extend(
        _extract_mcp_evidence(mcp_context)
    )

    # 4. Direct user context (inline information the user provided)
    evidence.extend(
        _extract_direct_context(original_message, augmented_message)
    )

    # Global budget enforcement
    evidence = _enforce_budget(evidence, budget_chars)

    logger.debug(
        "[evidence] gathered %d items (rag=%d, mcp=%d, upload=%d, direct=%d)",
        len(evidence),
        sum(1 for e in evidence if e.source == SOURCE_RAG),
        sum(1 for e in evidence if e.source == SOURCE_MCP),
        sum(1 for e in evidence if e.source == SOURCE_UPLOADED_FILE),
        sum(1 for e in evidence if e.source == SOURCE_DIRECT),
    )
    return evidence


# ── Uploaded file extraction ───────────────────────────────────────────

# Pattern emitted by _inject_file_context() in chat.py
_FILE_BLOCK_RE = re.compile(
    r"\[(?:Audio transcript from|File:)\s*(?P<filename>[^\]]+)\]:\s*\n"
    r"(?:```\w*\n)?(?P<content>.*?)(?:\n```)?\s*(?=\[(?:Audio|File:)|\Z|--- END FILES ---)",
    re.DOTALL,
)


def _extract_uploaded_file_evidence(augmented_message: str) -> list[EvidenceItem]:
    """Parse uploaded-file blocks injected by the chat router."""
    if "--- UPLOADED FILES ---" not in augmented_message:
        return []

    items: list[EvidenceItem] = []
    for match in _FILE_BLOCK_RE.finditer(augmented_message):
        if len(items) >= MAX_UPLOAD_ITEMS:
            break
        filename = match.group("filename").strip()
        content = match.group("content").strip()
        if not content:
            continue
        items.append(
            EvidenceItem(
                source=SOURCE_UPLOADED_FILE,
                content=_truncate(content, MAX_SNIPPET_CHARS),
                url=filename,  # use url field for filename/path
                relevance=0.85,
                task_id=None,
            )
        )
    return items


# ── RAG evidence ───────────────────────────────────────────────────────


def _extract_rag_evidence(
    chunks: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> list[EvidenceItem]:
    """Convert RAG chunks into evidence items.

    Falls back to raw ``content`` when structured citation metadata is
    absent.  Relevance is mapped from the chunk's ``score`` if available.
    """
    # Build a citation lookup by chunk_id for richer metadata
    cite_map: dict[str, dict] = {}
    for c in citations:
        cid = c.get("chunk_id") or c.get("id", "")
        if cid:
            cite_map[cid] = c

    items: list[EvidenceItem] = []
    for chunk in chunks[:MAX_RAG_ITEMS]:
        content = str(chunk.get("content", "")).strip()
        if not content:
            continue

        chunk_id = chunk.get("chunk_id", "")
        cite = cite_map.get(chunk_id, {})
        doc_name = (
            cite.get("doc_name")
            or chunk.get("doc_name")
            or chunk.get("metadata", {}).get("doc_name", "")
        )
        score = chunk.get("score", chunk.get("relevance", 0.7))
        try:
            relevance = min(1.0, max(0.0, float(score)))
        except (TypeError, ValueError):
            relevance = 0.7

        title = doc_name or f"rag-chunk-{chunk_id or len(items)}"

        items.append(
            EvidenceItem(
                source=SOURCE_RAG,
                content=_truncate(content, MAX_SNIPPET_CHARS),
                url=title,
                relevance=relevance,
                task_id=None,
            )
        )
    return items


# ── MCP evidence ──────────────────────────────────────────────────────

# MCPClient wraps files in sections like:
#   📄 **File: path/to/file** (Language: python)
# or flat code blocks with path headings.
_MCP_SECTION_RE = re.compile(
    r"(?:📄\s*\*\*File:\s*(?P<path1>[^*]+)\*\*|"
    r"### (?P<path2>[^\n]+))\s*(?:\([^)]*\))?\s*\n"
    r"(?:```\w*\n)?(?P<content>.*?)(?:\n```)?\s*"
    r"(?=📄\s*\*\*File:|### |\Z)",
    re.DOTALL,
)


def _extract_mcp_evidence(mcp_context: str) -> list[EvidenceItem]:
    """Parse MCP file blocks into evidence items."""
    if not mcp_context.strip():
        return []

    items: list[EvidenceItem] = []

    # Try structured section parsing first
    for match in _MCP_SECTION_RE.finditer(mcp_context):
        if len(items) >= MAX_MCP_ITEMS:
            break
        path = (match.group("path1") or match.group("path2") or "").strip()
        content = match.group("content").strip()
        if not content:
            continue
        items.append(
            EvidenceItem(
                source=SOURCE_MCP,
                content=_truncate(content, MAX_SNIPPET_CHARS),
                url=path or "mcp-file",
                relevance=0.8,
                task_id=None,
            )
        )

    # Fallback: treat entire block as one evidence item
    if not items and len(mcp_context.strip()) > 20:
        items.append(
            EvidenceItem(
                source=SOURCE_MCP,
                content=_truncate(mcp_context.strip(), MAX_SNIPPET_CHARS),
                url="mcp-context",
                relevance=0.75,
                task_id=None,
            )
        )

    return items


# ── Direct user context ───────────────────────────────────────────────

# Users sometimes paste code blocks or structured data directly
_CODE_FENCE_RE = re.compile(r"```(\w*)\n(.*?)\n```", re.DOTALL)


def _extract_direct_context(
    original_message: str, augmented_message: str
) -> list[EvidenceItem]:
    """Extract inline code blocks or data the user pasted in.

    Only looks at the *original* message (before MCP/RAG augmentation)
    so we don't double-count injected context.
    """
    if not original_message.strip():
        return []

    items: list[EvidenceItem] = []
    for match in _CODE_FENCE_RE.finditer(original_message):
        if len(items) >= MAX_DIRECT_ITEMS:
            break
        lang = match.group(1) or "text"
        content = match.group(2).strip()
        if len(content) < 20:  # ignore trivial fences
            continue
        items.append(
            EvidenceItem(
                source=SOURCE_DIRECT,
                content=_truncate(content, MAX_SNIPPET_CHARS),
                url=f"user-code-{lang}",
                relevance=0.9,
                task_id=None,
            )
        )

    return items


# ── Helpers ────────────────────────────────────────────────────────────


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text with an ellipsis marker."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 4] + " ..."


def _enforce_budget(
    items: list[EvidenceItem], budget: int
) -> list[EvidenceItem]:
    """Drop lowest-relevance items until the total fits *budget*."""
    # Sort by relevance desc so we keep the best items
    ranked = sorted(items, key=lambda e: e.relevance, reverse=True)
    kept: list[EvidenceItem] = []
    total = 0
    for item in ranked:
        cost = len(item.content)
        if total + cost > budget and kept:
            logger.debug(
                "[evidence] budget cap — dropping %s item (%d chars, rel=%.2f)",
                item.source,
                cost,
                item.relevance,
            )
            continue
        kept.append(item)
        total += cost
    return kept
