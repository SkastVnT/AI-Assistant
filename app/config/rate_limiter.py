"""
Rate Limiter for Gemini API - Giải quyết quota exceeded
Tự động throttle requests để không vượt rate limits
"""

import time
import threading
from collections import deque
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter với sliding window algorithm
    Giới hạn số requests trong 1 khoảng thời gian
    """

    def __init__(self, max_requests=15, time_window=60):
        """
        Args:
            max_requests: Số requests tối đa (Free tier Gemini = 15 RPM)
            time_window: Thời gian tính theo giây (60s = 1 phút)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = threading.Lock()

    def wait_if_needed(self):
        """
        Chờ nếu cần để không vượt rate limit
        """
        with self.lock:
            now = datetime.now()

            # Xóa các requests cũ ngoài time window
            while self.requests and (now - self.requests[0]) > timedelta(
                seconds=self.time_window
            ):
                self.requests.popleft()

            # Nếu đã đạt max, chờ cho đến khi request đầu tiên hết hạn
            if len(self.requests) >= self.max_requests:
                oldest_request = self.requests[0]
                wait_time = self.time_window - (now - oldest_request).total_seconds()

                if wait_time > 0:
                    logger.warning(
                        f"⏳ Rate limit reached ({len(self.requests)}/{self.max_requests}). Waiting {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time + 0.1)  # +0.1s safety margin

                    # Xóa request cũ nhất
                    self.requests.popleft()

            # Thêm request mới
            self.requests.append(datetime.now())

    def get_stats(self):
        """Lấy thống kê hiện tại"""
        with self.lock:
            now = datetime.now()
            # Xóa requests cũ
            while self.requests and (now - self.requests[0]) > timedelta(
                seconds=self.time_window
            ):
                self.requests.popleft()

            return {
                "current_requests": len(self.requests),
                "max_requests": self.max_requests,
                "time_window": self.time_window,
                "available_requests": self.max_requests - len(self.requests),
                "usage_percentage": (len(self.requests) / self.max_requests) * 100,
            }


class MultiKeyRateLimiter:
    """
    Rate limiter cho nhiều API keys
    Tự động chọn key có available requests
    """

    def __init__(self, num_keys=4, max_requests_per_key=15, time_window=60):
        """
        Args:
            num_keys: Số lượng API keys
            max_requests_per_key: Số requests tối đa mỗi key
            time_window: Thời gian window (giây)
        """
        self.limiters = [
            RateLimiter(max_requests_per_key, time_window) for _ in range(num_keys)
        ]
        self.current_key_index = 0
        self.lock = threading.Lock()

    def get_best_key(self):
        """
        Tìm key có ít requests nhất
        Returns: (key_index, limiter)
        """
        with self.lock:
            # Lấy stats của tất cả keys
            stats = [
                (i, limiter.get_stats()) for i, limiter in enumerate(self.limiters)
            ]

            # Sắp xếp theo available requests (nhiều nhất trước)
            stats.sort(key=lambda x: x[1]["available_requests"], reverse=True)

            best_key_index = stats[0][0]
            return best_key_index, self.limiters[best_key_index]

    def wait_and_get_key(self):
        """
        Chờ nếu cần và trả về key index tốt nhất
        Returns: key_index (0-3)
        """
        key_index, limiter = self.get_best_key()
        limiter.wait_if_needed()

        logger.debug(f"🔑 Using API Key #{key_index + 1}")
        return key_index

    def get_all_stats(self):
        """Lấy stats của tất cả keys"""
        return {
            f"key_{i + 1}": limiter.get_stats()
            for i, limiter in enumerate(self.limiters)
        }


# Global rate limiters
# Free tier Gemini: 15 RPM
gemini_rate_limiter = MultiKeyRateLimiter(
    num_keys=4,
    max_requests_per_key=15,  # Free tier
    time_window=60,  # 1 minute
)

# OpenAI có rate limit cao hơn
openai_rate_limiter = RateLimiter(
    max_requests=60,  # GPT-4o-mini free tier
    time_window=60,
)


def get_gemini_key_with_rate_limit():
    """
    Lấy Gemini API key index với rate limiting
    Tự động chờ nếu đạt rate limit

    Returns:
        int: Key index (0-3) để dùng
    """
    return gemini_rate_limiter.wait_and_get_key()


def wait_for_openai_rate_limit():
    """
    Chờ nếu OpenAI rate limit đạt ngưỡng
    """
    openai_rate_limiter.wait_if_needed()


def get_rate_limit_stats():
    """
    Lấy thống kê rate limit của tất cả services

    Returns:
        dict: Stats của Gemini và OpenAI
    """
    return {
        "gemini": gemini_rate_limiter.get_all_stats(),
        "openai": openai_rate_limiter.get_stats(),
    }


if __name__ == "__main__":
    # Test rate limiter
    import json

    print("🧪 Testing Rate Limiter...")
    print(f"Config: {gemini_rate_limiter.limiters[0].max_requests} RPM per key\n")

    # Simulate 50 requests
    for i in range(50):
        key_index = get_gemini_key_with_rate_limit()
        print(f"Request #{i + 1}: Using Key #{key_index + 1}")

        if (i + 1) % 10 == 0:
            print("\n📊 Current Stats:")
            stats = get_rate_limit_stats()
            print(json.dumps(stats, indent=2))
            print()

    print("\n✅ Test completed!")
