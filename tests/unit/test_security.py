"""
Tests for Security Module
"""

import pytest
from unittest.mock import MagicMock, patch


class TestAPIKeyManager:
    """Tests for API key management."""
    
    def test_generate_key(self):
        """Test API key generation."""
        from src.security.api_key_manager import APIKeyManager
        
        manager = APIKeyManager(key_prefix="test_")
        key = manager.generate_key("test-app")
        
        assert key.startswith("test_")
        assert len(key) > 20
    
    def test_validate_key(self):
        """Test API key validation."""
        from src.security.api_key_manager import APIKeyManager
        
        manager = APIKeyManager()
        key = manager.generate_key("test-app")
        
        # Valid key
        metadata = manager.validate_key(key)
        assert metadata is not None
        assert metadata['name'] == "test-app"
        
        # Invalid key
        assert manager.validate_key("invalid-key") is None
    
    def test_revoke_key(self):
        """Test API key revocation."""
        from src.security.api_key_manager import APIKeyManager
        
        manager = APIKeyManager()
        key = manager.generate_key("test-app")
        
        # Key should be valid
        assert manager.validate_key(key) is not None
        
        # Revoke key
        assert manager.revoke_key(key) is True
        
        # Key should now be invalid
        assert manager.validate_key(key) is None
    
    def test_rotate_key(self):
        """Test API key rotation."""
        from src.security.api_key_manager import APIKeyManager
        
        manager = APIKeyManager()
        old_key = manager.generate_key("test-app")
        
        # Rotate key
        new_key = manager.rotate_key(old_key)
        
        assert new_key is not None
        assert new_key != old_key
        
        # Old key should be invalid
        assert manager.validate_key(old_key) is None
        
        # New key should be valid
        assert manager.validate_key(new_key) is not None
    
    def test_mask_api_key(self):
        """Test API key masking."""
        from src.security.api_key_manager import mask_api_key
        
        key = "ak_abcdefghijklmnop1234567890"
        masked = mask_api_key(key)
        
        assert "..." in masked
        assert len(masked) < len(key)
    
    def test_key_expiration(self):
        """Test API key expiration."""
        import time
        from src.security.api_key_manager import APIKeyManager
        
        manager = APIKeyManager()
        key = manager.generate_key("test-app", expires_in=1)  # 1 second
        
        # Should be valid immediately
        assert manager.validate_key(key) is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert manager.validate_key(key) is None
    
    def test_get_stats(self):
        """Test getting key statistics."""
        from src.security.api_key_manager import APIKeyManager
        
        manager = APIKeyManager()
        manager.generate_key("app1")
        manager.generate_key("app2")
        
        stats = manager.get_stats()
        
        assert stats['active_keys'] == 2
        assert len(stats['keys']) == 2


class TestInputValidator:
    """Tests for input validation."""
    
    def test_validate_required_field(self):
        """Test required field validation."""
        from src.security.input_validator import InputValidator
        
        validator = InputValidator()
        
        schema = {
            'name': {'required': True, 'type': str}
        }
        
        # Missing required field
        result = validator.validate({}, schema)
        assert not result.is_valid
        assert len(result.errors) == 1
        
        # With required field
        result = validator.validate({'name': 'John'}, schema)
        assert result.is_valid
    
    def test_validate_string_length(self):
        """Test string length validation."""
        from src.security.input_validator import InputValidator
        
        validator = InputValidator()
        
        schema = {
            'username': {
                'type': str,
                'min_length': 3,
                'max_length': 20
            }
        }
        
        # Too short
        result = validator.validate({'username': 'ab'}, schema)
        assert not result.is_valid
        
        # Too long
        result = validator.validate({'username': 'a' * 25}, schema)
        assert not result.is_valid
        
        # Valid
        result = validator.validate({'username': 'john_doe'}, schema)
        assert result.is_valid
    
    def test_validate_email(self):
        """Test email validation."""
        from src.security.input_validator import InputValidator
        
        validator = InputValidator()
        
        assert validator.validate_email("user@example.com") is True
        assert validator.validate_email("invalid-email") is False
        assert validator.validate_email("user@") is False
    
    def test_validate_url(self):
        """Test URL validation."""
        from src.security.input_validator import InputValidator
        
        validator = InputValidator()
        
        assert validator.validate_url("https://example.com") is True
        assert validator.validate_url("http://test.org/path") is True
        assert validator.validate_url("not-a-url") is False
    
    def test_validate_filename(self):
        """Test filename validation."""
        from src.security.input_validator import InputValidator
        
        validator = InputValidator()
        
        assert validator.validate_filename("file.txt") is True
        assert validator.validate_filename("../etc/passwd") is False
        assert validator.validate_filename("/etc/passwd") is False
    
    def test_validate_pattern(self):
        """Test pattern matching validation."""
        from src.security.input_validator import InputValidator
        
        validator = InputValidator()
        
        schema = {
            'code': {
                'type': str,
                'pattern': 'alphanumeric'
            }
        }
        
        result = validator.validate({'code': 'ABC123'}, schema)
        assert result.is_valid
        
        result = validator.validate({'code': 'ABC-123'}, schema)
        assert not result.is_valid
    
    def test_validation_result_to_dict(self):
        """Test ValidationResult to dict conversion."""
        from src.security.input_validator import InputValidator
        
        validator = InputValidator()
        
        schema = {'name': {'required': True}}
        result = validator.validate({}, schema)
        
        result_dict = result.to_dict()
        assert 'valid' in result_dict
        assert 'errors' in result_dict
        assert result_dict['valid'] is False
    
    def test_number_validation(self):
        """Test number range validation."""
        from src.security.input_validator import InputValidator
        
        validator = InputValidator()
        
        schema = {
            'age': {
                'type': int,
                'min': 0,
                'max': 120
            }
        }
        
        result = validator.validate({'age': 25}, schema)
        assert result.is_valid
        
        result = validator.validate({'age': -5}, schema)
        assert not result.is_valid
        
        result = validator.validate({'age': 150}, schema)
        assert not result.is_valid


class TestSanitizer:
    """Tests for input sanitization."""
    
    def test_sanitize_string(self):
        """Test basic string sanitization."""
        from src.security.sanitizer import Sanitizer
        
        sanitizer = Sanitizer()
        
        # HTML escaping
        result = sanitizer.sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result
    
    def test_sanitize_string_strip(self):
        """Test string stripping."""
        from src.security.sanitizer import Sanitizer
        
        sanitizer = Sanitizer()
        
        result = sanitizer.sanitize_string("  hello world  ")
        assert result == "hello world"
    
    def test_sanitize_string_length_limit(self):
        """Test string length limiting."""
        from src.security.sanitizer import Sanitizer
        
        sanitizer = Sanitizer(max_length=10)
        
        result = sanitizer.sanitize_string("a" * 20)
        assert len(result) <= 10
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        from src.security.sanitizer import Sanitizer
        
        sanitizer = Sanitizer()
        
        # Path traversal
        assert ".." not in sanitizer.sanitize_filename("../../../etc/passwd")
        
        # Special characters
        safe = sanitizer.sanitize_filename("file<>name.txt")
        assert "<" not in safe
        assert ">" not in safe
    
    def test_sanitize_path(self):
        """Test path sanitization."""
        from src.security.sanitizer import Sanitizer
        
        sanitizer = Sanitizer()
        
        # Path traversal prevention
        safe = sanitizer.sanitize_path("../../../etc/passwd", "/app/uploads")
        assert "../" not in safe
    
    def test_sanitize_sql_input(self):
        """Test SQL input sanitization."""
        from src.security.sanitizer import Sanitizer
        
        sanitizer = Sanitizer()
        
        # SQL injection characters
        result = sanitizer.sanitize_sql_input("value'; DROP TABLE users;--")
        assert "--" not in result
        assert "'" not in result or "''" in result
    
    def test_sanitize_dict(self):
        """Test dictionary sanitization."""
        from src.security.sanitizer import Sanitizer
        
        sanitizer = Sanitizer()
        
        data = {
            'name': '<script>alert("xss")</script>',
            'nested': {
                'value': '<b>bold</b>'
            }
        }
        
        result = sanitizer.sanitize_dict(data)
        
        assert '<script>' not in result['name']
        assert '<b>' not in result['nested']['value']
    
    def test_sanitize_list(self):
        """Test list sanitization."""
        from src.security.sanitizer import Sanitizer
        
        sanitizer = Sanitizer()
        
        data = ['<script>xss</script>', 'normal', '<b>bold</b>']
        
        result = sanitizer.sanitize_list(data)
        
        assert '<script>' not in result[0]
        assert result[1] == 'normal'
        assert '<b>' not in result[2]
    
    def test_strip_html(self):
        """Test HTML stripping."""
        from src.security.sanitizer import Sanitizer
        
        sanitizer = Sanitizer()
        
        html = "<p>Hello <b>World</b>!</p>"
        result = sanitizer.strip_html(html)
        
        assert result == "Hello World!"
    
    def test_global_sanitize_function(self):
        """Test global sanitize function."""
        from src.security.sanitizer import sanitize
        
        result = sanitize("<script>xss</script>")
        assert "<script>" not in result
        
        dict_result = sanitize({'key': '<b>value</b>'})
        assert '<b>' not in dict_result['key']
