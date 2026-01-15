"""
Text2SQL Extensions
Initialize and manage external connections
"""

import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# ClickHouse client
_ch_client = None

# AI Clients
_gemini_client = None
_openai_client = None


def init_extensions(app):
    """Initialize all extensions with Flask app context."""
    # Create required directories
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(app.config.get('PRETRAIN_DIR', 'pretrain'), exist_ok=True)
    os.makedirs(app.config.get('MEMORY_DIR', 'knowledge_base/memory'), exist_ok=True)
    os.makedirs(os.path.join('sample', 'uploading'), exist_ok=True)
    os.makedirs(os.path.join('sample', 'uploaded'), exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Initialize AI clients
    _init_gemini_client(app.config.get('GEMINI_API_KEY'))
    _init_openai_client(app.config.get('OPENAI_API_KEY'))
    
    # Log configuration status
    _log_config_status(app.config)


def _init_gemini_client(api_key: str) -> None:
    """Initialize Gemini client."""
    global _gemini_client
    if api_key:
        try:
            from google import genai
            _gemini_client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")


def _init_openai_client(api_key: str) -> None:
    """Initialize OpenAI client."""
    global _openai_client
    if api_key:
        try:
            import openai
            _openai_client = openai.OpenAI(api_key=api_key)
            logger.info("OpenAI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")


def get_gemini_client():
    """Get Gemini client instance."""
    return _gemini_client


def get_openai_client():
    """Get OpenAI client instance."""
    return _openai_client


def get_clickhouse_client():
    """Get or create ClickHouse client."""
    global _ch_client
    
    if _ch_client is not None:
        return _ch_client
    
    try:
        from clickhouse_connect import get_client
        from flask import current_app
        
        _ch_client = get_client(
            host=current_app.config.get('CLICKHOUSE_HOST', 'localhost'),
            port=current_app.config.get('CLICKHOUSE_PORT', 8123),
            username=current_app.config.get('CLICKHOUSE_USER', 'default'),
            password=current_app.config.get('CLICKHOUSE_PASSWORD', ''),
            database=current_app.config.get('CLICKHOUSE_DATABASE', 'default')
        )
        logger.info("ClickHouse client connected successfully")
        return _ch_client
    except Exception as e:
        logger.warning(f"ClickHouse connection failed: {e}")
        return None


def _log_config_status(config: dict) -> None:
    """Log API configuration status."""
    print(f"[CONFIG] GROK_API_KEY: {'✓ Loaded' if config.get('GROK_API_KEY') else '✗ Missing'}")
    print(f"[CONFIG] OPENAI_API_KEY: {'✓ Loaded' if config.get('OPENAI_API_KEY') else '✗ Missing'}")
    print(f"[CONFIG] DEEPSEEK_API_KEY: {'✓ Loaded' if config.get('DEEPSEEK_API_KEY') else '✗ Missing'}")
    print(f"[CONFIG] GEMINI_API_KEY: {'✓ Loaded' if config.get('GEMINI_API_KEY') else '✗ Missing'}")
    print(f"[CONFIG] DEFAULT_MODEL: {config.get('DEFAULT_SQL_MODEL', 'grok')}")
