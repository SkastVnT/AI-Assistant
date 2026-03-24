"""
AI-Assistant Chatbot Application Package

This package contains the restructured chatbot service with:
- Modular architecture (routes, controllers, services, models)
- Clean separation of concerns
- Dependency injection ready
- Testable components
"""

from flask import Flask
from typing import Optional
import os

from core.config import SYSTEM_PROMPTS


def create_app(config_name: str = 'default') -> Flask:
    """
    Flask Application Factory
    
    Creates and configures the Flask application with:
    - Configuration loading
    - Blueprint registration
    - Extension initialization
    - Error handlers
    
    Args:
        config_name: Configuration environment ('development', 'production', 'testing')
    
    Returns:
        Configured Flask application instance
    """
    from .main import create_application
    return create_application(config_name)


# Backward-compatible module-level app for legacy tests/imports.
_default_config = 'testing' if os.getenv('TESTING', '').lower() == 'true' else 'default'
app = create_app(_default_config)


__all__ = ['create_app', 'app', 'SYSTEM_PROMPTS']
__version__ = '3.0.0'
