"""
Database Utils Package

Session management and utilities for optimization.
"""

from .session import DatabaseSession, get_db_session

# Optimization utilities
from .optimizer import (
    QueryOptimizer,
    BulkOperations,
    ConnectionPool,
    IndexManager,
    cached_query,
    timed_query
)

from .cache_optimizer import (
    CacheCompressor,
    RedisPipeline,
    CacheWarmer,
    CacheKeyBuilder,
    CacheInvalidator,
    MemoryLimiter
)

__all__ = [
    # Session
    'DatabaseSession',
    'get_db_session',
    
    # Query optimization
    'QueryOptimizer',
    'BulkOperations',
    'ConnectionPool',
    'IndexManager',
    'cached_query',
    'timed_query',
    
    # Cache optimization
    'CacheCompressor',
    'RedisPipeline',
    'CacheWarmer',
    'CacheKeyBuilder',
    'CacheInvalidator',
    'MemoryLimiter'
]
