"""Text normalization for parsed content.

Applied between the parse and metadata-extraction stages to ensure
consistent text before chunking and embedding.
"""

from __future__ import annotations

import re
import unicodedata

from libs.ingestion.parsers.base import ContentElement, ParseResult


def normalize_text(text: str) -> str:
    """Normalize a text string for consistency."""
    # NFC unicode normalization
    text = unicodedata.normalize("NFC", text)
    # Remove null bytes
    text = text.replace("\x00", "")
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse runs of spaces/tabs (preserve newlines)
    text = re.sub(r"[ \t]+", " ", text)
    # Strip trailing whitespace on each line
    text = re.sub(r" +\n", "\n", text)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_parse_result(result: ParseResult) -> ParseResult:
    """Normalize all text in a ParseResult in place and return it."""
    result.raw_text = normalize_text(result.raw_text)
    if result.title:
        result.title = normalize_text(result.title)

    normalized: list[ContentElement] = []
    for e in result.elements:
        content = normalize_text(e.content)
        if content or e.type.value == "page_break":
            normalized.append(
                ContentElement(
                    type=e.type,
                    content=content,
                    level=e.level,
                    page=e.page,
                    metadata=e.metadata,
                )
            )
    result.elements = normalized
    return result
