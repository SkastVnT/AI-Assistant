"""
Error Handler for Hub Gateway
Centralized error handling and custom exceptions
"""

from flask import jsonify
from functools import wraps
import logging

logger = logging.getLogger("ai_assistant_hub")


class HubException(Exception):
    """Base exception for Hub Gateway."""
    status_code = 500
    
    def __init__(self, message, status_code=None, payload=None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['error'] = self.message
        rv['status_code'] = self.status_code
        return rv


class ServiceNotFoundError(HubException):
    """Raised when requested service is not found."""
    status_code = 404


class ServiceUnavailableError(HubException):
    """Raised when service is unavailable."""
    status_code = 503


class ConfigurationError(HubException):
    """Raised when configuration is invalid."""
    status_code = 500


def handle_hub_exception(error):
    """Handle HubException and return JSON response."""
    logger.error(f"Hub exception: {error.message}")
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def handle_generic_exception(error):
    """Handle generic exceptions."""
    logger.exception("Unexpected error occurred")
    response = jsonify({
        'error': 'Internal server error',
        'message': str(error),
        'status_code': 500
    })
    response.status_code = 500
    return response


def error_handler(f):
    """Decorator for handling errors in routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except HubException as e:
            return handle_hub_exception(e)
        except Exception as e:
            return handle_generic_exception(e)
    return decorated_function
