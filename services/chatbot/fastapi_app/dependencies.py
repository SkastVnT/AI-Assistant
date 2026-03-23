"""
Shared dependencies for FastAPI routes — session helpers, chatbot cache, DB access
"""
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


# ── MongoDB helpers ────────────────────────────────────────────────────

def get_user_id(request: Request) -> str:
    """Derive a user id from the session (matches Flask logic)."""
    return request.session.get("user_id", get_session_id(request))


def require_mongodb():
    """Raise 503 if MongoDB is not available."""
    if not MONGODB_ENABLED:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="MongoDB not enabled")
