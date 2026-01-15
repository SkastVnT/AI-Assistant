"""
Tests for Error Handler Module
"""

import pytest
from unittest.mock import Mock, patch


class TestErrorCode:
    """Test ErrorCode enum."""
    
    def test_error_code_values(self):
        """Test error code enum values."""
        from src.errors import ErrorCode
        
        assert ErrorCode.BAD_REQUEST.code == "BAD_REQUEST"
        assert ErrorCode.BAD_REQUEST.http_status == 400
        assert ErrorCode.NOT_FOUND.http_status == 404
        assert ErrorCode.INTERNAL_ERROR.http_status == 500
    
    def test_error_code_has_message(self):
        """Test error codes have default messages."""
        from src.errors import ErrorCode
        
        assert ErrorCode.UNAUTHORIZED.default_message == "Authentication required"
        assert ErrorCode.RATE_LIMITED.default_message == "Too many requests"


class TestAPIError:
    """Test APIError class."""
    
    def test_api_error_creation(self):
        """Test creating API error."""
        from src.errors import APIError, ErrorCode
        
        error = APIError(ErrorCode.BAD_REQUEST, "Invalid input")
        
        assert error.error_code == ErrorCode.BAD_REQUEST
        assert error.message == "Invalid input"
        assert error.http_status == 400
    
    def test_api_error_default_message(self):
        """Test API error uses default message."""
        from src.errors import APIError, ErrorCode
        
        error = APIError(ErrorCode.NOT_FOUND)
        
        assert error.message == "Resource not found"
    
    def test_api_error_with_details(self):
        """Test API error with details."""
        from src.errors import APIError, ErrorCode
        
        error = APIError(
            ErrorCode.VALIDATION_ERROR,
            "Validation failed",
            details={"field": "email", "error": "invalid format"}
        )
        
        assert error.details["field"] == "email"
    
    def test_api_error_to_dict(self):
        """Test converting error to dict."""
        from src.errors import APIError, ErrorCode
        
        error = APIError(ErrorCode.FORBIDDEN, "Access denied")
        result = error.to_dict()
        
        assert result["error"]["code"] == "FORBIDDEN"
        assert result["error"]["message"] == "Access denied"
        assert result["error"]["status"] == 403


class TestSpecificErrors:
    """Test specific error classes."""
    
    def test_bad_request_error(self):
        """Test BadRequestError."""
        from src.errors import BadRequestError
        
        error = BadRequestError("Missing parameter")
        
        assert error.http_status == 400
        assert error.message == "Missing parameter"
    
    def test_not_found_error(self):
        """Test NotFoundError."""
        from src.errors import NotFoundError
        
        error = NotFoundError("User", "123")
        
        assert error.http_status == 404
        assert "User" in error.message
        assert "123" in error.message
        assert error.details["resource"] == "User"
        assert error.details["id"] == "123"
    
    def test_validation_error(self):
        """Test ValidationError."""
        from src.errors import ValidationError
        
        error = ValidationError({
            "email": "invalid format",
            "password": "too short"
        })
        
        assert error.http_status == 422
        assert "validation_errors" in error.details
        assert error.details["validation_errors"]["email"] == "invalid format"
    
    def test_rate_limit_error(self):
        """Test RateLimitError."""
        from src.errors import RateLimitError
        
        error = RateLimitError(retry_after=60)
        
        assert error.http_status == 429
        assert error.details["retry_after"] == 60
    
    def test_database_error(self):
        """Test DatabaseError."""
        from src.errors import DatabaseError
        
        original = Exception("Connection timeout")
        error = DatabaseError("Failed to connect", original)
        
        assert error.http_status == 500
        assert error.original_error == original
    
    def test_external_api_error(self):
        """Test ExternalAPIError."""
        from src.errors import ExternalAPIError
        
        error = ExternalAPIError("Google API", "Quota exceeded")
        
        assert error.http_status == 502
        assert error.details["service"] == "Google API"
    
    def test_ai_model_error(self):
        """Test AIModelError."""
        from src.errors import AIModelError
        
        error = AIModelError("GPT-4", "Token limit exceeded")
        
        assert error.http_status == 500
        assert error.details["model"] == "GPT-4"


class TestErrorFunctions:
    """Test error utility functions."""
    
    def test_create_error_response_api_error(self):
        """Test creating response from APIError."""
        from src.errors import create_error_response, NotFoundError
        
        error = NotFoundError("Document")
        response, status = create_error_response(error)
        
        assert status == 404
        assert response["error"]["code"] == "NOT_FOUND"
    
    def test_create_error_response_generic_error(self):
        """Test creating response from generic error."""
        from src.errors import create_error_response
        
        error = ValueError("Something went wrong")
        response, status = create_error_response(error)
        
        assert status == 500
        assert response["error"]["code"] == "INTERNAL_ERROR"
    
    def test_wrap_exception(self):
        """Test wrapping exception."""
        from src.errors import wrap_exception, ErrorCode
        
        original = ValueError("Invalid value")
        wrapped = wrap_exception(original, ErrorCode.BAD_REQUEST)
        
        assert wrapped.http_status == 400
        assert wrapped.original_error == original
    
    def test_safe_execute_success(self):
        """Test safe_execute with success."""
        from src.errors import safe_execute
        
        def add(a, b):
            return a + b
        
        result = safe_execute(add, 1, 2)
        
        assert result == 3
    
    def test_safe_execute_with_default(self):
        """Test safe_execute returns default on error."""
        from src.errors import safe_execute
        
        def failing():
            raise ValueError("Error")
        
        result = safe_execute(failing, default="fallback")
        
        assert result == "fallback"


class TestFlaskErrorHandlers:
    """Test Flask error handlers."""
    
    @pytest.fixture
    def app(self):
        """Create Flask test app."""
        from flask import Flask
        from src.errors import register_error_handlers, NotFoundError
        
        app = Flask(__name__)
        register_error_handlers(app)
        
        @app.route('/trigger-404')
        def trigger_404():
            raise NotFoundError("Item", "123")
        
        @app.route('/trigger-500')
        def trigger_500():
            raise Exception("Unexpected error")
        
        return app
    
    def test_api_error_handler(self, app):
        """Test API error handler."""
        with app.test_client() as client:
            response = client.get('/trigger-404')
            
            assert response.status_code == 404
            data = response.get_json()
            assert data["error"]["code"] == "NOT_FOUND"
    
    def test_generic_404_handler(self, app):
        """Test generic 404 handler."""
        with app.test_client() as client:
            response = client.get('/nonexistent')
            
            assert response.status_code == 404
            data = response.get_json()
            assert data["error"]["code"] == "NOT_FOUND"


class TestHandleExceptionsDecorator:
    """Test handle_exceptions decorator."""
    
    def test_decorator_success(self):
        """Test decorator with successful function."""
        from flask import Flask, jsonify
        from src.errors import handle_exceptions
        
        app = Flask(__name__)
        
        @app.route('/test')
        @handle_exceptions()
        def test_route():
            return jsonify({"success": True})
        
        with app.test_client() as client:
            response = client.get('/test')
            assert response.status_code == 200
    
    def test_decorator_catches_api_error(self):
        """Test decorator catches APIError."""
        from flask import Flask
        from src.errors import handle_exceptions, BadRequestError
        
        app = Flask(__name__)
        
        @app.route('/test')
        @handle_exceptions()
        def test_route():
            raise BadRequestError("Invalid data")
        
        with app.test_client() as client:
            response = client.get('/test')
            assert response.status_code == 400
            data = response.get_json()
            assert data["error"]["code"] == "BAD_REQUEST"
