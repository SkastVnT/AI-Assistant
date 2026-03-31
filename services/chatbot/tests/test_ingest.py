"""
Tests for document parsers and chunking.

Run from services/chatbot/:
    python -m pytest tests/test_ingest.py -v
"""
import textwrap

import pytest


# ── Parser tests ───────────────────────────────────────────────────────────


class TestPlainTextParser:
    def test_parse_utf8(self):
        from src.rag.ingest.parsers import PlainTextParser

        p = PlainTextParser()
        doc = p.parse(b"Hello world", source="readme.txt")
        assert doc.mime_type == "text/plain"
        assert doc.page_count == 1
        assert doc.pages[0].text == "Hello world"
        assert doc.pages[0].page_number == 1

    def test_markdown_mime(self):
        from src.rag.ingest.parsers import PlainTextParser

        doc = PlainTextParser().parse(b"# Title", source="notes.md")
        assert doc.mime_type == "text/markdown"

    def test_full_text(self):
        from src.rag.ingest.parsers import PlainTextParser

        doc = PlainTextParser().parse(b"line one", source="a.txt")
        assert doc.full_text == "line one"


class TestHTMLParser:
    def test_strips_script_and_style(self):
        from src.rag.ingest.parsers import HTMLParser

        html = b"""<html>
        <head><title>Test</title><style>body{color:red}</style></head>
        <body>
            <script>alert('xss')</script>
            <p>Visible text</p>
        </body></html>"""
        doc = HTMLParser().parse(html, source="page.html")
        assert "alert" not in doc.full_text
        assert "color:red" not in doc.full_text
        assert "Visible text" in doc.full_text
        assert doc.metadata.get("title") == "Test"

    def test_collapses_whitespace(self):
        from src.rag.ingest.parsers import HTMLParser

        html = b"<p>A</p><p>B</p><p>C</p>"
        doc = HTMLParser().parse(html)
        lines = [ln for ln in doc.full_text.splitlines() if ln.strip()]
        assert len(lines) == 3


class TestPDFParser:
    def test_parse_simple_pdf(self):
        """Build a minimal single-page PDF in memory and verify parsing."""
        import fitz

        from src.rag.ingest.parsers import PDFParser

        # Create a 1-page PDF with known text
        pdf_doc = fitz.open()
        page = pdf_doc.new_page()
        page.insert_text((72, 72), "Hello from PDF page 1")
        data = pdf_doc.tobytes()
        pdf_doc.close()

        parsed = PDFParser().parse(data, source="test.pdf")
        assert parsed.mime_type == "application/pdf"
        assert parsed.page_count == 1
        assert "Hello from PDF page 1" in parsed.pages[0].text
        assert parsed.pages[0].page_number == 1

    def test_multi_page(self):
        import fitz

        from src.rag.ingest.parsers import PDFParser

        pdf_doc = fitz.open()
        for i in range(3):
            page = pdf_doc.new_page()
            page.insert_text((72, 72), f"Page {i + 1} content")
        data = pdf_doc.tobytes()
        pdf_doc.close()

        parsed = PDFParser().parse(data, source="multi.pdf")
        assert parsed.page_count == 3
        assert parsed.pages[2].page_number == 3
        assert "Page 3" in parsed.pages[2].text


class TestGetParser:
    def test_by_mime_type(self):
        from src.rag.ingest.parsers import HTMLParser, get_parser

        assert isinstance(get_parser(mime_type="text/html"), HTMLParser)

    def test_by_filename(self):
        from src.rag.ingest.parsers import PDFParser, get_parser

        assert isinstance(get_parser(filename="report.pdf"), PDFParser)

    def test_unknown_raises(self):
        from src.rag.ingest.parsers import get_parser

        with pytest.raises(ValueError, match="No parser"):
            get_parser(mime_type="application/zip")


# ── Chunking tests ─────────────────────────────────────────────────────────


class TestRecursiveTextChunker:
    def test_short_text_single_chunk(self):
        from src.rag.ingest.chunking_pkg import RecursiveTextChunker

        chunker = RecursiveTextChunker(max_chars=100, overlap_chars=10)
        chunks = chunker.chunk("Short text")
        assert len(chunks) == 1
        assert chunks[0].text == "Short text"
        assert chunks[0].chunk_index == 0

    def test_respects_max_chars(self):
        from src.rag.ingest.chunking_pkg import RecursiveTextChunker

        text = "word " * 200  # 1000 chars
        chunker = RecursiveTextChunker(max_chars=100, overlap_chars=20)
        chunks = chunker.chunk(text)
        for c in chunks:
            assert len(c.text) <= 100

    def test_overlap_present(self):
        from src.rag.ingest.chunking_pkg import RecursiveTextChunker

        text = "A " * 100  # 200 chars
        chunker = RecursiveTextChunker(max_chars=50, overlap_chars=10)
        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        # Overlap means end of chunk N should appear at start of chunk N+1
        for i in range(len(chunks) - 1):
            tail = chunks[i].text[-8:]
            assert tail in chunks[i + 1].text

    def test_metadata_carry_over(self):
        from src.rag.ingest.chunking_pkg import RecursiveTextChunker

        chunker = RecursiveTextChunker(max_chars=50, overlap_chars=5)
        chunks = chunker.chunk("x " * 100, metadata={"source": "test.txt"})
        for c in chunks:
            assert c.metadata["source"] == "test.txt"

    def test_empty_text(self):
        from src.rag.ingest.chunking_pkg import RecursiveTextChunker

        assert RecursiveTextChunker().chunk("") == []
        assert RecursiveTextChunker().chunk("   ") == []

    def test_overlap_must_be_less_than_max(self):
        from src.rag.ingest.chunking_pkg import RecursiveTextChunker

        with pytest.raises(ValueError, match="overlap_chars must be less"):
            RecursiveTextChunker(max_chars=50, overlap_chars=50)

    def test_chunk_index_sequential(self):
        from src.rag.ingest.chunking_pkg import RecursiveTextChunker

        chunks = RecursiveTextChunker(max_chars=30, overlap_chars=5).chunk("hello " * 50)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))


class TestChunkPages:
    def test_page_number_in_metadata(self):
        from src.rag.ingest.chunking_pkg import chunk_pages

        pages = [
            {"text": "First page content here.", "page_number": 1},
            {"text": "Second page content here.", "page_number": 2},
        ]
        chunks = chunk_pages(pages, max_chars=500, overlap_chars=10)
        assert chunks[0].metadata["page_number"] == 1
        assert chunks[1].metadata["page_number"] == 2

    def test_global_index(self):
        from src.rag.ingest.chunking_pkg import chunk_pages

        pages = [
            {"text": "A " * 100, "page_number": 1},
            {"text": "B " * 100, "page_number": 2},
        ]
        chunks = chunk_pages(pages, max_chars=50, overlap_chars=5)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))


# ── Integration: parse → chunk ─────────────────────────────────────────────


class TestParseAndChunk:
    def test_plaintext_to_chunks(self):
        from src.rag.ingest.chunking_pkg import chunk_pages
        from src.rag.ingest.parsers import PlainTextParser

        text = ("This is paragraph one. " * 20 + "\n\n" + "Second paragraph. " * 20)
        parsed = PlainTextParser().parse(text.encode(), source="doc.txt")
        pages = [
            {
                "text": p.text,
                "page_number": p.page_number,
                "metadata": {"source": parsed.source},
            }
            for p in parsed.pages
        ]
        chunks = chunk_pages(pages, max_chars=100, overlap_chars=20)
        assert len(chunks) > 1
        assert all(c.metadata.get("source") == "doc.txt" for c in chunks)
        assert all(c.metadata.get("page_number") == 1 for c in chunks)

    def test_html_to_chunks(self):
        from src.rag.ingest.chunking_pkg import chunk_pages
        from src.rag.ingest.parsers import HTMLParser

        html = b"<p>" + b"Hello world. " * 50 + b"</p>"
        parsed = HTMLParser().parse(html, source="page.html")
        pages = [{"text": p.text, "page_number": p.page_number} for p in parsed.pages]
        chunks = chunk_pages(pages, max_chars=80, overlap_chars=10)
        assert len(chunks) > 1
        assert chunks[0].chunk_index == 0
