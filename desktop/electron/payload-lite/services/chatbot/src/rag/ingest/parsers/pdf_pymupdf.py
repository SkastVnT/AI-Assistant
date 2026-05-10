"""
PDF parser using PyMuPDF (``fitz``).

Extracts text page-by-page, preserving page numbers in metadata.
"""
from __future__ import annotations

from .base import DocumentParser, PageContent, ParsedDocument


class PDFParser(DocumentParser):
    """Handles ``application/pdf``."""

    def supported_mime_types(self) -> list[str]:
        return ["application/pdf"]

    def parse(self, data: bytes, source: str = "") -> ParsedDocument:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=data, filetype="pdf")
        pages: list[PageContent] = []
        metadata: dict = {}

        # Extract PDF-level metadata
        pdf_meta = doc.metadata or {}
        if pdf_meta.get("title"):
            metadata["title"] = pdf_meta["title"]
        if pdf_meta.get("author"):
            metadata["author"] = pdf_meta["author"]

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            if text:
                pages.append(
                    PageContent(
                        text=text,
                        page_number=page_num + 1,  # 1-indexed
                    )
                )

        doc.close()

        return ParsedDocument(
            source=source,
            mime_type="application/pdf",
            pages=pages,
            metadata=metadata,
        )
