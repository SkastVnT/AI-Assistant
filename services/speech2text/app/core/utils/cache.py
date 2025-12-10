"""
Caching Utilities for VistralS2T
Simple file-based caching for transcripts and results
"""

import json
import hashlib
from pathlib import Path
from typing import Optional, Any, Dict
from datetime import datetime


class ResultCache:
    """
    Simple file-based cache for storing transcription results
    """
    
    def __init__(self, cache_dir: str = "app/data/cache"):
        """
        Initialize cache
        
        Args:
            cache_dir: Directory to store cache files
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_cache_key(self, audio_path: str, model_name: str) -> str:
        """Generate cache key from audio path and model name"""
        key_string = f"{audio_path}:{model_name}"
        return hashlib.md5(key_string.encode()).hexdigest()
        
    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for given key"""
        return self.cache_dir / f"{cache_key}.json"
        
    def get(
        self,
        audio_path: str,
        model_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached result
        
        Args:
            audio_path: Path to audio file
            model_name: Name of model used
            
        Returns:
            Cached result dictionary or None if not found
        """
        cache_key = self._get_cache_key(audio_path, model_name)
        cache_path = self._get_cache_path(cache_key)
        
        if not cache_path.exists():
            return None
            
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            
            print(f"[Cache] HIT: {model_name} for {Path(audio_path).name}")
            return cached_data
            
        except Exception as e:
            print(f"[Cache] Error reading cache: {e}")
            return None
            
    def set(
        self,
        audio_path: str,
        model_name: str,
        result: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Store result in cache
        
        Args:
            audio_path: Path to audio file
            model_name: Name of model used
            result: Transcription result
            metadata: Optional metadata to store
        """
        cache_key = self._get_cache_key(audio_path, model_name)
        cache_path = self._get_cache_path(cache_key)
        
        cache_data = {
            "audio_path": audio_path,
            "model_name": model_name,
            "result": result,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            print(f"[Cache] STORED: {model_name} for {Path(audio_path).name}")
            
        except Exception as e:
            print(f"[Cache] Error writing cache: {e}")
            
    def clear(self, model_name: Optional[str] = None):
        """
        Clear cache
        
        Args:
            model_name: Clear only cache for specific model (None = clear all)
        """
        if model_name is None:
            # Clear all cache
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            print("[Cache] Cleared all cache")
        else:
            # Clear cache for specific model
            count = 0
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, "r") as f:
                        data = json.load(f)
                    if data.get("model_name") == model_name:
                        cache_file.unlink()
                        count += 1
                except:
                    pass
            print(f"[Cache] Cleared {count} cache files for {model_name}")


# Global cache instance
_cache = ResultCache()


# Convenience functions
def cache_result(
    audio_path: str,
    model_name: str,
    result: str,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Cache transcription result"""
    _cache.set(audio_path, model_name, result, metadata)


def get_cached_result(audio_path: str, model_name: str) -> Optional[str]:
    """Get cached transcription result"""
    cached = _cache.get(audio_path, model_name)
    return cached["result"] if cached else None


def clear_cache(model_name: Optional[str] = None):
    """Clear cache"""
    _cache.clear(model_name)


__all__ = [
    "ResultCache",
    "cache_result",
    "get_cached_result",
    "clear_cache",
]
