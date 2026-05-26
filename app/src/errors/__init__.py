"""
Errors Package
Standardized error handling utilities
"""

from .handler import (
    AIModelError,
    APIError,
    BadRequestError,
    DatabaseError,
    ErrorCode,
    ExternalAPIError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    UnauthorizedError,
    ValidationError,
    create_error_response,
    handle_exceptions,
    register_error_handlers,
    safe_execute,
    wrap_exception,
)

__all__ = [
    # Enums
    "ErrorCode",
    # Exceptions
    "APIError",
    "BadRequestError",
    "UnauthorizedError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationError",
    "RateLimitError",
    "DatabaseError",
    "ExternalAPIError",
    "AIModelError",
    # Functions
    "create_error_response",
    "handle_exceptions",
    "register_error_handlers",
    "wrap_exception",
    "safe_execute",
]
