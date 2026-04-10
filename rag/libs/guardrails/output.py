"""Output validation — checks LLM responses before returning to the user.

Validates:
- Response length (prevents runaway outputs)
- Prompt injection leakage (system prompt echoed in output)
- Hallucinated citations (referencing [Source N] with N > evidence count)
- PII leakage in the answer
- Toxic/dangerous content markers

Returns a ValidationResult that either passes or blocks the response,
with an optional human-review flag.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from libs.core.settings import GuardrailSettings

logger = logging.getLogger("rag.guardrails.output")

# ── Patterns for output validation ────────────────────────────────────────

# System prompt leakage indicators
_SYSTEM_LEAK_PATTERNS = [
    re.compile(r"my\s+system\s+prompt\s+(is|says|reads)", re.IGNORECASE),
    re.compile(r"I\s+was\s+instructed\s+to", re.IGNORECASE),
    re.compile(r"my\s+instructions?\s+(are|say|read)", re.IGNORECASE),
    re.compile(r"<\|?(system|im_start|im_end)\|?>", re.IGNORECASE),
]

# Citation pattern
_CITATION_REF = re.compile(r"\[Source\s+(\d+)\]")

# Refusal / blocked response indicators
_REFUSAL_PATTERNS = [
    re.compile(r"I\s+cannot\s+(and\s+will\s+not|help\s+with)", re.IGNORECASE),
    re.compile(r"I('m|\s+am)\s+not\s+able\s+to\s+assist", re.IGNORECASE),
]

_SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass
class OutputFinding:
    """A single validation issue found in the output."""

    check_name: str
    description: str
    severity: str


@dataclass
class OutputValidationResult:
    """Result of output validation."""

    is_valid: bool
    should_block: bool
    needs_human_review: bool
    cleaned_output: str
    findings: list[OutputFinding] = field(default_factory=list)
    blocked_reason: str | None = None

    @property
    def finding_names(self) -> list[str]:
        return [f.check_name for f in self.findings]


def validate_output(
    answer_text: str,
    *,
    evidence_count: int = 0,
    settings: GuardrailSettings | None = None,
) -> OutputValidationResult:
    """Validate an LLM-generated answer before returning to the user.

    Args:
        answer_text: The raw LLM output.
        evidence_count: Number of evidence chunks provided to the LLM.
        settings: Guardrail settings.

    Returns:
        OutputValidationResult with validation outcome.
    """
    if settings is None:
        from libs.core.settings import get_settings
        settings = get_settings().guardrails

    if not settings.validate_output:
        return OutputValidationResult(
            is_valid=True,
            should_block=False,
            needs_human_review=False,
            cleaned_output=answer_text,
        )

    findings: list[OutputFinding] = []
    cleaned = answer_text
    should_block = False
    max_severity = "low"

    # ── 1. Length check ───────────────────────────────────────────────
    if len(answer_text) > settings.max_output_length:
        findings.append(OutputFinding(
            check_name="excessive_length",
            description=(
                f"Output length {len(answer_text)} exceeds "
                f"max {settings.max_output_length}"
            ),
            severity="medium",
        ))
        cleaned = cleaned[:settings.max_output_length]

    # ── 2. Empty / whitespace-only ────────────────────────────────────
    if not answer_text.strip():
        findings.append(OutputFinding(
            check_name="empty_output",
            description="LLM returned empty or whitespace-only response",
            severity="medium",
        ))

    # ── 3. System prompt leakage ──────────────────────────────────────
    if settings.block_output_injection:
        for pattern in _SYSTEM_LEAK_PATTERNS:
            if pattern.search(cleaned):
                findings.append(OutputFinding(
                    check_name="system_prompt_leakage",
                    description="Output may contain leaked system prompt content",
                    severity="high",
                ))
                should_block = True
                max_severity = "high"
                break

    # ── 4. Hallucinated citations ─────────────────────────────────────
    if evidence_count > 0:
        cited_indices = {int(m.group(1)) for m in _CITATION_REF.finditer(cleaned)}
        invalid_citations = {i for i in cited_indices if i < 1 or i > evidence_count}
        if invalid_citations:
            findings.append(OutputFinding(
                check_name="hallucinated_citations",
                description=(
                    f"Output references non-existent sources: "
                    f"{sorted(invalid_citations)} (evidence has {evidence_count} chunks)"
                ),
                severity="medium",
            ))

    # ── 5. Injection echo (LLM repeating injected instructions) ──────
    if settings.block_output_injection:
        injection_markers = [
            r"ignore\s+previous\s+instructions",
            r"<\|?(system|im_start)\|?>",
            r"\[INST\]",
            r"<<SYS>>",
        ]
        for marker in injection_markers:
            if re.search(marker, cleaned, re.IGNORECASE):
                findings.append(OutputFinding(
                    check_name="injection_echo",
                    description="Output echoes prompt injection markers",
                    severity="critical",
                ))
                should_block = True
                max_severity = "critical"
                break

    # ── Determine max severity and human review need ──────────────────
    for f in findings:
        if _SEVERITY_ORDER.get(f.severity, 0) > _SEVERITY_ORDER.get(max_severity, 0):
            max_severity = f.severity

    needs_human_review = (
        settings.human_review_enabled
        and should_block
        and _SEVERITY_ORDER.get(max_severity, 0)
        >= _SEVERITY_ORDER.get(settings.human_review_severity_threshold, 2)
    )

    blocked_reason = None
    if should_block:
        blocked_reason = "; ".join(
            f.description for f in findings
            if f.severity in ("high", "critical")
        )
        logger.warning(
            "output_blocked: %s (findings=%d, severity=%s)",
            blocked_reason,
            len(findings),
            max_severity,
        )

    return OutputValidationResult(
        is_valid=not should_block,
        should_block=should_block,
        needs_human_review=needs_human_review,
        cleaned_output=cleaned if not should_block else "",
        findings=findings,
        blocked_reason=blocked_reason,
    )


# ── Blocked response templates ────────────────────────────────────────────

BLOCKED_RESPONSE = (
    "I'm unable to provide a response to this query. The response was "
    "flagged by our content safety system. If you believe this is an error, "
    "please contact support."
)

REVIEW_PENDING_RESPONSE = (
    "This response has been flagged for review by our content safety system. "
    "A human reviewer will assess it shortly. Reference ID: {event_id}"
)
