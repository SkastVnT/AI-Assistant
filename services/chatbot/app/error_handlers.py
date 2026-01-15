"""
Error Handlers

Centralized error handling for the application.
"""

import logging
from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    """Register error handlers with the Flask application"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors"""
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle unauthorized errors"""
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden errors"""
        return jsonify({
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors"""
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle method not allowed errors"""
        return jsonify({
            'error': 'Method Not Allowed',
            'message': 'The method is not allowed for this endpoint'
        }), 405
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle rate limit errors"""
        return jsonify({
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded. Please try again later.'
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors"""
        logger.error(f"Internal Server Error: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle all HTTP exceptions"""
        return jsonify({
            'error': error.name,
            'message': error.description
        }), error.code
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all unhandled exceptions"""
        logger.exception(f"Unhandled exception: {error}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred'
        }), 500
