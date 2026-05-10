"""
Sanitizer
Input sanitization and output encoding
"""

import re
import html
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


class Sanitizer:
    """
    Input sanitization utilities.
    """
    
    # Characters to remove/escape
    SQL_CHARS = [';', '--', '/*', '*/', 'xp_', 'EXEC', 'EXECUTE']
    HTML_TAGS = re.compile(r'<[^>]+>')
    SCRIPT_PATTERN = re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
    
    def __init__(self, allow_html: bool = False, max_length: int = 10000):
        """
        Initialize sanitizer.
        
        Args:
            allow_html: Allow HTML tags (will still escape script tags)
            max_length: Maximum string length
        """
        self.allow_html = allow_html
        self.max_length = max_length
    
    def sanitize_string(self, value: str, 
                        strip: bool = True,
                        escape_html: bool = True) -> str:
        """
        Sanitize a string value.
        
        Args:
            value: String to sanitize
            strip: Strip whitespace
            escape_html: HTML escape the string
        
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Strip whitespace
        if strip:
            value = value.strip()
        
        # Limit length
        if len(value) > self.max_length:
            value = value[:self.max_length]
        
        # Remove script tags even if allowing HTML
        value = self.SCRIPT_PATTERN.sub('', value)
        
        # Escape HTML if not allowing it
        if escape_html and not self.allow_html:
            value = html.escape(value)
        
        return value
    
    def sanitize_sql_input(self, value: str) -> str:
        """
        Sanitize input for SQL queries (for display only, use parameterized queries for execution).
        
        Args:
            value: Input value
        
        Returns:
            Sanitized value
        """
        if not isinstance(value, str):
            return str(value)
        
        # Escape quotes
        value = value.replace("'", "''")
        value = value.replace('"', '""')
        
        # Remove dangerous patterns
        for char in self.SQL_CHARS:
            value = value.replace(char.lower(), '')
            value = value.replace(char.upper(), '')
        
        return value
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename for safe file operations.
        
        Args:
            filename: Original filename
        
        Returns:
            Safe filename
        """
        if not filename:
            return "unnamed"
        
        # Remove path separators
        filename = filename.replace('/', '_')
        filename = filename.replace('\\', '_')
        
        # Remove path traversal
        filename = filename.replace('..', '_')
        
        # Keep only safe characters
        safe = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        
        # Remove leading dots (hidden files)
        safe = safe.lstrip('.')
        
        # Ensure not empty
        if not safe:
            safe = "unnamed"
        
        # Limit length
        if len(safe) > 255:
            name, ext = safe.rsplit('.', 1) if '.' in safe else (safe, '')
            max_name = 255 - len(ext) - 1
            safe = f"{name[:max_name]}.{ext}" if ext else name[:255]
        
        return safe
    
    def sanitize_path(self, path: str, base_dir: str = None) -> str:
        """
        Sanitize file path to prevent directory traversal.
        
        Args:
            path: Input path
            base_dir: Base directory to constrain to
        
        Returns:
            Safe path
        """
        import os
        
        # Normalize path
        path = os.path.normpath(path)
        
        # Remove leading slashes
        path = path.lstrip('/\\')
        
        # Remove drive letter on Windows
        if len(path) > 1 and path[1] == ':':
            path = path[2:].lstrip('/\\')
        
        # Remove path traversal
        parts = []
        for part in path.split(os.sep):
            if part == '..':
                continue  # Skip parent refs
            if part == '.':
                continue  # Skip current refs
            if part:
                parts.append(self.sanitize_filename(part))
        
        safe_path = os.sep.join(parts)
        
        # Constrain to base directory if specified
        if base_dir:
            full_path = os.path.normpath(os.path.join(base_dir, safe_path))
            if not full_path.startswith(os.path.normpath(base_dir)):
                logger.warning(f"Path traversal attempt: {path}")
                return ""
            return full_path
        
        return safe_path
    
    def sanitize_dict(self, data: Dict[str, Any], 
                      deep: bool = True) -> Dict[str, Any]:
        """
        Sanitize all string values in a dictionary.
        
        Args:
            data: Input dictionary
            deep: Recursively sanitize nested dicts/lists
        
        Returns:
            Sanitized dictionary
        """
        result = {}
        
        for key, value in data.items():
            # Sanitize key
            safe_key = self.sanitize_string(str(key), escape_html=False)
            
            # Sanitize value
            if isinstance(value, str):
                result[safe_key] = self.sanitize_string(value)
            elif isinstance(value, dict) and deep:
                result[safe_key] = self.sanitize_dict(value, deep=True)
            elif isinstance(value, list) and deep:
                result[safe_key] = self.sanitize_list(value, deep=True)
            else:
                result[safe_key] = value
        
        return result
    
    def sanitize_list(self, data: List[Any], 
                      deep: bool = True) -> List[Any]:
        """
        Sanitize all string values in a list.
        
        Args:
            data: Input list
            deep: Recursively sanitize nested dicts/lists
        
        Returns:
            Sanitized list
        """
        result = []
        
        for item in data:
            if isinstance(item, str):
                result.append(self.sanitize_string(item))
            elif isinstance(item, dict) and deep:
                result.append(self.sanitize_dict(item, deep=True))
            elif isinstance(item, list) and deep:
                result.append(self.sanitize_list(item, deep=True))
            else:
                result.append(item)
        
        return result
    
    def strip_html(self, value: str) -> str:
        """Remove all HTML tags from string."""
        return self.HTML_TAGS.sub('', value)


# Global sanitizer instance
_sanitizer = None


def get_sanitizer() -> Sanitizer:
    """Get global sanitizer."""
    global _sanitizer
    if _sanitizer is None:
        _sanitizer = Sanitizer()
    return _sanitizer


def sanitize(value: Any, **kwargs) -> Any:
    """
    Sanitize value using global sanitizer.
    
    Args:
        value: Value to sanitize
        **kwargs: Options for sanitize_string
    
    Returns:
        Sanitized value
    """
    sanitizer = get_sanitizer()
    
    if isinstance(value, str):
        return sanitizer.sanitize_string(value, **kwargs)
    elif isinstance(value, dict):
        return sanitizer.sanitize_dict(value)
    elif isinstance(value, list):
        return sanitizer.sanitize_list(value)
    
    return value
