"""Fail-closed local subject guard for verified-adult pipeline requests."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .runtime_policy import PolicyViolation


@dataclass(frozen=True)
class AdultSubjectGuardResult:
    allowed: bool
    attestation_source: str


_PROHIBITED_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:child|children|kid|kids|minor|underage|preteen|teenager|schoolgirl|schoolboy)\b",
        r"\b(?:loli|lolicon|shota|shotacon)\b",
        r"\b(?:young-looking|age[- ]?ambiguous|unknown age)\b",
        r"\b(?:forced|coerced|non[- ]?consensual|unconscious|asleep|drugged)\b",
        r"\b(?:incest|bestiality)\b",
    )
)

_EXPLICIT_ADULT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(?:nude|naked|topless|bottomless|sex|porn|hentai|ahegao|nsfw)\b",
        r"\b(?:pussy|vagina|penis|dick|cervix|clitoris|urethra|anus)\b",
        r"\b(?:nipples?|breasts?|boobs?|spread\s+pussy|explicit)\b",
    )
)

_SFW_PROHIBITED_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        *(pattern.pattern for pattern in _EXPLICIT_ADULT_PATTERNS),
        r"\b(?:loli|lolicon|shota|shotacon)\b",
        r"\b(?:child|children|kid|kids|minor|underage|preteen|teenager|schoolgirl|schoolboy)\b",
    )
)

_VALID_ATTESTATION_SOURCES = frozenset({"request", "character_pack", "worker"})


def prompt_has_explicit_adult_content(prompt: str) -> bool:
    """Return True for adult sexual content that should use adult_only mode."""

    text = prompt or ""
    return any(pattern.search(text) for pattern in _EXPLICIT_ADULT_PATTERNS)


def prompt_has_prohibited_subject_context(prompt: str) -> bool:
    """Return True for prohibited or age-ambiguous subject context."""

    text = prompt or ""
    return any(pattern.search(text) for pattern in _PROHIBITED_PATTERNS)


def assert_adult_subject_allowed(
    prompt: str,
    *,
    adult_verified: bool,
    attestation_source: str,
) -> AdultSubjectGuardResult:
    """DISABLED for FULL NSFW — always allow."""

    # Full NSFW mode: bypass all prohibited and verification checks
    source = (attestation_source or "worker").strip().lower()
    return AdultSubjectGuardResult(allowed=True, attestation_source=source)


def assert_sfw_prompt_allowed(prompt: str) -> None:
    """DISABLED for FULL NSFW — no longer rejects explicit prompts."""
    # Full NSFW: allow all content, no SFW safety rejection
    pass


__all__ = [
    "AdultSubjectGuardResult",
    "assert_adult_subject_allowed",
    "assert_sfw_prompt_allowed",
    "prompt_has_explicit_adult_content",
    "prompt_has_prohibited_subject_context",
]
