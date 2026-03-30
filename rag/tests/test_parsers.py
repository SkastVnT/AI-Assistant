"""Tests for document parser adapters.

Covers: TextParser, MarkdownParser, HtmlParser, PdfParser (with mock backend),
        registry lookup, normalizer, and metadata extractor.
"""

import pytest

from libs.ingestion.metadata_extractor import extract_metadata
from libs.ingestion.normalizer import normalize_parse_result, normalize_text
from libs.ingestion.parsers.base import (
    ContentElement,
    DocumentParser,
    ElementType,
    ParseResult,
)
from libs.ingestion.parsers.html_parser import HtmlParser
from libs.ingestion.parsers.markdown_parser import MarkdownParser
from libs.ingestion.parsers.pdf_parser import PdfBackend, PdfPage, PdfParser, PdfTextBlock
from libs.ingestion.parsers.registry import get_parser, get_supported_extensions, parse_document
from libs.ingestion.parsers.text_parser import TextParser

# ====================================================================
# Protocol conformance
# ====================================================================


class TestProtocolConformance:
    def test_text_parser_is_document_parser(self):
        assert isinstance(TextParser(), DocumentParser)

    def test_markdown_parser_is_document_parser(self):
        assert isinstance(MarkdownParser(), DocumentParser)

    def test_html_parser_is_document_parser(self):
        assert isinstance(HtmlParser(), DocumentParser)

    def test_pdf_parser_is_document_parser(self):
        assert isinstance(PdfParser(), DocumentParser)


# ====================================================================
# TextParser
# ====================================================================


class TestTextParser:
    def setup_method(self):
        self.parser = TextParser()

    def test_supported_extensions(self):
        assert ".txt" in self.parser.supported_extensions
        assert ".text" in self.parser.supported_extensions

    def test_parse_simple_text(self):
        content = b"Document Title\n\nFirst paragraph here.\n\nSecond paragraph."
        result = self.parser.parse(content, "test.txt")

        assert result.title == "Document Title"
        assert len(result.elements) == 3
        assert result.elements[0].type == ElementType.TITLE
        assert result.elements[0].content == "Document Title"
        assert result.elements[1].type == ElementType.PARAGRAPH
        assert result.elements[2].type == ElementType.PARAGRAPH
        assert result.raw_text == content.decode("utf-8")

    def test_parse_empty(self):
        result = self.parser.parse(b"", "empty.txt")
        assert result.elements == []
        assert result.title is None

    def test_parse_single_line(self):
        result = self.parser.parse(b"Just a title", "one.txt")
        assert len(result.elements) == 1
        assert result.elements[0].type == ElementType.TITLE
        assert result.title == "Just a title"

    def test_parse_utf8_content(self):
        content = "Tiêu đề\n\nNội dung tiếng Việt.".encode()
        result = self.parser.parse(content, "vn.txt")
        assert result.title == "Tiêu đề"
        assert "tiếng Việt" in result.raw_text

    def test_serialization_roundtrip(self):
        content = b"Title\n\nBody text here."
        result = self.parser.parse(content, "test.txt")
        d = result.to_dict()
        restored = ParseResult.from_dict(d)
        assert restored.title == result.title
        assert len(restored.elements) == len(result.elements)


# ====================================================================
# MarkdownParser
# ====================================================================


class TestMarkdownParser:
    def setup_method(self):
        self.parser = MarkdownParser()

    def test_supported_extensions(self):
        exts = self.parser.supported_extensions
        assert ".md" in exts
        assert ".markdown" in exts

    def test_parse_headings(self):
        md = b"# Main Title\n\nSome text.\n\n## Section\n\nMore text."
        result = self.parser.parse(md, "test.md")

        assert result.title == "Main Title"
        headings = [e for e in result.elements if e.type == ElementType.HEADING]
        assert len(headings) == 2
        assert headings[0].level == 1
        assert headings[1].level == 2

    def test_parse_code_block(self):
        md = b"# Title\n\n```python\nprint('hello')\n```\n\nAfter code."
        result = self.parser.parse(md, "code.md")

        code_blocks = [e for e in result.elements if e.type == ElementType.CODE_BLOCK]
        assert len(code_blocks) == 1
        assert "print('hello')" in code_blocks[0].content
        assert code_blocks[0].metadata.get("language") == "python"

    def test_parse_table(self):
        md = b"| Col1 | Col2 |\n| --- | --- |\n| a | b |\n| c | d |\n"
        result = self.parser.parse(md, "table.md")

        tables = [e for e in result.elements if e.type == ElementType.TABLE]
        assert len(tables) == 1
        assert "Col1" in tables[0].content

    def test_parse_blockquote(self):
        md = b"> This is a quote\n> continued here\n\nNormal text."
        result = self.parser.parse(md, "quote.md")

        quotes = [e for e in result.elements if e.type == ElementType.BLOCKQUOTE]
        assert len(quotes) == 1
        assert "quote" in quotes[0].content.lower()

    def test_parse_list_items(self):
        md = b"- Item 1\n- Item 2\n- Item 3\n"
        result = self.parser.parse(md, "list.md")

        items = [e for e in result.elements if e.type == ElementType.LIST_ITEM]
        assert len(items) >= 1  # may group into one element

    def test_parse_paragraphs(self):
        md = b"# Title\n\nFirst paragraph.\n\nSecond paragraph."
        result = self.parser.parse(md, "para.md")

        paras = [e for e in result.elements if e.type == ElementType.PARAGRAPH]
        assert len(paras) == 2


# ====================================================================
# HtmlParser
# ====================================================================


class TestHtmlParser:
    def setup_method(self):
        self.parser = HtmlParser()

    def test_supported_extensions(self):
        assert ".html" in self.parser.supported_extensions
        assert ".htm" in self.parser.supported_extensions

    def test_parse_basic_html(self):
        html = b"""<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
<h1>Main Heading</h1>
<p>A paragraph.</p>
<h2>Sub Heading</h2>
<p>Another paragraph.</p>
</body>
</html>"""
        result = self.parser.parse(html, "test.html")

        assert result.title == "Test Page"
        headings = [e for e in result.elements if e.type == ElementType.HEADING]
        assert len(headings) == 2
        assert headings[0].level == 1
        assert headings[1].level == 2

        paras = [e for e in result.elements if e.type == ElementType.PARAGRAPH]
        assert len(paras) == 2

    def test_parse_table(self):
        html = b"""<table>
<tr><th>Name</th><th>Age</th></tr>
<tr><td>Alice</td><td>30</td></tr>
</table>"""
        result = self.parser.parse(html, "table.html")

        tables = [e for e in result.elements if e.type == ElementType.TABLE]
        assert len(tables) == 1
        assert "Alice" in tables[0].content

    def test_parse_code_block(self):
        html = b"<pre><code class='language-js'>console.log('hi')</code></pre>"
        result = self.parser.parse(html, "code.html")

        codes = [e for e in result.elements if e.type == ElementType.CODE_BLOCK]
        assert len(codes) == 1
        assert "console.log" in codes[0].content

    def test_parse_list(self):
        html = b"<ul><li>One</li><li>Two</li></ul>"
        result = self.parser.parse(html, "list.html")

        items = [e for e in result.elements if e.type == ElementType.LIST_ITEM]
        assert len(items) == 2

    def test_parse_blockquote(self):
        html = b"<blockquote>A wise quote</blockquote>"
        result = self.parser.parse(html, "bq.html")

        bqs = [e for e in result.elements if e.type == ElementType.BLOCKQUOTE]
        assert len(bqs) == 1

    def test_raw_text(self):
        html = b"<p>Hello World</p>"
        result = self.parser.parse(html, "raw.html")
        assert "Hello World" in result.raw_text

    def test_title_fallback_to_h1(self):
        html = b"<body><h1>H1 Title</h1><p>text</p></body>"
        result = self.parser.parse(html, "notitle.html")
        assert result.title == "H1 Title"


# ====================================================================
# PdfParser (with mock backend)
# ====================================================================


class MockPdfBackend:
    """Test double for PdfBackend — returns canned pages."""

    def __init__(self, pages: list[PdfPage] | None = None):
        self._pages = pages or []

    def extract_pages(self, content: bytes) -> list[PdfPage]:
        return self._pages


class TestPdfParser:
    def test_protocol_conformance(self):
        assert isinstance(MockPdfBackend(), PdfBackend)

    def test_parse_empty_pdf(self):
        backend = MockPdfBackend(pages=[])
        parser = PdfParser(backend=backend)
        result = parser.parse(b"fake-pdf", "empty.pdf")

        assert result.elements == []
        assert result.title is None
        assert result.metadata["page_count"] == 0

    def test_parse_single_page(self):
        blocks = [
            PdfTextBlock(text="Document Title", font_size=24.0, is_bold=True),
            PdfTextBlock(text="This is body text in the first paragraph.", font_size=12.0),
            PdfTextBlock(text="Another sentence continues the paragraph.", font_size=12.0),
        ]
        page = PdfPage(
            page_number=1,
            blocks=blocks,
            raw_text="Document Title\nThis is body text...",
        )
        parser = PdfParser(backend=MockPdfBackend([page]))
        result = parser.parse(b"fake-pdf", "doc.pdf")

        assert result.title == "Document Title"
        headings = [e for e in result.elements if e.type == ElementType.HEADING]
        assert len(headings) >= 1
        assert headings[0].content == "Document Title"
        assert headings[0].page == 1

    def test_parse_multi_page(self):
        page1 = PdfPage(
            page_number=1,
            blocks=[
                PdfTextBlock(text="Chapter 1", font_size=20.0, is_bold=True),
                PdfTextBlock(text="Content on page 1.", font_size=12.0),
            ],
            raw_text="Chapter 1\nContent on page 1.",
        )
        page2 = PdfPage(
            page_number=2,
            blocks=[
                PdfTextBlock(text="Chapter 2", font_size=20.0, is_bold=True),
                PdfTextBlock(text="Content on page 2.", font_size=12.0),
            ],
            raw_text="Chapter 2\nContent on page 2.",
        )
        parser = PdfParser(backend=MockPdfBackend([page1, page2]))
        result = parser.parse(b"fake-pdf", "multi.pdf")

        assert result.metadata["page_count"] == 2
        # Should have page breaks between pages
        page_breaks = [e for e in result.elements if e.type == ElementType.PAGE_BREAK]
        assert len(page_breaks) == 1

    def test_heading_level_detection(self):
        blocks = [
            PdfTextBlock(text="Big Title", font_size=30.0),
            PdfTextBlock(text="Medium Heading", font_size=18.0),
            PdfTextBlock(text="Small Heading", font_size=15.0, is_bold=True),
            PdfTextBlock(text="Body text that is normal.", font_size=12.0),
            PdfTextBlock(text="More body text for median.", font_size=12.0),
            PdfTextBlock(text="Even more body text.", font_size=12.0),
        ]
        page = PdfPage(page_number=1, blocks=blocks, raw_text="...")
        parser = PdfParser(backend=MockPdfBackend([page]))
        result = parser.parse(b"fake-pdf", "levels.pdf")

        headings = [e for e in result.elements if e.type == ElementType.HEADING]
        # Big Title at 30pt vs median ~12pt → level 1
        assert headings[0].level == 1
        # Smaller headings should have higher level numbers
        assert all(h.level is not None for h in headings)


# ====================================================================
# Registry
# ====================================================================


class TestRegistry:
    def test_get_parser_txt(self):
        parser = get_parser("document.txt")
        assert isinstance(parser, TextParser)

    def test_get_parser_md(self):
        parser = get_parser("readme.md")
        assert isinstance(parser, MarkdownParser)

    def test_get_parser_html(self):
        parser = get_parser("page.html")
        assert isinstance(parser, HtmlParser)

    def test_get_parser_htm(self):
        parser = get_parser("page.htm")
        assert isinstance(parser, HtmlParser)

    def test_get_parser_pdf(self):
        parser = get_parser("file.pdf")
        assert isinstance(parser, PdfParser)

    def test_get_parser_unsupported(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            get_parser("data.xlsx")

    def test_supported_extensions(self):
        exts = get_supported_extensions()
        assert ".txt" in exts
        assert ".md" in exts
        assert ".html" in exts
        assert ".pdf" in exts

    def test_parse_document_convenience(self):
        result = parse_document(b"Hello world", "simple.txt")
        assert result.raw_text == "Hello world"


# ====================================================================
# Normalizer
# ====================================================================


class TestNormalizer:
    def test_normalize_text_whitespace(self):
        text = "  hello   world  \n\n\n\nfoo  "
        result = normalize_text(text)
        assert result == "hello world\n\nfoo"

    def test_normalize_text_line_endings(self):
        assert normalize_text("a\r\nb\rc") == "a\nb\nc"

    def test_normalize_text_null_bytes(self):
        assert normalize_text("ab\x00cd") == "abcd"

    def test_normalize_text_unicode(self):
        # NFC normalization: combining accent → precomposed
        import unicodedata

        decomposed = unicodedata.normalize("NFD", "café")
        result = normalize_text(decomposed)
        assert result == "café"
        assert unicodedata.is_normalized("NFC", result)

    def test_normalize_parse_result_drops_empty(self):
        result = ParseResult(
            elements=[
                ContentElement(type=ElementType.PARAGRAPH, content="  keep me  "),
                ContentElement(type=ElementType.PARAGRAPH, content="   "),  # empty
                ContentElement(type=ElementType.PAGE_BREAK, content=""),  # keep
            ],
            raw_text="  keep me  ",
        )
        normalized = normalize_parse_result(result)
        assert len(normalized.elements) == 2  # paragraph + page_break
        assert normalized.elements[0].content == "keep me"
        assert normalized.raw_text == "keep me"


# ====================================================================
# Metadata Extractor
# ====================================================================


class TestMetadataExtractor:
    def test_extract_title_from_parse_result(self):
        result = ParseResult(
            elements=[ContentElement(type=ElementType.PARAGRAPH, content="body")],
            title="My Document",
            raw_text="body",
        )
        meta = extract_metadata(result, "file.txt")
        assert meta["detected_title"] == "My Document"

    def test_extract_title_from_heading(self):
        result = ParseResult(
            elements=[
                ContentElement(type=ElementType.HEADING, content="Heading Title", level=1),
            ],
            title=None,
            raw_text="Heading Title",
        )
        meta = extract_metadata(result, "file.txt")
        assert meta["detected_title"] == "Heading Title"

    def test_extract_title_fallback_to_filename(self):
        result = ParseResult(elements=[], title=None, raw_text="")
        meta = extract_metadata(result, "my_report.pdf")
        assert meta["detected_title"] == "my_report"

    def test_word_count(self):
        result = ParseResult(
            elements=[], title=None, raw_text="one two three four five"
        )
        meta = extract_metadata(result, "f.txt")
        assert meta["word_count"] == 5

    def test_page_count(self):
        result = ParseResult(
            elements=[
                ContentElement(type=ElementType.PARAGRAPH, content="p1", page=1),
                ContentElement(type=ElementType.PARAGRAPH, content="p3", page=3),
            ],
            title=None,
            raw_text="p1 p3",
        )
        meta = extract_metadata(result, "f.pdf")
        assert meta["page_count"] == 3

    def test_element_counts(self):
        result = ParseResult(
            elements=[
                ContentElement(type=ElementType.HEADING, content="h", level=1),
                ContentElement(type=ElementType.PARAGRAPH, content="p1"),
                ContentElement(type=ElementType.PARAGRAPH, content="p2"),
            ],
            title="h",
            raw_text="h p1 p2",
        )
        meta = extract_metadata(result, "f.md")
        assert meta["element_counts"]["heading"] == 1
        assert meta["element_counts"]["paragraph"] == 2
