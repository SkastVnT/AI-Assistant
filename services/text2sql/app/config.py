"""
Text2SQL Configuration
Environment-based configuration management
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent.parent.parent / '.env'
load_dotenv(env_path)


class BaseConfig:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'text2sql-secret-key-change-in-production')
    DEBUG = False
    TESTING = False
    
    # Server
    HOST = os.getenv('TEXT2SQL_HOST', '0.0.0.0')
    PORT = int(os.getenv('TEXT2SQL_PORT', 5002))
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Upload
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'txt', 'json', 'jsonl', 'csv', 'sql'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Directories
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / 'data'
    PRETRAIN_DIR = BASE_DIR / 'pretrain'
    KNOWLEDGE_BASE_DIR = BASE_DIR / 'knowledge_base'
    MEMORY_DIR = KNOWLEDGE_BASE_DIR / 'memory'
    SAMPLE_DIR = BASE_DIR / 'sample'
    
    # Dataset files
    DATASET_FILE = DATA_DIR / 'dataset_base.jsonl'
    EVAL_FILE = DATA_DIR / 'eval.jsonl'
    
    # AI Models Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GROK_API_KEY = os.getenv('GROK_API_KEY')
    GROK_API_BASE = 'https://api.x.ai/v1'
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
    DEEPSEEK_API_BASE = 'https://api.deepseek.com'
    
    # Default model
    DEFAULT_SQL_MODEL = os.getenv('DEFAULT_SQL_MODEL', 'grok')
    REFINE_STRATEGY = os.getenv('REFINE_STRATEGY', 'gemini').lower()
    
    # SQLCoder
    SQLCODER_BACKEND = os.getenv('SQLCODER_BACKEND', 'hf').lower()
    SQLCODER_MODEL = os.getenv('SQLCODER_MODEL', 'defog/sqlcoder-7b-2')
    SQLCODER_REQUIRE_KNOWN_TABLE = os.getenv('SQLCODER_REQUIRE_KNOWN_TABLE', '1') == '1'
    
    # ClickHouse
    CLICKHOUSE_HOST = os.getenv('CLICKHOUSE_HOST', 'localhost')
    CLICKHOUSE_PORT = int(os.getenv('CLICKHOUSE_PORT', 8123))
    CLICKHOUSE_USER = os.getenv('CLICKHOUSE_USER', 'default')
    CLICKHOUSE_PASSWORD = os.getenv('CLICKHOUSE_PASSWORD', '')
    CLICKHOUSE_DATABASE = os.getenv('CLICKHOUSE_DATABASE', 'default')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/text2sql.log')


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
