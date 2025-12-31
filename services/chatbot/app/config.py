"""
Application Configuration

Centralized configuration management with environment-based settings.
"""

import os
from pathlib import Path
from typing import Dict, Any


class BaseConfig:
    """Base configuration shared by all environments"""
    
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/ai_assistant')
    MONGODB_ENABLED = os.getenv('MONGODB_ENABLED', 'true').lower() == 'true'
    
    # Redis Cache
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
    
    # AI API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    GROK_API_KEY = os.getenv('GROK_API_KEY')
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY_1')
    QWEN_API_KEY = os.getenv('QWEN_API_KEY')
    
    # File Storage
    STORAGE_PATH = Path(__file__).parent.parent / 'Storage'
    DATA_PATH = Path(__file__).parent.parent / 'data'
    LOCAL_DATA_PATH = Path(__file__).parent.parent / 'local_data'
    
    # Rate Limiting
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_DEFAULT = "100/hour"
    
    # Self-Learning
    LEARNING_ENABLED = os.getenv('LEARNING_ENABLED', 'true').lower() == 'true'
    LEARNING_MIN_QUALITY = float(os.getenv('LEARNING_MIN_QUALITY', '0.7'))
    
    # Default AI Model
    DEFAULT_MODEL = os.getenv('DEFAULT_AI_MODEL', 'grok')


class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Stricter security in production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    

class TestingConfig(BaseConfig):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    MONGODB_ENABLED = False
    CACHE_ENABLED = False
    LEARNING_ENABLED = False
    
    # Use in-memory or mock databases
    MONGODB_URI = 'mongodb://localhost:27017/ai_assistant_test'


# Configuration registry
_configs = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(name: str = 'default') -> BaseConfig:
    """
    Get configuration by name
    
    Args:
        name: Configuration name ('development', 'production', 'testing')
    
    Returns:
        Configuration class
    """
    env_name = os.getenv('FLASK_ENV', name)
    return _configs.get(env_name, DevelopmentConfig)
