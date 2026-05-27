"""
Authentication Middleware

Handles session, login, admin, and API key authentication.
"""

import os
from functools import wraps

from flask import jsonify, request, session


def require_session(f):
    """Decorator to require a valid session"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            # Create anonymous session
            import uuid

            session["user_id"] = f"anonymous_{str(uuid.uuid4())[:8]}"
        return f(*args, **kwargs)

    return decorated_function


def require_login(f):
    """No-op pass-through (auth UI removed in desktop-only build).

    Kept as a decorator for backward compatibility with existing route handlers.
    The chatbot is now packaged as a single-user Electron desktop app, so
    login enforcement is no longer required.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)

    return decorated_function


def require_admin(f):
    """No-op pass-through (auth UI removed in desktop-only build)."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)

    return decorated_function


def require_api_key(f):
    """Decorator to require a valid API key"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return (
                jsonify({"error": "Unauthorized", "message": "API key required"}),
                401,
            )

        # Validate API key (simple validation for now)
        valid_key = os.getenv("API_KEY")

        if valid_key and api_key != valid_key:
            return jsonify({"error": "Unauthorized", "message": "Invalid API key"}), 401

        return f(*args, **kwargs)

    return decorated_function
