"""
Rate Limiter Middleware

Handles request rate limiting.
"""

import time
from functools import wraps
from flask import request, jsonify
from collections import defaultdict


# Simple in-memory rate limiter
_request_counts = defaultdict(list)


def rate_limit(max_requests: int = 100, window: int = 3600):
    """
    Decorator to rate limit requests
    
    Args:
        max_requests: Maximum requests per window
        window: Time window in seconds
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get client identifier
            client_id = request.headers.get('X-API-Key') or request.remote_addr
            
            current_time = time.time()
            window_start = current_time - window
            
            # Clean old requests
            _request_counts[client_id] = [
                t for t in _request_counts[client_id]
                if t > window_start
            ]
            
            # Check limit
            if len(_request_counts[client_id]) >= max_requests:
                return jsonify({
                    'error': 'Too Many Requests',
                    'message': f'Rate limit of {max_requests} requests per {window}s exceeded',
                    'retry_after': int(window - (current_time - _request_counts[client_id][0]))
                }), 429
            
            # Record request
            _request_counts[client_id].append(current_time)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
