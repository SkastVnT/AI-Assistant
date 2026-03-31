"""
HTML parser using BeautifulSoup4.

Strips ``<script>``, ``<style>``, and non-visible elements,
then extracts clean text.
"""
from __future__ import annotations

from .base import DocumentParser, PageContent, ParsedDocument

_REMOVE_TAGS = {"script", "style", "noscript", "iframe", "svg", "head"}


class HTMLParser(DocumentParser):
    """Handles ``text/html``."""

    def supported_mime_types(self) -> list[str]:
        return ["text/html"]

    def parse(self, data: bytes, source: str = "") -> ParsedDocument:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(data, "html.parser")

        # Extract title before removing <head>
        title = ""
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title = title_tag.string.strip()

        # Remove unwanted elements
        for tag in soup.find_all(_REMOVE_TAGS):
            tag.decompose()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive blank lines
        lines = [ln for ln in text.splitlines() if ln.strip()]
        text = "\n".join(lines)

        metadata = {}
        if title:
            metadata["title"] = title

        return ParsedDocument(
            source=source,
            mime_type="text/html",
            pages=[PageContent(text=text, page_number=1)],
            metadata=metadata,
        )
