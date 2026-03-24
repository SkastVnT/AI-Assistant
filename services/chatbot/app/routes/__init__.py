"""
Blueprint Registration

Registers all API blueprints with the Flask application.
"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """
    Register all application blueprints
    
    Args:
        app: Flask application instance
    """
    # API v1 routes
    from .chat_routes import chat_bp
    from .conversation_routes import conversation_bp
    from .memory_routes import memory_bp
    from .file_routes import file_bp
    from .settings_routes import settings_bp
    from .learning_routes import learning_bp
    
    # Register with URL prefixes
    app.register_blueprint(chat_bp, url_prefix='/api/v1/chat')
    app.register_blueprint(conversation_bp, url_prefix='/api/v1/conversations')
    app.register_blueprint(memory_bp, url_prefix='/api/v1/memory')
    app.register_blueprint(file_bp, url_prefix='/api/v1/files')
    app.register_blueprint(settings_bp, url_prefix='/api/v1/settings')
    app.register_blueprint(learning_bp, url_prefix='/api/v1/learning')
    
    # Legacy routes (for backward compatibility)
    from .legacy_routes import legacy_bp
    app.register_blueprint(legacy_bp)
    
    app.logger.info("âœ… All blueprints registered")
