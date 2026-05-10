"""
Skill resolver — the single integration point for the chat pipeline.

Call ``resolve_skill()`` early in the request handler.  It returns a
``SkillOverrides`` dataclass whose fields are either concrete overrides
(from the resolved skill) or None (keep the caller's current value).

Resolution priority:
1. ``explicit_skill_id`` (from the request body ``skill`` field).
2. Session-level skill (via ``session_id`` + SkillSessionStore).
3. Auto-routing via ``SkillRouter.match()`` (if enabled).
4. No skill — return empty ``SkillOverrides`` (all ``None``).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.skills.registry import SkillDefinition, get_skill_registry
from core.skills.router import get_skill_router
from core.skills.session import get_session_skill

logger = logging.getLogger(__name__)


# ── Skill resolution sources ─────────────────────────────────────────────
SOURCE_EXPLICIT = "explicit"
SOURCE_SESSION = "session"
SOURCE_AUTO = "auto"


@dataclass
class SkillOverrides:
    """Values resolved from a skill that the chat pipeline should apply.

    ``None`` in any field means "keep the request's original value".
    """

    skill_id: Optional[str] = None
    skill_name: Optional[str] = None

    # How the skill was resolved: "explicit", "session", "auto", or None
    source: Optional[str] = None

    # Auto-route metadata (populated when source == "auto")
    auto_route_score: Optional[float] = None
    auto_route_keywords: List[str] = field(default_factory=list)

    # Extra text appended to the system prompt
    prompt_injection: Optional[str] = None

    # Tool gating
    preferred_tools: List[str] = field(default_factory=list)
    blocked_tools: List[str] = field(default_factory=list)

    # Model / thinking overrides
    model: Optional[str] = None
    thinking_mode: Optional[str] = None
    context: Optional[str] = None

    @property
    def active(self) -> bool:
        """True when a skill was actually resolved."""
        return self.skill_id is not None


def resolve_skill(
    *,
    message: str,
    explicit_skill_id: Optional[str] = None,
    session_id: Optional[str] = None,
    auto_route: bool = True,
) -> SkillOverrides:
    """Resolve a skill from an explicit ID, session state, or auto-routing.

    Priority order:
    1. ``explicit_skill_id`` — when the user or frontend picks a skill.
    2. Session skill — sticky skill activated for the current session.
    3. Auto-routing via ``SkillRouter.match()`` if *auto_route* is True.
    4. No skill — return empty ``SkillOverrides`` (all ``None``).

    Disabled skills (``enabled=False``) are skipped at every stage.
    """
    registry = get_skill_registry()

    skill: Optional[SkillDefinition] = None
    source: Optional[str] = None
    auto_score: Optional[float] = None
    auto_keywords: List[str] = []

    # 1. Explicit selection (by id or name)
    if explicit_skill_id:
        skill = registry.get(explicit_skill_id)
        if skill is None:
            skill = registry.get_by_name(explicit_skill_id)
        if skill is None:
            logger.warning(f"[SkillResolve] Requested skill '{explicit_skill_id}' not found")
        elif not skill.enabled:
            logger.info(f"[SkillResolve] Skill '{skill.id}' is disabled, skipping")
            skill = None
        else:
            source = SOURCE_EXPLICIT

    # 2. Session-level skill
    if skill is None and session_id:
        session_skill_id = get_session_skill(session_id)
        if session_skill_id:
            candidate = registry.get(session_skill_id)
            if candidate and candidate.enabled:
                skill = candidate
                source = SOURCE_SESSION
            else:
                logger.info(f"[SkillResolve] Session skill '{session_skill_id}' not found or disabled")

    # 3. Auto-routing
    if skill is None and auto_route:
        from core.skills.router import RouteMatch
        route_match = get_skill_router().match_detailed(message)
        if route_match is not None:
            skill = route_match.skill
            source = SOURCE_AUTO
            auto_score = route_match.score
            auto_keywords = route_match.matched_keywords

    # 4. No skill
    if skill is None:
        return SkillOverrides()

    logger.info(
        f"[SkillResolve] Resolved skill '{skill.id}' via {source}"
        + (f" (score={auto_score:.2f}, kw={auto_keywords})" if source == SOURCE_AUTO else "")
    )

    # Build the prompt injection string
    prompt_injection = None
    if skill.prompt_fragments:
        prompt_injection = "\n\n".join(skill.prompt_fragments)

    return SkillOverrides(
        skill_id=skill.id,
        skill_name=skill.name,
        source=source,
        auto_route_score=auto_score,
        auto_route_keywords=auto_keywords,
        prompt_injection=prompt_injection,
        preferred_tools=list(skill.preferred_tools),
        blocked_tools=list(skill.blocked_tools),
        model=skill.default_model,
        thinking_mode=skill.default_thinking_mode,
        context=skill.default_context,
    )
