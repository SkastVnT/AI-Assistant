"""
AI-Assistant Chatbot Application Package

This package contains legacy modular helpers. The active runtime is the
Flask monolith in `chatbot_main.py`.
"""

import os

from flask import Flask

from core.config import SYSTEM_PROMPTS


def create_app(config_name: str = "default") -> Flask:
    """Return the canonical Flask monolith app.

    Delegates to ``app_factory.create_app`` which is the canonical entry point.
    ``config_name`` is retained for legacy callers; runtime mode selection no
    longer uses config names.
    """
    from app_factory import create_app as _factory_create_app

    return _factory_create_app()


# Backward-compatible module-level app for legacy tests/imports.
# Use a lazy proxy so the monolith isn't created at package import time.
_app = None


def _get_app():
    global _app
    if _app is None:
        _default_config = (
            "testing" if os.getenv("TESTING", "").lower() == "true" else "default"
        )
        _app = create_app(_default_config)
    return _app


def __getattr__(name):
    if name == "app":
        return _get_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["create_app", "app", "SYSTEM_PROMPTS"]
__version__ = "3.0.0"
