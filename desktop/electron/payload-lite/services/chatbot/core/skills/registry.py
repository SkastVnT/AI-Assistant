"""
Skill registry — loads, stores, and queries skill definitions.

Skills are defined as YAML files under core/skills/builtins/ or loaded from
the database at runtime.  Each skill carries metadata that the chat pipeline
uses to customise prompts, tools, and model selection.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_BUILTINS_DIR = Path(__file__).parent / "builtins"


# ── Skill dataclass ──────────────────────────────────────────────────────

@dataclass
class SkillDefinition:
    """A single runtime skill — a behaviour bundle for the chatbot."""

    # Identity
    id: str
    name: str
    description: str = ""

    # Prompt injection — appended to the system prompt when the skill is active
    # ``system_prompt_append`` is the canonical alias used by YAML definitions.
    prompt_fragments: List[str] = field(default_factory=list)

    # Tool gating
    preferred_tools: List[str] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)

    # Model / thinking defaults (None = don't override)
    default_model: Optional[str] = None
    default_thinking_mode: Optional[str] = None
    default_context: Optional[str] = None

    # Auto-routing — keyword / regex patterns that trigger this skill
    trigger_keywords: List[str] = field(default_factory=list)

    # Priority for auto-routing ties (higher wins)
    priority: int = 0

    # Whether this skill is user-selectable from the UI
    ui_visible: bool = True

    # Built-in skills are immutable at runtime
    builtin: bool = False

    # Discovery tags (e.g. ["search", "realtime", "web"])
    tags: List[str] = field(default_factory=list)

    # Disabled skills are invisible to the router and resolver
    enabled: bool = True

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize to a plain dict (JSON-safe)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prompt_fragments": self.prompt_fragments,
            "preferred_tools": self.preferred_tools,
            "blocked_tools": self.blocked_tools,
            "default_model": self.default_model,
            "default_thinking_mode": self.default_thinking_mode,
            "default_context": self.default_context,
            "trigger_keywords": self.trigger_keywords,
            "priority": self.priority,
            "ui_visible": self.ui_visible,
            "builtin": self.builtin,
            "tags": self.tags,
            "enabled": self.enabled,
        }


# ── Registry ─────────────────────────────────────────────────────────────

class SkillRegistry:
    """Central store for all loaded skills."""

    def __init__(self):
        self._skills: Dict[str, SkillDefinition] = {}

    # ── Queries ──

    def get(self, skill_id: str) -> Optional[SkillDefinition]:
        return self._skills.get(skill_id)

    def get_by_name(self, name: str) -> Optional[SkillDefinition]:
        """Lookup a skill by its display name (case-insensitive)."""
        name_lower = name.lower()
        for skill in self._skills.values():
            if skill.name.lower() == name_lower:
                return skill
        return None

    def list_all(self) -> List[SkillDefinition]:
        return list(self._skills.values())

    def list_enabled(self) -> List[SkillDefinition]:
        """Return only skills whose ``enabled`` flag is True."""
        return [s for s in self._skills.values() if s.enabled]

    def list_ids(self) -> List[str]:
        return list(self._skills.keys())

    def list_ui_visible(self) -> List[SkillDefinition]:
        return [s for s in self._skills.values() if s.ui_visible and s.enabled]

    # ── Mutations ──

    def register(self, skill: SkillDefinition) -> None:
        if skill.id in self._skills:
            logger.debug(f"[Skills] Overwriting skill '{skill.id}'")
        self._skills[skill.id] = skill

    def unregister(self, skill_id: str) -> bool:
        removed = self._skills.pop(skill_id, None) is not None
        if removed:
            logger.info(f"[Skills] Unregistered skill '{skill_id}'")
        return removed

    # ── Loaders ──

    def load_builtins(self) -> int:
        """Load YAML skill definitions from the builtins directory.

        Returns the number of skills loaded.
        """
        import yaml  # local import — yaml is in profile_core_services

        loaded = 0
        if not _BUILTINS_DIR.is_dir():
            logger.warning(f"[Skills] Builtins directory not found: {_BUILTINS_DIR}")
            return loaded

        for path in sorted(_BUILTINS_DIR.glob("*.yaml")):
            try:
                with open(path, encoding="utf-8") as fh:
                    raw = yaml.safe_load(fh)
                if not raw or not isinstance(raw, dict):
                    continue
                skill = _parse_yaml(raw, builtin=True)
                self.register(skill)
                loaded += 1
            except Exception as exc:
                logger.error(f"[Skills] Failed to load {path.name}: {exc}")

        logger.info(f"[Skills] Loaded {loaded} built-in skill(s)")
        return loaded


# ── YAML parser ──────────────────────────────────────────────────────────

def _parse_yaml(raw: dict, builtin: bool = False) -> SkillDefinition:
    """Parse a raw dict (from YAML) into a SkillDefinition.

    Accepts both ``prompt_fragments`` and the ``system_prompt_append`` alias.
    """
    # Accept system_prompt_append as an alias for prompt_fragments
    fragments = raw.get("prompt_fragments") or raw.get("system_prompt_append")
    return SkillDefinition(
        id=raw["id"],
        name=raw.get("name", raw["id"]),
        description=raw.get("description", ""),
        prompt_fragments=_as_list(fragments),
        preferred_tools=_as_list(raw.get("preferred_tools")),
        blocked_tools=_as_list(raw.get("blocked_tools")),
        default_model=raw.get("default_model"),
        default_thinking_mode=raw.get("default_thinking_mode"),
        default_context=raw.get("default_context"),
        trigger_keywords=_as_list(raw.get("trigger_keywords")),
        priority=int(raw.get("priority", 0)),
        ui_visible=bool(raw.get("ui_visible", True)),
        builtin=builtin,
        tags=_as_list(raw.get("tags")),
        enabled=bool(raw.get("enabled", True)),
    )


def _as_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return val
    return [val]


# ── Singleton accessor ───────────────────────────────────────────────────

_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Return the global SkillRegistry (lazy-init, loads builtins once)."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
        try:
            _registry.load_builtins()
        except Exception as exc:
            logger.error(f"[Skills] Error loading builtins: {exc}")
    return _registry
