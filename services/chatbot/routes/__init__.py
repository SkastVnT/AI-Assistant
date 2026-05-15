"""
Routes package for chatbot.

Blueprint registration is performed **inline in chatbot_main.py** via
individual ``app.register_blueprint()`` calls inside ``try/except ImportError``
blocks.  This module provides:

* A reference ``register_blueprints()`` helper (not called by the monolith but
  useful for test harnesses and future migration to a full app factory).
* The canonical list of all registered blueprints (see REGISTERED_BLUEPRINTS).

Known overlap: ``mcp_bp`` is registered here with prefix ``/api/mcp`` AND
chatbot_main.py has inline ``@app.route('/api/mcp/*')`` decorators.  Flask
uses the first matching handler.  The inline routes were registered first
(module load) so they win.  This will be resolved when the inline MCP routes
are moved into the blueprint (P2 roadmap item).
"""
import sys
from pathlib import Path
from flask import Blueprint

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

# ---------------------------------------------------------------------------
# Canonical list of all blueprints registered in chatbot_main.py
# ---------------------------------------------------------------------------
# Keep this in sync with the register_blueprint() calls in chatbot_main.py.
# Format: (module, variable_name, url_prefix_or_None)
REGISTERED_BLUEPRINTS = [
    ("routes.stream",              "stream_bp",               None),
    ("routes.async_routes",        "async_bp",                None),
    ("routes.conversations",       "conversations_bp",        None),
    ("routes.memory",              "memory_bp",               "/memory"),
    ("routes.images",              "images_bp",               None),
    ("routes.mcp",                 "mcp_bp",                  "/api/mcp"),   # overlaps inline
    ("routes.stable_diffusion",    "sd_bp",                   None),
    ("routes.image_gen",           "image_gen_bp",            None),
    ("routes.nano_banana",         "nano_banana_bp",          None),
    ("routes.models",              "models_bp",               None),
    ("routes.skills",              "skills_bp",               None),
    ("routes.last30days",          "last30days_bp",           None),
    ("routes.hermes",              "hermes_bp",               None),
    ("routes.character_select",    "character_select_bp",     None),
    ("routes.reasoning_image_gen", "reasoning_image_gen_bp",  None),  # REASONING_PIPELINE only
    ("routes.anime_pipeline",      "anime_pipeline_bp",       None),
    ("routes.characters",          "characters_bp",           None),
    ("routes.jobs",                "jobs_bp",                 None),
    ("routes.video",               "video_bp",                None),
]


def register_blueprints(app):
    """Register all blueprints onto *app*.

    This function is **not called by the monolith** — it is provided for test
    harnesses and future migration.  It mirrors the try/except registration
    pattern used in chatbot_main.py so that partial failures degrade
    gracefully.
    """
    from routes.stream import stream_bp
    from routes.conversations import conversations_bp
    from routes.stable_diffusion import sd_bp
    from routes.memory import memory_bp
    from routes.images import images_bp
    from routes.mcp import mcp_bp
    from routes.stream import stream_bp
    from routes.skills import skills_bp

    app.register_blueprint(stream_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(sd_bp)
    app.register_blueprint(memory_bp, url_prefix='/memory')
    app.register_blueprint(images_bp)
    app.register_blueprint(mcp_bp, url_prefix='/api/mcp')
    app.register_blueprint(skills_bp)

    # Optional blueprints — graceful degradation on missing deps
    optional = [
        ("routes.async_routes",        "async_bp",               None),
        ("routes.image_gen",           "image_gen_bp",           None),
        ("routes.nano_banana",         "nano_banana_bp",         None),
        ("routes.models",              "models_bp",              None),
        ("routes.last30days",          "last30days_bp",          None),
        ("routes.hermes",              "hermes_bp",              None),
        ("routes.character_select",    "character_select_bp",    None),
        ("routes.reasoning_image_gen", "reasoning_image_gen_bp", None),
        ("routes.anime_pipeline",      "anime_pipeline_bp",      None),
        ("routes.characters",          "characters_bp",          None),
        ("routes.jobs",                "jobs_bp",                None),
        ("routes.video",               "video_bp",               None),
    ]
    for module_path, var_name, prefix in optional:
        try:
            import importlib
            mod = importlib.import_module(module_path)
            bp = getattr(mod, var_name)
            if prefix:
                app.register_blueprint(bp, url_prefix=prefix)
            else:
                app.register_blueprint(bp)
        except (ImportError, AttributeError):
            pass

