"""
Cache Manager for RAG Services
Supports in-memory caching with optional Redis backend
Improves performance by caching embeddings and search results
"""
import hashlib
import json
import time
from typing import Any, Optional, Dict, List
from functools import wraps
import logging

logger = logging.getLogger(__name__)

# Try to import Redis (optional dependency)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache only")


class CacheManager:
    """
    Unified cache manager with fallback support
    - Redis for distributed caching (production)
    - In-memory dict for development
    """
    
    def __init__(
        self,
        use_redis: bool = False,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None,
        default_ttl: int = 3600,  # 1 hour
        max_memory_items: int = 1000
    ):
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.default_ttl = default_ttl
        self.max_memory_items = max_memory_items
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'errors': 0
        }
        
        # Initialize Redis client
        self.redis_client = None
        if self.use_redis:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=False,  # We'll handle encoding
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Test connection
                self.redis_client.ping()
                logger.info(f"✅ Redis cache connected: {redis_host}:{redis_port}")
            except Exception as e:
                logger.warning(f"⚠️  Redis connection failed: {e}, falling back to in-memory cache")
                self.use_redis = False
                self.redis_client = None
        
        # In-memory cache (always available as fallback)
        self._memory_cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        
        logger.info(f"Cache initialized: {'Redis' if self.use_redis else 'In-Memory'} mode")
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from prefix and arguments"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"rag:{prefix}:{key_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            # Try Redis first
            if self.use_redis and self.redis_client:
                value = self.redis_client.get(key)
                if value is not None:
                    self.stats['hits'] += 1
                    return json.loads(value.decode('utf-8'))
            
            # Fallback to memory cache
            if key in self._memory_cache:
                value, expiry = self._memory_cache[key]
                # Check if expired
                if expiry is None or time.time() < expiry:
                    self.stats['hits'] += 1
                    return value
                else:
                    # Expired, remove it
                    del self._memory_cache[key]
            
            self.stats['misses'] += 1
            return None
            
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            self.stats['errors'] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL"""
        try:
            ttl = ttl or self.default_ttl
            
            # Store in Redis
            if self.use_redis and self.redis_client:
                serialized = json.dumps(value)
                self.redis_client.setex(key, ttl, serialized)
            
            # Always store in memory as backup
            expiry = time.time() + ttl if ttl else None
            self._memory_cache[key] = (value, expiry)
            
            # Limit memory cache size (LRU-style)
            if len(self._memory_cache) > self.max_memory_items:
                # Remove oldest entries
                sorted_items = sorted(
                    self._memory_cache.items(),
                    key=lambda x: x[1][1] if x[1][1] else float('inf')
                )
                for old_key, _ in sorted_items[:100]:  # Remove 100 oldest
                    del self._memory_cache[old_key]
            
            self.stats['sets'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            self.stats['errors'] += 1
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            # Delete from Redis
            if self.use_redis and self.redis_client:
                self.redis_client.delete(key)
            
            # Delete from memory
            if key in self._memory_cache:
                del self._memory_cache[key]
            
            self.stats['deletes'] += 1
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            self.stats['errors'] += 1
            return False
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache (all keys or by pattern)"""
        try:
            count = 0
            
            # Clear Redis
            if self.use_redis and self.redis_client:
                if pattern:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        count = self.redis_client.delete(*keys)
                else:
                    self.redis_client.flushdb()
                    count = len(self._memory_cache)
            
            # Clear memory cache
            if pattern:
                keys_to_delete = [k for k in self._memory_cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                count = max(count, len(keys_to_delete))
            else:
                count = max(count, len(self._memory_cache))
                self._memory_cache.clear()
            
            logger.info(f"Cleared {count} cache entries (pattern: {pattern or 'all'})")
            return count
            
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            self.stats['errors'] += 1
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'backend': 'redis' if self.use_redis else 'memory',
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'hit_rate': round(hit_rate, 2),
            'sets': self.stats['sets'],
            'deletes': self.stats['deletes'],
            'errors': self.stats['errors'],
            'memory_items': len(self._memory_cache),
            'redis_connected': self.redis_client is not None if self.use_redis else False
        }
    
    def cached(self, prefix: str, ttl: Optional[int] = None):
        """
        Decorator for caching function results
        
        Usage:
            @cache_manager.cached('embedding', ttl=3600)
            def get_embedding(text):
                return model.encode(text)
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self._generate_key(prefix, *args, **kwargs)
                
                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache HIT: {prefix}")
                    return cached_value
                
                # Cache miss, call function
                logger.debug(f"Cache MISS: {prefix}")
                result = func(*args, **kwargs)
                
                # Store in cache
                self.set(cache_key, result, ttl)
                
                return result
            
            return wrapper
        return decorator


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager(
    use_redis: bool = False,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_password: Optional[str] = None,
    **kwargs
) -> CacheManager:
    """Get or create global cache manager"""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager(
            use_redis=use_redis,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_password=redis_password,
            **kwargs
        )
    
    return _cache_manager


def clear_cache(pattern: Optional[str] = None) -> int:
    """Clear cache (convenience function)"""
    cache = get_cache_manager()
    return cache.clear(pattern)


# Specialized cache decorators for common use cases

def cache_embedding(ttl: int = 86400):  # 24 hours
    """Cache embedding results"""
    cache = get_cache_manager()
    return cache.cached('embedding', ttl=ttl)


def cache_search(ttl: int = 3600):  # 1 hour
    """Cache search results"""
    cache = get_cache_manager()
    return cache.cached('search', ttl=ttl)


def cache_rag_response(ttl: int = 1800):  # 30 minutes
    """Cache RAG responses"""
    cache = get_cache_manager()
    return cache.cached('rag', ttl=ttl)
