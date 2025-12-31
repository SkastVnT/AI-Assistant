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


__all__ = ['create_app']
__version__ = '3.0.0'
