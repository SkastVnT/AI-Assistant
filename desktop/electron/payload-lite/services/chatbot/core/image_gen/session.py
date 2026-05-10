"""
ImageSession â€” per-conversation image state management.
Tracks generated images, enables conversational editing ("add a rainbow"),
and maintains style/character consistency across a conversation.

This is what makes it feel like ChatGPT/Gemini â€” you can iteratively
refine images by chatting naturally.
"""

from __future__ import annotations

import time
import base64
import logging
from dataclasses import dataclass, field
from typing import Optional
from collections import deque

from .providers.base import ImageResult, ImageMode
from .enhancer import PromptEnhancer

logger = logging.getLogger(__name__)


@dataclass
class ImageHistoryEntry:
    """Single image generation record within a conversation."""
    timestamp: float
    prompt: str               # user's original prompt
    enhanced_prompt: str      # what was sent to the model
    result: ImageResult
    is_edit: bool = False     # was this an edit of a previous image?
    parent_index: Optional[int] = None  # index of image this was edited from


class ImageSession:
    """
    Per-conversation image session.
    
    Maintains:
    - History of all generated images
    - Last generated image (for iterative editing)
    - Style consistency hints
    - Token-efficient context for the LLM
    """

    MAX_HISTORY = 50

    def __init__(self, conversation_id: str = ""):
        self.conversation_id = conversation_id
        self.history: list[ImageHistoryEntry] = []
        self.active_style: Optional[str] = None
        self._created_at = time.time()

    @property
    def last_image(self) -> Optional[ImageHistoryEntry]:
        """Most recently generated image."""
        return self.history[-1] if self.history else None

    @property
    def last_image_b64(self) -> Optional[str]:
        """Base64 of last generated image (for img2img editing)."""
        if not self.history:
            return None
        last = self.history[-1].result
        if last.images_b64:
            return last.images_b64[0]
        return None

    @property
    def last_image_url(self) -> Optional[str]:
        """URL of last generated image."""
        if not self.history:
            return None
        last = self.history[-1].result
        if last.images_url:
            return last.images_url[0]
        return None

    def add_generation(
        self,
        user_prompt: str,
        enhanced_prompt: str,
        result: ImageResult,
        is_edit: bool = False,
    ):
        """Record a new generation in session history."""
        parent = len(self.history) - 1 if is_edit and self.history else None
        entry = ImageHistoryEntry(
            timestamp=time.time(),
            prompt=user_prompt,
            enhanced_prompt=enhanced_prompt,
            result=result,
            is_edit=is_edit,
            parent_index=parent,
        )
        self.history.append(entry)

        # Trim old entries
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY:]

    def get_context_for_enhancement(self) -> str:
        """
        Build context string from recent images for the prompt enhancer.
        This helps maintain consistency across edits.
        """
        if not self.history:
            return ""

        recent = self.history[-3:]  # last 3 images
        parts = ["Previous images in this conversation:"]
        for i, entry in enumerate(recent):
            parts.append(f"- Image {i+1}: \"{entry.prompt}\" â†’ {entry.result.model}")

        if self.active_style:
            parts.append(f"Active style: {self.active_style}")

        return "\n".join(parts)

    def get_edit_chain(self, index: int = -1) -> list[ImageHistoryEntry]:
        """
        Get the full edit chain for an image (original â†’ edit1 â†’ edit2 â†’ ...).
        Useful for showing the user the evolution of an image.
        """
        if not self.history:
            return []

        if index < 0:
            index = len(self.history) + index

        # Walk back to find the original
        chain = [self.history[index]]
        current = self.history[index]
        while current.parent_index is not None and current.parent_index >= 0:
            current = self.history[current.parent_index]
            chain.insert(0, current)

        # Walk forward to find subsequent edits
        idx = index + 1
        while idx < len(self.history):
            if self.history[idx].parent_index == index:
                chain.append(self.history[idx])
                index = idx
            idx += 1

        return chain

    def to_dict(self) -> dict:
        """Serialize session for storage."""
        return {
            "conversation_id": self.conversation_id,
            "created_at": self._created_at,
            "active_style": self.active_style,
            "history": [
                {
                    "timestamp": e.timestamp,
                    "prompt": e.prompt,
                    "enhanced_prompt": e.enhanced_prompt,
                    "is_edit": e.is_edit,
                    "parent_index": e.parent_index,
                    "provider": e.result.provider,
                    "model": e.result.model,
                    "images_url": e.result.images_url,
                    "cost_usd": e.result.cost_usd,
                    "latency_ms": e.result.latency_ms,
                }
                for e in self.history
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImageSession":
        """Deserialize session from storage."""
        session = cls(conversation_id=data.get("conversation_id", ""))
        session._created_at = data.get("created_at", time.time())
        session.active_style = data.get("active_style")
        for h in data.get("history", []):
            entry = ImageHistoryEntry(
                timestamp=h["timestamp"],
                prompt=h["prompt"],
                enhanced_prompt=h["enhanced_prompt"],
                result=ImageResult(
                    success=True,
                    images_url=h.get("images_url", []),
                    provider=h.get("provider", ""),
                    model=h.get("model", ""),
                    cost_usd=h.get("cost_usd", 0),
                    latency_ms=h.get("latency_ms", 0),
                ),
                is_edit=h.get("is_edit", False),
                parent_index=h.get("parent_index"),
            )
            session.history.append(entry)
        return session


class SessionManager:
    """Manage image sessions across conversations (in-memory with optional DB backing)."""

    def __init__(self):
        self._sessions: dict[str, ImageSession] = {}

    def get_or_create(self, conversation_id: str) -> ImageSession:
        if conversation_id not in self._sessions:
            self._sessions[conversation_id] = ImageSession(conversation_id)
        return self._sessions[conversation_id]

    def get(self, conversation_id: str) -> Optional[ImageSession]:
        return self._sessions.get(conversation_id)

    def delete(self, conversation_id: str):
        self._sessions.pop(conversation_id, None)

    def cleanup_old(self, max_age_hours: float = 24.0):
        """Remove sessions older than max_age_hours."""
        cutoff = time.time() - (max_age_hours * 3600)
        expired = [
            cid for cid, sess in self._sessions.items()
            if sess._created_at < cutoff
        ]
        for cid in expired:
            del self._sessions[cid]
        if expired:
            logger.info(f"[SessionManager] Cleaned up {len(expired)} expired sessions")
