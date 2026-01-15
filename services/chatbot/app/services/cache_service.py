"""
Cache Service

Handles caching for improved performance.
"""

import logging
import hashlib
from typing import Any, Optional
from flask import Flask

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching responses"""
    
    def __init__(self, app: Flask = None):
        self._cache: dict = {}
        self._enabled = True
        self._redis_client = None
        
        if app:
            self._enabled = app.config.get('CACHE_ENABLED', True)
            # Get redis client once during initialization to avoid cyclic import
            try:
                from ..extensions import get_redis
                self._redis_client = get_redis()
            except (ImportError, Exception):
                pass
    
    def get(self, key: str) -> Optional[Any]:
        """Get a cached value"""
        if not self._enabled:
            return None
        
        try:
            if self._redis_client:
                value = self._redis_client.get(key)
                return value
            else:
                return self._cache.get(key)
                
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
            return self._cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a cached value"""
        if not self._enabled:
            return False
        
        try:
            if self._redis_client:
                self._redis_client.setex(key, ttl, value)
            else:
                self._cache[key] = value
            
            return True
            
        except Exception as e:
            logger.debug(f"Cache set error: {e}")
            self._cache[key] = value
            return True
    
    def delete(self, key: str) -> bool:
        """Delete a cached value"""
        try:
            if self._redis_client:
                self._redis_client.delete(key)
            elif key in self._cache:
                del self._cache[key]
            
            return True
            
        except Exception as e:
            logger.debug(f"Cache delete error: {e}")
            return False
    
    def clear(self) -> bool:
        """Clear all cached values"""
        try:
            if self._redis_client:
                self._redis_client.flushdb()
            else:
                self._cache.clear()
            
            return True
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """Generate a cache key from arguments"""
        content = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(content.encode()).hexdigest()
