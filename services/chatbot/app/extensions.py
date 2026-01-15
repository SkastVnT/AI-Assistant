"""
Flask Extensions Initialization

Centralized extension management for:
- Database connections (MongoDB)
- Cache (Redis)
- Rate limiting
- Other Flask extensions
"""

import logging
from flask import Flask
from typing import Optional

logger = logging.getLogger(__name__)

# Extension instances (initialized lazily)
_mongodb_client = None
_redis_client = None
_cache_manager = None


def init_extensions(app: Flask) -> None:
    """
    Initialize all Flask extensions
    
    Args:
        app: Flask application instance
    """
    init_mongodb(app)
    init_redis(app)
    init_cache(app)
    logger.info("✅ All extensions initialized")


def init_mongodb(app: Flask) -> None:
    """Initialize MongoDB connection"""
    global _mongodb_client
    
    if not app.config.get('MONGODB_ENABLED', False):
        logger.info("ℹ️ MongoDB disabled by configuration")
        return
    
    try:
        from pymongo import MongoClient
        
        uri = app.config.get('MONGODB_URI')
        _mongodb_client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        _mongodb_client.admin.command('ping')
        
        app.extensions['mongodb'] = _mongodb_client
        logger.info("✅ MongoDB connected successfully")
        
    except Exception as e:
        logger.warning(f"⚠️ MongoDB connection failed: {e}")
        app.config['MONGODB_ENABLED'] = False


def init_redis(app: Flask) -> None:
    """Initialize Redis connection"""
    global _redis_client
    
    if not app.config.get('CACHE_ENABLED', False):
        logger.info("ℹ️ Redis cache disabled by configuration")
        return
    
    try:
        import redis
        
        url = app.config.get('REDIS_URL')
        _redis_client = redis.from_url(url, decode_responses=True)
        
        # Test connection
        _redis_client.ping()
        
        app.extensions['redis'] = _redis_client
        logger.info("✅ Redis connected successfully")
        
    except Exception as e:
        logger.warning(f"⚠️ Redis connection failed: {e}")
        app.config['CACHE_ENABLED'] = False


def init_cache(app: Flask) -> None:
    """Initialize cache manager"""
    global _cache_manager
    
    if not app.config.get('CACHE_ENABLED', False):
        return
    
    try:
        from .services.cache_service import CacheService
        _cache_manager = CacheService(app)
        app.extensions['cache'] = _cache_manager
        logger.info("✅ Cache manager initialized")
    except ImportError:
        logger.info("ℹ️ Cache service not available")


def get_mongodb():
    """Get MongoDB client instance"""
    return _mongodb_client


def get_redis():
    """Get Redis client instance"""
    return _redis_client


def get_cache():
    """Get cache manager instance"""
    return _cache_manager
