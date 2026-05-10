"""
Session-level skill activation.

Tracks which skill is active for a given session (or request).
The session store is in-memory by default — state is lost on restart,
which is acceptable because the frontend re-sends ``skill`` on every
request and Flask sessions carry their own session_id.

Usage in the chat pipeline::

    from core.skills.session import get_session_skill, set_session_skill, clear_session_skill

    # Activate a skill for a session
    set_session_skill(session_id, "coding-assistant")

    # Retrieve
    skill_id = get_session_skill(session_id)   # "coding-assistant" | None

    # Deactivate
    clear_session_skill(session_id)
"""
from __future__ import annotations

import logging
import threading
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SkillSessionStore:
    """Thread-safe in-memory map of session_id → active skill_id."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: Dict[str, str] = {}

    def get(self, session_id: str) -> Optional[str]:
        """Return the active skill id for *session_id*, or ``None``."""
        with self._lock:
            return self._active.get(session_id)

    def set(self, session_id: str, skill_id: str) -> None:
        """Bind *skill_id* as the active skill for *session_id*."""
        with self._lock:
            self._active[session_id] = skill_id
        logger.debug(f"[SkillSession] session={session_id} → skill={skill_id}")

    def clear(self, session_id: str) -> bool:
        """Remove the active skill for *session_id*.  Returns True if one was removed."""
        with self._lock:
            return self._active.pop(session_id, None) is not None

    def list_active(self) -> Dict[str, str]:
        """Snapshot of all active session→skill bindings."""
        with self._lock:
            return dict(self._active)

    def clear_all(self) -> int:
        """Clear all session skill bindings.  Returns the count removed."""
        with self._lock:
            n = len(self._active)
            self._active.clear()
            logger.info("[SkillSession] Cleared all session bindings (%d sessions)", n)
            return n


# ── Singleton accessor ───────────────────────────────────────────────────

_store: Optional[SkillSessionStore] = None


def _get_store() -> SkillSessionStore:
    global _store
    if _store is None:
        _store = SkillSessionStore()
    return _store


def get_session_skill(session_id: str) -> Optional[str]:
    """Return the active skill id for the session, or None."""
    return _get_store().get(session_id)


def set_session_skill(session_id: str, skill_id: str) -> None:
    """Activate a skill for the session."""
    _get_store().set(session_id, skill_id)


def clear_session_skill(session_id: str) -> bool:
    """Deactivate the session skill.  Returns True if one was active."""
    return _get_store().clear(session_id)
