"""
image_pipeline.reasoning.capability_router — Deterministic request classifier.

Classifies a user-facing image request into one of five capability kinds before
any planner runs. This is the very first node in the reasoning chain (SKILL.md
step 1). Rules are deterministic and ordered; LLM disambiguation may be added
later as a tie-breaker but is never the primary signal.

Capability kinds (modeled on the four documented sources):

* ``TEXT_TO_IMAGE``      — pure text → image (Gemini text-to-image, Midjourney
                           short-prompt mode).
* ``IMAGE_EDIT``         — one input image + instruction (ChatGPT Images edit,
                           Gemini image+text editing, Grok natural-language
                           editing).
* ``MULTI_IMAGE_COMPOSE``— two or more reference images merged into one output
                           (Gemini multi-image composition, Midjourney
                           moodboard/style-reference/character-reference).
* ``ITERATIVE_REFINE``   — follow-up turn that tweaks the previous result
                           without new images (Gemini conversation-aware,
                           Grok multi-turn refinement, ChatGPT Images
                           iterative refinement).
* ``COMIC_SEQUENCE``     — ordered multi-panel output from a single request
                           (storyboards / strips / pages — required by
                           SKILL.md "multi-panel workflows").

This module imports nothing from the rest of the package so it can be used
independently by the chat router, the FastAPI path, and tests.
"""

from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Iterable

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


class RequestKind(str, enum.Enum):
    """Top-level capability kinds the router emits."""

    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_EDIT = "image_edit"
    MULTI_IMAGE_COMPOSE = "multi_image_compose"
    ITERATIVE_REFINE = "iterative_refine"
    COMIC_SEQUENCE = "comic_sequence"


@dataclass(frozen=True, slots=True)
class CapabilityRequest:
    """Inbound request descriptor consumed by ``classify``."""

    text: str = ""
    attached_images: int = 0
    is_followup: bool = False
    prior_image_ref: str | None = None
    explicit_kind: RequestKind | None = None  # UI override; bypasses rules.


@dataclass(frozen=True, slots=True)
class CapabilityDecision:
    """Router output. ``required_stages`` is a hint the execution planner refines."""

    kind: RequestKind
    confidence: float
    reasons: tuple[str, ...] = ()
    required_stages: tuple[str, ...] = ()
    panel_count_hint: int | None = None  # Set when COMIC_SEQUENCE detected a count.

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "required_stages": list(self.required_stages),
            "panel_count_hint": self.panel_count_hint,
        }


# ---------------------------------------------------------------------------
# Keyword tables (anchored, case-insensitive, word-boundary)
# ---------------------------------------------------------------------------

# Comic / sequence triggers. Order matters only for reason logging.
_COMIC_PHRASE_RE = re.compile(
    r"\b("
    r"comic|comic\s*strip|comic\s*page|storyboard|story\s*board|"
    r"manga\s*page|webtoon|four[-\s]?koma|yonkoma|"
    r"sequence\s+of\s+\d+\s+(?:images|panels|scenes|frames)"
    r")\b",
    re.IGNORECASE,
)

# "4 panels", "4-panel", "panel 1 / panel 2", etc.
_PANEL_COUNT_RE = re.compile(
    r"\b(\d{1,2})\s*[-\s]?\s*(?:panel|panels|frame|frames|scene|scenes|page|pages)\b",
    re.IGNORECASE,
)
_PANEL_LABEL_RE = re.compile(
    r"\bpanel\s*([0-9]{1,2})\b",
    re.IGNORECASE,
)

# Edit / instruction keywords (ChatGPT Images + Grok natural-language editing).
_EDIT_KEYWORDS_RE = re.compile(
    r"\b("
    r"edit|remove|delete|erase|add|insert|replace|swap|change|"
    r"recolor|repaint|crop|extend|outpaint|inpaint|fix|"
    r"make\s+(?:the|her|his|their|its)\s+\w+|"
    r"turn\s+(?:the|her|his|their|its)\s+\w+\s+(?:into|to)|"
    r"without\s+the\s+\w+|with\s+a\s+different\s+\w+|"
    r"change\s+the\s+background|new\s+background"
    r")\b",
    re.IGNORECASE,
)

# Pure refinement keywords (no new content; conversation-aware tweaks).
_REFINE_KEYWORDS_RE = re.compile(
    r"\b("
    r"refine|tweak|polish|improve|enhance|sharpen|softer|brighter|darker|"
    r"more\s+\w+|less\s+\w+|a\s+bit\s+\w+|slightly|just\s+a\s+little|"
    r"now\s+make\s+it|instead|but\s+make\s+it|same\s+but|same\s+image\s+but|"
    r"redo|try\s+again|another\s+version|variation|same\s+pose"
    r")\b",
    re.IGNORECASE,
)

# Composition triggers (Midjourney moodboard / character-reference language).
_COMPOSE_KEYWORDS_RE = re.compile(
    r"\b("
    r"combine|merge|composite|mix|blend|put\s+(?:them|these)\s+together|"
    r"using\s+these\s+(?:references|images)|in\s+the\s+style\s+of\s+(?:these|the\s+attached)|"
    r"moodboard|style\s+reference|character\s+reference|omni\s+reference"
    r")\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(request: CapabilityRequest) -> CapabilityDecision:
    """
    Classify ``request`` into a :class:`RequestKind` using deterministic rules.

    Rule order (first match wins, except UI override):

    1. ``request.explicit_kind`` (UI dropdown / API caller) wins outright.
    2. Comic / sequence cues in text → ``COMIC_SEQUENCE``.
    3. ≥2 attached images → ``MULTI_IMAGE_COMPOSE`` (Gemini multi-image,
       Midjourney moodboard).
    4. Composition keywords with ≥1 attached image → ``MULTI_IMAGE_COMPOSE``.
    5. Follow-up turn with no new image and a refinement cue
       → ``ITERATIVE_REFINE`` (Gemini conversation-aware, Grok multi-turn).
    6. 1 attached image, OR follow-up with a prior_image_ref, with edit cue
       → ``IMAGE_EDIT``.
    7. 1 attached image and no edit cue → ``IMAGE_EDIT`` (best-effort default
       per ChatGPT Images doc: any single attached image implies an edit).
    8. Otherwise → ``TEXT_TO_IMAGE``.
    """
    if request.explicit_kind is not None:
        return CapabilityDecision(
            kind=request.explicit_kind,
            confidence=1.0,
            reasons=("explicit_kind override",),
            required_stages=_default_stages_for(request.explicit_kind),
        )

    text = request.text or ""
    reasons: list[str] = []

    # 2. Comic sequence.
    panel_count = _detect_panel_count(text)
    comic_match = _COMIC_PHRASE_RE.search(text)
    if comic_match or (panel_count and panel_count >= 2):
        if comic_match:
            reasons.append(f"comic phrase: {comic_match.group(0).lower()!r}")
        if panel_count:
            reasons.append(f"panel count detected: {panel_count}")
        return CapabilityDecision(
            kind=RequestKind.COMIC_SEQUENCE,
            confidence=0.95 if comic_match and panel_count else 0.85,
            reasons=tuple(reasons),
            required_stages=_default_stages_for(RequestKind.COMIC_SEQUENCE),
            panel_count_hint=panel_count,
        )

    # 3. Multi-image attached.
    if request.attached_images >= 2:
        reasons.append(f"{request.attached_images} attached images")
        return CapabilityDecision(
            kind=RequestKind.MULTI_IMAGE_COMPOSE,
            confidence=0.95,
            reasons=tuple(reasons),
            required_stages=_default_stages_for(RequestKind.MULTI_IMAGE_COMPOSE),
        )

    # 4. Composition keywords with one attachment.
    compose_match = _COMPOSE_KEYWORDS_RE.search(text)
    if compose_match and request.attached_images >= 1:
        reasons.append(f"composition keyword: {compose_match.group(0).lower()!r}")
        return CapabilityDecision(
            kind=RequestKind.MULTI_IMAGE_COMPOSE,
            confidence=0.8,
            reasons=tuple(reasons),
            required_stages=_default_stages_for(RequestKind.MULTI_IMAGE_COMPOSE),
        )

    # 5. Iterative refine on follow-up.
    refine_match = _REFINE_KEYWORDS_RE.search(text)
    if request.is_followup and request.attached_images == 0 and refine_match:
        reasons.append("follow-up turn")
        reasons.append(f"refine keyword: {refine_match.group(0).lower()!r}")
        return CapabilityDecision(
            kind=RequestKind.ITERATIVE_REFINE,
            confidence=0.9,
            reasons=tuple(reasons),
            required_stages=_default_stages_for(RequestKind.ITERATIVE_REFINE),
        )

    # 6./7. Image edit.
    edit_match = _EDIT_KEYWORDS_RE.search(text)
    has_prior_image = bool(request.prior_image_ref)
    if (request.attached_images == 1) or (
        request.is_followup and has_prior_image and edit_match
    ):
        if edit_match:
            reasons.append(f"edit keyword: {edit_match.group(0).lower()!r}")
        if request.attached_images == 1:
            reasons.append("1 attached image")
        if has_prior_image and request.is_followup:
            reasons.append("follow-up referencing prior image")
        confidence = 0.9 if edit_match else 0.7
        return CapabilityDecision(
            kind=RequestKind.IMAGE_EDIT,
            confidence=confidence,
            reasons=tuple(reasons),
            required_stages=_default_stages_for(RequestKind.IMAGE_EDIT),
        )

    # 8. Default.
    reasons.append("no edit/compose/refine/sequence signal")
    return CapabilityDecision(
        kind=RequestKind.TEXT_TO_IMAGE,
        confidence=0.6 if not text.strip() else 0.85,
        reasons=tuple(reasons),
        required_stages=_default_stages_for(RequestKind.TEXT_TO_IMAGE),
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _detect_panel_count(text: str) -> int | None:
    """Return the largest plausible panel count in ``text`` (1–32) or ``None``."""
    candidates: list[int] = []
    for m in _PANEL_COUNT_RE.finditer(text):
        try:
            n = int(m.group(1))
        except ValueError:
            continue
        if 1 <= n <= 32:
            candidates.append(n)
    label_count = len({m.group(1) for m in _PANEL_LABEL_RE.finditer(text)})
    if label_count >= 2:
        candidates.append(label_count)
    if not candidates:
        return None
    return max(candidates)


# Default stage hints. The execution planner replaces this with a real
# ExecutionPlan that respects the capability matrix; this is just a sane
# starting point so callers don't have to special-case the kind themselves.
_STAGE_HINTS: dict[RequestKind, tuple[str, ...]] = {
    RequestKind.TEXT_TO_IMAGE: ("base", "refine"),
    RequestKind.IMAGE_EDIT: ("inpaint", "refine"),
    RequestKind.MULTI_IMAGE_COMPOSE: ("reference_encode", "base", "refine"),
    RequestKind.ITERATIVE_REFINE: ("inpaint", "refine"),
    RequestKind.COMIC_SEQUENCE: ("base", "face_patch", "overlay", "refine"),
}


def _default_stages_for(kind: RequestKind) -> tuple[str, ...]:
    return _STAGE_HINTS.get(kind, ())


__all__ = [
    "CapabilityDecision",
    "CapabilityRequest",
    "RequestKind",
    "classify",
]
