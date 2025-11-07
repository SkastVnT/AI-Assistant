"""
Redis caching layer for ChatBot database operations.

Provides decorators and utilities for caching frequently accessed data:
- User information
- Conversations
- Messages
- Memories
- File metadata

Features:
- TTL-based expiration
- Cache invalidation on updates
- Automatic serialization/deserialization
- Cache warming on startup
"""

import json
import hashlib
import logging
from functools import wraps
from typing import Any, Callable, Optional, Union, Dict, List
from datetime import timedelta

import redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


# ============================================================
# REDIS CLIENT
# ============================================================

class RedisCache:
    """Redis cache manager with automatic connection handling"""
    
    def __init__(
        self,
        host: str = 'localhost',
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        decode_responses: bool = True,
        max_connections: int = 50,
        socket_timeout: int = 5,
        socket_connect_timeout: int = 5
    ):
        """
        Initialize Redis connection pool
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (if required)
            decode_responses: Decode bytes to strings
            max_connections: Maximum connections in pool
            socket_timeout: Socket timeout in seconds
            socket_connect_timeout: Connection timeout in seconds
        """
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses,
            max_connections=max_connections,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_connect_timeout
        )
        self.client = redis.Redis(connection_pool=self.pool)
        self._test_connection()
    
    def _test_connection(self):
        """Test Redis connection"""
        try:
            self.client.ping()
            logger.info("✅ Redis connection successful")
        except RedisError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        try:
            return self.client.get(key)
        except RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None
    
    def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to store
            ex: Expiration time in seconds
            px: Expiration time in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
        
        Returns:
            True if successful
        """
        try:
            return self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
        except RedisError as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False
    
    def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        try:
            return self.client.delete(*keys)
        except RedisError as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0
    
    def exists(self, *keys: str) -> int:
        """Check if keys exist"""
        try:
            return self.client.exists(*keys)
        except RedisError as e:
            logger.error(f"Redis EXISTS error: {e}")
            return 0
    
    def expire(self, key: str, time: int) -> bool:
        """Set expiration time for key"""
        try:
            return self.client.expire(key, time)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key '{key}': {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """Get time to live for key"""
        try:
            return self.client.ttl(key)
        except RedisError as e:
            logger.error(f"Redis TTL error for key '{key}': {e}")
            return -2
    
    def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"Redis FLUSH_PATTERN error for pattern '{pattern}': {e}")
            return 0
    
    def flush_all(self) -> bool:
        """Flush all keys in current database"""
        try:
            return self.client.flushdb()
        except RedisError as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            return False


# ============================================================
# CACHE KEY GENERATORS
# ============================================================

def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate cache key from prefix and arguments
    
    Args:
        prefix: Key prefix (e.g., 'user', 'conversation')
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        Cache key string
    """
    parts = [prefix]
    
    # Add positional args
    for arg in args:
        parts.append(str(arg))
    
    # Add keyword args (sorted for consistency)
    for key in sorted(kwargs.keys()):
        parts.append(f"{key}:{kwargs[key]}")
    
    return ":".join(parts)


def hash_query(query: str) -> str:
    """Generate hash for search queries"""
    return hashlib.md5(query.encode()).hexdigest()[:16]


# ============================================================
# CACHE DECORATORS
# ============================================================

def cached(
    key_prefix: str,
    ttl: int = 3600,
    key_builder: Optional[Callable] = None
):
    """
    Cache decorator for functions
    
    Args:
        key_prefix: Cache key prefix
        ttl: Time to live in seconds
        key_builder: Custom key builder function
    
    Usage:
        @cached(key_prefix='user', ttl=3600)
        def get_user(user_id: int):
            return fetch_user_from_db(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = generate_cache_key(key_prefix, *args, **kwargs)
            
            # Try to get from cache
            try:
                cached_value = cache_client.get(cache_key)
                if cached_value:
                    logger.debug(f"Cache HIT: {cache_key}")
                    return json.loads(cached_value)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
            
            # Cache miss - execute function
            logger.debug(f"Cache MISS: {cache_key}")
            result = func(*args, **kwargs)
            
            # Store in cache
            try:
                if result is not None:
                    cache_client.set(
                        cache_key,
                        json.dumps(result, default=str),
                        ex=ttl
                    )
            except Exception as e:
                logger.warning(f"Cache write error: {e}")
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(key_prefix: str, *args, **kwargs):
    """
    Invalidate cache for specific key
    
    Args:
        key_prefix: Cache key prefix
        *args: Positional arguments for key generation
        **kwargs: Keyword arguments for key generation
    """
    cache_key = generate_cache_key(key_prefix, *args, **kwargs)
    try:
        cache_client.delete(cache_key)
        logger.debug(f"Cache INVALIDATED: {cache_key}")
    except Exception as e:
        logger.warning(f"Cache invalidation error: {e}")


def invalidate_pattern(pattern: str):
    """
    Invalidate all keys matching pattern
    
    Args:
        pattern: Redis key pattern (e.g., 'user:*', 'conversation:123:*')
    """
    try:
        deleted = cache_client.flush_pattern(pattern)
        logger.debug(f"Cache INVALIDATED pattern '{pattern}': {deleted} keys")
    except Exception as e:
        logger.warning(f"Cache pattern invalidation error: {e}")


# ============================================================
# DOMAIN-SPECIFIC CACHE UTILITIES
# ============================================================

class UserCache:
    """Cache utilities for user data"""
    
    @staticmethod
    def get_user_key(user_id: int) -> str:
        return f"user:{user_id}"
    
    @staticmethod
    def get_username_key(username: str) -> str:
        return f"username:{username}"
    
    @staticmethod
    def cache_user(user_data: Dict[str, Any], ttl: int = 3600):
        """Cache user data by ID and username"""
        user_id = user_data.get('id')
        username = user_data.get('username')
        
        if user_id:
            key = UserCache.get_user_key(user_id)
            cache_client.set(key, json.dumps(user_data, default=str), ex=ttl)
        
        if username:
            key = UserCache.get_username_key(username)
            cache_client.set(key, json.dumps(user_data, default=str), ex=ttl)
    
    @staticmethod
    def invalidate_user(user_id: int, username: Optional[str] = None):
        """Invalidate user cache"""
        keys = [UserCache.get_user_key(user_id)]
        if username:
            keys.append(UserCache.get_username_key(username))
        cache_client.delete(*keys)


class ConversationCache:
    """Cache utilities for conversation data"""
    
    @staticmethod
    def get_conversation_key(conversation_id: int) -> str:
        return f"conversation:{conversation_id}"
    
    @staticmethod
    def get_user_conversations_key(user_id: int, page: int = 1) -> str:
        return f"user:{user_id}:conversations:page:{page}"
    
    @staticmethod
    def cache_conversation(conv_data: Dict[str, Any], ttl: int = 1800):
        """Cache conversation data"""
        conv_id = conv_data.get('id')
        if conv_id:
            key = ConversationCache.get_conversation_key(conv_id)
            cache_client.set(key, json.dumps(conv_data, default=str), ex=ttl)
    
    @staticmethod
    def invalidate_conversation(conversation_id: int, user_id: Optional[int] = None):
        """Invalidate conversation cache"""
        # Invalidate specific conversation
        cache_client.delete(ConversationCache.get_conversation_key(conversation_id))
        
        # Invalidate user's conversation list
        if user_id:
            invalidate_pattern(f"user:{user_id}:conversations:*")


class MessageCache:
    """Cache utilities for message data"""
    
    @staticmethod
    def get_messages_key(conversation_id: int, limit: int = 50) -> str:
        return f"conversation:{conversation_id}:messages:limit:{limit}"
    
    @staticmethod
    def invalidate_messages(conversation_id: int):
        """Invalidate all message caches for conversation"""
        invalidate_pattern(f"conversation:{conversation_id}:messages:*")


class MemoryCache:
    """Cache utilities for memory data"""
    
    @staticmethod
    def get_memories_key(user_id: int, limit: int = 100) -> str:
        return f"user:{user_id}:memories:limit:{limit}"
    
    @staticmethod
    def get_search_key(user_id: int, query: str) -> str:
        query_hash = hash_query(query)
        return f"user:{user_id}:memories:search:{query_hash}"
    
    @staticmethod
    def invalidate_memories(user_id: int):
        """Invalidate all memory caches for user"""
        invalidate_pattern(f"user:{user_id}:memories:*")


# ============================================================
# INITIALIZE CACHE CLIENT
# ============================================================

# Global cache client instance
cache_client: Optional[RedisCache] = None


def init_cache(
    host: str = 'localhost',
    port: int = 6379,
    db: int = 0,
    password: Optional[str] = None
) -> RedisCache:
    """
    Initialize Redis cache client
    
    Args:
        host: Redis host
        port: Redis port
        db: Redis database number
        password: Redis password
    
    Returns:
        RedisCache instance
    """
    global cache_client
    cache_client = RedisCache(
        host=host,
        port=port,
        db=db,
        password=password
    )
    return cache_client


def get_cache() -> Optional[RedisCache]:
    """Get cache client instance"""
    return cache_client


# ============================================================
# CACHE WARMING
# ============================================================

def warm_cache():
    """Pre-populate cache with frequently accessed data"""
    logger.info("🔥 Starting cache warming...")
    
    try:
        from database.services import chatbot_service
        from database.utils.session_context import db_session_no_commit
        from database.repositories.user_repository import UserRepository
        
        # Warm user cache
        with db_session_no_commit() as session:
            user_repo = UserRepository()
            recent_users = user_repo.get_all(session, limit=100)
            
            for user in recent_users:
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'full_name': user.full_name,
                    'last_login': str(user.last_login)
                }
                UserCache.cache_user(user_data)
        
        logger.info(f"✅ Cache warming complete: {len(recent_users)} users cached")
    
    except Exception as e:
        logger.error(f"❌ Cache warming failed: {e}")


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    'RedisCache',
    'cached',
    'invalidate_cache',
    'invalidate_pattern',
    'UserCache',
    'ConversationCache',
    'MessageCache',
    'MemoryCache',
    'init_cache',
    'get_cache',
    'warm_cache',
    'cache_client'
]
