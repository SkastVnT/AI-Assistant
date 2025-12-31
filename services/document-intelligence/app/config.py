"""
Document Intelligence Configuration
Environment-based configuration management
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class BaseConfig:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'doc-intel-secret-key')
    DEBUG = False
    TESTING = False
    
    # Server
    HOST = os.getenv('DOC_INTEL_HOST', '0.0.0.0')
    PORT = int(os.getenv('DOC_INTEL_PORT', 5003))
    
    # Directories
    BASE_DIR = Path(__file__).parent.parent
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    OUTPUT_FOLDER = BASE_DIR / 'output'
    
    # File handling
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'pdf', 'webp'}
    
    # OCR Configuration
    OCR_LANGUAGE = os.getenv('OCR_LANGUAGE', 'vi')
    OCR_USE_GPU = os.getenv('OCR_USE_GPU', 'false').lower() == 'true'
    OCR_SHOW_LOG = os.getenv('OCR_SHOW_LOG', 'false').lower() == 'true'
    
    # AI Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    ENABLE_AI_ENHANCEMENT = os.getenv('ENABLE_AI_ENHANCEMENT', 'true').lower() == 'true'
    AI_MODEL = os.getenv('AI_MODEL', 'gemini-2.0-flash')
    
    # AI Features
    AI_FEATURES = {
        'classification': True,
        'extraction': True,
        'summarization': True,
        'translation': True,
        'qa': True
    }
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/doc-intel.log')


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = 'WARNING'


class TestingConfig(BaseConfig):
    """Testing configuration."""
    TESTING = True
    DEBUG = True


def get_config(config_name: str = None) -> BaseConfig:
    """Get configuration based on environment."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    return configs.get(config_name, DevelopmentConfig)()


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in BaseConfig.ALLOWED_EXTENSIONS
