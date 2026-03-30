"""Document parsers — adapter-based extraction for multiple file types."""

from libs.ingestion.parsers.base import (
    ContentElement,
    DocumentParser,
    ElementType,
    ParseResult,
)
from libs.ingestion.parsers.registry import get_parser, get_supported_extensions

__all__ = [
    "ContentElement",
    "DocumentParser",
    "ElementType",
    "ParseResult",
    "get_parser",
    "get_supported_extensions",
]
