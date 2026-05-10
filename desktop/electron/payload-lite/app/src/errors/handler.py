"""
Error Handling Module
Standardized error responses and exception handling
"""

import logging
import traceback
from typing import Dict, Any, Optional, Type
from functools import wraps
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standard error codes."""
    
    # Client errors (4xx)
    BAD_REQUEST = ("BAD_REQUEST", 400, "Invalid request")
    UNAUTHORIZED = ("UNAUTHORIZED", 401, "Authentication required")
    FORBIDDEN = ("FORBIDDEN", 403, "Access denied")
    NOT_FOUND = ("NOT_FOUND", 404, "Resource not found")
    METHOD_NOT_ALLOWED = ("METHOD_NOT_ALLOWED", 405, "Method not allowed")
    CONFLICT = ("CONFLICT", 409, "Resource conflict")
    VALIDATION_ERROR = ("VALIDATION_ERROR", 422, "Validation failed")
    RATE_LIMITED = ("RATE_LIMITED", 429, "Too many requests")
    
    # Server errors (5xx)
    INTERNAL_ERROR = ("INTERNAL_ERROR", 500, "Internal server error")
    SERVICE_UNAVAILABLE = ("SERVICE_UNAVAILABLE", 503, "Service unavailable")
    GATEWAY_TIMEOUT = ("GATEWAY_TIMEOUT", 504, "Gateway timeout")
    
    # Domain errors
    DATABASE_ERROR = ("DATABASE_ERROR", 500, "Database error")
    EXTERNAL_API_ERROR = ("EXTERNAL_API_ERROR", 502, "External API error")
    AI_MODEL_ERROR = ("AI_MODEL_ERROR", 500, "AI model error")
    FILE_PROCESSING_ERROR = ("FILE_PROCESSING_ERROR", 500, "File processing error")
    
    def __init__(self, code: str, http_status: int, default_message: str):
        self.code = code
        self.http_status = http_status
        self.default_message = default_message


class APIError(Exception):
    """
    Base API exception with standardized error response.
    """
    
    def __init__(self, 
                 error_code: ErrorCode,
                 message: str = None,
                 details: Dict[str, Any] = None,
                 original_error: Exception = None):
        """
        Initialize API error.
        
        Args:
            error_code: ErrorCode enum value
            message: Custom error message
            details: Additional error details
            original_error: Original exception if any
        """
        self.error_code = error_code
        self.message = message or error_code.default_message
        self.details = details or {}
        self.original_error = original_error
        
        super().__init__(self.message)
    
    @property
    def http_status(self) -> int:
        """Get HTTP status code."""
        return self.error_code.http_status
    
    def to_dict(self, include_traceback: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary response.
        
        Args:
            include_traceback: Include stack trace (for development)
        
        Returns:
            Error response dictionary
        """
        response = {
            "error": {
                "code": self.error_code.code,
                "message": self.message,
                "status": self.http_status
            }
        }
        
        if self.details:
            response["error"]["details"] = self.details
        
        if include_traceback and self.original_error:
            response["error"]["traceback"] = traceback.format_exception(
                type(self.original_error),
                self.original_error,
                self.original_error.__traceback__
            )
        
        return response


# ============================================================================
# SPECIFIC EXCEPTIONS
# ============================================================================

class BadRequestError(APIError):
    """Invalid request error."""
    
    def __init__(self, message: str = None, details: Dict = None):
        super().__init__(ErrorCode.BAD_REQUEST, message, details)


class UnauthorizedError(APIError):
    """Authentication error."""
    
    def __init__(self, message: str = None, details: Dict = None):
        super().__init__(ErrorCode.UNAUTHORIZED, message, details)


class ForbiddenError(APIError):
    """Authorization error."""
    
    def __init__(self, message: str = None, details: Dict = None):
        super().__init__(ErrorCode.FORBIDDEN, message, details)


class NotFoundError(APIError):
    """Resource not found error."""
    
    def __init__(self, resource: str, resource_id: str = None):
        details = {"resource": resource}
        if resource_id:
            details["id"] = resource_id
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with ID '{resource_id}' not found"
        super().__init__(ErrorCode.NOT_FOUND, message, details)


class ValidationError(APIError):
    """Validation error."""
    
    def __init__(self, errors: Dict[str, str]):
        super().__init__(
            ErrorCode.VALIDATION_ERROR,
            "Validation failed",
            {"validation_errors": errors}
        )


class RateLimitError(APIError):
    """Rate limit exceeded error."""
    
    def __init__(self, retry_after: int = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(ErrorCode.RATE_LIMITED, "Rate limit exceeded", details)


class DatabaseError(APIError):
    """Database error."""
    
    def __init__(self, message: str = None, original_error: Exception = None):
        super().__init__(
            ErrorCode.DATABASE_ERROR,
            message,
            original_error=original_error
        )


class ExternalAPIError(APIError):
    """External API error."""
    
    def __init__(self, service: str, message: str = None, 
                 original_error: Exception = None):
        super().__init__(
            ErrorCode.EXTERNAL_API_ERROR,
            message or f"Error from {service}",
            {"service": service},
            original_error
        )


class AIModelError(APIError):
    """AI model error."""
    
    def __init__(self, model: str, message: str = None,
                 original_error: Exception = None):
        super().__init__(
            ErrorCode.AI_MODEL_ERROR,
            message or f"Error from AI model {model}",
            {"model": model},
            original_error
        )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

def create_error_response(error: Exception, 
                          include_traceback: bool = False) -> tuple:
    """
    Create standardized error response.
    
    Args:
        error: Exception to convert
        include_traceback: Include stack trace
    
    Returns:
        (response_dict, status_code)
    """
    if isinstance(error, APIError):
        return error.to_dict(include_traceback), error.http_status
    
    # Convert unknown exceptions
    logger.exception(f"Unhandled exception: {error}")
    
    response = {
        "error": {
            "code": ErrorCode.INTERNAL_ERROR.code,
            "message": "An unexpected error occurred",
            "status": 500
        }
    }
    
    if include_traceback:
        response["error"]["details"] = {"message": str(error)}
        response["error"]["traceback"] = traceback.format_exc().split("\n")
    
    return response, 500


def handle_exceptions(include_traceback: bool = False):
    """
    Decorator to handle exceptions in Flask routes.
    
    Args:
        include_traceback: Include stack trace in response
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except APIError as e:
                logger.warning(f"API error: {e.error_code.code} - {e.message}")
                from flask import jsonify
                return jsonify(e.to_dict(include_traceback)), e.http_status
            except Exception as e:
                logger.exception(f"Unhandled exception in {func.__name__}")
                response, status = create_error_response(e, include_traceback)
                from flask import jsonify
                return jsonify(response), status
        return wrapper
    return decorator


def register_error_handlers(app, include_traceback: bool = False):
    """
    Register Flask error handlers.
    
    Args:
        app: Flask application
        include_traceback: Include stack trace in development
    """
    from flask import jsonify
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        return jsonify(error.to_dict(include_traceback)), error.http_status
    
    @app.errorhandler(400)
    def handle_400(error):
        return jsonify({
            "error": {
                "code": "BAD_REQUEST",
                "message": str(error.description),
                "status": 400
            }
        }), 400
    
    @app.errorhandler(404)
    def handle_404(error):
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": "Resource not found",
                "status": 404
            }
        }), 404
    
    @app.errorhandler(405)
    def handle_405(error):
        return jsonify({
            "error": {
                "code": "METHOD_NOT_ALLOWED",
                "message": "Method not allowed",
                "status": 405
            }
        }), 405
    
    @app.errorhandler(429)
    def handle_429(error):
        return jsonify({
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests",
                "status": 429
            }
        }), 429
    
    @app.errorhandler(500)
    def handle_500(error):
        logger.exception("Internal server error")
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "status": 500
            }
        }), 500


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def wrap_exception(error: Exception, 
                   error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
                   message: str = None) -> APIError:
    """
    Wrap exception in APIError.
    
    Args:
        error: Original exception
        error_code: Error code to use
        message: Custom message
    
    Returns:
        APIError instance
    """
    return APIError(
        error_code=error_code,
        message=message or str(error),
        original_error=error
    )


def safe_execute(func, *args, 
                 error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
                 default=None,
                 **kwargs):
    """
    Execute function safely with error handling.
    
    Args:
        func: Function to execute
        *args: Function arguments
        error_code: Error code on failure
        default: Default value on failure
        **kwargs: Function keyword arguments
    
    Returns:
        Function result or default
    """
    try:
        return func(*args, **kwargs)
    except APIError:
        raise
    except Exception as e:
        logger.exception(f"Error in {func.__name__}")
        if default is not None:
            return default
        raise wrap_exception(e, error_code)
