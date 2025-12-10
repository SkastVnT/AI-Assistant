"""
Rate Limiter Utility
Implement rate limiting for API requests
"""

from functools import wraps
from flask import request, jsonify
import time
from collections import defaultdict
import logging

logger = logging.getLogger("ai_assistant_hub")


class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests=100, window_seconds=60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed for the identifier.
        
        Args:
            identifier: Unique identifier (e.g., IP address)
        
        Returns:
            True if request is allowed, False otherwise
        """
        current_time = time.time()
        
        # Remove old requests outside the window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < self.window_seconds
        ]
        
        # Check if limit exceeded
        if len(self.requests[identifier]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False
        
        # Add current request
        self.requests[identifier].append(current_time)
        return True
    
    def get_remaining(self, identifier: str) -> int:
        """Get remaining requests for identifier."""
        current_time = time.time()
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < self.window_seconds
        ]
        return max(0, self.max_requests - len(self.requests[identifier]))


# Global rate limiter instance
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


def rate_limit(max_requests=None, window_seconds=None):
    """
    Decorator for rate limiting routes.
    
    Args:
        max_requests: Override default max requests
        window_seconds: Override default window seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Use IP address as identifier
            identifier = request.remote_addr
            
            # Use custom limiter if parameters provided
            if max_requests and window_seconds:
                limiter = RateLimiter(max_requests, window_seconds)
            else:
                limiter = rate_limiter
            
            if not limiter.is_allowed(identifier):
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {limiter.max_requests} requests per {limiter.window_seconds} seconds',
                    'retry_after': limiter.window_seconds
                }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
