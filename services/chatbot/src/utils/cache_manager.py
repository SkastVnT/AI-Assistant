"""
Redis Cache Manager - Performance Optimization
Implements intelligent caching for AI responses, API calls, and static data
"""

import redis
import json
import hashlib
import logging
from datetime import timedelta
from typing import Optional, Any, Dict
from functools import wraps
import os

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Intelligent caching system using Redis
    
    Features:
    - Response caching for AI models
    - API call deduplication
    - Session data caching
    - Automatic cache invalidation
    """
    
    def __init__(self, redis_url: str = None):
        """
        Initialize Redis connection
        
        Args:
            redis_url: Redis connection URL (default: from env or localhost)
        """
        self.redis_url = redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"✅ Redis connected: {self.redis_url}")
        except Exception as e:
            logger.warning(f"⚠️ Redis unavailable: {e}. Caching disabled.")
            self.redis_client = None
            self.enabled = False
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate cache key from arguments
        
        Args:
            prefix: Key prefix (e.g., 'chat', 'sd_model', 'session')
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            str: Unique cache key
        """
        # Create unique hash from arguments
        key_data = {
            'args': args,
            'kwargs': kwargs
        }
        key_json = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()[:16]
        
        return f"{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None
        """
        if not self.enabled:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"🎯 Cache HIT: {key}")
                return json.loads(value)
            else:
                logger.debug(f"❌ Cache MISS: {key}")
                return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
        
        Returns:
            bool: Success status
        """
        if not self.enabled:
            return False
        
        try:
            value_json = json.dumps(value)
            self.redis_client.setex(key, ttl, value_json)
            logger.debug(f"💾 Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False
        
        try:
            self.redis_client.delete(key)
            logger.debug(f"🗑️ Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern
        
        Args:
            pattern: Key pattern (e.g., 'chat:*', 'session:user123:*')
        
        Returns:
            int: Number of keys deleted
        """
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"🗑️ Cache DELETE pattern '{pattern}': {deleted} keys")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error: {e}")
            return 0
    
    def cache_response(self, ttl: int = 3600):
        """
        Decorator to cache function responses
        
        Usage:
            @cache_manager.cache_response(ttl=1800)
            def expensive_function(arg1, arg2):
                return result
        
        Args:
            ttl: Time to live in seconds
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_key(func.__name__, *args, **kwargs)
                
                # Try to get from cache
                cached = self.get(cache_key)
                if cached is not None:
                    return cached
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Cache result
                self.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator
    
    # ============================================================================
    # SPECIALIZED CACHE METHODS
    # ============================================================================
    
    def cache_ai_response(
        self,
        model: str,
        message: str,
        context: str,
        response: str,
        ttl: int = 3600
    ) -> bool:
        """
        Cache AI model response
        
        Args:
            model: Model name (gemini, gpt-4, etc.)
            message: User message
            context: Context mode
            response: AI response
            ttl: Cache duration (default: 1 hour)
        
        Returns:
            bool: Success status
        """
        key = self._generate_key('ai_response', model, message, context)
        return self.set(key, response, ttl)
    
    def get_ai_response(self, model: str, message: str, context: str) -> Optional[str]:
        """Get cached AI response"""
        key = self._generate_key('ai_response', model, message, context)
        return self.get(key)
    
    def cache_sd_models(self, models: list, ttl: int = 600) -> bool:
        """
        Cache Stable Diffusion model list
        
        Args:
            models: List of models
            ttl: Cache duration (default: 10 minutes)
        """
        return self.set('sd_models', models, ttl)
    
    def get_sd_models(self) -> Optional[list]:
        """Get cached SD models"""
        return self.get('sd_models')
    
    def cache_session_history(
        self,
        session_id: str,
        history: list,
        ttl: int = 1800
    ) -> bool:
        """
        Cache conversation history
        
        Args:
            session_id: Session ID
            history: Conversation history
            ttl: Cache duration (default: 30 minutes)
        """
        key = f"session:{session_id}:history"
        return self.set(key, history, ttl)
    
    def get_session_history(self, session_id: str) -> Optional[list]:
        """Get cached session history"""
        key = f"session:{session_id}:history"
        return self.get(key)
    
    def invalidate_session(self, session_id: str) -> int:
        """Invalidate all cache for a session"""
        pattern = f"session:{session_id}:*"
        return self.delete_pattern(pattern)
    
    def cache_file_analysis(
        self,
        file_hash: str,
        analysis: Dict,
        ttl: int = 7200
    ) -> bool:
        """
        Cache file analysis results
        
        Args:
            file_hash: File content hash
            analysis: Analysis result
            ttl: Cache duration (default: 2 hours)
        """
        key = f"file_analysis:{file_hash}"
        return self.set(key, analysis, ttl)
    
    def get_file_analysis(self, file_hash: str) -> Optional[Dict]:
        """Get cached file analysis"""
        key = f"file_analysis:{file_hash}"
        return self.get(key)
    
    # ============================================================================
    # STATISTICS & MONITORING
    # ============================================================================
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dict with cache stats (hits, misses, size, etc.)
        """
        if not self.enabled:
            return {
                'enabled': False,
                'message': 'Redis not available'
            }
        
        try:
            info = self.redis_client.info('stats')
            memory = self.redis_client.info('memory')
            
            return {
                'enabled': True,
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(info),
                'memory_used': memory.get('used_memory_human', 'N/A'),
                'total_keys': self.redis_client.dbsize(),
                'connected_clients': info.get('connected_clients', 0)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'enabled': True, 'error': str(e)}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        """Calculate cache hit rate percentage"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
        
        return round((hits / total) * 100, 2)
    
    def clear_all(self) -> bool:
        """Clear all cache (use with caution!)"""
        if not self.enabled:
            return False
        
        try:
            self.redis_client.flushdb()
            logger.warning("🗑️ All cache cleared!")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False


# ============================================================================
# GLOBAL CACHE INSTANCE
# ============================================================================

# Singleton instance
_cache_instance = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = CacheManager()
    
    return _cache_instance


# Convenience decorator
def cached(ttl: int = 3600):
    """
    Convenience decorator for caching
    
    Usage:
        @cached(ttl=1800)
        def my_function(arg):
            return result
    """
    cache = get_cache_manager()
    return cache.cache_response(ttl)
