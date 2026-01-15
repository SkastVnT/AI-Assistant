"""
Document Intelligence Routes Package
API endpoint definitions
"""


def register_blueprints(app):
    """Register all blueprints with the Flask app."""
    from .main_routes import main_bp
    from .ocr_routes import ocr_bp
    from .ai_routes import ai_bp
    from .batch_routes import batch_bp
    from .history_routes import history_bp
    from .health_routes import health_bp
    
    # Main routes
    app.register_blueprint(main_bp)
    
    # API routes
    app.register_blueprint(ocr_bp, url_prefix='/api')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(batch_bp, url_prefix='/api')
    app.register_blueprint(history_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')
