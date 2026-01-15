"""
Errors Package
Standardized error handling utilities
"""

from .handler import (
    ErrorCode,
    APIError,
    BadRequestError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
    RateLimitError,
    DatabaseError,
    ExternalAPIError,
    AIModelError,
    create_error_response,
    handle_exceptions,
    register_error_handlers,
    wrap_exception,
    safe_execute
)

__all__ = [
    # Enums
    'ErrorCode',
    
    # Exceptions
    'APIError',
    'BadRequestError',
    'UnauthorizedError',
    'ForbiddenError',
    'NotFoundError',
    'ValidationError',
    'RateLimitError',
    'DatabaseError',
    'ExternalAPIError',
    'AIModelError',
    
    # Functions
    'create_error_response',
    'handle_exceptions',
    'register_error_handlers',
    'wrap_exception',
    'safe_execute'
]
