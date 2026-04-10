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
try:
    from services.shared_env import load_shared_env
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    for _parent in Path(__file__).resolve().parents:
        if (_parent / "services" / "shared_env.py").exists():
            if str(_parent) not in sys.path:
                sys.path.insert(0, str(_parent))
            break
    from services.shared_env import load_shared_env

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
    load_shared_env(__file__)
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
    
    # Session config
    from datetime import timedelta
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
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

    # Register security headers
    register_security_headers(app)

    # Seed admin users
    _seed_admin_users(app)

    app.logger.info(f"âœ… Chatbot application created with config: {config_name}")
    
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


def register_security_headers(app: Flask) -> None:
    """Register security headers on all responses"""
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response


def _seed_admin_users(app: Flask) -> None:
    """Seed admin users into MongoDB on startup."""
    try:
        from core.user_auth import init_admin_users
        from core.extensions import get_db
        db = get_db()
        if db is not None:
            init_admin_users(db)
            app.logger.info("âœ… Admin users seeded")
    except Exception as e:
        app.logger.warning(f"âš ï¸ Admin seed skipped: {e}")


