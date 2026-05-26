"""
core/image_intent.py — Lightweight image-intent detector for the Hermes bridge.

This module is the ONLY place in services/chatbot/ that imports from
image_pipeline.reasoning.  All other chatbot code must NOT import image_pipeline
directly.

Usage (inside routes/hermes.py):
    from core.image_intent import detect_image_intent, IMAGE_KINDS

    decision = detect_image_intent(message)
    if decision and decision.kind in IMAGE_KINDS:
        # redirect to reasoning pipeline
        ...

Design decisions:
- Import of image_pipeline is done lazily (inside the function) so that if
  REASONING_PIPELINE is False or image_pipeline is absent, nothing blows up at
  service startup.
- Returns None on any import/runtime error (graceful degradation: fall through
  to Hermes chat path).
- No state, no singleton — pure function, safe to call from any context.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from image_pipeline.reasoning.capability_router import CapabilityDecision

logger = logging.getLogger(__name__)

# Capability kinds that should be routed to the image/reasoning pipeline.
# TEXT_TO_IMAGE, COMIC_SEQUENCE — pure generation requests.
# IMAGE_EDIT, MULTI_IMAGE_COMPOSE, ITERATIVE_REFINE — also image work but
# require attached images; Hermes route currently receives text-only, so these
# are included for future-proofing but will rarely be triggered in practice.
IMAGE_KINDS_NAMES: frozenset[str] = frozenset(
    {
        "text_to_image",
        "comic_sequence",
        "image_edit",
        "multi_image_compose",
        "iterative_refine",
    }
)


def is_reasoning_pipeline_enabled() -> bool:
    """Return True if the reasoning pipeline opt-in flag is active."""
    return os.environ.get("REASONING_PIPELINE", "").lower() in ("1", "true", "yes")


def detect_image_intent(
    message: str,
    *,
    attached_images: int = 0,
    is_followup: bool = False,
) -> CapabilityDecision | None:
    """Classify *message* using capability_router and return a decision.

    Returns None if:
    - REASONING_PIPELINE env is not set/true (feature disabled)
    - image_pipeline is not importable (venv-image not active, etc.)
    - Any runtime error during classification

    The caller should treat None as "no redirect — continue to Hermes".

    Parameters
    ----------
    message : str
        The user message text.
    attached_images : int
        Number of images attached to the request (0 for text-only Hermes calls).
    is_followup : bool
        Whether this is a follow-up turn in an ongoing image conversation.
    """
    if not is_reasoning_pipeline_enabled():
        return None

    try:
        from image_pipeline.reasoning.capability_router import (  # noqa: PLC0415
            CapabilityRequest,
            classify,
        )

        request = CapabilityRequest(
            text=message,
            attached_images=attached_images,
            is_followup=is_followup,
        )
        decision = classify(request)
        logger.debug(
            "[IMAGE-INTENT] kind=%s confidence=%.2f reasons=%s",
            decision.kind.value,
            decision.confidence,
            decision.reasons,
        )
        return decision
    except ImportError:
        logger.debug(
            "[IMAGE-INTENT] image_pipeline not importable — reasoning bridge inactive"
        )
        return None
    except Exception as exc:
        logger.warning(
            "[IMAGE-INTENT] classify() raised %s: %s", type(exc).__name__, exc
        )
        return None


def should_redirect_to_reasoning(message: str) -> bool:
    """Convenience boolean check for route-level gating.

    Returns True only when:
    1. REASONING_PIPELINE=true
    2. image_pipeline.reasoning is importable
    3. classifier returns a confidence >= 0.75
    4. detected kind is an image-generation kind

    Threshold of 0.75 avoids misfires on ambiguous phrasing like "show me X"
    that could be either a question or an image request.
    """
    decision = detect_image_intent(message)
    if decision is None:
        return False
    return decision.kind.value in IMAGE_KINDS_NAMES and decision.confidence >= 0.75
