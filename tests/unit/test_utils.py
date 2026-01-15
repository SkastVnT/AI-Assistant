"""
Tests for Shared Utilities
"""

import pytest
import time
from unittest.mock import MagicMock, patch


class TestCache:
    """Tests for cache utilities."""
    
    def test_cache_set_get(self, tmp_path):
        """Test cache basic operations."""
        from src.utils.cache import Cache
        
        cache = Cache(cache_dir=str(tmp_path / "cache"), ttl_seconds=3600)
        
        # Set and get
        cache.set("key1", {"data": "value1"})
        result = cache.get("key1")
        
        assert result == {"data": "value1"}
    
    def test_cache_expiration(self, tmp_path):
        """Test cache expiration."""
        from src.utils.cache import Cache
        
        cache = Cache(cache_dir=str(tmp_path / "cache"), ttl_seconds=1)  # 1 second TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None
    
    def test_cache_delete(self, tmp_path):
        """Test cache deletion."""
        from src.utils.cache import Cache
        
        cache = Cache(cache_dir=str(tmp_path / "cache"), ttl_seconds=3600)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.delete("key1")
        assert cache.get("key1") is None
    
    def test_cache_clear(self, tmp_path):
        """Test cache clearing."""
        from src.utils.cache import Cache
        
        cache = Cache(cache_dir=str(tmp_path / "cache"), ttl_seconds=3600)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestRateLimiter:
    """Tests for rate limiter utilities."""
    
    def test_rate_limiter_is_allowed(self):
        """Test rate limiting is_allowed."""
        from src.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        # First 3 requests should be allowed
        allowed1, remaining1 = limiter.is_allowed("user1")
        allowed2, remaining2 = limiter.is_allowed("user1")
        allowed3, remaining3 = limiter.is_allowed("user1")
        
        assert allowed1 is True
        assert allowed2 is True
        assert allowed3 is True
        
        # 4th request should be denied
        allowed4, remaining4 = limiter.is_allowed("user1")
        assert allowed4 is False
        assert remaining4 == 0
    
    def test_rate_limiter_different_keys(self):
        """Test rate limiting with different keys."""
        from src.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # User1 uses their quota
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        allowed_user1, _ = limiter.is_allowed("user1")
        
        # User2 should still have quota
        allowed_user2, _ = limiter.is_allowed("user2")
        
        assert allowed_user1 is False
        assert allowed_user2 is True
    
    def test_rate_limiter_reset(self):
        """Test rate limiter reset."""
        from src.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        
        # Reset user1
        limiter.reset("user1")
        
        # Should be allowed again
        allowed, _ = limiter.is_allowed("user1")
        assert allowed is True
    
    def test_rate_limiter_get_remaining(self):
        """Test get remaining requests."""
        from src.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        limiter.is_allowed("user1")
        limiter.is_allowed("user1")
        
        remaining = limiter.get_remaining("user1")
        assert remaining == 3


class TestConnectionPool:
    """Tests for connection pool utilities."""
    
    def test_connection_pool_creation(self):
        """Test connection pool initialization."""
        from src.utils.connection_pool import ConnectionPool
        
        created_count = 0
        
        def factory():
            nonlocal created_count
            created_count += 1
            return MagicMock()
        
        pool = ConnectionPool(
            factory=factory,
            max_size=5,
            min_size=2
        )
        
        # Should pre-create minimum connections
        assert created_count == 2
    
    def test_connection_pool_get_connection(self):
        """Test getting connection from pool."""
        from src.utils.connection_pool import ConnectionPool
        
        mock_conn = MagicMock()
        
        def factory():
            return mock_conn
        
        pool = ConnectionPool(
            factory=factory,
            max_size=5,
            min_size=1
        )
        
        with pool.get_connection() as pooled_conn:
            # Pooled connection wraps the actual connection
            assert pooled_conn is not None
            assert hasattr(pooled_conn, 'connection')


class TestPerformanceMonitor:
    """Tests for performance monitoring utilities."""
    
    def test_timing_stats(self):
        """Test timing statistics."""
        from src.utils.performance import TimingStats
        
        stats = TimingStats()
        stats.add(0.1)
        stats.add(0.2)
        stats.add(0.3)
        
        assert stats.count == 3
        assert stats.min == 0.1
        assert stats.max == 0.3
        assert abs(stats.avg - 0.2) < 0.001
    
    def test_performance_monitor_timing(self):
        """Test performance monitor timing."""
        from src.utils.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor(enable_logging=False)
        
        with monitor.timer("test_operation"):
            time.sleep(0.01)
        
        stats = monitor.get_timing("test_operation")
        assert stats.count == 1
        assert stats.total > 0
    
    def test_timing_decorator(self):
        """Test timing decorator."""
        from src.utils.performance import PerformanceMonitor, timing_decorator
        
        monitor = PerformanceMonitor(enable_logging=False)
        
        @timing_decorator("test_func", monitor)
        def sample_function():
            time.sleep(0.01)
            return "result"
        
        result = sample_function()
        
        assert result == "result"
        stats = monitor.get_timing("test_func")
        assert stats.count == 1
    
    def test_performance_monitor_counters(self):
        """Test counter functionality."""
        from src.utils.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor(enable_logging=False)
        
        monitor.increment_counter("api_calls")
        monitor.increment_counter("api_calls")
        monitor.increment_counter("api_calls", 3)
        
        assert monitor.get_counter("api_calls") == 5
    
    def test_performance_monitor_gauges(self):
        """Test gauge functionality."""
        from src.utils.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor(enable_logging=False)
        
        monitor.set_gauge("memory_usage", 1024.5)
        assert monitor.get_gauge("memory_usage") == 1024.5
        
        monitor.set_gauge("memory_usage", 2048.0)
        assert monitor.get_gauge("memory_usage") == 2048.0
    
    def test_get_all_stats(self):
        """Test getting all stats."""
        from src.utils.performance import PerformanceMonitor
        
        monitor = PerformanceMonitor(enable_logging=False)
        
        with monitor.timer("operation1"):
            pass
        monitor.increment_counter("counter1")
        monitor.set_gauge("gauge1", 100)
        
        stats = monitor.get_all_stats()
        
        assert 'timings' in stats
        assert 'counters' in stats
        assert 'gauges' in stats
