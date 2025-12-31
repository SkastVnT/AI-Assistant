"""
Document Intelligence Application Package
Modular Flask application for document processing and AI analysis
"""

from flask import Flask
from flask_cors import CORS
import os
import logging


def create_app(config_name: str = None) -> Flask:
    """
    Application factory for Document Intelligence service.
    
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
    CORS(app)
    
    # Initialize extensions
    from .extensions import init_extensions
    init_extensions(app)
    
    # Register blueprints
    from .routes import register_blueprints
    register_blueprints(app)
    
    # Register error handlers
    from .error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    return app
