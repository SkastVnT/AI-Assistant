"""Cheap, side-effect-free request-cost estimator for image-generation
routes.

The estimator is intentionally heuristic: it never opens a network
connection, never touches ComfyUI, never imports ``image_pipeline``. It
inspects the request payload and an optional ``character_preflight_result``
(the dict returned by ``routes/reasoning_image_gen.py::_assess_preflight``)
and returns a small classification object that callers can use to:

* short-circuit obviously expensive requests (``max_cost_level``),
* surface a confirmation prompt to the user
  (``should_require_confirmation``),
* hint at a faster path (``recommended_mode == "fast"``) when one
  exists upstream.

This module deliberately does NOT decide *what* the fast path is — it
only suggests "fast" so a route can pick its own cheaper preset (e.g.
single panel, fewer correction passes). No new image backend is
introduced.
"""
from __future__ import annotations

from typing import Any, Mapping

CostLevel = str  # "low" | "medium" | "high"
RecommendedMode = str  # "normal" | "fast" | "ask_confirmation"

_HIGH_LAYOUTS = frozenset({
    "grid_2x2", "grid_2x3", "grid_3x2", "grid_3x3",
    "horizontal_strip", "vertical_strip",
    "comic", "storyboard", "multi_panel",
})
_LARGE_PIXEL_THRESHOLD = 1024 * 1024 * 2  # ≥ ~2 MP → "high resolution"
_MANY_REFERENCES = 3  # ≥ 3 attachments → high


def _layout_is_multi_panel(payload: Mapping[str, Any]) -> bool:
    layout = (payload.get("layout") or "").lower()
    if layout and layout != "single" and layout in _HIGH_LAYOUTS:
        return True
    # ``num_panels`` / ``panel_count`` overrides a missing ``layout``.
    for key in ("num_panels", "panel_count", "panels"):
        v = payload.get(key)
        if isinstance(v, int) and v > 1:
            return True
    return False


def _is_high_res(payload: Mapping[str, Any]) -> bool:
    w = int(payload.get("width") or 0)
    h = int(payload.get("height") or 0)
    if w and h and (w * h) >= _LARGE_PIXEL_THRESHOLD:
        return True
    if payload.get("upscale") or payload.get("refine") or payload.get("hires_fix"):
        return True
    return False


def _correction_loop_requested(payload: Mapping[str, Any]) -> bool:
    v = payload.get("max_correction_passes")
    if isinstance(v, int) and v > 1:
        return True
    return bool(payload.get("correction_loop"))


def estimate_image_request_cost(
    payload: Mapping[str, Any] | None,
    character_preflight_result: Mapping[str, Any] | None = None,
) -> dict:
    """Classify how expensive an image request is likely to be.

    Returns a dict with keys:
      * ``estimated_cost_level`` — ``"low"`` | ``"medium"`` | ``"high"``
      * ``reasons`` — list of short tags explaining the signals seen.
      * ``recommended_mode`` — ``"normal"`` | ``"fast"`` | ``"ask_confirmation"``
      * ``should_require_confirmation`` — bool

    All inputs are read-only. ``payload`` may be ``None`` (treated as
    empty); ``character_preflight_result`` may be ``None`` (no character
    risk signal available).
    """
    payload = payload or {}
    preflight = character_preflight_result or {}
    reasons: list[str] = []
    high = False
    medium = False

    # ── HIGH signals ──────────────────────────────────────────────────
    if _layout_is_multi_panel(payload):
        high = True
        reasons.append("multi_panel_layout")

    if preflight.get("blocking_reason") == "multiple_characters" or (
        preflight.get("signals", {}).get("multiple_characters")
    ):
        high = True
        reasons.append("multiple_characters")

    char_risk = preflight.get("risk_level")
    block_reason = preflight.get("blocking_reason") or ""
    if char_risk == "high":
        # Includes: unresolved_unknown_no_traits, collision_no_series,
        # asks_for_known_identity_unsafe, style_misparsed_as_character.
        high = True
        reasons.append(f"character_risk_high:{block_reason or 'unknown'}")

    if _is_high_res(payload):
        high = True
        reasons.append("high_resolution_or_upscale")

    n_refs = int(payload.get("attached_images") or 0)
    if n_refs >= _MANY_REFERENCES:
        high = True
        reasons.append(f"many_references:{n_refs}")

    if _correction_loop_requested(payload):
        high = True
        reasons.append("correction_loop")

    # ── MEDIUM signals (only matter if not already HIGH) ─────────────
    if not high:
        if char_risk == "medium":
            medium = True
            reasons.append(f"character_risk_medium:{block_reason or 'unknown'}")
        elif preflight.get("character_mode") == "low_data_profile":
            medium = True
            reasons.append("low_data_profile")
        elif n_refs == 2:
            medium = True
            reasons.append("two_references")

    # ── Resolve level ────────────────────────────────────────────────
    if high:
        level: CostLevel = "high"
    elif medium:
        level = "medium"
    else:
        level = "low"
        if not reasons:
            reasons.append("generic_request")

    # ── Recommended mode ─────────────────────────────────────────────
    budget_mode = (payload.get("budget_mode") or "").lower()
    max_cost = (payload.get("max_cost_level") or "").lower()

    if budget_mode == "fast":
        recommended: RecommendedMode = "fast"
    elif level == "high" and max_cost in {"low", "medium"}:
        recommended = "ask_confirmation"
    elif level == "high":
        recommended = "ask_confirmation"
    else:
        recommended = "normal"

    should_require_confirmation = (
        max_cost in {"low", "medium"}
        and _level_exceeds(level, max_cost)
    )

    return {
        "estimated_cost_level": level,
        "reasons": reasons,
        "recommended_mode": recommended,
        "should_require_confirmation": bool(should_require_confirmation),
    }


_LEVEL_RANK = {"low": 0, "medium": 1, "high": 2}


def _level_exceeds(actual: str, ceiling: str) -> bool:
    return _LEVEL_RANK.get(actual, 0) > _LEVEL_RANK.get(ceiling, 2)


__all__ = ["estimate_image_request_cost"]
