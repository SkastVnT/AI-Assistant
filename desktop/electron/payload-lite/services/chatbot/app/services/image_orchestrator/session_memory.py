"""
SessionMemory
=============
In-memory per-session state for the image orchestrator layer.

Stores:
    session_id          : str   — unique conversation key
    last_prompt         : str   — final enhanced prompt used in the last turn
    last_scene_spec     : SceneSpec | None — structured scene from last turn
    last_provider       : str   — provider name reported by the last result
    last_image_reference: str   — short reference to the last image:
                                    • URL if available ("https://...")
                                    • "b64:<first 32 chars>" otherwise
    last_seed           : int | None — seed used (if reported by provider)
    updated_at          : float — unix timestamp of last update

Pattern mirrors core/image_gen/session.py SessionManager — a plain dict with
dataclass values; no persistence; keys expire automatically via max-size LRU.
"""

from __future__ import annotations

import time
import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .schemas import SceneSpec

logger = logging.getLogger(__name__)

# Max number of sessions held in memory (oldest are evicted when exceeded)
_MAX_SESSIONS = 512


# ─────────────────────────────────────────────────────────────────────
# Data carrier
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ImageSessionMemory:
    """State snapshot for one user session."""

    session_id:             str
    last_prompt:            str            = ""
    last_scene_spec:        Optional["SceneSpec"] = None
    last_provider:          str            = ""
    last_image_reference:   str            = ""
    last_seed:              Optional[int]  = None
    edit_lineage_count:     int            = 0
    updated_at:             float          = field(default_factory=time.time)

    @property
    def has_previous_image(self) -> bool:
        """True when a previous image URL or b64 snippet is available."""
        return bool(self.last_image_reference)

    @property
    def has_previous_scene(self) -> bool:
        return self.last_scene_spec is not None


# ─────────────────────────────────────────────────────────────────────
# Store
# ─────────────────────────────────────────────────────────────────────

class SessionMemoryStore:
    """
    Thread-unsafe in-memory store with LRU eviction.

    This is intentionally simple — the chatbot runs single-process and
    the existing core/image_gen/session.py follows the same pattern.
    """

    def __init__(self, max_sessions: int = _MAX_SESSIONS):
        self._max = max_sessions
        self._store: OrderedDict[str, ImageSessionMemory] = OrderedDict()

    # ── Read ─────────────────────────────────────────────────────────

    def get(self, session_id: str) -> Optional[ImageSessionMemory]:
        """Return the memory for session_id, or None if not found."""
        mem = self._store.get(session_id)
        if mem:
            self._store.move_to_end(session_id)   # mark recently-used
        return mem

    def get_or_create(self, session_id: str) -> ImageSessionMemory:
        """Return existing memory or create a blank one."""
        mem = self.get(session_id)
        if mem is None:
            mem = ImageSessionMemory(session_id=session_id)
            self._set(session_id, mem)
        return mem

    def has_previous_image(self, session_id: str) -> bool:
        mem = self._store.get(session_id)
        return mem.has_previous_image if mem else False

    def last_scene(self, session_id: str) -> Optional["SceneSpec"]:
        mem = self._store.get(session_id)
        return mem.last_scene_spec if mem else None

    # ── Write ────────────────────────────────────────────────────────

    def update(
        self,
        session_id:  str,
        prompt:      str,
        scene:       Optional["SceneSpec"],
        result,                              # core.image_gen.providers.base.ImageResult
        *,
        is_edit:     bool = False,
    ) -> None:
        """
        Persist the outcome of one image generation turn.

        Accepts an ImageResult object from the provider layer.
        When *is_edit* is True the lineage counter increments;
        otherwise it resets to 0 (fresh generation).
        """
        mem = self.get_or_create(session_id)
        mem.last_prompt      = prompt
        mem.last_scene_spec  = scene
        mem.last_provider    = getattr(result, "provider", "") or ""
        mem.last_seed        = getattr(result, "metadata", {}).get("seed") if \
                               hasattr(result, "metadata") else None
        mem.edit_lineage_count = (mem.edit_lineage_count + 1) if is_edit else 0
        mem.updated_at       = time.time()

        # Build a compact image reference
        images_url = getattr(result, "images_url", []) or []
        images_b64 = getattr(result, "images_b64", []) or []
        if images_url:
            mem.last_image_reference = images_url[0]
        elif images_b64:
            snippet = images_b64[0][:32] if images_b64[0] else ""
            mem.last_image_reference = f"b64:{snippet}"
        else:
            mem.last_image_reference = ""

        self._set(session_id, mem)
        logger.debug(
            f"[SessionMemory] {session_id}: "
            f"provider={mem.last_provider}, ref={mem.last_image_reference[:60]}"
        )

    def clear(self, session_id: str) -> None:
        """Remove session state entirely."""
        self._store.pop(session_id, None)

    # ── Internal LRU helper ──────────────────────────────────────────

    def _set(self, session_id: str, mem: ImageSessionMemory) -> None:
        self._store[session_id] = mem
        self._store.move_to_end(session_id)
        if len(self._store) > self._max:
            evicted_id, _ = self._store.popitem(last=False)
            logger.debug(f"[SessionMemory] Evicted session {evicted_id}")


# ─────────────────────────────────────────────────────────────────────
# Module-level singleton (same access pattern as core/image_gen/session.py)
# ─────────────────────────────────────────────────────────────────────

_store: Optional[SessionMemoryStore] = None


def get_session_memory_store() -> SessionMemoryStore:
    """Return the shared SessionMemoryStore, creating it on first call."""
    global _store
    if _store is None:
        _store = SessionMemoryStore()
    return _store
