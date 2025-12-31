"""
Routes package for chatbot
"""
import sys
from pathlib import Path
from flask import Blueprint

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))


def register_blueprints(app):
    """Register all blueprints"""
    from routes.main import main_bp
    from routes.conversations import conversations_bp
    from routes.stable_diffusion import sd_bp
    from routes.memory import memory_bp
    from routes.images import images_bp
    from routes.mcp import mcp_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(conversations_bp, url_prefix='/api')
    app.register_blueprint(sd_bp)
    app.register_blueprint(memory_bp, url_prefix='/api/memory')
    app.register_blueprint(images_bp)
    app.register_blueprint(mcp_bp, url_prefix='/api/mcp')
