"""
Response Cache cho LLM APIs - Giảm số lượng API calls
Cache responses để tránh gọi API lặp lại cho cùng 1 prompt
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    In-memory cache với TTL (Time To Live)
    """

    def __init__(self, max_size=1000, ttl_seconds=3600):
        """
        Args:
            max_size: Số lượng items tối đa trong cache
            ttl_seconds: Thời gian cache hết hạn (default 1 hour)
        """
        self.cache: dict[str, dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds

        # Statistics
        self.hits = 0
        self.misses = 0
        self.saves = 0

    def _make_key(self, prompt: str, model: str, **kwargs) -> str:
        """
        Tạo cache key từ prompt và params
        """
        # Eliminate sensitive fields (such as raw API keys) from kwargs before hashing
        non_sensitive_kwargs = {
            k: v
            for k, v in kwargs.items()
            if not (
                k.lower() in {"api_key", "apikey", "gemini_api_key", "key"}
                or "api_key" in k.lower()
            )
        }
        params = {"prompt": prompt, "model": model, **non_sensitive_kwargs}

        # Create hash
        params_str = json.dumps(params, sort_keys=True)
        key = hashlib.sha256(params_str.encode()).hexdigest()[:16]
        return key

    def get(self, prompt: str, model: str, **kwargs) -> str | None:
        """
        Lấy response từ cache

        Returns:
            str hoặc None nếu không có trong cache hoặc đã hết hạn
        """
        key = self._make_key(prompt, model, **kwargs)

        if key in self.cache:
            item = self.cache[key]

            # Check TTL
            if time.time() - item["timestamp"] < self.ttl_seconds:
                self.hits += 1
                logger.debug(f"✅ Cache HIT for prompt: {prompt[:50]}...")
                return item["response"]
            else:
                # Expired
                del self.cache[key]
                logger.debug(f"⏰ Cache EXPIRED for prompt: {prompt[:50]}...")

        self.misses += 1
        logger.debug(f"❌ Cache MISS for prompt: {prompt[:50]}...")
        return None

    def set(self, prompt: str, model: str, response: str, **kwargs):
        """
        Lưu response vào cache
        """
        key = self._make_key(prompt, model, **kwargs)

        # Check size limit
        if len(self.cache) >= self.max_size:
            # Remove oldest item
            oldest_key = min(
                self.cache.keys(), key=lambda k: self.cache[k]["timestamp"]
            )
            del self.cache[oldest_key]
            logger.debug("🗑️ Cache full, removed oldest item")

        self.cache[key] = {
            "response": response,
            "timestamp": time.time(),
            "prompt": prompt[:100],  # Store short version for debugging
            "model": model,
        }

        self.saves += 1
        logger.debug(f"💾 Cached response for prompt: {prompt[:50]}...")

    def clear(self):
        """Xóa toàn bộ cache"""
        self.cache.clear()
        logger.info("🗑️ Cache cleared")

    def get_stats(self) -> dict[str, Any]:
        """Lấy thống kê cache"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "saves": self.saves,
            "hit_rate_percentage": round(hit_rate, 2),
            "ttl_seconds": self.ttl_seconds,
        }

    def cleanup_expired(self):
        """Xóa các items đã hết hạn"""
        now = time.time()
        expired_keys = [
            key
            for key, item in self.cache.items()
            if now - item["timestamp"] >= self.ttl_seconds
        ]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            logger.info(f"🗑️ Cleaned up {len(expired_keys)} expired cache items")


class FileBasedCache(ResponseCache):
    """
    Cache lưu vào file để persist qua sessions
    """

    def __init__(self, cache_dir="cache", **kwargs):
        super().__init__(**kwargs)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "llm_responses.json"

        # Load existing cache
        self._load_cache()

    def _load_cache(self):
        """Load cache từ file"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, encoding="utf-8") as f:
                    data = json.load(f)
                    self.cache = data.get("cache", {})
                    self.hits = data.get("hits", 0)
                    self.misses = data.get("misses", 0)
                    self.saves = data.get("saves", 0)
                    logger.info(
                        f"📂 Loaded cache from {self.cache_file} ({len(self.cache)} items)"
                    )
            except Exception as e:
                logger.error(f"❌ Failed to load cache: {e}")
                self.cache = {}

    def _save_cache(self):
        """Lưu cache vào file"""
        try:
            data = {
                "cache": self.cache,
                "hits": self.hits,
                "misses": self.misses,
                "saves": self.saves,
            }
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"💾 Saved cache to {self.cache_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save cache: {e}")

    def set(self, prompt: str, model: str, response: str, **kwargs):
        """Override set để auto-save"""
        super().set(prompt, model, response, **kwargs)

        # Auto-save mỗi 10 saves
        if self.saves % 10 == 0:
            self._save_cache()


# Global caches
# Gemini cache - 1 hour TTL
gemini_cache = ResponseCache(
    max_size=500,
    ttl_seconds=3600,  # 1 hour
)

# OpenAI cache - 30 minutes TTL
openai_cache = ResponseCache(
    max_size=300,
    ttl_seconds=1800,  # 30 minutes
)

# Chat history cache - longer TTL
chat_cache = FileBasedCache(
    cache_dir="local_data/cache",
    max_size=1000,
    ttl_seconds=7200,  # 2 hours
)


def get_cached_response(
    prompt: str, model: str, provider: str = "gemini", **kwargs
) -> str | None:
    """
    Lấy cached response cho prompt

    Args:
        prompt: User prompt
        model: Model name
        provider: 'gemini', 'openai', hoặc 'chat'
        **kwargs: Additional params (temperature, max_tokens, etc.)

    Returns:
        Cached response hoặc None
    """
    if provider == "gemini":
        return gemini_cache.get(prompt, model, **kwargs)
    elif provider == "openai":
        return openai_cache.get(prompt, model, **kwargs)
    elif provider == "chat":
        return chat_cache.get(prompt, model, **kwargs)
    return None


def cache_response(
    prompt: str, model: str, response: str, provider: str = "gemini", **kwargs
):
    """
    Cache response

    Args:
        prompt: User prompt
        model: Model name
        response: LLM response
        provider: 'gemini', 'openai', hoặc 'chat'
        **kwargs: Additional params
    """
    if provider == "gemini":
        gemini_cache.set(prompt, model, response, **kwargs)
    elif provider == "openai":
        openai_cache.set(prompt, model, response, **kwargs)
    elif provider == "chat":
        chat_cache.set(prompt, model, response, **kwargs)


def get_all_cache_stats() -> dict[str, Any]:
    """
    Lấy stats của tất cả caches
    """
    return {
        "gemini": gemini_cache.get_stats(),
        "openai": openai_cache.get_stats(),
        "chat": chat_cache.get_stats(),
    }


def clear_all_caches():
    """Xóa tất cả caches"""
    gemini_cache.clear()
    openai_cache.clear()
    chat_cache.clear()
    logger.info("🗑️ All caches cleared")


if __name__ == "__main__":
    # Test cache
    print("🧪 Testing Response Cache...\n")

    # Test GROK cache
    prompt = "What is AI?"
    model = "grok-3"

    # First call - MISS
    result = get_cached_response(prompt, model, provider="grok")
    print(f"First call: {result}")  # None

    # Cache response
    cache_response(prompt, model, "AI is artificial intelligence", provider="grok")

    # Second call - HIT
    result = get_cached_response(prompt, model, provider="grok")
    print(f"Second call: {result}")  # "AI is artificial intelligence"

    # Stats
    print("\n📊 Stats:")
    print(json.dumps(get_all_cache_stats(), indent=2))

    print("\n✅ Test completed!")
