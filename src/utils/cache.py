"""
Cache Utility
Simple file-based caching for API responses
"""

import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger("ai_assistant_hub")


class Cache:
    """Simple file-based cache."""
    
    def __init__(self, cache_dir: str = "data/cache", ttl_seconds: int = 3600):
        """
        Initialize cache.
        
        Args:
            cache_dir: Directory for cache files
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = ttl_seconds
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            # Check if expired
            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time > timedelta(seconds=self.ttl_seconds):
                logger.debug(f"Cache expired for key: {key}")
                cache_path.unlink()
                return None
            
            logger.debug(f"Cache hit for key: {key}")
            return cached['value']
        
        except Exception as e:
            logger.warning(f"Error reading cache for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        
        Returns:
            True if successful, False otherwise
        """
        cache_path = self._get_cache_path(key)
        
        try:
            cached = {
                'key': key,
                'value': value,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cached, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Cache set for key: {key}")
            return True
        
        except Exception as e:
            logger.warning(f"Error writing cache for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete cache entry."""
        cache_path = self._get_cache_path(key)
        
        try:
            if cache_path.exists():
                cache_path.unlink()
                logger.debug(f"Cache deleted for key: {key}")
            return True
        except Exception as e:
            logger.warning(f"Error deleting cache for key {key}: {e}")
            return False
    
    def clear(self) -> int:
        """Clear all cache entries."""
        count = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
                count += 1
            logger.info(f"Cleared {count} cache entries")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
        return count
