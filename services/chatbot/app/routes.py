"""
app/routes.py — Blueprint registration bridge for the Flask app factory.

Registers the same blueprints as the main chatbot_main.py entry-point so
that test clients created via ``from app import app`` see all routes.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure services/chatbot is on sys.path so absolute imports work.
_CHATBOT_DIR = Path(__file__).resolve().parent.parent
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


def register_blueprints(app) -> None:
    """Register all production blueprints on *app*."""
    from routes.main import main_bp
    from routes.stream import stream_bp
    from routes.conversations import conversations_bp
    from routes.memory import memory_bp
    from routes.images import images_bp
    from routes.mcp import mcp_bp
    from routes.stable_diffusion import sd_bp
    from routes.skills import skills_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(stream_bp)
    app.register_blueprint(conversations_bp, url_prefix='/api')
    app.register_blueprint(memory_bp, url_prefix='/api/memory')
    app.register_blueprint(images_bp)
    app.register_blueprint(mcp_bp, url_prefix='/api/mcp')
    app.register_blueprint(sd_bp)
    app.register_blueprint(skills_bp)

    # Optional blueprints — register only when available.
    _optional = [
        ("routes.async_routes", "async_bp", {}),
        ("routes.hermes", "hermes_bp", {}),
        ("routes.last30days", "last30days_bp", {}),
        ("routes.characters", "characters_bp", {}),
        ("routes.jobs", "jobs_bp", {}),
        ("routes.image_gen", "image_gen_bp", {}),
    ]
    import importlib
    import logging
    _log = logging.getLogger(__name__)
    for module_name, bp_name, kwargs in _optional:
        try:
            mod = importlib.import_module(module_name)
            bp = getattr(mod, bp_name)
            app.register_blueprint(bp, **kwargs)
        except (ImportError, AttributeError) as exc:
            _log.debug("Optional blueprint %s skipped: %s", module_name, exc)
