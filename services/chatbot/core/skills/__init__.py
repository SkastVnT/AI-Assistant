"""
Runtime Skill System — behavior bundles for the chatbot.

A skill encapsulates: prompt fragments, tool preferences, default model,
default thinking mode, and context override.  Skills are loaded from YAML
definitions and activated per-request or per-session via explicit selection
or auto-routing.
"""

from core.skills.applicator import AppliedSkill, apply_skill_overrides
from core.skills.registry import SkillDefinition, SkillRegistry, get_skill_registry
from core.skills.resolver import (
    SOURCE_AUTO,
    SOURCE_EXPLICIT,
    SOURCE_SESSION,
    SkillOverrides,
    resolve_skill,
)
from core.skills.router import RouteMatch, SkillRouter, get_skill_router
from core.skills.session import (
    SkillSessionStore,
    clear_session_skill,
    get_session_skill,
    set_session_skill,
)

__all__ = [
    "SkillDefinition",
    "SkillRegistry",
    "get_skill_registry",
    "SkillRouter",
    "RouteMatch",
    "get_skill_router",
    "resolve_skill",
    "SkillOverrides",
    "SOURCE_EXPLICIT",
    "SOURCE_SESSION",
    "SOURCE_AUTO",
    "AppliedSkill",
    "apply_skill_overrides",
    "get_session_skill",
    "set_session_skill",
    "clear_session_skill",
    "SkillSessionStore",
]
