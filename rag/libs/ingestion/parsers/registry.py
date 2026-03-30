"""Parser registry — maps file extensions to parser instances."""

from __future__ import annotations

from pathlib import PurePath

from libs.ingestion.parsers.base import DocumentParser, ParseResult
from libs.ingestion.parsers.html_parser import HtmlParser
from libs.ingestion.parsers.markdown_parser import MarkdownParser
from libs.ingestion.parsers.text_parser import TextParser

# PDF parser is lazy-loaded to avoid hard dependency on PyMuPDF
_pdf_parser: DocumentParser | None = None


def _get_pdf_parser() -> DocumentParser:
    global _pdf_parser
    if _pdf_parser is None:
        from libs.ingestion.parsers.pdf_parser import PdfParser

        _pdf_parser = PdfParser()
    return _pdf_parser


# Extension → parser mapping (built once)
_PARSERS: list[DocumentParser] = [
    TextParser(),
    MarkdownParser(),
    HtmlParser(),
]

_EXT_MAP: dict[str, DocumentParser] = {}
for _p in _PARSERS:
    for _ext in _p.supported_extensions:
        _EXT_MAP[_ext] = _p


def get_parser(filename: str) -> DocumentParser:
    """Return the appropriate parser for a file, based on extension.

    Raises ValueError if no parser supports the file type.
    """
    ext = PurePath(filename).suffix.lower()

    # Check static parsers first
    if ext in _EXT_MAP:
        return _EXT_MAP[ext]

    # Check PDF (lazy)
    if ext == ".pdf":
        return _get_pdf_parser()

    supported = get_supported_extensions()
    raise ValueError(
        f"Unsupported file type: '{ext}'. Supported: {', '.join(sorted(supported))}"
    )


def get_supported_extensions() -> set[str]:
    """Return all file extensions we can parse."""
    exts = set(_EXT_MAP.keys())
    exts.add(".pdf")
    return exts


def parse_document(content: bytes, filename: str) -> ParseResult:
    """Convenience: find the right parser and parse in one call."""
    parser = get_parser(filename)
    return parser.parse(content, filename)
