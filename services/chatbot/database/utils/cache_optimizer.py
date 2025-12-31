"""
Cache Optimization Module

Provides utilities for optimizing cache operations:
- Pipeline operations
- Compression for large values
- Cache warming
- Memory management
"""

import logging
import json
import zlib
import hashlib
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)


class CacheCompressor:
    """
    Utilities for compressing cache values.
    Reduces memory usage for large objects.
    """
    
    COMPRESSION_THRESHOLD = 1024  # Compress values > 1KB
    
    @classmethod
    def compress(cls, data: Any) -> bytes:
        """Compress data for cache storage"""
        json_str = json.dumps(data, default=str)
        
        if len(json_str) > cls.COMPRESSION_THRESHOLD:
            compressed = zlib.compress(json_str.encode('utf-8'), level=6)
            # Add marker prefix
            return b'ZLIB:' + compressed
        
        return json_str.encode('utf-8')
    
    @classmethod
    def decompress(cls, data: bytes) -> Any:
        """Decompress cached data"""
        if data.startswith(b'ZLIB:'):
            decompressed = zlib.decompress(data[5:])
            return json.loads(decompressed.decode('utf-8'))
        
        return json.loads(data.decode('utf-8'))
    
    @classmethod
    def get_compression_stats(cls, original: Any, compressed: bytes) -> Dict[str, Any]:
        """Get compression statistics"""
        original_size = len(json.dumps(original, default=str).encode('utf-8'))
        compressed_size = len(compressed)
        
        return {
            'original_size': original_size,
            'compressed_size': compressed_size,
            'ratio': round(compressed_size / original_size, 2) if original_size > 0 else 1,
            'savings_percent': round((1 - compressed_size / original_size) * 100, 1) if original_size > 0 else 0
        }


class RedisPipeline:
    """
    Redis pipeline wrapper for batch operations.
    Reduces network round trips.
    """
    
    def __init__(self, redis_client):
        self.client = redis_client
        self._operations = []
    
    def set(self, key: str, value: Any, ttl: int = None):
        """Add set operation to pipeline"""
        self._operations.append(('set', key, value, ttl))
        return self
    
    def get(self, key: str):
        """Add get operation to pipeline"""
        self._operations.append(('get', key))
        return self
    
    def delete(self, key: str):
        """Add delete operation to pipeline"""
        self._operations.append(('delete', key))
        return self
    
    def execute(self) -> List[Any]:
        """Execute all pipeline operations"""
        if not self._operations:
            return []
        
        try:
            pipe = self.client.pipeline()
            
            for op in self._operations:
                if op[0] == 'set':
                    _, key, value, ttl = op
                    if ttl:
                        pipe.setex(key, ttl, json.dumps(value, default=str))
                    else:
                        pipe.set(key, json.dumps(value, default=str))
                elif op[0] == 'get':
                    pipe.get(op[1])
                elif op[0] == 'delete':
                    pipe.delete(op[1])
            
            results = pipe.execute()
            
            # Parse get results
            parsed = []
            op_idx = 0
            for result in results:
                if self._operations[op_idx][0] == 'get' and result:
                    parsed.append(json.loads(result))
                else:
                    parsed.append(result)
                op_idx += 1
            
            self._operations.clear()
            return parsed
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}")
            self._operations.clear()
            raise
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.execute()
        return False


class CacheWarmer:
    """
    Utilities for warming cache with frequently accessed data.
    """
    
    def __init__(self, cache_client):
        self.cache = cache_client
        self._warm_functions = []
    
    def register(self, func: Callable, args_list: List[tuple] = None):
        """Register a function for cache warming"""
        self._warm_functions.append((func, args_list or [()]))
    
    def warm(self) -> Dict[str, Any]:
        """Execute all registered warming functions"""
        results = {
            'warmed': 0,
            'failed': 0,
            'duration_ms': 0
        }
        
        start = datetime.utcnow()
        
        for func, args_list in self._warm_functions:
            for args in args_list:
                try:
                    func(*args)
                    results['warmed'] += 1
                except Exception as e:
                    logger.warning(f"Cache warm failed for {func.__name__}: {e}")
                    results['failed'] += 1
        
        results['duration_ms'] = (datetime.utcnow() - start).total_seconds() * 1000
        
        logger.info(f"Cache warming complete", extra=results)
        return results


class CacheKeyBuilder:
    """
    Utilities for building consistent cache keys.
    """
    
    PREFIX = "chatbot"
    SEPARATOR = ":"
    
    @classmethod
    def build(cls, *parts) -> str:
        """Build a cache key from parts"""
        return cls.SEPARATOR.join([cls.PREFIX] + [str(p) for p in parts])
    
    @classmethod
    def conversation(cls, conversation_id: str) -> str:
        """Build conversation cache key"""
        return cls.build("conv", conversation_id)
    
    @classmethod
    def user_conversations(cls, user_id: str) -> str:
        """Build user conversations list key"""
        return cls.build("user", user_id, "convs")
    
    @classmethod
    def messages(cls, conversation_id: str) -> str:
        """Build messages cache key"""
        return cls.build("conv", conversation_id, "msgs")
    
    @classmethod
    def memory(cls, memory_id: str) -> str:
        """Build memory cache key"""
        return cls.build("mem", memory_id)
    
    @classmethod
    def query(cls, query_hash: str) -> str:
        """Build query result cache key"""
        return cls.build("query", query_hash)
    
    @classmethod
    def hash_query(cls, query: Dict[str, Any]) -> str:
        """Generate hash for query dict"""
        query_str = json.dumps(query, sort_keys=True, default=str)
        return hashlib.md5(query_str.encode()).hexdigest()[:16]


class CacheInvalidator:
    """
    Utilities for cache invalidation patterns.
    """
    
    def __init__(self, cache_client):
        self.cache = cache_client
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern (Redis only)"""
        try:
            if hasattr(self.cache, 'keys'):
                keys = self.cache.keys(pattern)
                if keys:
                    self.cache.delete(*keys)
                    logger.debug(f"Invalidated {len(keys)} keys matching {pattern}")
        except Exception as e:
            logger.warning(f"Pattern invalidation failed: {e}")
    
    def invalidate_user(self, user_id: str):
        """Invalidate all cache for a user"""
        self.invalidate_pattern(f"{CacheKeyBuilder.PREFIX}:user:{user_id}:*")
    
    def invalidate_conversation(self, conversation_id: str):
        """Invalidate all cache for a conversation"""
        keys_to_delete = [
            CacheKeyBuilder.conversation(conversation_id),
            CacheKeyBuilder.messages(conversation_id)
        ]
        
        for key in keys_to_delete:
            try:
                self.cache.delete(key)
            except:
                pass


class MemoryLimiter:
    """
    Limits in-memory cache size to prevent memory issues.
    """
    
    def __init__(self, max_entries: int = 10000, max_size_mb: int = 100):
        self.max_entries = max_entries
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._entries = {}
        self._access_times = {}
        self._total_size = 0
    
    def can_add(self, key: str, value: Any) -> bool:
        """Check if we can add this entry"""
        size = len(json.dumps(value, default=str).encode('utf-8'))
        
        if len(self._entries) >= self.max_entries:
            return False
        
        if self._total_size + size > self.max_size_bytes:
            return False
        
        return True
    
    def add(self, key: str, value: Any) -> bool:
        """Add entry if within limits"""
        size = len(json.dumps(value, default=str).encode('utf-8'))
        
        # Evict if needed
        while not self.can_add(key, value) and self._entries:
            self._evict_lru()
        
        if self.can_add(key, value):
            self._entries[key] = value
            self._access_times[key] = datetime.utcnow()
            self._total_size += size
            return True
        
        return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get entry and update access time"""
        if key in self._entries:
            self._access_times[key] = datetime.utcnow()
            return self._entries[key]
        return None
    
    def _evict_lru(self):
        """Evict least recently used entry"""
        if not self._access_times:
            return
        
        lru_key = min(self._access_times, key=self._access_times.get)
        value = self._entries.pop(lru_key, None)
        self._access_times.pop(lru_key, None)
        
        if value:
            size = len(json.dumps(value, default=str).encode('utf-8'))
            self._total_size -= size
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory limiter statistics"""
        return {
            'entries': len(self._entries),
            'max_entries': self.max_entries,
            'size_bytes': self._total_size,
            'max_size_bytes': self.max_size_bytes,
            'utilization_percent': round(self._total_size / self.max_size_bytes * 100, 1)
        }
