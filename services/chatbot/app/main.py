"""
Flask Application Factory

This module creates and configures the Flask application
using the factory pattern for better testability and modularity.
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from .config import get_config
from .extensions import init_extensions
from .routes import register_blueprints
from .error_handlers import register_error_handlers


def create_application(config_name: str = 'default') -> Flask:
    """
    Create and configure Flask application
    
    Args:
        config_name: Configuration to load ('development', 'production', 'testing')
    
    Returns:
        Configured Flask application
    """
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(
        __name__,
        static_folder='../static',
        template_folder='../templates',
        static_url_path='/static'
    )
    
    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Setup logging
    setup_logging(app)
    
    # Initialize CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize extensions (database, cache, etc.)
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register health check
    register_health_check(app)
    
    app.logger.info(f"✅ Chatbot application created with config: {config_name}")
    
    return app


def setup_logging(app: Flask) -> None:
    """Configure application logging"""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(
                Path(__file__).parent.parent / 'logs' / 'app.log',
                encoding='utf-8'
            ) if os.getenv('FLASK_ENV') == 'production' else logging.NullHandler()
        ]
    )


def register_health_check(app: Flask) -> None:
    """Register health check endpoint"""
    @app.route('/health')
    def health():
        return {'status': 'healthy', 'service': 'chatbot'}, 200
