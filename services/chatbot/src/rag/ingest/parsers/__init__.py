"""
src.rag.ingest.parsers — Document format parsers.

Auto-selects the right parser based on MIME type or file extension.
"""
from __future__ import annotations

from .base import DocumentParser, PageContent, ParsedDocument
from .html_bs4 import HTMLParser
from .pdf_pymupdf import PDFParser
from .plaintext import PlainTextParser

__all__ = [
    "DocumentParser",
    "PageContent",
    "ParsedDocument",
    "PlainTextParser",
    "HTMLParser",
    "PDFParser",
    "get_parser",
]

_EXT_TO_MIME: dict[str, str] = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".html": "text/html",
    ".htm": "text/html",
    ".pdf": "application/pdf",
}

_PARSERS: list[DocumentParser] = [
    PlainTextParser(),
    HTMLParser(),
    PDFParser(),
]

_MIME_MAP: dict[str, DocumentParser] = {}
for _p in _PARSERS:
    for _m in _p.supported_mime_types():
        _MIME_MAP[_m] = _p


def get_parser(
    mime_type: str | None = None,
    filename: str | None = None,
) -> DocumentParser:
    """Return a parser for the given MIME type or filename extension.

    Raises ``ValueError`` if no parser matches.
    """
    if mime_type and mime_type in _MIME_MAP:
        return _MIME_MAP[mime_type]

    if filename:
        import os

        ext = os.path.splitext(filename)[1].lower()
        resolved = _EXT_TO_MIME.get(ext)
        if resolved and resolved in _MIME_MAP:
            return _MIME_MAP[resolved]

    raise ValueError(
        f"No parser for mime_type={mime_type!r}, filename={filename!r}. "
        f"Supported: {sorted(_MIME_MAP)}"
    )
