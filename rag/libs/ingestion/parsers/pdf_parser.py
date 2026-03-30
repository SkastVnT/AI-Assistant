"""PDF parser with swappable backend adapter.

Default backend: PyMuPDF (fitz).
The PdfBackend protocol allows replacing it with a VLM-based parser,
Unstructured.io, or any other PDF extraction library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from libs.ingestion.parsers.base import (
    ContentElement,
    ElementType,
    ParseResult,
)

# ---------------------------------------------------------------------------
# PDF backend protocol
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PdfTextBlock:
    """A bounding-box text span on one page."""

    text: str
    font_size: float = 12.0
    is_bold: bool = False
    bbox: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class PdfPage:
    """Extracted content for a single PDF page."""

    page_number: int  # 1-based
    blocks: list[PdfTextBlock] = field(default_factory=list)
    raw_text: str = ""


@runtime_checkable
class PdfBackend(Protocol):
    """Swappable PDF extraction backend."""

    def extract_pages(self, content: bytes) -> list[PdfPage]:
        """Extract pages from raw PDF bytes."""
        ...


# ---------------------------------------------------------------------------
# PyMuPDF backend (default)
# ---------------------------------------------------------------------------


class PyMuPdfBackend:
    """PDF extraction using PyMuPDF (fitz)."""

    def extract_pages(self, content: bytes) -> list[PdfPage]:
        try:
            import fitz  # PyMuPDF
        except ImportError as exc:
            raise ImportError(
                "PyMuPDF is required for PDF parsing. "
                "Install with: pip install PyMuPDF"
            ) from exc

        doc = fitz.open(stream=content, filetype="pdf")
        pages: list[PdfPage] = []

        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                raw_text = page.get_text("text")

                blocks: list[PdfTextBlock] = []
                block_dicts = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)

                for block in block_dicts.get("blocks", []):
                    if block.get("type") != 0:  # text block
                        continue
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                blocks.append(
                                    PdfTextBlock(
                                        text=text,
                                        font_size=span.get("size", 12.0),
                                        is_bold="bold" in span.get("font", "").lower(),
                                        bbox=tuple(span.get("bbox", (0, 0, 0, 0))),
                                    )
                                )

                pages.append(
                    PdfPage(
                        page_number=page_idx + 1,
                        blocks=blocks,
                        raw_text=raw_text,
                    )
                )
        finally:
            doc.close()

        return pages


# ---------------------------------------------------------------------------
# PDF parser (uses backend adapter)
# ---------------------------------------------------------------------------

# Heading detection heuristics
_DEFAULT_BODY_FONT_SIZE = 12.0
_HEADING_FONT_RATIO = 1.2  # 20% larger than body = heading


class PdfParser:
    """Parses PDF files into structured elements.

    Uses the adapter pattern: supply a PdfBackend to change extraction.
    Default: PyMuPdfBackend.
    """

    def __init__(self, backend: PdfBackend | None = None) -> None:
        self._backend = backend or PyMuPdfBackend()

    @property
    def supported_extensions(self) -> set[str]:
        return {".pdf"}

    def parse(self, content: bytes, filename: str) -> ParseResult:
        pages = self._backend.extract_pages(content)

        if not pages:
            return ParseResult(
                elements=[], title=None, raw_text="", metadata={"page_count": 0}
            )

        # Determine median body font size for heading detection
        all_sizes = [b.font_size for p in pages for b in p.blocks if b.text.strip()]
        body_size = _median(all_sizes) if all_sizes else _DEFAULT_BODY_FONT_SIZE

        elements: list[ContentElement] = []
        title: str | None = None
        raw_parts: list[str] = []

        for page in pages:
            raw_parts.append(page.raw_text)

            # Group consecutive blocks into paragraphs
            current_paragraph: list[str] = []

            for block in page.blocks:
                text = block.text.strip()
                if not text:
                    if current_paragraph:
                        elements.append(
                            ContentElement(
                                type=ElementType.PARAGRAPH,
                                content=" ".join(current_paragraph),
                                page=page.page_number,
                            )
                        )
                        current_paragraph = []
                    continue

                is_heading = (
                    block.font_size > body_size * _HEADING_FONT_RATIO or block.is_bold
                ) and len(text) < 200

                if is_heading:
                    # Flush any pending paragraph
                    if current_paragraph:
                        elements.append(
                            ContentElement(
                                type=ElementType.PARAGRAPH,
                                content=" ".join(current_paragraph),
                                page=page.page_number,
                            )
                        )
                        current_paragraph = []

                    level = self._estimate_heading_level(block.font_size, body_size)
                    elements.append(
                        ContentElement(
                            type=ElementType.HEADING,
                            content=text,
                            level=level,
                            page=page.page_number,
                        )
                    )
                    if title is None:
                        title = text
                else:
                    current_paragraph.append(text)

            # Flush trailing paragraph
            if current_paragraph:
                elements.append(
                    ContentElement(
                        type=ElementType.PARAGRAPH,
                        content=" ".join(current_paragraph),
                        page=page.page_number,
                    )
                )

            # Page break between pages (except last)
            if page.page_number < len(pages):
                elements.append(
                    ContentElement(
                        type=ElementType.PAGE_BREAK,
                        content="",
                        page=page.page_number,
                    )
                )

        return ParseResult(
            elements=elements,
            title=title,
            raw_text="\n\n".join(raw_parts),
            metadata={
                "page_count": len(pages),
                "format": "pdf",
            },
        )

    @staticmethod
    def _estimate_heading_level(font_size: float, body_size: float) -> int:
        ratio = font_size / body_size if body_size > 0 else 1.0
        if ratio > 2.0:
            return 1
        if ratio > 1.6:
            return 2
        if ratio > 1.3:
            return 3
        return 4


def _median(values: list[float]) -> float:
    """Return the median of a non-empty list."""
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return (s[mid - 1] + s[mid]) / 2.0
    return s[mid]
