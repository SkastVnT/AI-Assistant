"""Ingestion-time content sanitization.

Scans raw document text for:
- Hidden / invisible Unicode characters (zero-width spaces, RTL overrides, etc.)
- Homoglyph substitution (Cyrillic chars posing as Latin)
- Malformed control sequences (null bytes, ANSI escapes)
- Excessive base64-encoded blobs that may hide payloads

Returns a SanitizeResult indicating whether the content is safe, with
details about each finding.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from libs.core.settings import GuardrailSettings

logger = logging.getLogger("rag.guardrails.sanitizer")

# ── Hidden / invisible character patterns ─────────────────────────────────

# Zero-width and formatting control chars
_INVISIBLE_CHARS = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f"   # zero-width, LTR/RTL marks
    r"\u2060\u2061\u2062\u2063\u2064"     # word joiner, invisible operators
    r"\ufeff"                              # BOM / zero-width no-break space
    r"\u00ad"                              # soft hyphen
    r"\u034f"                              # combining grapheme joiner
    r"\u061c"                              # Arabic letter mark
    r"\u180e"                              # Mongolian vowel separator
    r"\ufff9\ufffa\ufffb"                 # interlinear annotations
    r"]"
)

# Bidirectional override/embedding chars (used in Trojan Source attacks)
_BIDI_OVERRIDES = re.compile(
    r"[\u202a\u202b\u202c\u202d\u202e"   # LRE, RLE, PDF, LRO, RLO
    r"\u2066\u2067\u2068\u2069"           # LRI, RLI, FSI, PDI
    r"]"
)

# ANSI escape sequences
_ANSI_ESCAPES = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")

# Null bytes and other C0 control chars (except \t, \n, \r)
_DANGEROUS_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Large base64 blobs (≥200 chars of continuous base64)
_BASE64_BLOB = re.compile(r"[A-Za-z0-9+/=]{200,}")

# Common homoglyph: Cyrillic chars that look identical to Latin
_CYRILLIC_HOMOGLYPHS = re.compile(
    r"[\u0410\u0412\u0415\u041a\u041c\u041d\u041e\u0420\u0421\u0422"
    r"\u0425\u0430\u0435\u043e\u0440\u0441\u0443\u0445]"
)


@dataclass
class SanitizeFinding:
    """A single suspicious pattern found during sanitization."""

    pattern_name: str
    description: str
    count: int
    severity: str  # low | medium | high | critical
    sample_positions: list[int] = field(default_factory=list)


@dataclass
class SanitizeResult:
    """Outcome of ingestion-time sanitization."""

    is_clean: bool
    should_reject: bool
    cleaned_text: str
    findings: list[SanitizeFinding] = field(default_factory=list)
    original_length: int = 0
    removed_char_count: int = 0

    @property
    def finding_names(self) -> list[str]:
        return [f.pattern_name for f in self.findings]


def sanitize_text(
    text: str,
    settings: GuardrailSettings | None = None,
) -> SanitizeResult:
    """Scan and clean document text for hidden/malicious content.

    Returns SanitizeResult with cleaned text and detailed findings.
    Does NOT mutate the input string.
    """
    if settings is None:
        from libs.core.settings import get_settings
        settings = get_settings().guardrails

    if not settings.sanitize_on_ingest:
        return SanitizeResult(
            is_clean=True,
            should_reject=False,
            cleaned_text=text,
            original_length=len(text),
        )

    findings: list[SanitizeFinding] = []
    cleaned = text
    original_length = len(text)
    total_removed = 0

    # ── 1. Null bytes and dangerous control chars ─────────────────────
    matches = list(_DANGEROUS_CONTROL.finditer(cleaned))
    if matches:
        findings.append(SanitizeFinding(
            pattern_name="dangerous_control_chars",
            description="Null bytes or C0 control characters detected",
            count=len(matches),
            severity="high",
            sample_positions=[m.start() for m in matches[:5]],
        ))
        total_removed += len(matches)
        cleaned = _DANGEROUS_CONTROL.sub("", cleaned)

    # ── 2. ANSI escape sequences ──────────────────────────────────────
    matches = list(_ANSI_ESCAPES.finditer(cleaned))
    if matches:
        findings.append(SanitizeFinding(
            pattern_name="ansi_escapes",
            description="ANSI escape sequences detected (terminal injection risk)",
            count=len(matches),
            severity="medium",
            sample_positions=[m.start() for m in matches[:5]],
        ))
        total_removed += sum(len(m.group()) for m in matches)
        cleaned = _ANSI_ESCAPES.sub("", cleaned)

    # ── 3. Bidirectional overrides (Trojan Source) ────────────────────
    matches = list(_BIDI_OVERRIDES.finditer(cleaned))
    if matches:
        findings.append(SanitizeFinding(
            pattern_name="bidi_override",
            description="Bidirectional text override characters (Trojan Source attack)",
            count=len(matches),
            severity="critical",
            sample_positions=[m.start() for m in matches[:5]],
        ))
        total_removed += len(matches)
        cleaned = _BIDI_OVERRIDES.sub("", cleaned)

    # ── 4. Invisible / zero-width characters ──────────────────────────
    matches = list(_INVISIBLE_CHARS.finditer(cleaned))
    if matches:
        invisible_ratio = len(matches) / max(len(cleaned), 1)
        severity = "high" if invisible_ratio > settings.max_hidden_text_ratio else "low"
        findings.append(SanitizeFinding(
            pattern_name="invisible_chars",
            description=(
                f"Invisible/zero-width characters: {len(matches)} "
                f"({invisible_ratio:.1%} of text)"
            ),
            count=len(matches),
            severity=severity,
            sample_positions=[m.start() for m in matches[:5]],
        ))
        total_removed += len(matches)
        cleaned = _INVISIBLE_CHARS.sub("", cleaned)

    # ── 5. Cyrillic homoglyphs mixed with Latin ──────────────────────
    if _CYRILLIC_HOMOGLYPHS.search(cleaned):
        # Only flag if the text is predominantly Latin
        latin_count = len(re.findall(r"[a-zA-Z]", cleaned))
        cyrillic_matches = list(_CYRILLIC_HOMOGLYPHS.finditer(cleaned))
        if latin_count > 0 and len(cyrillic_matches) > 0:
            ratio = len(cyrillic_matches) / max(latin_count + len(cyrillic_matches), 1)
            if ratio < 0.5:  # mixed script → suspicious
                findings.append(SanitizeFinding(
                    pattern_name="cyrillic_homoglyphs",
                    description=(
                        f"Cyrillic homoglyphs mixed with Latin text: "
                        f"{len(cyrillic_matches)} chars ({ratio:.1%})"
                    ),
                    count=len(cyrillic_matches),
                    severity="high",
                    sample_positions=[m.start() for m in cyrillic_matches[:5]],
                ))

    # ── 6. Large base64 blobs ─────────────────────────────────────────
    b64_matches = list(_BASE64_BLOB.finditer(cleaned))
    if b64_matches:
        findings.append(SanitizeFinding(
            pattern_name="base64_blob",
            description=(
                f"Large base64-encoded blobs detected: {len(b64_matches)} "
                f"(may hide embedded payloads)"
            ),
            count=len(b64_matches),
            severity="medium",
            sample_positions=[m.start() for m in b64_matches[:3]],
        ))

    # ── Decision: reject or pass ──────────────────────────────────────
    should_reject = False
    if settings.reject_on_hidden_text:
        has_critical = any(f.severity == "critical" for f in findings)
        high_invisible = any(
            f.pattern_name == "invisible_chars" and f.severity == "high"
            for f in findings
        )
        if has_critical or high_invisible:
            should_reject = True

    is_clean = len(findings) == 0

    if findings:
        logger.info(
            "sanitize: %d findings, reject=%s, removed=%d chars",
            len(findings),
            should_reject,
            total_removed,
        )

    return SanitizeResult(
        is_clean=is_clean,
        should_reject=should_reject,
        cleaned_text=cleaned,
        findings=findings,
        original_length=original_length,
        removed_char_count=total_removed,
    )
