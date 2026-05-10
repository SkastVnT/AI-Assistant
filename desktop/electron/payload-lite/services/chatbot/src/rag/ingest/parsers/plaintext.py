"""
Plain-text and Markdown parser.
"""
from __future__ import annotations

from .base import DocumentParser, PageContent, ParsedDocument


class PlainTextParser(DocumentParser):
    """Handles ``text/plain`` and ``text/markdown``."""

    def supported_mime_types(self) -> list[str]:
        return ["text/plain", "text/markdown"]

    def parse(self, data: bytes, source: str = "") -> ParsedDocument:
        text = data.decode("utf-8", errors="replace")
        mime = "text/markdown" if source.lower().endswith(".md") else "text/plain"
        return ParsedDocument(
            source=source,
            mime_type=mime,
            pages=[PageContent(text=text, page_number=1)],
        )
