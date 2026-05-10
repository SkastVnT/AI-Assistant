"""Parser interface and data types for structured document parsing.

The parser interface follows the Adapter pattern — each file type gets
a concrete parser that produces a standardized ParseResult.  This allows
swapping parser backends (e.g., switch from PyMuPDF to a multimodal VLM
for PDFs) without touching the ingestion pipeline.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Element types
# ---------------------------------------------------------------------------


class ElementType(enum.StrEnum):
    TITLE = "title"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    CODE_BLOCK = "code_block"
    LIST_ITEM = "list_item"
    TABLE = "table"
    BLOCKQUOTE = "blockquote"
    PAGE_BREAK = "page_break"
    IMAGE = "image"  # placeholder for future multimodal support


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContentElement:
    """A single logical block from a parsed document."""

    type: ElementType
    content: str
    level: int | None = None  # heading level 1-6
    page: int | None = None  # page reference (PDF)
    metadata: dict = field(default_factory=dict)


@dataclass
class ParseResult:
    """Structured output from a document parser."""

    elements: list[ContentElement]
    title: str | None = None
    raw_text: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict for DB / MinIO storage."""
        return {
            "elements": [
                {
                    "type": e.type.value,
                    "content": e.content,
                    "level": e.level,
                    "page": e.page,
                    "metadata": e.metadata,
                }
                for e in self.elements
            ],
            "title": self.title,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: dict) -> ParseResult:
        """Deserialize from a JSON dict."""
        elements = [
            ContentElement(
                type=ElementType(e["type"]),
                content=e["content"],
                level=e.get("level"),
                page=e.get("page"),
                metadata=e.get("metadata", {}),
            )
            for e in data.get("elements", [])
        ]
        return ParseResult(
            elements=elements,
            title=data.get("title"),
            raw_text="",  # raw_text stored separately
            metadata=data.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Parser protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class DocumentParser(Protocol):
    """Interface all document parsers must satisfy."""

    @property
    def supported_extensions(self) -> set[str]:
        """File extensions this parser handles (e.g., {'.txt', '.text'})."""
        ...

    def parse(self, content: bytes, filename: str) -> ParseResult:
        """Parse raw file bytes into structured content.

        Raises ValueError for unparseable content.
        """
        ...
