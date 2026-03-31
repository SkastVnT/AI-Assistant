"""
Base parser interface and shared data model.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PageContent:
    """A single logical page / section extracted from a document."""

    text: str
    page_number: int | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ParsedDocument:
    """Normalized output every parser must return.

    Attributes:
        source:     Original filename, URL, or identifier.
        mime_type:  Detected MIME type (e.g. ``text/plain``).
        pages:      Ordered list of extracted page contents.
        metadata:   Document-level metadata (title, author, …).
    """

    source: str
    mime_type: str
    pages: list[PageContent] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        """Concatenated text of all pages (double-newline separated)."""
        return "\n\n".join(p.text for p in self.pages if p.text)

    @property
    def page_count(self) -> int:
        return len(self.pages)


class DocumentParser(ABC):
    """Abstract interface for document parsers."""

    @abstractmethod
    def parse(self, data: bytes, source: str = "") -> ParsedDocument:
        """Parse raw bytes into a :class:`ParsedDocument`."""
        ...

    @abstractmethod
    def supported_mime_types(self) -> list[str]:
        """Return MIME types this parser can handle."""
        ...
