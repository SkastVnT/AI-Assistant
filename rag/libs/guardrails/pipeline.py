"""Guardrail pipeline — orchestrates all guardrail checks.

Provides two main entry points:

    run_ingestion_guardrails()  — called during document ingestion
    run_retrieval_guardrails()  — called during RAG answer generation

Each pipeline composes the individual guardrail modules and logs
security events to the database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.models import SecurityEventKind
from libs.core.settings import GuardrailSettings, get_settings
from libs.guardrails.events import log_security_event
from libs.guardrails.injection import scan_chunks_for_injection
from libs.guardrails.output import (
    BLOCKED_RESPONSE,
    REVIEW_PENDING_RESPONSE,
    OutputValidationResult,
    validate_output,
)
from libs.guardrails.pii import PIIResult, scan_and_redact_pii
from libs.guardrails.sanitizer import SanitizeResult, sanitize_text
from libs.guardrails.trust import (
    format_evidence_with_trust_isolation,
    partition_by_trust,
)

logger = logging.getLogger("rag.guardrails.pipeline")


# ═══════════════════════════════════════════════════════════════════════════
# Ingestion guardrails
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class IngestionGuardrailResult:
    """Outcome of ingestion-time guardrail checks."""

    allowed: bool
    sanitize_result: SanitizeResult | None = None
    pii_result: PIIResult | None = None
    cleaned_text: str = ""
    rejection_reason: str | None = None
    events_logged: int = 0


async def run_ingestion_guardrails(
    db: AsyncSession,
    *,
    text: str,
    tenant_id: UUID,
    document_id: UUID | None = None,
    user_id: UUID | None = None,
    settings: GuardrailSettings | None = None,
) -> IngestionGuardrailResult:
    """Run all ingestion-time guardrail checks on raw document text.

    Steps:
        1. Sanitize (hidden text, malformed patterns)
        2. PII scan + redact on cleaned text

    Returns IngestionGuardrailResult with cleaned text or rejection.
    """
    if settings is None:
        settings = get_settings().guardrails

    if not settings.enabled:
        return IngestionGuardrailResult(allowed=True, cleaned_text=text)

    events_logged = 0

    # ── Step 1: Sanitize ──────────────────────────────────────────────
    sanitize_result = sanitize_text(text, settings)
    current_text = sanitize_result.cleaned_text

    if sanitize_result.findings:
        await log_security_event(
            db,
            tenant_id=tenant_id,
            kind=SecurityEventKind.INGESTION_SANITIZE,
            severity=max(
                (f.severity for f in sanitize_result.findings),
                key=lambda s: {"low": 0, "medium": 1, "high": 2, "critical": 3}.get(s, 0),
            ),
            source="sanitizer",
            description=f"Sanitization found {len(sanitize_result.findings)} issues",
            document_id=document_id,
            user_id=user_id,
            details={
                "findings": [
                    {"pattern": f.pattern_name, "count": f.count, "severity": f.severity}
                    for f in sanitize_result.findings
                ],
                "removed_chars": sanitize_result.removed_char_count,
            },
        )
        events_logged += 1

    if sanitize_result.should_reject:
        return IngestionGuardrailResult(
            allowed=False,
            sanitize_result=sanitize_result,
            cleaned_text="",
            rejection_reason="Content rejected: malicious patterns detected",
            events_logged=events_logged,
        )

    # ── Step 2: PII scan ──────────────────────────────────────────────
    pii_result = scan_and_redact_pii(current_text, settings)

    if pii_result.has_pii:
        await log_security_event(
            db,
            tenant_id=tenant_id,
            kind=SecurityEventKind.PII_REDACTED,
            severity="medium",
            source="pii_redactor",
            description=f"PII detected: {pii_result.categories_found}",
            document_id=document_id,
            user_id=user_id,
            details={
                "categories": pii_result.categories_found,
                "count": pii_result.pii_count,
                "action": pii_result.action_taken,
            },
        )
        events_logged += 1
        current_text = pii_result.redacted_text

    if pii_result.action_taken == "blocked":
        return IngestionGuardrailResult(
            allowed=False,
            sanitize_result=sanitize_result,
            pii_result=pii_result,
            cleaned_text="",
            rejection_reason="Content blocked: PII detected and policy is block",
            events_logged=events_logged,
        )

    return IngestionGuardrailResult(
        allowed=True,
        sanitize_result=sanitize_result,
        pii_result=pii_result,
        cleaned_text=current_text,
        events_logged=events_logged,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Retrieval / output guardrails
# ═══════════════════════════════════════════════════════════════════════════


@dataclass
class RetrievalGuardrailResult:
    """Outcome of retrieval-time guardrail checks."""

    allowed: bool
    answer: str
    safe_evidence: list[dict] = field(default_factory=list)
    flagged_evidence: list[dict] = field(default_factory=list)
    formatted_evidence: str = ""
    output_validation: OutputValidationResult | None = None
    pii_result: PIIResult | None = None
    needs_human_review: bool = False
    review_event_id: UUID | None = None
    events_logged: int = 0


async def run_pre_generation_guardrails(
    db: AsyncSession,
    *,
    evidence_blocks: list[dict],
    evidence_formatter: callable,
    tenant_id: UUID,
    trace_id: UUID | None = None,
    user_id: UUID | None = None,
    settings: GuardrailSettings | None = None,
) -> tuple[list[dict], str, int]:
    """Run guardrails on retrieved evidence BEFORE LLM generation.

    Steps:
        1. Scan chunks for prompt injection
        2. Classify source trust
        3. Format evidence with trust isolation

    Returns:
        (safe_evidence, formatted_evidence_text, events_logged)
    """
    if settings is None:
        settings = get_settings().guardrails

    if not settings.enabled:
        return evidence_blocks, evidence_formatter(evidence_blocks), 0

    events_logged = 0

    # ── Step 1: Prompt injection scan ─────────────────────────────────
    safe_chunks, flagged_chunks = scan_chunks_for_injection(
        evidence_blocks, settings,
    )

    if flagged_chunks:
        await log_security_event(
            db,
            tenant_id=tenant_id,
            kind=SecurityEventKind.PROMPT_INJECTION,
            severity="high",
            source="injection_detector",
            description=f"{len(flagged_chunks)} chunks flagged for injection",
            trace_id=trace_id,
            user_id=user_id,
            details={
                "flagged_count": len(flagged_chunks),
                "total_count": len(evidence_blocks),
                "flagged_chunks": [
                    {
                        "source_index": c.get("source_index"),
                        "scan": c.get("injection_scan"),
                    }
                    for c in flagged_chunks
                ],
            },
        )
        events_logged += 1

    # ── Step 2: Source trust classification + isolation ────────────────
    if settings.classify_source_trust and safe_chunks:
        trusted, untrusted = partition_by_trust(safe_chunks, settings)

        if untrusted:
            await log_security_event(
                db,
                tenant_id=tenant_id,
                kind=SecurityEventKind.SOURCE_UNTRUSTED,
                severity="low",
                source="trust_classifier",
                description=f"{len(untrusted)} untrusted sources isolated in prompt",
                trace_id=trace_id,
                user_id=user_id,
                details={
                    "trusted_count": len(trusted),
                    "untrusted_count": len(untrusted),
                },
            )
            events_logged += 1

        formatted = format_evidence_with_trust_isolation(
            trusted, untrusted, evidence_formatter,
        )
    else:
        formatted = evidence_formatter(safe_chunks)

    return safe_chunks, formatted, events_logged


async def run_post_generation_guardrails(
    db: AsyncSession,
    *,
    answer_text: str,
    evidence_count: int,
    tenant_id: UUID,
    trace_id: UUID | None = None,
    user_id: UUID | None = None,
    settings: GuardrailSettings | None = None,
) -> RetrievalGuardrailResult:
    """Run guardrails on LLM output AFTER generation.

    Steps:
        1. Validate output (length, injection echo, hallucinated citations)
        2. PII redaction on final answer
        3. Queue for human review if needed

    Returns RetrievalGuardrailResult.
    """
    if settings is None:
        settings = get_settings().guardrails

    if not settings.enabled:
        return RetrievalGuardrailResult(
            allowed=True,
            answer=answer_text,
        )

    events_logged = 0

    # ── Step 1: Output validation ─────────────────────────────────────
    output_val = validate_output(
        answer_text,
        evidence_count=evidence_count,
        settings=settings,
    )

    if output_val.should_block:
        event = await log_security_event(
            db,
            tenant_id=tenant_id,
            kind=SecurityEventKind.OUTPUT_BLOCKED,
            severity="high",
            source="output_validator",
            description=output_val.blocked_reason or "Output blocked",
            trace_id=trace_id,
            user_id=user_id,
            details={
                "findings": [
                    {"check": f.check_name, "severity": f.severity}
                    for f in output_val.findings
                ],
            },
        )
        events_logged += 1

        if output_val.needs_human_review:
            review_event = await log_security_event(
                db,
                tenant_id=tenant_id,
                kind=SecurityEventKind.HUMAN_REVIEW,
                severity="high",
                source="output_validator",
                description="Response queued for human review",
                trace_id=trace_id,
                user_id=user_id,
                details={
                    "blocked_event_id": str(event.id),
                    "original_answer_length": len(answer_text),
                },
            )
            events_logged += 1
            return RetrievalGuardrailResult(
                allowed=False,
                answer=REVIEW_PENDING_RESPONSE.format(event_id=review_event.id),
                output_validation=output_val,
                needs_human_review=True,
                review_event_id=review_event.id,
                events_logged=events_logged,
            )

        return RetrievalGuardrailResult(
            allowed=False,
            answer=BLOCKED_RESPONSE,
            output_validation=output_val,
            events_logged=events_logged,
        )

    current_answer = output_val.cleaned_output

    # ── Step 2: PII redaction on answer ───────────────────────────────
    pii_result = scan_and_redact_pii(current_answer, settings)

    if pii_result.has_pii:
        await log_security_event(
            db,
            tenant_id=tenant_id,
            kind=SecurityEventKind.PII_REDACTED,
            severity="medium",
            source="pii_redactor",
            description=f"PII in answer: {pii_result.categories_found}",
            trace_id=trace_id,
            user_id=user_id,
            details={
                "categories": pii_result.categories_found,
                "count": pii_result.pii_count,
                "action": pii_result.action_taken,
            },
        )
        events_logged += 1
        current_answer = pii_result.redacted_text

    return RetrievalGuardrailResult(
        allowed=True,
        answer=current_answer,
        output_validation=output_val,
        pii_result=pii_result,
        events_logged=events_logged,
    )
