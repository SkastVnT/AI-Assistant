"""Plain-text parser — extracts paragraphs from .txt files."""

from __future__ import annotations

import re

from libs.ingestion.parsers.base import (
    ContentElement,
    ElementType,
    ParseResult,
)


class TextParser:
    """Parses plain text files into paragraph-level elements."""

    @property
    def supported_extensions(self) -> set[str]:
        return {".txt", ".text"}

    def parse(self, content: bytes, filename: str) -> ParseResult:
        text = content.decode("utf-8", errors="replace")
        elements: list[ContentElement] = []

        # Split on double-newlines to find paragraph boundaries
        blocks = re.split(r"\n{2,}", text)

        title: str | None = None
        for block in blocks:
            block = block.strip()
            if not block:
                continue

            # Heuristic: first non-empty short line could be a title
            if title is None and len(block) < 200 and "\n" not in block:
                title = block
                elements.append(
                    ContentElement(type=ElementType.TITLE, content=block)
                )
            else:
                elements.append(
                    ContentElement(type=ElementType.PARAGRAPH, content=block)
                )

        return ParseResult(
            elements=elements,
            title=title,
            raw_text=text,
            metadata={"encoding": "utf-8"},
        )
