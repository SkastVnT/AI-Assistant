"""
app_factory.py — Canonical Flask application factory for the chatbot service.

Usage:
    from app_factory import create_app
    app = create_app()

The monolith (chatbot_main.py) owns the Flask `app` object and all route
registrations. This module is a thin, stable import boundary so that tests,
CLI tooling, and future refactors always go through one well-known entry point
instead of importing `chatbot_main` directly.

Why a separate file instead of app/__init__.py?
- `app/__init__.py` is a legacy compatibility shim that must stay for old
  imports (`from app import app`).  app_factory.py is the NEW canonical
  location.
- Tools like pytest-flask's `--app` CLI flag, Flask's `flask --app` option,
  and programmatic test setup all look for a `create_app` callable at a
  well-known path.
"""

from __future__ import annotations

import os
from typing import Any


def create_app(config: dict[str, Any] | None = None) -> Flask:  # noqa: F821
    """Return the canonical Flask monolith app.

    Parameters
    ----------
    config:
        Optional dict of Flask config overrides applied **before** the app is
        imported and **after** it is created.  Pass
        ``{"TESTING": True, "MONGODB_ENABLED": False}`` to initialize the app
        in test mode.  Values are set unconditionally via ``os.environ[k]``
        so they override any pre-existing shell/CI environment variables.

    Returns
    -------
    flask.Flask
        The fully-wired monolith app with all blueprints registered.
    """
    # TESTING / MONGODB_ENABLED must be set before chatbot_main is imported
    # because it reads them at module scope.  Use direct assignment so that
    # the caller's values override any pre-existing env vars (e.g. from CI or
    # shell), not os.environ.setdefault which silently ignores existing values.
    if config:
        for k, v in config.items():
            os.environ[k] = str(v)

    from chatbot_main import app as _app  # type: ignore[import]

    if config:
        _app.config.update(config)

    return _app
