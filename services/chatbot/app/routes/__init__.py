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
    
    # Video generation routes (Sora 2)
    from .video_routes import video_bp
    app.register_blueprint(video_bp, url_prefix='/api/video')

    # Legacy routes (for backward compatibility)
    from .legacy_routes import legacy_bp
    app.register_blueprint(legacy_bp)
    
    # Register original route blueprints that the frontend depends on
    # (images, stream, memory, stable_diffusion, etc.)
    _register_original_blueprints(app)
    
    app.logger.info("âœ… All blueprints registered")


def _register_original_blueprints(app: Flask) -> None:
    """Register original route blueprints from routes/ directory for full frontend compatibility."""
    import logging
    logger = logging.getLogger(__name__)
    
    blueprint_imports = [
        ('routes.user_auth', 'user_auth_bp', None),
        ('routes.admin', 'admin_bp', None),
        ('routes.images', 'images_bp', None),
        ('routes.stream', 'stream_bp', None),
        ('routes.memory', 'memory_bp', '/memory'),
        ('routes.conversations', 'conversations_bp', None),
        ('routes.stable_diffusion', 'sd_bp', None),
        ('routes.image_gen', 'image_gen_bp', None),
        ('routes.models', 'models_bp', None),
        ('routes.async_routes', 'async_bp', None),
        ('routes.mcp', 'mcp_bp', '/api/mcp'),
        ('routes.qr_payment', 'qr_bp', None),
    ]
    
    for module_name, bp_attr, url_prefix in blueprint_imports:
        try:
            import importlib
            mod = importlib.import_module(module_name)
            bp = getattr(mod, bp_attr)
            kwargs = {'url_prefix': url_prefix} if url_prefix else {}
            app.register_blueprint(bp, **kwargs)
            logger.info(f"âœ… Registered original blueprint: {bp_attr}")
        except Exception as e:
            logger.warning(f"âš ï¸ Could not register {bp_attr}: {e}")
