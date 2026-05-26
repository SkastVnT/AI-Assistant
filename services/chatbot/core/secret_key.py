"""Flask secret-key policy shared by chatbot entry points."""

from __future__ import annotations

import logging
import os
import secrets

_TEST_SECRET_KEY = "test-only-flask-secret-key"
_DEV_ENV_NAMES = {"", "dev", "development", "local"}
_TEST_TRUE_VALUES = {"1", "true", "yes", "on"}


def _is_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in _TEST_TRUE_VALUES


def resolve_flask_secret_key(*, logger: logging.Logger | None = None) -> str:
    """Return the Flask secret key according to the repo trust boundary.

    Order:
    1. ``FLASK_SECRET_KEY`` from env.
    2. Stable test-only value when ``TESTING=true``.
    3. Ephemeral dev-only value when ``env``/``FLASK_ENV`` are dev-like.
    4. Runtime error for non-dev without an explicit secret.
    """

    configured = os.getenv("FLASK_SECRET_KEY")
    if configured:
        return configured

    if _is_enabled(os.getenv("TESTING")):
        return _TEST_SECRET_KEY

    env_name = (os.getenv("env", "dev") or "dev").strip().lower()
    flask_env = (os.getenv("FLASK_ENV", "") or "").strip().lower()
    if env_name in _DEV_ENV_NAMES and flask_env in _DEV_ENV_NAMES:
        key = secrets.token_urlsafe(32)
        (logger or logging.getLogger(__name__)).warning(
            "[Config] FLASK_SECRET_KEY not set; using an ephemeral dev-only secret"
        )
        return key

    raise RuntimeError("FLASK_SECRET_KEY must be set outside dev/test environments")
