"""PII detection and redaction.

Detects personally identifiable information via regex patterns and
replaces matches with category-labelled placeholders:

    john.doe@example.com  →  [EMAIL_REDACTED]
    555-123-4567          →  [PHONE_REDACTED]
    123-45-6789           →  [SSN_REDACTED]
    4111 1111 1111 1111   →  [CREDIT_CARD_REDACTED]
    192.168.1.1           →  [IP_ADDRESS_REDACTED]

Three action modes:
    - "redact" — replace PII in-place and continue
    - "flag"   — keep PII but log a security event
    - "block"  — reject the entire content
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from libs.core.settings import GuardrailSettings

logger = logging.getLogger("rag.guardrails.pii")


# ── PII pattern definitions ──────────────────────────────────────────────
# Each tuple: (name, compiled_regex, replacement_label)

_PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "email",
        re.compile(
            r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"
        ),
        "[EMAIL_REDACTED]",
    ),
    (
        "phone",
        re.compile(
            r"(?<!\d)"                             # not preceded by digit
            r"(?:\+?1[-.\s]?)?"                    # optional country code
            r"(?:\(?\d{3}\)?[-.\s]?)"              # area code
            r"\d{3}[-.\s]?\d{4}"                   # subscriber number
            r"(?!\d)"                              # not followed by digit
        ),
        "[PHONE_REDACTED]",
    ),
    (
        "ssn",
        re.compile(
            r"\b\d{3}-\d{2}-\d{4}\b"
        ),
        "[SSN_REDACTED]",
    ),
    (
        "credit_card",
        re.compile(
            r"\b(?:\d[ -]*?){13,19}\b"
        ),
        "[CREDIT_CARD_REDACTED]",
    ),
    (
        "ip_address",
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
        ),
        "[IP_ADDRESS_REDACTED]",
    ),
]


@dataclass
class PIIFinding:
    """A single PII match found in text."""

    category: str
    position: int
    original_length: int
    replacement: str


@dataclass
class PIIResult:
    """Outcome of PII scanning / redaction."""

    has_pii: bool
    action_taken: str  # "none" | "redacted" | "flagged" | "blocked"
    redacted_text: str
    findings: list[PIIFinding] = field(default_factory=list)
    categories_found: list[str] = field(default_factory=list)

    @property
    def pii_count(self) -> int:
        return len(self.findings)


def scan_and_redact_pii(
    text: str,
    settings: GuardrailSettings | None = None,
) -> PIIResult:
    """Scan text for PII and apply the configured action.

    Returns PIIResult with:
    - redacted_text: text with PII replaced (if action == "redact")
    - findings: list of all PII matches
    - action_taken: what was done
    """
    if settings is None:
        from libs.core.settings import get_settings
        settings = get_settings().guardrails

    if not settings.redact_pii:
        return PIIResult(
            has_pii=False,
            action_taken="none",
            redacted_text=text,
        )

    enabled_categories = set(settings.pii_patterns)
    findings: list[PIIFinding] = []
    categories_found: set[str] = set()

    # Collect all matches first (before modifying text)
    all_matches: list[tuple[str, re.Match[str], str]] = []
    for name, pattern, replacement in _PII_PATTERNS:
        if name not in enabled_categories:
            continue
        for match in pattern.finditer(text):
            all_matches.append((name, match, replacement))
            categories_found.add(name)

    if not all_matches:
        return PIIResult(
            has_pii=False,
            action_taken="none",
            redacted_text=text,
        )

    # Build findings
    for name, match, replacement in all_matches:
        findings.append(PIIFinding(
            category=name,
            position=match.start(),
            original_length=len(match.group()),
            replacement=replacement,
        ))

    action = settings.pii_action
    categories_list = sorted(categories_found)

    if action == "block":
        logger.warning(
            "pii_blocked: %d PII items found, categories=%s",
            len(findings),
            categories_list,
        )
        return PIIResult(
            has_pii=True,
            action_taken="blocked",
            redacted_text="",  # empty — content is blocked
            findings=findings,
            categories_found=categories_list,
        )

    if action == "flag":
        logger.info(
            "pii_flagged: %d PII items found, categories=%s",
            len(findings),
            categories_list,
        )
        return PIIResult(
            has_pii=True,
            action_taken="flagged",
            redacted_text=text,  # unchanged — just flagged
            findings=findings,
            categories_found=categories_list,
        )

    # Default: redact
    # Sort matches by position descending so replacements don't shift offsets
    sorted_matches = sorted(all_matches, key=lambda x: x[1].start(), reverse=True)
    redacted = text
    for _name, match, replacement in sorted_matches:
        redacted = redacted[:match.start()] + replacement + redacted[match.end():]

    logger.info(
        "pii_redacted: %d items redacted, categories=%s",
        len(findings),
        categories_list,
    )

    return PIIResult(
        has_pii=True,
        action_taken="redacted",
        redacted_text=redacted,
        findings=findings,
        categories_found=categories_list,
    )
