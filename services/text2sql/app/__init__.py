"""
Text2SQL Application Package
Modular Flask application for natural language to SQL conversion
"""

from flask import Flask
from flask_cors import CORS
import os


def create_app(config_name: str = None) -> Flask:
    """
    Application factory for Text2SQL service.
    
    Args:
        config_name: Configuration environment (development, production, testing)
    
    Returns:
        Flask application instance
    """
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Load configuration
    from .config import get_config
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize CORS
    CORS(app, origins=config.CORS_ORIGINS)
    
    # Initialize extensions
    from .extensions import init_extensions
    init_extensions(app)
    
    # Register blueprints
    from .routes import register_blueprints
    register_blueprints(app)
    
    # Register error handlers
    from .error_handlers import register_error_handlers
    register_error_handlers(app)
    
    return app
