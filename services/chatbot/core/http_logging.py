"""
HTTP Request/Response Logging Middleware
Captures all GET/POST requests and responses with detailed information
"""

import logging
import json
import time
from datetime import datetime
from flask import request, g, has_request_context
from functools import wraps

# Create logger
logger = logging.getLogger(__name__)

SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "session",
    "token",
    "api_key",
    "apikey",
    "access_key",
    "private_key",
)
REDACTED = "[REDACTED]"


def _is_sensitive_key(key) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def redact_for_log(value):
    """Recursively redact sensitive values before serializing log payloads."""
    if isinstance(value, dict):
        return {
            key: REDACTED if _is_sensitive_key(key) else redact_for_log(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_for_log(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_for_log(item) for item in value)
    return value


def _body_summary_for_log(path: str, body):
    """Return metadata-only summaries for high-risk chat bodies."""
    if path not in {"/chat", "/chat/stream"} or not isinstance(body, dict):
        return redact_for_log(body)

    message = body.get("message")
    images = body.get("images")
    tools = body.get("tools")
    history = body.get("history")
    return {
        "keys": sorted(str(key) for key in body.keys()),
        "message_length": len(message) if isinstance(message, str) else 0,
        "model": body.get("model"),
        "context": body.get("context"),
        "thinking_mode": body.get("thinking_mode") or body.get("mode"),
        "tools_count": len(tools) if isinstance(tools, list) else 0,
        "images_count": len(images) if isinstance(images, list) else 0,
        "history_count": len(history) if isinstance(history, list) else 0,
    }


def _truncate_for_log(value, limit: int) -> str:
    payload = json.dumps(redact_for_log(value), default=str)
    if len(payload) > limit:
        return payload[:limit] + f"... ({len(payload)} chars total)"
    return payload


# Create detailed log handler
def setup_http_logging(app):
    """
    Configure HTTP logging for Flask app
    Logs all requests and responses with timing and status
    """
    
    # Paths to suppress from request/response logging (method → set of paths)
    _SKIP_LOG = {
        'POST': {'/', '/favicon.ico'},
    }

    @app.before_request
    def log_request():
        """Log incoming request details"""
        g.request_start_time = time.time()
        
        try:
            # Get request info
            method = request.method
            path = request.path
            remote_addr = request.remote_addr

            # Suppress noisy external probes (e.g. CS:GO GSI, health checkers)
            if path in _SKIP_LOG.get(method, set()):
                return

            # Log basic info
            if method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                log_msg = f"[{method}] {path} from {remote_addr}"
                
                # Add query params if GET
                if request.args:
                    log_msg += f" | Params: {redact_for_log(dict(request.args))}"
                
                # Add body if POST/PUT/PATCH (truncate if too large)
                if method in ['POST', 'PUT', 'PATCH']:
                    try:
                        if request.is_json:
                            body = request.get_json(silent=True)
                            body_repr = _truncate_for_log(
                                _body_summary_for_log(path, body),
                                500,
                            )
                            log_msg += f" | Body: {body_repr}"
                        else:
                            content_type = request.content_type or 'unknown'
                            content_length = request.content_length or 0
                            log_msg += f" | Content: {content_type} ({content_length} bytes)"
                    except Exception as e:
                        log_msg += f" | Body: (parse error: {e})"
                
                logger.info(f"➡️  REQUEST: {log_msg}")
        
        except Exception as e:
            logger.warning(f"[HTTP Logging] Error logging request: {e}")
    
    @app.after_request
    def log_response(response):
        """Log response details"""
        try:
            # Calculate duration
            if hasattr(g, 'request_start_time'):
                duration = time.time() - g.request_start_time
            else:
                duration = 0
            
            method = request.method
            path = request.path
            status_code = response.status_code

            # Suppress noisy external probes (same paths as request filter)
            if path in _SKIP_LOG.get(method, set()):
                return response
            
            # Determine emoji based on status code
            if status_code >= 500:
                emoji = "❌"  # Server error
            elif status_code >= 400:
                emoji = "⚠️ "  # Client error
            elif status_code >= 300:
                emoji = "↪️ "  # Redirect
            elif status_code >= 200:
                emoji = "✅"  # Success
            else:
                emoji = "❓"  # Unknown
            
            # Get response info
            content_type = response.content_type or 'unknown'
            content_length = response.content_length or len(response.get_data())
            
            log_msg = (
                f"[{method}] {path} | "
                f"Status: {status_code} | "
                f"Duration: {duration:.3f}s | "
                f"Size: {content_length} bytes | "
                f"Type: {content_type}"
            )
            
            logger.info(f"{emoji} RESPONSE: {log_msg}")
            
            # Log response body for errors (truncated)
            if status_code >= 400:
                try:
                    if response.is_json:
                        body = response.get_json(silent=True)
                        body_repr = _truncate_for_log(body, 300)
                        logger.debug(f"   Response Body: {body_repr}")
                except Exception:
                    pass
        
        except Exception as e:
            logger.warning(f"[HTTP Logging] Error logging response: {e}")
        
        return response


def create_http_log_file(app):
    """
    Create a separate HTTP request log file
    Saves detailed request/response info to logs/http_calls.log
    """
    from pathlib import Path
    import os
    
    log_dir = Path(app.root_path).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    http_log_file = log_dir / 'http_calls.log'
    
    # Create file handler
    from logging.handlers import RotatingFileHandler
    handler = RotatingFileHandler(
        str(http_log_file),
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Create separate logger for HTTP calls
    http_logger = logging.getLogger('http_calls')
    http_logger.addHandler(handler)
    http_logger.setLevel(logging.INFO)
    
    return http_logger


class HTTPCallTracker:
    """
    Tracks API calls and saves summary to JSON file
    Useful for debugging and monitoring service interactions
    """
    
    def __init__(self, log_file='logs/api_calls.json'):
        self.log_file = log_file
        self.calls = []
    
    def log_call(self, service_name: str, endpoint: str, method: str, status_code: int, duration: float, error: str = None):
        """
        Log an API call
        
        Args:
            service_name: Name of the service (e.g., 'GoogleDrive', 'MongoDB', 'ImgBB')
            endpoint: API endpoint URL
            method: HTTP method (GET, POST, etc.)
            status_code: Response status code
            duration: Request duration in seconds
            error: Error message if failed
        """
        call_record = {
            'timestamp': datetime.now().isoformat(),
            'service': service_name,
            'endpoint': endpoint,
            'method': method,
            'status': status_code,
            'duration_ms': round(duration * 1000, 2),
            'success': 200 <= status_code < 300,
            'error': error
        }
        self.calls.append(call_record)
        
        # Keep only last 1000 calls in memory
        if len(self.calls) > 1000:
            self.calls = self.calls[-1000:]
        
        # Save to file periodically
        if len(self.calls) % 10 == 0:
            self.save()
    
    def save(self):
        """Save call tracker to JSON file"""
        try:
            from pathlib import Path
            import json
            
            log_file = Path(self.log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'total_calls': len(self.calls),
                    'last_updated': datetime.now().isoformat(),
                    'calls': self.calls[-100:]  # Save last 100 calls
                }, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            logger.error(f"[HTTPTracker] Failed to save: {e}")


# Global tracker instance
http_tracker = HTTPCallTracker()


def track_external_call(service_name: str, endpoint: str, method: str = 'GET'):
    """
    Decorator to track external API calls
    
    Usage:
        @track_external_call('GoogleDrive', '/upload')
        def upload_image():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = None
            status_code = 500
            error = None
            
            try:
                result = func(*args, **kwargs)
                
                # Try to extract status code from result
                if isinstance(result, tuple) and len(result) >= 2:
                    if isinstance(result[1], int):
                        status_code = result[1]
                elif isinstance(result, dict):
                    status_code = result.get('status_code', 200)
                else:
                    status_code = 200
                
                return result
            
            except Exception as e:
                error = str(e)
                status_code = 500
                raise
            
            finally:
                duration = time.time() - start_time
                http_tracker.log_call(
                    service_name=service_name,
                    endpoint=endpoint,
                    method=method,
                    status_code=status_code,
                    duration=duration,
                    error=error
                )
        
        return wrapper
    return decorator


# Convenience decorators for common services
def track_google_drive_call(endpoint=''):
    return track_external_call('GoogleDrive', f'/drive{endpoint}', 'POST')

def track_mongodb_call(endpoint=''):
    return track_external_call('MongoDB', f'/db{endpoint}', 'POST')

def track_imgbb_call(endpoint=''):
    return track_external_call('ImgBB', f'/upload{endpoint}', 'POST')

def track_firebase_call(endpoint=''):
    return track_external_call('Firebase', f'/firestore{endpoint}', 'POST')
