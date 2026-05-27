"""
image_pipeline.reasoning.state.character_state_manager
======================================================

Resolve a character query (key, display name, or alias) against an external
registry and emit a frozen :class:`CharacterState`.

The manager is **registry-agnostic**: it duck-types on two methods:

* ``registry.get(key) -> record | None``
* ``registry.resolve_query(q) -> record | None``

The chatbot's :mod:`services.chatbot.core.character_registry` matches this
shape (its ``CharacterRecord`` carries ``key``, ``display_name``, ``series``,
``character_tag``, ``series_tag``, ``aliases``, ``lora_hint``).

Per Cycle-2 decision (NANO_BANANA_LOCAL_INTEGRATION_PLAN.md §4.2):
``CharacterState.must_keep`` is sourced from the registry record's identity
tokens (display_name + character_tag). When the registry has no entry for
a given key, the caller falls back to the placeholder behavior preserved
in :func:`from_hint` so Cycle-1 tests stay green.

This module performs no I/O and does not load .env. The registry is
imported lazily by :func:`_default_registry` only when a registry is not
explicitly injected.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Mapping, Optional, Protocol

from image_pipeline.reasoning.schemas import (
    CharacterAppearance,
    CharacterState,
)

logger = logging.getLogger(__name__)

_ID_SAFE_RE = re.compile(r"[^A-Za-z0-9_.\-]+")


def _safe_id(raw: str) -> str:
    cleaned = _ID_SAFE_RE.sub("_", (raw or "").strip()).strip("_")
    return (cleaned or "x")[:128]


class _RegistryLike(Protocol):
    """Duck type the manager expects from a character registry."""

    def get(self, key: str) -> Any: ...  # CharacterRecord | None
    def resolve_query(self, query: str) -> Any: ...


def _default_registry() -> Optional[_RegistryLike]:
    """Lazy import of the chatbot's CharacterRegistry singleton.

    Returns ``None`` if the chatbot package is not importable in this
    process (i.e. ``services/chatbot/`` is not on ``sys.path``). The
    chatbot's own runtime always satisfies this; standalone uses of
    ``image_pipeline`` (tests, future microservices) should inject a
    registry explicitly via the ``registry=`` constructor kwarg.
    """
    try:
        from core.character_registry import get_registry  # type: ignore[import-not-found]
    except Exception as exc:
        logger.debug("CharacterRegistry unavailable in this process: %s", exc)
        return None
    try:
        return get_registry()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("CharacterRegistry get_instance failed: %s", exc)
        return None


class CharacterStateManager:
    """Resolve characters from an injectable registry into ``CharacterState``."""

    def __init__(self, registry: Optional[_RegistryLike] = None) -> None:
        self._registry = registry
        self._tried_default = False

    # -- Internal --------------------------------------------------------

    def _get_registry(self) -> Optional[_RegistryLike]:
        if self._registry is not None:
            return self._registry
        if not self._tried_default:
            self._tried_default = True
            self._registry = _default_registry()
        return self._registry

    # -- Public ----------------------------------------------------------

    @staticmethod
    def from_record(record: Any) -> CharacterState:
        """Build a :class:`CharacterState` from a registry record.

        ``record`` is duck-typed: any object with attributes
        ``key``, ``display_name``, ``series``, ``character_tag``,
        ``series_tag``, ``aliases`` (iterable of str), and an optional
        ``lora_hint`` (str | None) is accepted.
        """
        key = _safe_id(getattr(record, "key", "") or "")
        name = getattr(record, "display_name", "") or ""
        if not key or not name:
            raise ValueError(
                "CharacterStateManager.from_record: record missing key/display_name"
            )

        char_tag = (getattr(record, "character_tag", "") or "").strip()
        series_tag = (getattr(record, "series_tag", "") or "").strip()
        series = (getattr(record, "series", "") or "").strip()
        aliases = tuple(
            str(a).strip() for a in (getattr(record, "aliases", ()) or ()) if a
        )

        canonical: list[str] = []
        for token in (char_tag, series_tag, *aliases):
            t = token.strip()
            if t and t not in canonical:
                canonical.append(t)

        # Identity tokens that must never drift across the run.
        must_keep: list[str] = []
        for token in (name, char_tag):
            t = (token or "").strip()
            if t and t not in must_keep:
                must_keep.append(t)

        lora_hint = getattr(record, "lora_hint", None)
        lora_hints = (str(lora_hint),) if lora_hint else ()

        return CharacterState(
            character_key=key,
            character_name=name,
            appearance=CharacterAppearance(),
            source_series=series,
            canonical_tags=tuple(canonical),
            must_keep=tuple(must_keep),
            lora_hints=lora_hints,
            notes="registry resolved",
        )

    @staticmethod
    def from_hint(hint: Mapping[str, str]) -> Optional[tuple[str, CharacterState]]:
        """Placeholder fallback when no registry record is available.

        Mirrors the Cycle-1 behavior of ``prompt_parser._build_character_placeholder``.
        Returns ``None`` if the hint lacks a key or name.
        """
        key_raw = hint.get("character_key") or hint.get("key") or ""
        name_raw = hint.get("character_name") or hint.get("name") or ""
        if not key_raw or not name_raw:
            return None
        key = _safe_id(key_raw)
        state = CharacterState(
            character_key=key,
            character_name=name_raw,
            appearance=CharacterAppearance(),
            notes="parser placeholder",
        )
        return (key, state)

    def resolve(
        self,
        query: str | Mapping[str, str] | None,
    ) -> Optional[tuple[str, CharacterState]]:
        """Resolve a character to ``(key, CharacterState)`` or ``None``.

        Lookup order:
          1. If ``query`` is a Mapping with ``character_key`` and the
             registry has that key → registry record.
          2. If a Mapping with ``character_name`` → ``registry.resolve_query``.
          3. If a str → ``registry.get`` then ``registry.resolve_query``.
          4. If still nothing and ``query`` is a Mapping → fall back to
             :meth:`from_hint` (placeholder behavior).
        """
        if query is None:
            return None

        registry = self._get_registry()

        # Mapping path
        if isinstance(query, Mapping):
            key_raw = query.get("character_key") or query.get("key") or ""
            name_raw = query.get("character_name") or query.get("name") or ""
            if registry is not None:
                record = None
                if key_raw:
                    record = registry.get(_safe_id(key_raw))
                if record is None and name_raw:
                    record = registry.resolve_query(name_raw)
                if record is not None:
                    state = self.from_record(record)
                    return (state.character_key, state)
            return self.from_hint(query)

        # String path
        text = str(query).strip()
        if not text:
            return None
        if registry is not None:
            record = registry.get(_safe_id(text)) or registry.resolve_query(text)
            if record is not None:
                state = self.from_record(record)
                return (state.character_key, state)
        return None


__all__ = ["CharacterStateManager"]
