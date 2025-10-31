"""
Error handlers and exception management
Centralized error handling for the application
"""

from .error_handler import (
    VistralError,
    ModelError,
    AudioError,
    ConfigError,
    handle_error,
    log_error,
)

__all__ = [
    "VistralError",
    "ModelError", 
    "AudioError",
    "ConfigError",
    "handle_error",
    "log_error",
]
