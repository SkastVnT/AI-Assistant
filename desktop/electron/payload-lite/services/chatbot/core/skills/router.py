"""
Skill router — auto-detect the best skill from user intent.

Matches the incoming message against trigger_keywords defined on each skill.
Falls back to None (no skill) when nothing matches.

Conservative by design:
- Requires a minimum score threshold before auto-routing.
- Short messages (≤3 words) are not auto-routed to avoid false positives.
- Returns match metadata (score, matched keywords) for logging/UI.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from core.skills.registry import SkillDefinition, SkillRegistry, get_skill_registry

logger = logging.getLogger(__name__)

# Minimum score required for auto-routing.  A single keyword hit on a
# low-priority skill (score ~1.0) will NOT pass the threshold.
MIN_AUTO_ROUTE_SCORE = 1.05

# Messages with this many words or fewer are skipped (too ambiguous).
MIN_MESSAGE_WORDS = 3


@dataclass
class RouteMatch:
    """Result of auto-routing: the matched skill plus debugging metadata."""

    skill: SkillDefinition
    score: float
    matched_keywords: List[str] = field(default_factory=list)


class SkillRouter:
    """Scores skills against an incoming message and picks the best match."""

    def __init__(self, registry: Optional[SkillRegistry] = None):
        self.registry = registry or get_skill_registry()

    def match(self, message: str) -> Optional[SkillDefinition]:
        """Return the best-matching skill, or None.

        Wrapper for ``match_detailed`` that returns only the skill.
        """
        result = self.match_detailed(message)
        return result.skill if result else None

    def match_detailed(self, message: str) -> Optional[RouteMatch]:
        """Return the best match with metadata, or None.

        Scoring:
        - Each trigger keyword that appears in the message contributes +1.
        - Final score is (hit_count + skill.priority / 100).
        - Highest score wins; ties broken by priority.
        - Score must meet ``MIN_AUTO_ROUTE_SCORE`` to be accepted.
        - Messages with ≤ ``MIN_MESSAGE_WORDS`` words are skipped.
        """
        if not message:
            return None

        # Skip very short messages to avoid false positives
        word_count = len(message.split())
        if word_count <= MIN_MESSAGE_WORDS:
            return None

        msg_lower = message.lower()
        best: Optional[RouteMatch] = None
        best_score: float = 0.0

        for skill in self.registry.list_all():
            if not skill.trigger_keywords or not skill.enabled:
                continue

            matched = [kw for kw in skill.trigger_keywords if kw.lower() in msg_lower]
            hits = len(matched)
            if hits == 0:
                continue

            score = hits + skill.priority / 100
            if score > best_score:
                best_score = score
                best = RouteMatch(
                    skill=skill,
                    score=score,
                    matched_keywords=matched,
                )

        # Apply minimum threshold
        if best and best.score < MIN_AUTO_ROUTE_SCORE:
            logger.debug(
                f"[SkillRouter] Score {best.score:.2f} below threshold "
                f"{MIN_AUTO_ROUTE_SCORE} for skill '{best.skill.id}', skipping"
            )
            return None

        if best:
            logger.info(
                f"[SkillRouter] Auto-matched skill '{best.skill.id}' "
                f"(score={best.score:.2f}, keywords={best.matched_keywords}) "
                f"for message: {message[:60]}"
            )
        return best


# ── Singleton ────────────────────────────────────────────────────────────

_router: Optional[SkillRouter] = None


def get_skill_router() -> SkillRouter:
    global _router
    if _router is None:
        _router = SkillRouter()
    return _router
