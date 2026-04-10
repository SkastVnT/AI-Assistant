"""
Shared dependencies for FastAPI routes — session helpers, chatbot cache, DB access
"""
import os
import uuid
from typing import Any

from fastapi import Request
from starlette.requests import Request as StarletteRequest

from core.extensions import MONGODB_ENABLED, ConversationDB, logger


# ── Session helpers ────────────────────────────────────────────────────

def get_session_id(request: Request) -> str:
    """Get or create session_id stored in the Starlette session."""
    sid = request.session.get("session_id")
    if not sid:
        sid = str(uuid.uuid4())
        request.session["session_id"] = sid
    return sid


def get_gallery_session_id(request: Request) -> str:
    """Gallery-scoped session id for image privacy."""
    gid = request.session.get("gallery_session_id")
    if not gid:
        gid = str(uuid.uuid4())
        request.session["gallery_session_id"] = gid
    return gid


# ── Chatbot instance cache ────────────────────────────────────────────
# We maintain our own cache instead of importing core.chatbot_v2.get_chatbot()
# because that function accesses Flask's session object directly.

_chatbot_cache: dict[str, Any] = {}


def get_chatbot_for_session(request: Request):
    """Return a ChatbotAgent instance tied to the current session."""
    session_id = get_session_id(request)

    if session_id not in _chatbot_cache:
        from core.chatbot_v2 import ChatbotAgent
        _chatbot_cache[session_id] = ChatbotAgent(conversation_id=None)

    return _chatbot_cache[session_id]


# ── Image Orchestrator cache ──────────────────────────────────────────

_orchestrator_cache: dict[str, Any] = {}


def get_image_orchestrator_for_session(request: Request):
    """
    Return a per-session ImageOrchestrator (holds image history / session).

    Returns None if the image orchestration module is unavailable
    so callers must guard: ``orch = get_image_orchestrator_for_session(req)``
    """
    try:
        from core.image_gen.orchestrator import ImageOrchestrator
        session_id = get_session_id(request)
        if session_id not in _orchestrator_cache:
            _orchestrator_cache[session_id] = ImageOrchestrator(session_id=session_id)
        return _orchestrator_cache[session_id]
    except Exception as exc:
        logger.warning(f"[Deps] ImageOrchestrator unavailable: {exc}")
        return None


# ── MongoDB helpers ────────────────────────────────────────────────────

def get_user_id(request: Request) -> str:
    """Derive a user id from the session (matches Flask logic)."""
    return request.session.get("user_id", get_session_id(request))


def require_mongodb():
    """Raise 503 if MongoDB is not available."""
    if not MONGODB_ENABLED:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="MongoDB not enabled")


# ── New app-layer Image Orchestration Service ──────────────────────────

# Feature flag: set USE_NEW_IMAGE_ORCHESTRATOR=1 to route through the new
# ScenePlanner → PromptBuilder → ProviderRouter pipeline (with automatic
# fallback to the legacy core.image_gen.orchestrator if it fails).

def use_new_image_orchestrator() -> bool:
    """Return True when the new image orchestration pipeline is enabled."""
    flag = os.getenv("USE_NEW_IMAGE_ORCHESTRATOR", "").lower()
    return flag in ("1", "true", "yes", "on")


_new_orch_service = None


def get_new_orchestration_service():
    """
    Return the shared ImageOrchestrationService (new pipeline).

    Returns None if the module is unavailable so callers must guard.
    """
    global _new_orch_service
    if _new_orch_service is not None:
        return _new_orch_service
    try:
        from app.services.image_orchestrator import ImageOrchestrationService
        _new_orch_service = ImageOrchestrationService()
        return _new_orch_service
    except Exception as exc:
        logger.warning(f"[Deps] New ImageOrchestrationService unavailable: {exc}")
        return None
