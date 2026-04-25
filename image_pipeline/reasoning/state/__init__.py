"""
image_pipeline.reasoning.state — Cycle 2 state managers.

Bridges raw user input + external registries → :mod:`schemas`
``CharacterState`` / ``PropState`` / ``SceneState``.

Public API
----------
* :class:`CharacterStateManager` — wraps a duck-typed character registry
  (the chatbot's :mod:`core.character_registry` is the canonical source,
  but any object exposing ``get(key)`` + ``resolve_query(q)`` works) and
  emits frozen ``CharacterState`` objects.
* :class:`PropStateManager` — session-scoped prop registry. Extracts props
  from free text, deduplicates by canonical key, and resolves bare names
  to previously seen entries.
* :func:`extract_scene` — pure-function scene extractor (location / time /
  mood) returning a frozen :class:`SceneState`.
* :class:`StateResolver` — bundle that ``prompt_parser.parse`` accepts via
  the optional ``state_resolver=`` kwarg.

Importing this module performs **no I/O** and triggers no env loading.
The character registry is fetched lazily and only when actually queried.
"""

from __future__ import annotations

from .character_state_manager import CharacterStateManager
from .prop_state_manager import PropStateManager
from .resolver import StateResolver, default_resolver
from .scene_state_manager import extract_scene

__all__ = [
    "CharacterStateManager",
    "PropStateManager",
    "StateResolver",
    "default_resolver",
    "extract_scene",
]
