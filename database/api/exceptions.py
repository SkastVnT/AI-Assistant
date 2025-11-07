"""
API Exception Handling

Custom exceptions and error handlers for FastAPI
"""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

logger = logging.getLogger(__name__)


class DatabaseException(HTTPException):
    """Base exception for database operations"""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        headers: Optional[Dict[str, str]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(DatabaseException):
    """Exception raised when resource is not found"""
    
    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} with ID {resource_id} not found"
        )


class ValidationException(DatabaseException):
    """Exception raised for validation errors"""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )


class ConflictException(DatabaseException):
    """Exception raised for conflicts (e.g., duplicate username)"""
    
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail
        )


class UnauthorizedException(DatabaseException):
    """Exception raised for unauthorized access"""
    
    def __init__(self, detail: str = "Unauthorized access"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class ForbiddenException(DatabaseException):
    """Exception raised for forbidden actions"""
    
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


# Exception handlers
async def not_found_exception_handler(
    request: Request,
    exc: NotFoundException
) -> JSONResponse:
    """Handle NotFoundException"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Not Found",
            "detail": exc.detail,
            "path": str(request.url)
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: ValidationException
) -> JSONResponse:
    """Handle ValidationException"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Validation Error",
            "detail": exc.detail,
            "path": str(request.url)
        }
    )


async def conflict_exception_handler(
    request: Request,
    exc: ConflictException
) -> JSONResponse:
    """Handle ConflictException"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Conflict",
            "detail": exc.detail,
            "path": str(request.url)
        }
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle FastAPI RequestValidationError"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Request Validation Error",
            "detail": "Invalid request data",
            "errors": errors,
            "path": str(request.url)
        }
    )


async def sqlalchemy_exception_handler(
    request: Request,
    exc: SQLAlchemyError
) -> JSONResponse:
    """Handle SQLAlchemy errors"""
    logger.error(f"Database error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database Error",
            "detail": "An error occurred while accessing the database",
            "path": str(request.url)
        }
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle generic exceptions"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "path": str(request.url)
        }
    )


# Exception handler mapping
exception_handlers = {
    NotFoundException: not_found_exception_handler,
    ValidationException: validation_exception_handler,
    ConflictException: conflict_exception_handler,
    RequestValidationError: request_validation_exception_handler,
    SQLAlchemyError: sqlalchemy_exception_handler,
    Exception: generic_exception_handler
}
