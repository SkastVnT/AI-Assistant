"""
Document Intelligence Error Handlers
Centralized error handling for the application
"""

from flask import jsonify
import logging

logger = logging.getLogger(__name__)


class DocumentIntelException(Exception):
    """Base exception for Document Intelligence service."""
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


class FileNotFoundError(DocumentIntelException):
    """Raised when file is not found."""
    status_code = 404


class InvalidFileError(DocumentIntelException):
    """Raised for invalid file type."""
    status_code = 400


class OCRError(DocumentIntelException):
    """Raised when OCR processing fails."""
    status_code = 500


class AIProcessingError(DocumentIntelException):
    """Raised when AI processing fails."""
    status_code = 500


def handle_doc_intel_exception(error: DocumentIntelException):
    """Handle Document Intelligence exceptions."""
    logger.error(f"Document Intelligence exception: {error.message}")
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
    app.register_error_handler(DocumentIntelException, handle_doc_intel_exception)
    app.register_error_handler(InvalidFileError, handle_doc_intel_exception)
    app.register_error_handler(OCRError, handle_doc_intel_exception)
    app.register_error_handler(AIProcessingError, handle_doc_intel_exception)
    app.register_error_handler(404, handle_404_error)
    app.register_error_handler(Exception, handle_generic_exception)
