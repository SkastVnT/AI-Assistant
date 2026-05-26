"""
image_pipeline.reasoning.state.prop_state_manager
=================================================

Session-scoped prop registry. Extracts (color, noun) and bare-noun props
from free text and emits frozen :class:`PropState` objects, deduplicated
by canonical key.

This is intentionally a tiny, in-memory store. A future cycle can back it
with a persistent prop database; today its scope is one parse() call or
one chat session, whichever the caller prefers.

The regex tables are duplicated (intentionally) from
``prompt_parser._extract_props`` so the parser keeps working without a
resolver. When a resolver IS injected, the parser delegates to this
manager instead. There is no behavioral drift between the two paths.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

from image_pipeline.reasoning.schemas import PropState

# Color + noun → prop candidate (Midjourney short-prompt style).
_COLOR_WORDS: tuple[str, ...] = (
    "red",
    "blue",
    "green",
    "yellow",
    "orange",
    "purple",
    "pink",
    "white",
    "black",
    "gray",
    "grey",
    "brown",
    "gold",
    "silver",
)
_PROP_NOUNS: tuple[str, ...] = (
    "phone",
    "mug",
    "cup",
    "book",
    "pillow",
    "blanket",
    "bed",
    "lamp",
    "laptop",
    "card",
    "letter",
    "knife",
    "gun",
    "sword",
    "guitar",
    "umbrella",
    "bag",
    "backpack",
    "hat",
    "mask",
    "ring",
    "necklace",
    "id",
    "license",
    "ticket",
    "key",
    "watch",
    "camera",
)

_PROP_RE = re.compile(
    r"\b(" + "|".join(_COLOR_WORDS) + r")\s+(" + "|".join(_PROP_NOUNS) + r")\b",
    re.IGNORECASE,
)
_BARE_PROP_RE = re.compile(
    r"\b(?:the|a|an)\s+(" + "|".join(_PROP_NOUNS) + r")\b",
    re.IGNORECASE,
)

_ID_SAFE_RE = re.compile(r"[^A-Za-z0-9_.\-]+")


def _safe_id(raw: str) -> str:
    cleaned = _ID_SAFE_RE.sub("_", (raw or "").strip()).strip("_")
    return (cleaned or "x")[:128]


class PropStateManager:
    """Holds a per-session ``dict[prop_key, PropState]`` and grows it from text."""

    def __init__(self) -> None:
        self._store: dict[str, PropState] = {}

    # -- Mutators --------------------------------------------------------

    def register(self, state: PropState) -> PropState:
        """Idempotent: register a prop. Returns the stored instance.

        If a prop with the same key already exists, the existing entry wins
        (first-write-wins) — drift is the caller's problem.
        """
        existing = self._store.get(state.prop_key)
        if existing is not None:
            return existing
        self._store[state.prop_key] = state
        return state

    def extract_props_from_text(self, text: str) -> tuple[tuple[str, PropState], ...]:
        """Scan ``text``, register new props, and return the props seen here.

        The return value mirrors ``prompt_parser._extract_props`` (Cycle 1)
        so the parser can swap implementations without restructuring.
        """
        if not text:
            return ()

        seen_keys: list[str] = []
        matched_nouns: set[str] = set()

        for m in _PROP_RE.finditer(text):
            color = m.group(1).lower()
            noun = m.group(2).lower()
            key = _safe_id(f"{color}_{noun}")
            if key in seen_keys:
                continue
            existing = self._store.get(key)
            if existing is None:
                state = PropState(
                    prop_key=key,
                    label=f"{color} {noun}",
                    canonical_tags=(color, noun),
                    color=color,
                    is_recurring=True,
                    notes="prop_state_manager extract",
                )
                self._store[key] = state
            seen_keys.append(key)
            matched_nouns.add(noun)

        for m in _BARE_PROP_RE.finditer(text):
            noun = m.group(1).lower()
            if noun in matched_nouns:
                continue
            key = _safe_id(noun)
            if key in seen_keys:
                continue
            existing = self._store.get(key)
            if existing is None:
                state = PropState(
                    prop_key=key,
                    label=noun,
                    canonical_tags=(noun,),
                    is_recurring=True,
                    notes="prop_state_manager extract (uncolored)",
                )
                self._store[key] = state
            seen_keys.append(key)
            matched_nouns.add(noun)

        return tuple((k, self._store[k]) for k in seen_keys)

    # -- Read accessors --------------------------------------------------

    def resolve(self, label_or_key: str) -> Optional[PropState]:
        """Find a registered prop by exact key, then by case-insensitive label."""
        if not label_or_key:
            return None
        key = _safe_id(label_or_key)
        if key in self._store:
            return self._store[key]
        target = label_or_key.strip().lower()
        for state in self._store.values():
            if state.label.lower() == target:
                return state
        return None

    def all(self) -> tuple[tuple[str, PropState], ...]:
        return tuple(self._store.items())

    def keys(self) -> Iterable[str]:
        return self._store.keys()

    def __len__(self) -> int:
        return len(self._store)


__all__ = ["PropStateManager"]
