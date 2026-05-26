"""
image_pipeline.reasoning.prompt_revision — Normalize natural-language image
requests into a short, structured form before planning.

Modeled on:
* xAI/Grok prompt-revision: rewrite the user's prose into a concise generation
  prompt while preserving original intent.
* Midjourney short-prompt preference: prefer comma-separated tokens over long
  conversational sentences.
* ChatGPT Images precise instruction following: extract explicit must-keep /
  forbidden-drift / region-targeting hints.
* Gemini conversation-aware editing: carry must-keep / forbidden-drift from
  prior turns through ``prior_must_keep`` / ``prior_forbidden_drift``.

Hard rules
----------
* **Never invent content.** Only tokens derived from ``text`` (or carried in
  via prior_*) appear in the output.
* **Preserve original intent.** ``source_text`` always retains the raw input.
* **Deterministic.** No LLM calls, no randomness, no I/O.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from image_pipeline.reasoning.schemas import (
    OverlayKind,
    SchemaValidationError,
)

# ---------------------------------------------------------------------------
# Public type
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RevisedPrompt:
    """Output of :func:`revise`. All fields are derived from ``source_text``."""

    source_text: str
    normalized_prompt: str
    must_keep: tuple[str, ...] = ()
    may_change: tuple[str, ...] = ()
    forbidden_drift: tuple[str, ...] = ()
    requires_overlay: bool = False
    requires_regional_patch: bool = False
    detected_overlay_kinds: tuple[OverlayKind, ...] = ()
    detected_regions: tuple[str, ...] = ()  # e.g. "face", "eyes", "background"
    extracted_quoted_text: tuple[str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "source_text": self.source_text,
            "normalized_prompt": self.normalized_prompt,
            "must_keep": list(self.must_keep),
            "may_change": list(self.may_change),
            "forbidden_drift": list(self.forbidden_drift),
            "requires_overlay": self.requires_overlay,
            "requires_regional_patch": self.requires_regional_patch,
            "detected_overlay_kinds": [k.value for k in self.detected_overlay_kinds],
            "detected_regions": list(self.detected_regions),
            "extracted_quoted_text": list(self.extracted_quoted_text),
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Pattern tables
# ---------------------------------------------------------------------------

# Filler clauses Midjourney/Grok docs explicitly recommend stripping.
_FILLER_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bplease\b",
        r"\bcould\s+you\b",
        r"\bcan\s+you\b",
        r"\bwould\s+you\b",
        r"\bi\s+(?:want|would\s+like|need|wish)\b",
        r"\bi'?d\s+like\b",
        r"\bfor\s+me\b",
        r"\bif\s+possible\b",
        r"\bthank\s+you\b",
        r"\bthanks\b",
        r"\bsure\b,?\s*",
        r"\bok(?:ay)?\b,?\s*",
        r"\bjust\s+(?:make|create|generate|draw)\b",
        r"\b(?:make|create|generate|draw|render|produce|paint|give\s+me)\s+(?:me\s+)?(?:an?|the)\b",
        r"\b(?:make|create|generate|draw|render|produce|paint|give\s+me)\s+(?:me\s+)?\b",
    )
)

# Must-keep language (ChatGPT Images "preserve" + Gemini conversation continuity).
_MUST_KEEP_RE = re.compile(
    r"\b(?:keep|preserve|retain|maintain|same|still\s+(?:wearing|has|with)|"
    r"do\s+not\s+change|don'?t\s+change|leave\s+(?:the|her|his|their|its)\s+\w+\s+(?:alone|untouched))"
    r"\s+(?:the\s+)?([a-z][a-z0-9 \-']{2,40})",
    re.IGNORECASE,
)

# Explicit forbidden-drift markers.
_FORBIDDEN_DRIFT_RE = re.compile(
    r"\b(?:no|without|avoid|never|must\s+not\s+(?:have|change|include)|do\s+not\s+(?:have|include|change))"
    r"\s+(?:the\s+|a\s+|any\s+)?([a-z][a-z0-9 \-']{2,40})",
    re.IGNORECASE,
)

# Change-allowed markers.
_MAY_CHANGE_RE = re.compile(
    r"\b(?:but\s+change|now\s+with|swap\s+to|switch\s+to|change\s+(?:the|her|his|their|its))"
    r"\s+(?:the\s+)?([a-z][a-z0-9 \-']{2,40})",
    re.IGNORECASE,
)

# Quoted text → overlay candidate ("Hello", 'Hello', “Hello”).
_QUOTED_RE = re.compile(r"""(?:"([^"]{1,120})"|'([^']{1,120})'|“([^”]{1,120})”)""")

# Overlay-kind keywords. Order matters: longest/most-specific first.
_OVERLAY_KEYWORDS: tuple[tuple[OverlayKind, re.Pattern[str]], ...] = (
    (
        OverlayKind.SPEECH_BUBBLE,
        re.compile(r"\b(?:speech\s*bubble|dialogue\s*bubble|word\s*balloon)\b", re.I),
    ),
    (
        OverlayKind.THOUGHT_BUBBLE,
        re.compile(r"\b(?:thought\s*bubble|thinking\s*cloud)\b", re.I),
    ),
    (
        OverlayKind.PHONE_UI,
        re.compile(
            r"\b(?:phone\s*(?:screen|ui)|notification|text\s+message\s+on\s+(?:the\s+)?phone)\b",
            re.I,
        ),
    ),
    (
        OverlayKind.ID_CARD,
        re.compile(
            r"\b(?:id\s*card|driver'?s?\s*license|business\s*card|name\s*tag)\b", re.I
        ),
    ),
    (
        OverlayKind.TITLE_BAR,
        re.compile(r"\b(?:title\s*bar|header\s*bar|title\s+at\s+the\s+top)\b", re.I),
    ),
    (
        OverlayKind.PANEL_LABEL,
        re.compile(
            r"\b(?:panel\s*label|panel\s*title|caption\s+for\s+(?:the\s+)?panel)\b",
            re.I,
        ),
    ),
    (OverlayKind.CAPTION, re.compile(r"\b(?:caption|subtitle|text\s*overlay)\b", re.I)),
    (OverlayKind.SFX, re.compile(r"\b(?:sound\s*effect|sfx|onomatopoeia)\b", re.I)),
    (OverlayKind.WATERMARK, re.compile(r"\bwatermark\b", re.I)),
)

# Region keywords used to flag regional patch needs.
_REGION_TOKENS: tuple[str, ...] = (
    "face",
    "eyes",
    "eye",
    "iris",
    "pupil",
    "mouth",
    "lips",
    "nose",
    "ear",
    "hair",
    "hand",
    "hands",
    "finger",
    "background",
    "foreground",
    "logo",
    "text",
    "skin",
    "outfit",
    "clothing",
    "shirt",
    "dress",
    "shoes",
)
_REGION_RE = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in _REGION_TOKENS) + r")\b",
    re.IGNORECASE,
)

# Tokens collapsed to canonical form so equality checks survive whitespace
# differences.
_WS_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def revise(
    text: str,
    *,
    prior_must_keep: Iterable[str] = (),
    prior_forbidden_drift: Iterable[str] = (),
) -> RevisedPrompt:
    """
    Normalize ``text`` into a :class:`RevisedPrompt`.

    Carries ``prior_must_keep`` and ``prior_forbidden_drift`` from earlier
    turns (Gemini conversation-aware, Grok multi-turn) without inventing new
    content.
    """
    if not isinstance(text, str):
        raise SchemaValidationError("revise(text=...) requires a string")
    source_text = text
    working = text

    # 1. Pull quoted text out before any other normalization (these become
    #    overlay text candidates and must not be mangled by filler stripping).
    quoted = _extract_quoted(working)
    for q in quoted:
        # Replace the quoted occurrence with a placeholder so filler regexes
        # don't touch the quoted body.
        working = (
            working.replace(f'"{q}"', " ").replace(f"'{q}'", " ").replace(f"“{q}”", " ")
        )

    # 2. Extract structured slots from the *raw* working text (case-insensitive).
    must_keep = _dedupe_preserve_order(
        list(prior_must_keep) + _find_all(_MUST_KEEP_RE, working)
    )
    may_change = _dedupe_preserve_order(_find_all(_MAY_CHANGE_RE, working))
    forbidden_drift = _dedupe_preserve_order(
        list(prior_forbidden_drift) + _find_all(_FORBIDDEN_DRIFT_RE, working)
    )

    # 3. Detect overlay needs.
    detected_overlay_kinds: list[OverlayKind] = []
    for kind, pat in _OVERLAY_KEYWORDS:
        if pat.search(working) or (
            kind in (OverlayKind.CAPTION, OverlayKind.TITLE_BAR) and quoted
        ):
            if kind not in detected_overlay_kinds:
                detected_overlay_kinds.append(kind)
    # Quoted text without any specific overlay keyword still implies a caption.
    if quoted and not detected_overlay_kinds:
        detected_overlay_kinds.append(OverlayKind.CAPTION)

    # 4. Detect regional patch needs.
    regions = _dedupe_preserve_order(
        m.group(1).lower() for m in _REGION_RE.finditer(working)
    )

    # 5. Strip filler from the prose body to produce normalized_prompt.
    body = working
    for pat in _FILLER_PATTERNS:
        body = pat.sub(" ", body)
    body = _WS_RE.sub(" ", body).strip(" ,.;:")
    normalized = _midjourney_compress(body)

    return RevisedPrompt(
        source_text=source_text,
        normalized_prompt=normalized,
        must_keep=tuple(must_keep),
        may_change=tuple(may_change),
        forbidden_drift=tuple(forbidden_drift),
        requires_overlay=bool(detected_overlay_kinds),
        requires_regional_patch=bool(regions),
        detected_overlay_kinds=tuple(detected_overlay_kinds),
        detected_regions=tuple(regions),
        extracted_quoted_text=tuple(quoted),
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _find_all(pattern: re.Pattern[str], text: str) -> list[str]:
    out: list[str] = []
    for m in pattern.finditer(text):
        captured = next((g for g in m.groups() if g), "")
        cleaned = _WS_RE.sub(" ", captured).strip(" ,.;:'\"").lower()
        if cleaned:
            out.append(cleaned)
    return out


def _extract_quoted(text: str) -> list[str]:
    out: list[str] = []
    for m in _QUOTED_RE.finditer(text):
        for g in m.groups():
            if g and g.strip():
                out.append(g.strip())
                break
    return out


def _dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        key = v.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _midjourney_compress(text: str) -> str:
    """
    Apply Midjourney short-prompt style: collapse common conjunctions to commas
    and dedupe trivial repeats. Never adds new tokens.
    """
    if not text:
        return ""
    # Replace " and ", " with ", " plus " between visual tokens with commas.
    out = re.sub(r"\s*\b(?:and|with|plus)\b\s*", ", ", text, flags=re.IGNORECASE)
    out = re.sub(r"\s*,\s*", ", ", out)
    # Drop trailing/leading commas and collapse repeats.
    parts = [p.strip() for p in out.split(",") if p.strip()]
    deduped: list[str] = []
    seen: set[str] = set()
    for p in parts:
        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)
    return ", ".join(deduped)


__all__ = ["RevisedPrompt", "revise"]
