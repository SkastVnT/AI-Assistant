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
        r"\b(?:young-looking|age[- ]?ambiguous|unknown age)\b",
        r"\b(?:forced|coerced|non[- ]?consensual|unconscious|asleep|drugged)\b",
        r"\b(?:incest|bestiality)\b",
    )
)

_VALID_ATTESTATION_SOURCES = frozenset({"request", "character_pack", "worker"})


def assert_adult_subject_allowed(
    prompt: str,
    *,
    adult_verified: bool,
    attestation_source: str,
) -> AdultSubjectGuardResult:
    """Reject adult-only work unless local adult attestation is explicit and clean."""

    source = (attestation_source or "").strip().lower()
    if not adult_verified or source not in _VALID_ATTESTATION_SOURCES:
        raise PolicyViolation(
            "adult_only requires a verified-adult attestation source"
        )

    text = prompt or ""
    if any(pattern.search(text) for pattern in _PROHIBITED_PATTERNS):
        raise PolicyViolation(
            "adult_only rejected: prohibited or age-ambiguous subject context"
        )

    return AdultSubjectGuardResult(allowed=True, attestation_source=source)


__all__ = ["AdultSubjectGuardResult", "assert_adult_subject_allowed"]
