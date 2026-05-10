"""Metadata extraction from parsed content.

Runs after normalization to derive document-level metadata
from the structured parse result.
"""

from __future__ import annotations

from collections import Counter
from pathlib import PurePath

from libs.ingestion.parsers.base import ElementType, ParseResult


def extract_metadata(parse_result: ParseResult, filename: str) -> dict:
    """Derive document-level metadata from a ParseResult."""
    metadata: dict = {}

    # Title: from parse result, or first heading, or filename stem
    if parse_result.title:
        metadata["detected_title"] = parse_result.title
    else:
        for e in parse_result.elements:
            if e.type in (ElementType.TITLE, ElementType.HEADING):
                metadata["detected_title"] = e.content
                break
        else:
            metadata["detected_title"] = PurePath(filename).stem

    # Word count
    if parse_result.raw_text:
        metadata["word_count"] = len(parse_result.raw_text.split())

    # Page count (from element page references)
    pages = {e.page for e in parse_result.elements if e.page is not None}
    if pages:
        metadata["page_count"] = max(pages)

    # Element-type distribution
    type_counts = Counter(e.type.value for e in parse_result.elements)
    metadata["element_counts"] = dict(type_counts)

    # Propagate parser-level metadata
    metadata.update(parse_result.metadata)

    return metadata
