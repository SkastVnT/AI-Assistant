"""Tests for the answer generation layer.

Covers:
- Prompt templates (evidence formatting, system prompts, user prompts)
- Citation extraction from answer text
- Answer generation service (full pipeline)
- AnswerRequest / AnswerResponse / CitationRef schemas
- POST /query/answer endpoint integration
- AnswerGenerationSettings
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.core.schemas import AnswerRequest, AnswerResponse, CitationRef
from libs.core.settings import AnswerGenerationSettings
from libs.retrieval.answer.prompts import (
    SYSTEM_PROMPTS,
    build_user_prompt,
    format_evidence,
)
from libs.retrieval.answer.service import (
    AnswerResult,
    _prepare_evidence,
    extract_citations,
    generate_grounded_answer,
)
from libs.retrieval.service import RetrievalResponse, RetrievedChunk

# ── Helpers ────────────────────────────────────────────────────────────────

TENANT_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
DOC_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
VER_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _chunk(
    content: str = "Test content",
    score: float = 0.9,
    idx: int = 0,
    filename: str = "test.md",
    page_number: int | None = None,
    heading_path: str | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=DOC_ID,
        version_id=VER_ID,
        content=content,
        score=score,
        chunk_index=idx,
        document_title="Test Doc",
        filename=filename,
        version_number=1,
        page_number=page_number,
        heading_path=heading_path,
        sensitivity_level="internal",
        language="en",
    )


def _retrieval_response(
    chunks: list[RetrievedChunk] | None = None,
) -> RetrievalResponse:
    if chunks is None:
        chunks = [_chunk(content="Revenue was $10M in Q3.", filename="financials.md")]
    return RetrievalResponse(
        query="What was Q3 revenue?",
        chunks=chunks,
        total_found=len(chunks),
        trace_id=uuid.uuid4(),
        retrieval_ms=42,
    )


# ====================================================================
# Prompt templates
# ====================================================================


class TestSystemPrompts:
    def test_all_modes_exist(self):
        assert set(SYSTEM_PROMPTS) == {"concise", "standard", "detailed"}

    def test_each_prompt_contains_rules(self):
        for mode, prompt in SYSTEM_PROMPTS.items():
            assert "ONLY from the evidence" in prompt, f"{mode} missing grounding rule"
            assert "[Source N]" in prompt, f"{mode} missing citation format"
            assert "NEVER fabricate" in prompt, f"{mode} missing no-fabrication rule"

    def test_concise_is_shortest(self):
        assert len(SYSTEM_PROMPTS["concise"]) < len(SYSTEM_PROMPTS["detailed"])


class TestFormatEvidence:
    def test_empty_evidence(self):
        result = format_evidence([])
        assert result == "<no evidence retrieved>"

    def test_single_evidence_block(self):
        blocks = [
            {"source_index": 1, "filename": "doc.md", "content": "Hello world", "score": 0.95}
        ]
        result = format_evidence(blocks)
        assert "[Source 1]" in result
        assert "doc.md" in result
        assert "Hello world" in result
        assert "0.95" in result

    def test_multiple_blocks_separated_by_divider(self):
        blocks = [
            {"source_index": 1, "filename": "a.md", "content": "A", "score": 0.9},
            {"source_index": 2, "filename": "b.md", "content": "B", "score": 0.8},
        ]
        result = format_evidence(blocks)
        assert result.count("---") == 1  # one divider between two blocks
        assert "[Source 1]" in result
        assert "[Source 2]" in result


class TestBuildUserPrompt:
    def test_contains_evidence_and_query(self):
        prompt = build_user_prompt("What is X?", "some evidence text")
        assert "some evidence text" in prompt
        assert "What is X?" in prompt
        assert "Answer:" in prompt

    def test_structure_has_sections(self):
        prompt = build_user_prompt("Q", "E")
        assert prompt.startswith("Evidence:")
        assert "Question:" in prompt


# ====================================================================
# Citation extraction
# ====================================================================


class TestCitationExtraction:
    def _evidence(self, n: int = 3) -> list[dict]:
        return [
            {
                "source_index": i,
                "filename": f"doc{i}.md",
                "content": f"Content of source {i}",
                "score": 0.9 - i * 0.1,
                "chunk_id": uuid.uuid4(),
                "document_id": DOC_ID,
                "version_id": VER_ID,
                "page_number": i,
                "heading_path": f"Section {i}",
            }
            for i in range(1, n + 1)
        ]

    def test_extracts_single_citation(self):
        evidence = self._evidence()
        answer = "The answer is X [Source 1]."
        citations = extract_citations(answer, evidence)
        assert len(citations) == 1
        assert citations[0].source_index == 1
        assert citations[0].filename == "doc1.md"

    def test_extracts_multiple_citations(self):
        evidence = self._evidence()
        answer = "A [Source 1] and B [Source 3]."
        citations = extract_citations(answer, evidence)
        assert len(citations) == 2
        assert citations[0].source_index == 1
        assert citations[1].source_index == 3

    def test_deduplicates_same_source(self):
        evidence = self._evidence()
        answer = "Fact [Source 2]. Also [Source 2]."
        citations = extract_citations(answer, evidence)
        assert len(citations) == 1

    def test_ignores_invalid_source_index(self):
        evidence = self._evidence(2)
        answer = "Fact [Source 99]."
        citations = extract_citations(answer, evidence)
        assert len(citations) == 0

    def test_no_citations_in_answer(self):
        evidence = self._evidence()
        answer = "I don't have enough evidence to answer."
        citations = extract_citations(answer, evidence)
        assert len(citations) == 0

    def test_preserves_page_and_heading(self):
        evidence = self._evidence()
        answer = "Result [Source 2]."
        citations = extract_citations(answer, evidence)
        assert citations[0].page_number == 2
        assert citations[0].heading_path == "Section 2"

    def test_content_snippet_truncated(self):
        evidence = [{
            "source_index": 1,
            "filename": "big.md",
            "content": "x" * 500,
            "score": 0.9,
            "chunk_id": uuid.uuid4(),
            "document_id": DOC_ID,
            "version_id": VER_ID,
        }]
        answer = "Fact [Source 1]."
        citations = extract_citations(answer, evidence)
        assert len(citations[0].content_snippet) == 300


# ====================================================================
# Evidence preparation
# ====================================================================


class TestPrepareEvidence:
    def test_builds_blocks_from_chunks(self):
        resp = _retrieval_response([
            _chunk("Revenue info", score=0.95, filename="fin.md"),
            _chunk("Engineering info", score=0.8, filename="eng.md"),
        ])
        blocks = _prepare_evidence(resp)
        assert len(blocks) == 2
        assert blocks[0]["source_index"] == 1
        assert blocks[0]["filename"] == "fin.md"
        assert blocks[1]["source_index"] == 2

    def test_empty_chunks(self):
        resp = _retrieval_response([])
        blocks = _prepare_evidence(resp)
        assert blocks == []


# ====================================================================
# Answer generation service
# ====================================================================


class TestGenerateGroundedAnswer:
    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """End-to-end: retrieve → prompt → generate → citations."""
        llm = AsyncMock()
        llm.complete = AsyncMock(
            return_value="Revenue was $10M [Source 1]. See financials [Source 1]."
        )
        llm.model = "test-model"
        embedder = AsyncMock()
        embedder.embed = AsyncMock(return_value=[[0.1] * 10])
        embedder.dimensions = 10
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.get = AsyncMock(return_value=None)

        chunk = _chunk("Revenue was $10M in Q3.", filename="fin.md")
        fake_retrieval = _retrieval_response([chunk])

        with patch(
            "libs.retrieval.answer.service.retrieve",
            new_callable=AsyncMock,
            return_value=fake_retrieval,
        ):
            result = await generate_grounded_answer(
                db, embedder, llm,
                query="Q3 revenue?",
                tenant_id=TENANT_ID,
                mode="standard",
            )

        assert isinstance(result, AnswerResult)
        assert "10M" in result.answer
        assert result.mode == "standard"
        assert result.evidence_used == 1
        assert len(result.citations) == 1
        assert result.citations[0].source_index == 1
        assert result.retrieval_ms > 0 or result.retrieval_ms == 42
        assert result.generation_ms >= 0

    @pytest.mark.asyncio
    async def test_concise_mode(self):
        llm = AsyncMock()
        llm.complete = AsyncMock(return_value="Short answer.")
        embedder = AsyncMock()
        embedder.embed = AsyncMock(return_value=[[0.1] * 10])
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.get = AsyncMock(return_value=None)

        fake_retrieval = _retrieval_response([_chunk()])

        with patch(
            "libs.retrieval.answer.service.retrieve",
            new_callable=AsyncMock,
            return_value=fake_retrieval,
        ):
            result = await generate_grounded_answer(
                db, embedder, llm,
                query="test", tenant_id=TENANT_ID, mode="concise",
            )

        assert result.mode == "concise"
        # Check that the system prompt used the concise variant
        call_kwargs = llm.complete.call_args
        assert "shortest correct answer" in call_kwargs.kwargs.get(
            "system", call_kwargs.args[0] if len(call_kwargs.args) > 0 else ""
        )

    @pytest.mark.asyncio
    async def test_no_evidence(self):
        llm = AsyncMock()
        llm.complete = AsyncMock(
            return_value="I don't have enough evidence to answer this question."
        )
        embedder = AsyncMock()
        embedder.embed = AsyncMock(return_value=[[0.1] * 10])
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.get = AsyncMock(return_value=None)

        fake_retrieval = _retrieval_response([])

        with patch(
            "libs.retrieval.answer.service.retrieve",
            new_callable=AsyncMock,
            return_value=fake_retrieval,
        ):
            result = await generate_grounded_answer(
                db, embedder, llm,
                query="unknown?", tenant_id=TENANT_ID,
            )

        assert result.evidence_used == 0
        assert len(result.citations) == 0
        assert "evidence" in result.answer.lower()

    @pytest.mark.asyncio
    async def test_timeout_fallback(self):
        import asyncio

        async def slow_complete(*args, **kwargs):
            await asyncio.sleep(10)

        llm = AsyncMock()
        llm.complete = slow_complete
        embedder = AsyncMock()
        embedder.embed = AsyncMock(return_value=[[0.1] * 10])
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.get = AsyncMock(return_value=None)

        fake_retrieval = _retrieval_response([_chunk()])

        with (
            patch(
                "libs.retrieval.answer.service.retrieve",
                new_callable=AsyncMock,
                return_value=fake_retrieval,
            ),
            patch(
                "libs.retrieval.answer.service.get_settings",
            ) as mock_settings,
        ):
            ans_settings = AnswerGenerationSettings()
            ans_settings.timeout_ms = 50  # 50ms timeout
            mock_settings.return_value.answer_generation = ans_settings
            result = await generate_grounded_answer(
                db, embedder, llm,
                query="test", tenant_id=TENANT_ID,
            )

        assert "unable to generate" in result.answer.lower()

    @pytest.mark.asyncio
    async def test_invalid_mode_falls_back(self):
        llm = AsyncMock()
        llm.complete = AsyncMock(return_value="Answer.")
        embedder = AsyncMock()
        embedder.embed = AsyncMock(return_value=[[0.1] * 10])
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.get = AsyncMock(return_value=None)

        fake_retrieval = _retrieval_response([_chunk()])

        with patch(
            "libs.retrieval.answer.service.retrieve",
            new_callable=AsyncMock,
            return_value=fake_retrieval,
        ):
            result = await generate_grounded_answer(
                db, embedder, llm,
                query="test", tenant_id=TENANT_ID, mode="invalid_mode",
            )

        assert result.mode == "standard"

    @pytest.mark.asyncio
    async def test_trace_updated_with_answer(self):
        llm = AsyncMock()
        llm.complete = AsyncMock(return_value="Answer [Source 1].")
        llm.model = "gpt-4o-test"
        embedder = AsyncMock()
        embedder.embed = AsyncMock(return_value=[[0.1] * 10])

        trace_id = uuid.uuid4()
        fake_trace = MagicMock()
        fake_trace.metadata_ = {}

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.get = AsyncMock(return_value=fake_trace)

        fake_retrieval = _retrieval_response([_chunk()])
        fake_retrieval = RetrievalResponse(
            query="test", chunks=[_chunk()], total_found=1,
            trace_id=trace_id, retrieval_ms=10,
        )

        with patch(
            "libs.retrieval.answer.service.retrieve",
            new_callable=AsyncMock,
            return_value=fake_retrieval,
        ):
            await generate_grounded_answer(
                db, embedder, llm,
                query="test", tenant_id=TENANT_ID,
            )

        assert fake_trace.answer_text == "Answer [Source 1]."
        assert fake_trace.llm_model == "gpt-4o-test"
        assert fake_trace.metadata_["answer_mode"] == "standard"
        assert fake_trace.metadata_["citation_count"] == 1


# ====================================================================
# API schemas
# ====================================================================


class TestAnswerSchemas:
    def test_answer_request_defaults(self):
        req = AnswerRequest(query="test")
        assert req.mode == "standard"
        assert req.top_k == 5
        assert req.score_threshold == 0.0

    def test_answer_request_mode_validation(self):
        for valid in ("concise", "standard", "detailed"):
            req = AnswerRequest(query="test", mode=valid)
            assert req.mode == valid

    def test_answer_request_invalid_mode(self):
        with pytest.raises(ValueError):
            AnswerRequest(query="test", mode="verbose")

    def test_citation_ref_fields(self):
        cit = CitationRef(
            source_index=1,
            chunk_id=uuid.uuid4(),
            document_id=DOC_ID,
            version_id=VER_ID,
            filename="test.md",
            content_snippet="snippet",
            score=0.9,
            page_number=5,
            heading_path="Section 1.2",
        )
        assert cit.source_index == 1
        assert cit.page_number == 5

    def test_answer_response_structure(self):
        resp = AnswerResponse(
            answer="Test answer [Source 1].",
            citations=[
                CitationRef(
                    source_index=1,
                    chunk_id=uuid.uuid4(),
                    document_id=DOC_ID,
                    version_id=VER_ID,
                    filename="doc.md",
                    content_snippet="content",
                    score=0.9,
                )
            ],
            query="test?",
            mode="standard",
            evidence_used=1,
            retrieval_ms=10,
            generation_ms=50,
            total_ms=60,
        )
        assert len(resp.citations) == 1
        assert resp.total_ms == 60


# ====================================================================
# Settings
# ====================================================================


class TestAnswerGenerationSettings:
    def test_defaults(self):
        s = AnswerGenerationSettings()
        assert s.default_mode == "standard"
        assert s.temperature == 0.1
        assert s.max_tokens_concise == 256
        assert s.max_tokens_standard == 1024
        assert s.max_tokens_detailed == 4096
        assert s.timeout_ms == 30000

    def test_env_prefix(self):
        assert AnswerGenerationSettings.model_config["env_prefix"] == "ANSWER_"
