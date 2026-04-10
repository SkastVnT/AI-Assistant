"""
Tests for evidence_gathering module and ResearcherAgent evidence integration.

Covers:
  • gather_all — full pipeline with all sources
  • _extract_uploaded_file_evidence — file block parsing
  • _extract_rag_evidence — RAG chunk/citation conversion
  • _extract_mcp_evidence — MCP section parsing + fallback
  • _extract_direct_context — inline code fence extraction
  • _enforce_budget — budget cap with relevance ranking
  • _truncate — snippet truncation
  • ResearcherAgent._gather_pre_evidence — PreContext → evidence
  • ResearcherAgent._merge_evidence — dedup + merge
  • ResearcherAgent._format_evidence_for_llm — compact formatting
  • ResearcherAgent._tools_from_evidence — source→tool mapping
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.agentic.contracts import EvidenceItem, PlannerOutput, ResearcherOutput, TaskNode
from core.agentic.evidence_gathering import (
    DEFAULT_BUDGET_CHARS,
    MAX_MCP_ITEMS,
    MAX_RAG_ITEMS,
    MAX_SNIPPET_CHARS,
    MAX_UPLOAD_ITEMS,
    SOURCE_DIRECT,
    SOURCE_MCP,
    SOURCE_RAG,
    SOURCE_UPLOADED_FILE,
    _enforce_budget,
    _extract_direct_context,
    _extract_mcp_evidence,
    _extract_rag_evidence,
    _extract_uploaded_file_evidence,
    _truncate,
    gather_all,
)
from core.agentic.agents.researcher import ResearcherAgent
from core.agentic.config import CouncilConfig
from core.agentic.state import PreContext


# ═══════════════════════════════════════════════════════════════════════
# _truncate
# ═══════════════════════════════════════════════════════════════════════


class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello", 100) == "hello"

    def test_long_text_truncated(self):
        text = "a" * 200
        result = _truncate(text, 50)
        assert len(result) == 50
        assert result.endswith(" ...")

    def test_exact_boundary(self):
        text = "a" * 100
        assert _truncate(text, 100) == text


# ═══════════════════════════════════════════════════════════════════════
# Uploaded file evidence
# ═══════════════════════════════════════════════════════════════════════


class TestUploadedFileEvidence:
    def test_no_marker_returns_empty(self):
        result = _extract_uploaded_file_evidence("just a question")
        assert result == []

    def test_parse_file_blocks(self):
        msg = """
--- UPLOADED FILES ---

[File: report.pdf]:
```pdf
This is the extracted PDF content with analysis data.
```

[Audio transcript from meeting.mp3]:
The transcript of the audio recording about Q4 results.

--- END FILES ---

What does this report say?
"""
        result = _extract_uploaded_file_evidence(msg)
        assert len(result) == 2

        assert result[0].source == SOURCE_UPLOADED_FILE
        assert result[0].url == "report.pdf"
        assert "PDF content" in result[0].content

        assert result[1].source == SOURCE_UPLOADED_FILE
        assert result[1].url == "meeting.mp3"
        assert "transcript" in result[1].content

    def test_cap_at_max(self):
        blocks = "\n".join(
            f"[File: file{i}.txt]:\nContent number {i} has some text here.\n"
            for i in range(20)
        )
        msg = f"--- UPLOADED FILES ---\n{blocks}\n--- END FILES ---"
        result = _extract_uploaded_file_evidence(msg)
        assert len(result) <= MAX_UPLOAD_ITEMS


# ═══════════════════════════════════════════════════════════════════════
# RAG evidence
# ═══════════════════════════════════════════════════════════════════════


class TestRAGEvidence:
    def test_empty_chunks(self):
        assert _extract_rag_evidence([], []) == []

    def test_basic_chunks(self):
        chunks = [
            {"content": "Paris is the capital of France.", "score": 0.95, "chunk_id": "c1"},
            {"content": "Berlin is the capital of Germany.", "score": 0.88, "chunk_id": "c2"},
        ]
        result = _extract_rag_evidence(chunks, [])
        assert len(result) == 2
        assert result[0].source == SOURCE_RAG
        assert result[0].relevance == 0.95
        assert "Paris" in result[0].content

    def test_citation_metadata_used(self):
        chunks = [{"content": "Some content", "chunk_id": "c1", "score": 0.9}]
        citations = [{"chunk_id": "c1", "doc_name": "geography-guide.pdf"}]
        result = _extract_rag_evidence(chunks, citations)
        assert result[0].url == "geography-guide.pdf"

    def test_cap_at_max(self):
        chunks = [{"content": f"Chunk {i}"} for i in range(20)]
        result = _extract_rag_evidence(chunks, [])
        assert len(result) <= MAX_RAG_ITEMS

    def test_empty_content_skipped(self):
        chunks = [{"content": ""}, {"content": "Real content"}]
        result = _extract_rag_evidence(chunks, [])
        assert len(result) == 1

    def test_invalid_score_defaults(self):
        chunks = [{"content": "data", "score": "invalid"}]
        result = _extract_rag_evidence(chunks, [])
        assert result[0].relevance == 0.7


# ═══════════════════════════════════════════════════════════════════════
# MCP evidence
# ═══════════════════════════════════════════════════════════════════════


class TestMCPEvidence:
    def test_empty_context(self):
        assert _extract_mcp_evidence("") == []
        assert _extract_mcp_evidence("   ") == []

    def test_structured_sections(self):
        mcp = """📄 **File: src/main.py** (Language: python)
```python
def hello():
    return "world"
```

📄 **File: README.md** (Language: markdown)
# Project Title
This is a description.
"""
        result = _extract_mcp_evidence(mcp)
        assert len(result) == 2
        assert result[0].source == SOURCE_MCP
        assert result[0].url == "src/main.py"
        assert "hello" in result[0].content
        assert result[1].url == "README.md"

    def test_fallback_single_block(self):
        mcp = "Here is some relevant code context that was retrieved from the workspace."
        result = _extract_mcp_evidence(mcp)
        assert len(result) == 1
        assert result[0].source == SOURCE_MCP
        assert result[0].url == "mcp-context"

    def test_short_context_ignored(self):
        result = _extract_mcp_evidence("tiny")
        assert result == []

    def test_cap_at_max(self):
        sections = "\n".join(
            f"📄 **File: file{i}.py** (Language: python)\ncode content {i}\n"
            for i in range(20)
        )
        result = _extract_mcp_evidence(sections)
        assert len(result) <= MAX_MCP_ITEMS


# ═══════════════════════════════════════════════════════════════════════
# Direct user context
# ═══════════════════════════════════════════════════════════════════════


class TestDirectContext:
    def test_empty_message(self):
        assert _extract_direct_context("", "") == []

    def test_code_fence_extracted(self):
        msg = """Here is my code:
```python
def calculate(x, y):
    return x + y * 2
```
What's wrong with it?"""
        result = _extract_direct_context(msg, msg)
        assert len(result) == 1
        assert result[0].source == SOURCE_DIRECT
        assert result[0].url == "user-code-python"
        assert "calculate" in result[0].content

    def test_trivial_fence_ignored(self):
        msg = "```\nhi\n```"
        result = _extract_direct_context(msg, msg)
        assert result == []  # < 20 chars

    def test_multiple_fences(self):
        msg = """
```python
def foo():
    return "long enough content"
```
```javascript
function bar() {
    return "also long enough";
}
```
"""
        result = _extract_direct_context(msg, msg)
        assert len(result) == 2
        assert result[0].url == "user-code-python"
        assert result[1].url == "user-code-javascript"


# ═══════════════════════════════════════════════════════════════════════
# Budget enforcement
# ═══════════════════════════════════════════════════════════════════════


class TestEnforceBudget:
    def test_under_budget_keeps_all(self):
        items = [
            EvidenceItem(source="rag", content="short", relevance=0.9),
            EvidenceItem(source="mcp", content="also short", relevance=0.8),
        ]
        result = _enforce_budget(items, 10_000)
        assert len(result) == 2

    def test_over_budget_drops_lowest_relevance(self):
        items = [
            EvidenceItem(source="rag", content="a" * 5000, relevance=0.5),
            EvidenceItem(source="rag", content="b" * 5000, relevance=0.9),
            EvidenceItem(source="mcp", content="c" * 5000, relevance=0.7),
        ]
        result = _enforce_budget(items, 10_000)
        # Should keep the two highest relevance and drop the lowest
        assert len(result) == 2
        sources = {e.content[0] for e in result}
        assert "b" in sources  # highest relevance
        assert "c" in sources  # second highest

    def test_single_item_always_kept(self):
        items = [EvidenceItem(source="rag", content="x" * 50_000, relevance=0.5)]
        result = _enforce_budget(items, 100)
        # First item is always kept even if over budget
        assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════
# gather_all integration
# ═══════════════════════════════════════════════════════════════════════


class TestGatherAll:
    def test_empty_inputs(self):
        result = gather_all()
        assert result == []

    def test_all_sources_combined(self):
        augmented = """
--- UPLOADED FILES ---

[File: data.csv]:
```csv
id,name,value
1,Alice,100
2,Bob,200 this is long enough text
```

--- END FILES ---

What does this data show?
"""
        original = """```python
def analyze(data):
    return sum(d['value'] for d in data)
```
What does this data show?"""
        rag_chunks = [
            {"content": "CSV analysis best practices include validation of headers.", "score": 0.8},
        ]
        mcp_context = "Some workspace context about the project configuration and setup details."

        result = gather_all(
            rag_chunks=rag_chunks,
            mcp_context=mcp_context,
            augmented_message=augmented,
            original_message=original,
        )

        sources = {e.source for e in result}
        assert SOURCE_UPLOADED_FILE in sources
        assert SOURCE_RAG in sources
        assert SOURCE_MCP in sources
        assert SOURCE_DIRECT in sources

    def test_budget_respected(self):
        big_chunks = [
            {"content": "x" * 3000, "score": 0.9} for _ in range(10)
        ]
        result = gather_all(
            rag_chunks=big_chunks,
            budget_chars=5_000,
        )
        total_chars = sum(len(e.content) for e in result)
        # Budget is soft but should be roughly respected
        assert total_chars <= 10_000  # generous bound


# ═══════════════════════════════════════════════════════════════════════
# ResearcherAgent integration
# ═══════════════════════════════════════════════════════════════════════


class TestResearcherGatherPreEvidence:
    def test_none_pre_context(self):
        agent = ResearcherAgent(CouncilConfig())
        result = agent._gather_pre_evidence(None)
        assert result == []

    def test_with_rag_chunks(self):
        pre = PreContext(
            original_message="test question",
            rag_chunks=[
                {"content": "RAG fact about topic", "score": 0.9, "chunk_id": "r1"},
            ],
        )
        agent = ResearcherAgent(CouncilConfig())
        result = agent._gather_pre_evidence(pre)
        assert len(result) >= 1
        assert any(e.source == SOURCE_RAG for e in result)

    def test_with_mcp_context(self):
        pre = PreContext(
            original_message="test",
            mcp_context="📄 **File: app.py** (Language: python)\ndef main(): pass\n",
        )
        agent = ResearcherAgent(CouncilConfig())
        result = agent._gather_pre_evidence(pre)
        assert any(e.source == SOURCE_MCP for e in result)


class TestResearcherToolsFromEvidence:
    def test_empty(self):
        assert ResearcherAgent._tools_from_evidence([]) == []

    def test_maps_sources_to_tools(self):
        evidence = [
            EvidenceItem(source=SOURCE_RAG, content="data"),
            EvidenceItem(source=SOURCE_MCP, content="code"),
            EvidenceItem(source=SOURCE_RAG, content="more data"),  # duplicate source
        ]
        tools = ResearcherAgent._tools_from_evidence(evidence)
        assert "rag_query" in tools
        assert "mcp_read" in tools
        assert len(tools) == 2  # no duplicates


class TestResearcherMergeEvidence:
    def test_no_pre_evidence(self):
        output = ResearcherOutput(
            evidence=[EvidenceItem(source="llm", content="LLM fact")],
            summary="test",
        )
        result = ResearcherAgent._merge_evidence(output, [])
        assert len(result.evidence) == 1

    def test_pre_evidence_first(self):
        pre = [EvidenceItem(source=SOURCE_RAG, content="RAG fact")]
        output = ResearcherOutput(
            evidence=[EvidenceItem(source="llm", content="LLM addition")],
            summary="test",
        )
        result = ResearcherAgent._merge_evidence(output, pre)
        assert len(result.evidence) == 2
        assert result.evidence[0].source == SOURCE_RAG  # pre first
        assert result.evidence[1].source == "llm"

    def test_dedup_by_prefix(self):
        pre = [EvidenceItem(source=SOURCE_RAG, content="Same content that appears in both")]
        output = ResearcherOutput(
            evidence=[EvidenceItem(source="llm", content="Same content that appears in both")],
            summary="test",
        )
        result = ResearcherAgent._merge_evidence(output, pre)
        assert len(result.evidence) == 1  # deduped

    def test_cap_at_15(self):
        pre = [EvidenceItem(source=SOURCE_RAG, content=f"item {i}") for i in range(10)]
        llm_items = [EvidenceItem(source="llm", content=f"llm {i}") for i in range(10)]
        output = ResearcherOutput(evidence=llm_items, summary="test")
        result = ResearcherAgent._merge_evidence(output, pre)
        assert len(result.evidence) <= 15


class TestResearcherFormatEvidence:
    def test_empty(self):
        assert ResearcherAgent._format_evidence_for_llm([]) == ""

    def test_formatted_output(self):
        evidence = [
            EvidenceItem(source=SOURCE_RAG, content="Paris is capital", url="geo.pdf", relevance=0.95),
        ]
        result = ResearcherAgent._format_evidence_for_llm(evidence)
        assert "Pre-gathered evidence" in result
        assert "rag" in result
        assert "geo.pdf" in result
        assert "0.95" in result
