"""
Text2SQL Routes Package
API endpoint definitions
"""

from flask import Blueprint


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    from .main_routes import main_bp
    from .chat_routes import chat_bp
    from .schema_routes import schema_bp
    from .pretrain_routes import pretrain_bp
    from .health_routes import health_bp
    
    # Main routes (no prefix)
    app.register_blueprint(main_bp)
    
    # API routes - also register at root for backward compatibility
    app.register_blueprint(chat_bp)  # /chat, /check, /refine, /evaluate
    app.register_blueprint(schema_bp)  # /upload-schema, /schema
    app.register_blueprint(pretrain_bp)  # /pretrain, /pretrain-*
    app.register_blueprint(health_bp)  # /health, /stats
