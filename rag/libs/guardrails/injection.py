"""Prompt injection detection for retrieved context chunks.

Scans retrieved text for patterns commonly used in prompt injection attacks:
- Direct instruction overrides ("ignore previous instructions", "you are now...")
- System prompt extraction attempts ("repeat your system prompt")
- Delimiter abuse (###, ```, <|im_sep|>, etc.)
- Role-play manipulation ("pretend you are", "act as")
- Encoded payloads (base64-encoded instructions)

Each chunk is scored 0.0-1.0. Chunks exceeding the threshold are flagged,
and an optional hard-block rejects the entire query.

This is a heuristic detector — not an LLM classifier. It is fast enough
to run on every retrieved chunk without adding meaningful latency.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from libs.core.settings import GuardrailSettings

logger = logging.getLogger("rag.guardrails.injection")

# ── Pattern catalog ───────────────────────────────────────────────────────
# Each tuple: (pattern, weight, description)
# Weights sum to produce a score ∈ [0, 1] via min(total, 1.0).

_INJECTION_PATTERNS: list[tuple[re.Pattern[str], float, str]] = [
    # Direct instruction overrides
    (re.compile(
        r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+"
        r"(instructions?|prompts?|rules?|context)",
        re.IGNORECASE,
    ), 0.6, "instruction_override"),

    (re.compile(
        r"disregard\s+(all\s+)?(previous|prior|above)\s+"
        r"(instructions?|prompts?|context)",
        re.IGNORECASE,
    ), 0.6, "instruction_override"),

    (re.compile(
        r"forget\s+(everything|all)\s+(above|before|previous)",
        re.IGNORECASE,
    ), 0.5, "instruction_override"),

    # New persona / role injection
    (re.compile(
        r"you\s+are\s+(now|actually|really)\s+",
        re.IGNORECASE,
    ), 0.4, "role_injection"),

    (re.compile(
        r"(pretend|act|behave)\s+(as\s+if\s+)?you\s+(are|were)\s+",
        re.IGNORECASE,
    ), 0.3, "role_injection"),

    (re.compile(
        r"switch\s+to\s+(a\s+)?(new|different)\s+(mode|role|persona)",
        re.IGNORECASE,
    ), 0.4, "role_injection"),

    # System prompt extraction
    (re.compile(
        r"(repeat|show|reveal|print|output|display)\s+"
        r"(your\s+)?(system\s+)?(prompt|instructions?|rules?|context)",
        re.IGNORECASE,
    ), 0.5, "prompt_extraction"),

    (re.compile(
        r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?|rules?)",
        re.IGNORECASE,
    ), 0.4, "prompt_extraction"),

    # Delimiter abuse (trying to inject system/assistant messages)
    (re.compile(
        r"<\|?(system|im_start|im_sep|im_end|endoftext)\|?>",
        re.IGNORECASE,
    ), 0.7, "delimiter_abuse"),

    (re.compile(
        r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>",
        re.IGNORECASE,
    ), 0.7, "delimiter_abuse"),

    (re.compile(
        r"```\s*(system|assistant|user)\s*\n",
        re.IGNORECASE,
    ), 0.4, "delimiter_abuse"),

    # Output manipulation
    (re.compile(
        r"(always|must|should)\s+respond\s+with",
        re.IGNORECASE,
    ), 0.3, "output_manipulation"),

    (re.compile(
        r"your\s+(answer|response|output)\s+(must|should|will)\s+be",
        re.IGNORECASE,
    ), 0.3, "output_manipulation"),

    # Data exfiltration attempts
    (re.compile(
        r"(send|post|fetch|curl|wget|http)\s+.*(api|url|endpoint|webhook)",
        re.IGNORECASE,
    ), 0.5, "data_exfiltration"),

    # Markdown/HTML injection (attempting to render executable content)
    (re.compile(
        r"<script[\s>]|javascript:|on(load|error|click)\s*=",
        re.IGNORECASE,
    ), 0.6, "html_injection"),

    (re.compile(
        r"\!\[.*\]\(https?://[^\)]*\)",
        re.IGNORECASE,
    ), 0.2, "markdown_image_injection"),
]


@dataclass
class InjectionFinding:
    """A single injection pattern matched in a chunk."""

    pattern_name: str
    description: str
    weight: float
    match_text: str


@dataclass
class InjectionScanResult:
    """Result of scanning a single text block for prompt injection."""

    score: float
    is_flagged: bool
    findings: list[InjectionFinding] = field(default_factory=list)

    @property
    def finding_names(self) -> list[str]:
        return [f.pattern_name for f in self.findings]


def scan_prompt_injection(
    text: str,
    settings: GuardrailSettings | None = None,
) -> InjectionScanResult:
    """Score a text block for prompt injection risk.

    Returns InjectionScanResult with a 0.0-1.0 score and individual findings.
    Score >= threshold means flagged.
    """
    if settings is None:
        from libs.core.settings import get_settings
        settings = get_settings().guardrails

    if not settings.detect_prompt_injection:
        return InjectionScanResult(score=0.0, is_flagged=False)

    findings: list[InjectionFinding] = []
    total_weight = 0.0

    for pattern, weight, name in _INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(InjectionFinding(
                pattern_name=name,
                description=f"Matched: {match.group()[:80]}",
                weight=weight,
                match_text=match.group()[:120],
            ))
            total_weight += weight

    score = min(total_weight, 1.0)
    is_flagged = score >= settings.injection_score_threshold

    if is_flagged:
        logger.warning(
            "injection_detected score=%.2f findings=%d: %s",
            score,
            len(findings),
            [f.pattern_name for f in findings],
        )

    return InjectionScanResult(
        score=score,
        is_flagged=is_flagged,
        findings=findings,
    )


def scan_chunks_for_injection(
    chunks: list[dict],
    settings: GuardrailSettings | None = None,
) -> tuple[list[dict], list[dict]]:
    """Scan a list of evidence chunks for prompt injection.

    Args:
        chunks: Evidence block dicts with at least a "content" key.
        settings: Guardrail settings.

    Returns:
        (safe_chunks, flagged_chunks) — flagged chunks are removed from the
        safe list. Each flagged chunk gets an "injection_scan" key added.
    """
    safe: list[dict] = []
    flagged: list[dict] = []

    for chunk in chunks:
        result = scan_prompt_injection(chunk.get("content", ""), settings)
        if result.is_flagged:
            chunk["injection_scan"] = {
                "score": result.score,
                "findings": result.finding_names,
            }
            flagged.append(chunk)
        else:
            safe.append(chunk)

    if flagged:
        logger.info(
            "injection_scan: %d/%d chunks flagged",
            len(flagged),
            len(chunks),
        )

    return safe, flagged
