"""Markdown parser — extracts headings, paragraphs, code blocks, lists, tables."""

from __future__ import annotations

import re

from libs.ingestion.parsers.base import (
    ContentElement,
    ElementType,
    ParseResult,
)

# Regex patterns for Markdown constructs
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_FENCED_CODE_RE = re.compile(r"^```(\w*)\n(.*?)^```", re.MULTILINE | re.DOTALL)
_TABLE_RE = re.compile(
    r"^(\|.+\|)\n(\|[-:| ]+\|)\n((?:\|.+\|\n?)+)", re.MULTILINE
)
_BLOCKQUOTE_RE = re.compile(r"^(?:>\s?.+\n?)+", re.MULTILINE)
_LIST_ITEM_RE = re.compile(r"^[ \t]*[-*+][ \t]+.+(?:\n(?![ \t]*[-*+][ \t]).+)*", re.MULTILINE)
_ORDERED_LIST_RE = re.compile(r"^[ \t]*\d+\.[ \t]+.+(?:\n(?![ \t]*\d+\.[ \t]).+)*", re.MULTILINE)


class MarkdownParser:
    """Parses Markdown files preserving logical structure."""

    @property
    def supported_extensions(self) -> set[str]:
        return {".md", ".markdown", ".mdx"}

    def parse(self, content: bytes, filename: str) -> ParseResult:
        text = content.decode("utf-8", errors="replace")
        elements: list[ContentElement] = []

        # Track consumed regions to avoid double-processing
        consumed: list[tuple[int, int]] = []

        # 1) Fenced code blocks
        for m in _FENCED_CODE_RE.finditer(text):
            lang = m.group(1) or None
            meta = {"language": lang} if lang else {}
            elements.append(
                ContentElement(
                    type=ElementType.CODE_BLOCK,
                    content=m.group(2).rstrip("\n"),
                    metadata=meta,
                )
            )
            consumed.append((m.start(), m.end()))

        # 2) Tables
        for m in _TABLE_RE.finditer(text):
            if not self._is_consumed(m.start(), consumed):
                table_text = m.group(0).strip()
                elements.append(
                    ContentElement(type=ElementType.TABLE, content=table_text)
                )
                consumed.append((m.start(), m.end()))

        # 3) Blockquotes
        for m in _BLOCKQUOTE_RE.finditer(text):
            if not self._is_consumed(m.start(), consumed):
                quote = re.sub(r"^>\s?", "", m.group(0), flags=re.MULTILINE).strip()
                elements.append(
                    ContentElement(type=ElementType.BLOCKQUOTE, content=quote)
                )
                consumed.append((m.start(), m.end()))

        # 4) Headings
        for m in _HEADING_RE.finditer(text):
            if not self._is_consumed(m.start(), consumed):
                level = len(m.group(1))
                heading_text = m.group(2).strip()
                elements.append(
                    ContentElement(
                        type=ElementType.HEADING,
                        content=heading_text,
                        level=level,
                    )
                )
                consumed.append((m.start(), m.end()))

        # 5) List items (unordered + ordered)
        for pattern in (_LIST_ITEM_RE, _ORDERED_LIST_RE):
            for m in pattern.finditer(text):
                if not self._is_consumed(m.start(), consumed):
                    elements.append(
                        ContentElement(
                            type=ElementType.LIST_ITEM,
                            content=m.group(0).strip(),
                        )
                    )
                    consumed.append((m.start(), m.end()))

        # 6) Remaining paragraphs — text between consumed regions
        self._extract_paragraphs(text, consumed, elements)

        # Sort elements by their approximate source position
        # (we track insert-order above; no re-sort needed for stable output)

        # Derive title from first heading level 1, or first heading
        title = None
        for e in elements:
            if e.type == ElementType.HEADING:
                if e.level == 1:
                    title = e.content
                    break
                if title is None:
                    title = e.content

        return ParseResult(
            elements=elements,
            title=title,
            raw_text=text,
            metadata={"format": "markdown"},
        )

    # ------------------------------------------------------------------

    @staticmethod
    def _is_consumed(pos: int, consumed: list[tuple[int, int]]) -> bool:
        return any(start <= pos < end for start, end in consumed)

    @staticmethod
    def _extract_paragraphs(
        text: str,
        consumed: list[tuple[int, int]],
        elements: list[ContentElement],
    ) -> None:
        """Find paragraph-like text not covered by other elements."""
        consumed_sorted = sorted(consumed)
        prev_end = 0
        for start, end in consumed_sorted:
            gap = text[prev_end:start]
            for para in re.split(r"\n{2,}", gap):
                para = para.strip()
                if para and not re.match(r"^#{1,6}\s", para):
                    elements.append(
                        ContentElement(type=ElementType.PARAGRAPH, content=para)
                    )
            prev_end = max(prev_end, end)
        # Trailing text
        gap = text[prev_end:]
        for para in re.split(r"\n{2,}", gap):
            para = para.strip()
            if para and not re.match(r"^#{1,6}\s", para):
                elements.append(
                    ContentElement(type=ElementType.PARAGRAPH, content=para)
                )
