"""
Tests for Redis Cache Module
"""

import sys
from pathlib import Path
import pytest
import time
from unittest.mock import Mock, patch, MagicMock

# Ensure project root is in path
project_root = Path(__file__).parent.parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class TestInMemoryCache:
    """Test InMemoryCache class."""
    
    def test_cache_get_set(self):
        """Test basic get/set operations."""
        from src.cache import InMemoryCache
        
        cache = InMemoryCache()
        cache.set("key1", "value1")
        
        assert cache.get("key1") == "value1"
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        from src.cache import InMemoryCache
        
        cache = InMemoryCache()
        
        assert cache.get("nonexistent") is None
    
    def test_cache_with_ttl(self):
        """Test cache with TTL expiration."""
        from src.cache import InMemoryCache
        
        cache = InMemoryCache()
        cache.set("key1", "value1", ttl=1)
        
        assert cache.get("key1") == "value1"
        
        time.sleep(1.1)
        
        assert cache.get("key1") is None
    
    def test_cache_delete(self):
        """Test deleting cache entry."""
        from src.cache import InMemoryCache
        
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.delete("key1")
        
        assert cache.get("key1") is None
    
    def test_cache_clear(self):
        """Test clearing cache."""
        from src.cache import InMemoryCache
        
        cache = InMemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_cache_max_size(self):
        """Test cache respects max size."""
        from src.cache import InMemoryCache
        
        cache = InMemoryCache(max_size=2)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # First key should be evicted
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
    
    def test_cache_complex_values(self):
        """Test caching complex objects."""
        from src.cache import InMemoryCache
        
        cache = InMemoryCache()
        data = {"name": "test", "items": [1, 2, 3]}
        cache.set("complex", data)
        
        assert cache.get("complex") == data


class TestRedisCacheService:
    """Test RedisCacheService class."""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        return Mock()
    
    def test_initialization_with_fallback(self):
        """Test initialization uses fallback when Redis unavailable."""
        from src.cache import RedisCacheService
        
        # Create service - it will fall back to in-memory when Redis fails
        service = RedisCacheService(redis_url="redis://invalid:6379", fallback_enabled=True)
        
        assert service._use_fallback is True
        assert service._memory_cache is not None
    
    def test_get_set_with_fallback(self):
        """Test get/set with in-memory fallback."""
        from src.cache import RedisCacheService
        
        service = RedisCacheService(redis_url="redis://invalid:6379", fallback_enabled=True)
        service.set("key1", "value1")
        
        assert service.get("key1") == "value1"
    
    def test_get_or_set(self):
        """Test get_or_set pattern."""
        from src.cache import RedisCacheService
        
        service = RedisCacheService(redis_url="redis://invalid:6379", fallback_enabled=True)
        
        call_count = 0
        def factory():
            nonlocal call_count
            call_count += 1
            return "computed_value"
        
        # First call - should compute
        result1 = service.get_or_set("unique_key_1", factory)
        assert result1 == "computed_value"
        assert call_count == 1
        
        # Second call - should use cache
        result2 = service.get_or_set("unique_key_1", factory)
        assert result2 == "computed_value"
        assert call_count == 1  # Factory not called again
    
    def test_delete(self):
        """Test delete operation."""
        from src.cache import RedisCacheService
        
        service = RedisCacheService(redis_url="redis://invalid:6379", fallback_enabled=True)
        service.set("key1", "value1")
        
        result = service.delete("key1")
        
        assert result is True
        assert service.get("key1") is None
    
    def test_health_check_fallback(self):
        """Test health check with fallback."""
        from src.cache import RedisCacheService
        
        service = RedisCacheService(redis_url="redis://invalid:6379", fallback_enabled=True)
        
        # Fallback health check returns dict with status
        result = service.health_check()
        assert result["status"] == "fallback"
        assert result["backend"] == "in_memory"


class TestCachedDecorator:
    """Test @cached decorator."""
    
    def test_cached_function(self):
        """Test caching function results."""
        from src.cache import cached
        from src.cache.redis_cache import RedisCacheService
        
        # Create a fresh cache instance
        cache = RedisCacheService(redis_url="redis://invalid:6379", fallback_enabled=True)
        
        call_count = 0
        
        @cached(cache, ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        result1 = expensive_function(1)
        result2 = expensive_function(1)
        
        assert result1 == 2
        assert result2 == 2
        # Second call should use cache
        assert call_count == 1
    
    def test_cached_different_args(self):
        """Test cached with different arguments."""
        from src.cache import cached
        from src.cache.redis_cache import RedisCacheService
        
        cache = RedisCacheService(redis_url="redis://invalid:6379", fallback_enabled=True)
        
        @cached(cache, ttl=60)
        def multiply(x, y):
            return x * y
        
        result1 = multiply(2, 3)
        result2 = multiply(3, 4)
        
        assert result1 == 6
        assert result2 == 12


class TestCacheInvalidateDecorator:
    """Test @cache_invalidate decorator."""
    
    def test_cache_invalidation(self):
        """Test cache invalidation on write."""
        from src.cache import cache_invalidate
        from src.cache.redis_cache import RedisCacheService
        
        cache = RedisCacheService(redis_url="redis://invalid:6379", fallback_enabled=True)
        cache.set("users:123", {"name": "test"})
        
        @cache_invalidate(cache, patterns=["users:*"])
        def update_user(user_id, data):
            return {"updated": True}
        
        # This should invalidate the cache
        result = update_user(123, {"name": "updated"})
        
        # Verify function runs without error and returns result
        assert result["updated"] is True


class TestGetCacheService:
    """Test get_cache_service singleton."""
    
    def test_get_cache_service(self):
        """Test that get_cache_service returns a service."""
        from src.cache import get_cache_service
        
        service = get_cache_service()
        assert service is not None
    
    def test_create_new_instance(self):
        """Test creating new cache service."""
        from src.cache import RedisCacheService
        
        service = RedisCacheService(redis_url="redis://invalid:6379", fallback_enabled=True)
        assert service is not None
        assert service._use_fallback is True
