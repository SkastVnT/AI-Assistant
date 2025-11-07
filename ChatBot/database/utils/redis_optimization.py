"""
Redis optimization utilities.

Provides pipeline operations, compression, and memory optimization for Redis caching.
"""
import zlib
import json
import pickle
from typing import Any, Dict, List, Optional, Tuple
from redis import Redis
from redis.client import Pipeline

from .cache import cache_client
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class RedisCompression:
    """Compression utilities for Redis values."""
    
    COMPRESSION_THRESHOLD = 1024  # Compress values larger than 1KB
    
    @staticmethod
    def compress(value: bytes, level: int = 6) -> bytes:
        """
        Compress bytes using zlib.
        
        Args:
            value: Bytes to compress
            level: Compression level (1-9, default 6)
            
        Returns:
            Compressed bytes with compression marker
        """
        if len(value) < RedisCompression.COMPRESSION_THRESHOLD:
            return b'\x00' + value  # No compression marker
        
        compressed = zlib.compress(value, level)
        compression_ratio = len(compressed) / len(value)
        
        # Only use compression if it saves at least 20%
        if compression_ratio < 0.8:
            logger.debug(f"Compressed {len(value)} -> {len(compressed)} bytes (ratio: {compression_ratio:.2f})")
            return b'\x01' + compressed  # Compression marker
        else:
            return b'\x00' + value
    
    @staticmethod
    def decompress(value: bytes) -> bytes:
        """
        Decompress bytes if compressed.
        
        Args:
            value: Bytes to decompress (with compression marker)
            
        Returns:
            Decompressed bytes
        """
        if not value:
            return value
        
        marker = value[0:1]
        data = value[1:]
        
        if marker == b'\x01':
            return zlib.decompress(data)
        else:
            return data
    
    @staticmethod
    def serialize_and_compress(obj: Any) -> bytes:
        """
        Serialize object to JSON and compress.
        
        Args:
            obj: Object to serialize
            
        Returns:
            Compressed bytes
        """
        json_str = json.dumps(obj, default=str)
        json_bytes = json_str.encode('utf-8')
        return RedisCompression.compress(json_bytes)
    
    @staticmethod
    def decompress_and_deserialize(data: bytes) -> Any:
        """
        Decompress and deserialize JSON.
        
        Args:
            data: Compressed bytes
            
        Returns:
            Deserialized object
        """
        json_bytes = RedisCompression.decompress(data)
        json_str = json_bytes.decode('utf-8')
        return json.loads(json_str)


class RedisPipeline:
    """Redis pipeline operations for bulk cache operations."""
    
    def __init__(self, client: Optional[Redis] = None):
        """
        Initialize pipeline.
        
        Args:
            client: Redis client (uses cache_client if not provided)
        """
        self.client = client or cache_client
        self.pipeline: Optional[Pipeline] = None
    
    def __enter__(self) -> Pipeline:
        """Start pipeline context."""
        self.pipeline = self.client.pipeline()
        return self.pipeline
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Execute pipeline and cleanup."""
        if self.pipeline:
            if exc_type is None:
                self.pipeline.execute()
            self.pipeline = None
    
    @staticmethod
    def bulk_set(items: Dict[str, Any], ttl: Optional[int] = None, 
                 compress: bool = True) -> int:
        """
        Set multiple keys in a single pipeline.
        
        Args:
            items: Dictionary of key-value pairs
            ttl: Time-to-live in seconds
            compress: Whether to compress values
            
        Returns:
            Number of keys set
        """
        if not items:
            return 0
        
        with RedisPipeline() as pipe:
            for key, value in items.items():
                if compress:
                    serialized = RedisCompression.serialize_and_compress(value)
                else:
                    serialized = json.dumps(value, default=str)
                
                if ttl:
                    pipe.setex(key, ttl, serialized)
                else:
                    pipe.set(key, serialized)
        
        logger.debug(f"Bulk set {len(items)} keys")
        return len(items)
    
    @staticmethod
    def bulk_get(keys: List[str], decompress: bool = True) -> Dict[str, Any]:
        """
        Get multiple keys in a single pipeline.
        
        Args:
            keys: List of keys to get
            decompress: Whether values are compressed
            
        Returns:
            Dictionary of key-value pairs (missing keys excluded)
        """
        if not keys:
            return {}
        
        with RedisPipeline() as pipe:
            for key in keys:
                pipe.get(key)
        
        # Execute returns list of values in same order as keys
        values = cache_client.pipeline().get(*keys).execute()
        
        result = {}
        for key, value in zip(keys, values):
            if value:
                try:
                    if decompress:
                        result[key] = RedisCompression.decompress_and_deserialize(value)
                    else:
                        result[key] = json.loads(value)
                except Exception as e:
                    logger.warning(f"Failed to deserialize key {key}: {e}")
        
        hit_ratio = len(result) / len(keys) if keys else 0
        logger.debug(f"Bulk get {len(keys)} keys, hit ratio: {hit_ratio:.2%}")
        return result
    
    @staticmethod
    def bulk_delete(keys: List[str]) -> int:
        """
        Delete multiple keys in a single pipeline.
        
        Args:
            keys: List of keys to delete
            
        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0
        
        count = cache_client.delete(*keys)
        logger.debug(f"Bulk deleted {count} keys")
        return count


class RedisMemoryOptimizer:
    """Memory optimization utilities for Redis."""
    
    @staticmethod
    def get_memory_info() -> Dict[str, Any]:
        """
        Get Redis memory usage information.
        
        Returns:
            Dictionary with memory stats
        """
        info = cache_client.info('memory')
        
        return {
            'used_memory': info.get('used_memory', 0),
            'used_memory_human': info.get('used_memory_human', 'N/A'),
            'used_memory_peak': info.get('used_memory_peak', 0),
            'used_memory_peak_human': info.get('used_memory_peak_human', 'N/A'),
            'maxmemory': info.get('maxmemory', 0),
            'maxmemory_human': info.get('maxmemory_human', 'N/A'),
            'mem_fragmentation_ratio': info.get('mem_fragmentation_ratio', 0),
        }
    
    @staticmethod
    def get_key_count() -> int:
        """Get total number of keys in Redis."""
        return cache_client.dbsize()
    
    @staticmethod
    def get_key_memory_usage(key: str) -> int:
        """
        Get memory usage of a specific key in bytes.
        
        Args:
            key: Redis key
            
        Returns:
            Memory usage in bytes
        """
        try:
            return cache_client.memory_usage(key) or 0
        except Exception as e:
            logger.warning(f"Failed to get memory usage for key {key}: {e}")
            return 0
    
    @staticmethod
    def analyze_large_keys(pattern: str = '*', limit: int = 10) -> List[Tuple[str, int]]:
        """
        Find largest keys matching pattern.
        
        Args:
            pattern: Key pattern to match
            limit: Maximum number of keys to return
            
        Returns:
            List of (key, size_bytes) tuples, sorted by size descending
        """
        keys = []
        for key in cache_client.scan_iter(pattern):
            size = RedisMemoryOptimizer.get_key_memory_usage(key)
            keys.append((key.decode() if isinstance(key, bytes) else key, size))
        
        # Sort by size descending and return top N
        keys.sort(key=lambda x: x[1], reverse=True)
        return keys[:limit]
    
    @staticmethod
    def cleanup_expired_keys() -> int:
        """
        Force Redis to cleanup expired keys.
        
        Returns:
            Approximate number of keys removed
        """
        initial_count = RedisMemoryOptimizer.get_key_count()
        
        # Trigger active expiration by accessing random keys
        for _ in range(100):
            key = cache_client.randomkey()
            if key:
                cache_client.exists(key)
        
        final_count = RedisMemoryOptimizer.get_key_count()
        removed = max(0, initial_count - final_count)
        
        logger.info(f"Cleanup removed approximately {removed} expired keys")
        return removed
    
    @staticmethod
    def get_compression_ratio(sample_size: int = 100) -> float:
        """
        Calculate average compression ratio for cached data.
        
        Args:
            sample_size: Number of keys to sample
            
        Returns:
            Average compression ratio (compressed/original)
        """
        ratios = []
        count = 0
        
        for key in cache_client.scan_iter('*'):
            if count >= sample_size:
                break
            
            try:
                value = cache_client.get(key)
                if value and len(value) > 10:
                    # Check if compressed (marker byte)
                    if value[0:1] == b'\x01':
                        compressed_size = len(value) - 1  # Exclude marker
                        decompressed = RedisCompression.decompress(value)
                        original_size = len(decompressed)
                        
                        if original_size > 0:
                            ratio = compressed_size / original_size
                            ratios.append(ratio)
                            count += 1
            except Exception as e:
                logger.debug(f"Failed to check compression for key {key}: {e}")
        
        if ratios:
            avg_ratio = sum(ratios) / len(ratios)
            logger.info(f"Compression ratio: {avg_ratio:.2%} (sampled {len(ratios)} keys)")
            return avg_ratio
        else:
            logger.warning("No compressed keys found in sample")
            return 1.0


# Convenience functions
def cache_with_compression(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Cache value with automatic compression.
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time-to-live in seconds
        
    Returns:
        True if successful
    """
    try:
        serialized = RedisCompression.serialize_and_compress(value)
        
        if ttl:
            cache_client.setex(key, ttl, serialized)
        else:
            cache_client.set(key, serialized)
        
        return True
    except Exception as e:
        logger.error(f"Failed to cache with compression: {e}")
        return False


def get_cached_compressed(key: str) -> Optional[Any]:
    """
    Get cached value with automatic decompression.
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found
    """
    try:
        value = cache_client.get(key)
        if value:
            return RedisCompression.decompress_and_deserialize(value)
        return None
    except Exception as e:
        logger.error(f"Failed to get cached compressed value: {e}")
        return None
