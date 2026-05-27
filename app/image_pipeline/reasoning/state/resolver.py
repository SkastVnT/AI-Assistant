"""
image_pipeline.reasoning.state.resolver
=======================================

Aggregate the three Cycle-2 state managers into one object that
:func:`prompt_parser.parse` accepts via the ``state_resolver=`` kwarg.

A resolver is a pure dependency-injection container: no module-level state,
no I/O on construction. Use :func:`default_resolver` for the standard
chatbot wiring (registry-backed character manager + fresh prop manager +
scene function).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional

from image_pipeline.reasoning.schemas import CharacterState, PropState, SceneState

from .character_state_manager import CharacterStateManager
from .prop_state_manager import PropStateManager
from .scene_state_manager import extract_scene


@dataclass
class StateResolver:
    """Bundle of state managers used by the prompt parser.

    ``character`` and ``prop`` are stateful; ``extract_scene`` is a
    pure function. Using a dataclass (not frozen) so callers can swap
    implementations in tests.
    """

    character: CharacterStateManager = field(default_factory=CharacterStateManager)
    prop: PropStateManager = field(default_factory=PropStateManager)

    # ---- Forwarding helpers (parser uses these) ------------------------

    def resolve_character(
        self, query: str | Mapping[str, str] | None
    ) -> Optional[tuple[str, CharacterState]]:
        return self.character.resolve(query)

    def extract_props(self, text: str) -> tuple[tuple[str, PropState], ...]:
        return self.prop.extract_props_from_text(text)

    def extract_scene(self, text: str) -> SceneState:
        return extract_scene(text)


def default_resolver() -> StateResolver:
    """Return a resolver wired with the chatbot CharacterRegistry singleton.

    Safe to call when the chatbot package is not importable (the character
    manager will simply have no registry and behave like the placeholder).
    """
    return StateResolver(
        character=CharacterStateManager(),
        prop=PropStateManager(),
    )


__all__ = ["StateResolver", "default_resolver"]
