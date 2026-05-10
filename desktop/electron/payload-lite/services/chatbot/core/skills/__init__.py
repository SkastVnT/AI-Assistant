"""
Runtime Skill System — behavior bundles for the chatbot.

A skill encapsulates: prompt fragments, tool preferences, default model,
default thinking mode, and context override.  Skills are loaded from YAML
definitions and activated per-request or per-session via explicit selection
or auto-routing.
"""
from core.skills.registry import SkillDefinition, SkillRegistry, get_skill_registry
from core.skills.router import SkillRouter, RouteMatch, get_skill_router
from core.skills.resolver import (
    resolve_skill,
    SkillOverrides,
    SOURCE_EXPLICIT,
    SOURCE_SESSION,
    SOURCE_AUTO,
)
from core.skills.applicator import AppliedSkill, apply_skill_overrides
from core.skills.session import (
    get_session_skill,
    set_session_skill,
    clear_session_skill,
    SkillSessionStore,
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
