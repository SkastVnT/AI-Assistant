"""
Input Validator
Secure input validation for API endpoints
"""

import re
import logging
from typing import Any, Dict, List, Optional, Callable, Type
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Validation error details."""
    field: str
    message: str
    value: Any = None


class ValidationResult:
    """Result of validation."""
    
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.sanitized_data: Dict[str, Any] = {}
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    def add_error(self, field: str, message: str, value: Any = None):
        self.errors.append(ValidationError(field, message, value))
    
    def to_dict(self) -> Dict:
        return {
            'valid': self.is_valid,
            'errors': [
                {'field': e.field, 'message': e.message}
                for e in self.errors
            ],
            'data': self.sanitized_data if self.is_valid else None
        }


class InputValidator:
    """
    Input validation with support for common patterns.
    """
    
    # Common regex patterns
    PATTERNS = {
        'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        'url': r'^https?://[^\s<>"{}|\\^`\[\]]+$',
        'uuid': r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        'alphanumeric': r'^[a-zA-Z0-9]+$',
        'alphanumeric_dash': r'^[a-zA-Z0-9_-]+$',
        'filename': r'^[a-zA-Z0-9._-]+$',
        'sql_safe': r'^[^;\'"\\]+$',  # No SQL injection chars
        'path_safe': r'^[a-zA-Z0-9._/-]+$',  # Safe path chars
    }
    
    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>',  # XSS
        r'javascript:',  # XSS
        r'on\w+\s*=',  # Event handlers
        r'(?:SELECT|INSERT|UPDATE|DELETE|DROP|UNION)\s',  # SQL
        r'(?:exec|system|passthru|shell_exec)\s*\(',  # Command injection
        r'\.\./|\.\.\\',  # Path traversal
    ]
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, reject any suspicious input
        """
        self.strict_mode = strict_mode
        self._compiled_dangerous = [
            re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_PATTERNS
        ]
    
    def validate(self, data: Dict[str, Any], 
                 schema: Dict[str, Dict]) -> ValidationResult:
        """
        Validate input data against schema.
        
        Args:
            data: Input data dictionary
            schema: Validation schema
        
        Returns:
            ValidationResult
        """
        result = ValidationResult()
        
        for field, rules in schema.items():
            value = data.get(field)
            
            # Required check
            if rules.get('required', False) and value is None:
                result.add_error(field, 'Field is required')
                continue
            
            if value is None:
                if 'default' in rules:
                    result.sanitized_data[field] = rules['default']
                continue
            
            # Type check
            expected_type = rules.get('type')
            if expected_type and not isinstance(value, expected_type):
                result.add_error(field, f'Expected type {expected_type.__name__}')
                continue
            
            # String validations
            if isinstance(value, str):
                # Min length
                if 'min_length' in rules and len(value) < rules['min_length']:
                    result.add_error(field, f"Minimum length is {rules['min_length']}")
                    continue
                
                # Max length
                if 'max_length' in rules and len(value) > rules['max_length']:
                    result.add_error(field, f"Maximum length is {rules['max_length']}")
                    continue
                
                # Pattern match
                if 'pattern' in rules:
                    pattern = rules['pattern']
                    if pattern in self.PATTERNS:
                        pattern = self.PATTERNS[pattern]
                    
                    if not re.match(pattern, value):
                        result.add_error(field, 'Invalid format')
                        continue
                
                # Dangerous content check
                if self._has_dangerous_content(value):
                    result.add_error(field, 'Contains potentially dangerous content')
                    continue
            
            # Number validations
            if isinstance(value, (int, float)):
                if 'min' in rules and value < rules['min']:
                    result.add_error(field, f"Minimum value is {rules['min']}")
                    continue
                
                if 'max' in rules and value > rules['max']:
                    result.add_error(field, f"Maximum value is {rules['max']}")
                    continue
            
            # List validations
            if isinstance(value, list):
                if 'min_items' in rules and len(value) < rules['min_items']:
                    result.add_error(field, f"Minimum items is {rules['min_items']}")
                    continue
                
                if 'max_items' in rules and len(value) > rules['max_items']:
                    result.add_error(field, f"Maximum items is {rules['max_items']}")
                    continue
            
            # Custom validator
            if 'validator' in rules:
                try:
                    if not rules['validator'](value):
                        result.add_error(field, rules.get('validator_message', 'Validation failed'))
                        continue
                except Exception as e:
                    result.add_error(field, f'Validation error: {str(e)}')
                    continue
            
            # Passed all validations
            result.sanitized_data[field] = value
        
        return result
    
    def _has_dangerous_content(self, value: str) -> bool:
        """Check for dangerous patterns."""
        for pattern in self._compiled_dangerous:
            if pattern.search(value):
                if self.strict_mode:
                    logger.warning(f"Dangerous content detected: {pattern.pattern}")
                return self.strict_mode
        return False
    
    def validate_email(self, email: str) -> bool:
        """Validate email format."""
        return bool(re.match(self.PATTERNS['email'], email))
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format."""
        return bool(re.match(self.PATTERNS['url'], url))
    
    def validate_filename(self, filename: str) -> bool:
        """Validate filename (prevent path traversal)."""
        if not filename:
            return False
        
        # Check for path traversal
        if '..' in filename or '/' in filename or '\\' in filename:
            return False
        
        return bool(re.match(self.PATTERNS['filename'], filename))


def validate_input(schema: Dict[str, Dict], strict: bool = False):
    """
    Decorator to validate Flask request input.
    
    Args:
        schema: Validation schema
        strict: Enable strict mode
    """
    validator = InputValidator(strict_mode=strict)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, jsonify
            
            # Get input data
            if request.is_json:
                data = request.get_json() or {}
            else:
                data = request.form.to_dict()
            
            # Validate
            result = validator.validate(data, schema)
            
            if not result.is_valid:
                return jsonify({
                    'error': 'Validation failed',
                    'details': result.to_dict()['errors']
                }), 400
            
            # Add sanitized data to request
            request.validated_data = result.sanitized_data
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator
