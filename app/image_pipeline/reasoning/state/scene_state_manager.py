"""
image_pipeline.reasoning.state.scene_state_manager
==================================================

Pure-function scene extractor.

Wraps the keyword tables that previously lived inline in
``prompt_parser._build_scene`` so the same logic is reusable from the
state-resolver path. Behavior is byte-identical to Cycle 1.
"""

from __future__ import annotations

from image_pipeline.reasoning.schemas import SceneState

_LOCATION_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("bedroom", "bedroom"),
    ("kitchen", "kitchen"),
    ("bathroom", "bathroom"),
    ("living room", "living_room"),
    ("classroom", "classroom"),
    ("school", "school"),
    ("office", "office"),
    ("park", "park"),
    ("forest", "forest"),
    ("beach", "beach"),
    ("street", "street"),
    ("cafe", "cafe"),
    ("coffee shop", "cafe"),
    ("library", "library"),
    ("rooftop", "rooftop"),
    ("subway", "subway"),
    ("train station", "train_station"),
)

_TIME_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("morning", "morning"),
    ("noon", "noon"),
    ("afternoon", "afternoon"),
    ("evening", "evening"),
    ("sunset", "sunset"),
    ("dusk", "dusk"),
    ("night", "night"),
    ("midnight", "midnight"),
    ("dawn", "dawn"),
)

_MOOD_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("cozy", "cozy"),
    ("tense", "tense"),
    ("dramatic", "dramatic"),
    ("playful", "playful"),
    ("romantic", "romantic"),
    ("sad", "sad"),
    ("happy", "happy"),
    ("mysterious", "mysterious"),
    ("creepy", "creepy"),
)


def extract_scene(text: str) -> SceneState:
    """Return a :class:`SceneState` populated from keyword matches in ``text``."""
    lower = (text or "").lower()
    location = ""
    for kw, canon in _LOCATION_KEYWORDS:
        if kw in lower:
            location = canon
            break
    time_of_day = ""
    for kw, canon in _TIME_KEYWORDS:
        if kw in lower:
            time_of_day = canon
            break
    mood = ""
    for kw, canon in _MOOD_KEYWORDS:
        if kw in lower:
            mood = canon
            break
    return SceneState(
        location=location,
        time_of_day=time_of_day,
        mood=mood,
        lock_scene=True,
    )


__all__ = ["extract_scene"]
