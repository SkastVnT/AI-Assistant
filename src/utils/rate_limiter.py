"""
Rate Limiter Utility
Simple in-memory rate limiting
"""

import time
import logging
from typing import Dict, Tuple
from threading import Lock

logger = logging.getLogger("ai_assistant")


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = {}
        self._lock = Lock()
    
    def _cleanup_old_requests(self, key: str, current_time: float):
        """Remove requests outside the time window."""
        cutoff_time = current_time - self.window_seconds
        self._requests[key] = [
            req_time for req_time in self._requests.get(key, [])
            if req_time > cutoff_time
        ]
    
    def is_allowed(self, key: str) -> Tuple[bool, int]:
        """
        Check if request is allowed.
        
        Args:
            key: Identifier for the request source (e.g., IP, user ID)
        
        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        with self._lock:
            current_time = time.time()
            
            # Initialize or cleanup
            if key not in self._requests:
                self._requests[key] = []
            else:
                self._cleanup_old_requests(key, current_time)
            
            # Check limit
            request_count = len(self._requests[key])
            
            if request_count >= self.max_requests:
                return False, 0
            
            # Record request
            self._requests[key].append(current_time)
            remaining = self.max_requests - request_count - 1
            
            return True, remaining
    
    def reset(self, key: str):
        """
        Reset rate limit for a key.
        
        Args:
            key: Identifier to reset
        """
        with self._lock:
            if key in self._requests:
                del self._requests[key]
    
    def get_remaining(self, key: str) -> int:
        """
        Get remaining requests for a key.
        
        Args:
            key: Identifier to check
        
        Returns:
            Number of remaining requests
        """
        with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(key, current_time)
            request_count = len(self._requests.get(key, []))
            return max(0, self.max_requests - request_count)
    
    def get_reset_time(self, key: str) -> float:
        """
        Get time until rate limit resets.
        
        Args:
            key: Identifier to check
        
        Returns:
            Seconds until reset (0 if no requests)
        """
        with self._lock:
            requests = self._requests.get(key, [])
            if not requests:
                return 0
            
            oldest_request = min(requests)
            reset_time = oldest_request + self.window_seconds
            return max(0, reset_time - time.time())
