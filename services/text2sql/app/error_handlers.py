"""
Text2SQL Error Handlers
Centralized error handling for the application
"""

from flask import jsonify
import logging

logger = logging.getLogger(__name__)


class Text2SQLException(Exception):
    """Base exception for Text2SQL service."""
    status_code = 500
    
    def __init__(self, message: str, status_code: int = None, payload: dict = None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self) -> dict:
        rv = dict(self.payload or ())
        rv['error'] = self.message
        rv['status_code'] = self.status_code
        return rv


class SchemaNotFoundError(Text2SQLException):
    """Raised when no schema is uploaded."""
    status_code = 400


class SQLGenerationError(Text2SQLException):
    """Raised when SQL generation fails."""
    status_code = 500


class DatabaseConnectionError(Text2SQLException):
    """Raised when database connection fails."""
    status_code = 503


class ValidationError(Text2SQLException):
    """Raised for validation errors."""
    status_code = 400


def handle_text2sql_exception(error: Text2SQLException):
    """Handle Text2SQL exceptions."""
    logger.error(f"Text2SQL exception: {error.message}")
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def handle_generic_exception(error: Exception):
    """Handle unexpected exceptions."""
    logger.exception("Unexpected error occurred")
    response = jsonify({
        'error': 'Internal server error',
        'message': str(error),
        'status_code': 500
    })
    response.status_code = 500
    return response


def handle_404_error(error):
    """Handle 404 errors."""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found',
        'status_code': 404
    }), 404


def register_error_handlers(app):
    """Register all error handlers with the Flask app."""
    app.register_error_handler(Text2SQLException, handle_text2sql_exception)
    app.register_error_handler(SchemaNotFoundError, handle_text2sql_exception)
    app.register_error_handler(SQLGenerationError, handle_text2sql_exception)
    app.register_error_handler(DatabaseConnectionError, handle_text2sql_exception)
    app.register_error_handler(ValidationError, handle_text2sql_exception)
    app.register_error_handler(404, handle_404_error)
    app.register_error_handler(Exception, handle_generic_exception)
