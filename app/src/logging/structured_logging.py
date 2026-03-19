"""
Centralized Logging Module
Structured JSON logging with request tracing
"""

import os
import sys
import json
import logging
import traceback
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
from threading import local
from contextvars import ContextVar

# Context variable for request ID
request_id_var: ContextVar[str] = ContextVar('request_id', default='')


class RequestContext:
    """
    Thread-local storage for request context.
    """
    _local = local()
    
    @classmethod
    def set_request_id(cls, request_id: str = None):
        """Set request ID for current context."""
        cls._local.request_id = request_id or str(uuid.uuid4())[:8]
        request_id_var.set(cls._local.request_id)
    
    @classmethod
    def get_request_id(cls) -> str:
        """Get request ID for current context."""
        return getattr(cls._local, 'request_id', '') or request_id_var.get()
    
    @classmethod
    def set(cls, key: str, value: Any):
        """Set context value."""
        setattr(cls._local, key, value)
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Get context value."""
        return getattr(cls._local, key, default)
    
    @classmethod
    def clear(cls):
        """Clear all context."""
        cls._local.__dict__.clear()


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    """
    
    def __init__(self, service_name: str = "ai-assistant", 
                 include_extra: bool = True,
                 indent: int = None):
        super().__init__()
        self.service_name = service_name
        self.include_extra = include_extra
        self.indent = indent
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self.service_name,
        }
        
        # Add request ID if available
        request_id = RequestContext.get_request_id()
        if request_id:
            log_data["request_id"] = request_id
        
        # Add location info
        log_data["location"] = {
            "file": record.filename,
            "line": record.lineno,
            "function": record.funcName
        }
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if self.include_extra:
            extra = {}
            for key, value in record.__dict__.items():
                if key not in [
                    'name', 'msg', 'args', 'created', 'filename', 'funcName',
                    'levelname', 'levelno', 'lineno', 'module', 'msecs',
                    'pathname', 'process', 'processName', 'relativeCreated',
                    'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
                    'message', 'taskName'
                ]:
                    extra[key] = value
            
            if extra:
                log_data["extra"] = extra
        
        return json.dumps(log_data, default=str, indent=self.indent)


class ColoredFormatter(logging.Formatter):
    """
    Colored console formatter for development.
    """
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, include_request_id: bool = True):
        super().__init__()
        self.include_request_id = include_request_id
    
    def format(self, record: logging.LogRecord) -> str:
        """Format with colors."""
        color = self.COLORS.get(record.levelname, '')
        
        # Build message parts
        parts = [
            f"{color}{record.levelname:8}{self.RESET}",
            f"{datetime.now().strftime('%H:%M:%S')}",
            f"[{record.name}]"
        ]
        
        # Add request ID
        if self.include_request_id:
            request_id = RequestContext.get_request_id()
            if request_id:
                parts.append(f"[{request_id}]")
        
        parts.append(record.getMessage())
        
        message = " ".join(parts)
        
        # Add exception
        if record.exc_info:
            message += "\n" + "".join(traceback.format_exception(*record.exc_info))
        
        return message


def setup_logging(
    service_name: str = "ai-assistant",
    log_level: str = None,
    log_format: str = None,
    log_file: str = None,
    json_logs: bool = None
) -> logging.Logger:
    """
    Setup logging configuration.
    
    Args:
        service_name: Service name for logs
        log_level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_format: 'json' or 'colored'
        log_file: Optional log file path
        json_logs: Force JSON format
    
    Returns:
        Root logger
    """
    # Get config from environment
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    log_format = log_format or os.getenv("LOG_FORMAT", "colored")
    json_logs = json_logs if json_logs is not None else os.getenv("JSON_LOGS", "").lower() == "true"
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Choose formatter
    if json_logs or log_format == "json":
        formatter = JSONFormatter(service_name=service_name)
    else:
        formatter = ColoredFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(JSONFormatter(service_name=service_name))
        root_logger.addHandler(file_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# ============================================================================
# LOGGING DECORATORS
# ============================================================================

def log_function_call(logger: logging.Logger = None, 
                      log_args: bool = True,
                      log_result: bool = False,
                      level: int = logging.DEBUG):
    """
    Decorator to log function calls.
    
    Args:
        logger: Logger instance
        log_args: Log function arguments
        log_result: Log function result
        level: Log level
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"
            
            # Log call
            if log_args:
                logger.log(level, f"Calling {func_name}", 
                          extra={"args": args, "kwargs": kwargs})
            else:
                logger.log(level, f"Calling {func_name}")
            
            try:
                result = func(*args, **kwargs)
                
                if log_result:
                    logger.log(level, f"{func_name} returned", 
                              extra={"result": result})
                
                return result
                
            except Exception as e:
                logger.exception(f"{func_name} raised {type(e).__name__}: {e}")
                raise
        
        return wrapper
    return decorator


def log_execution_time(logger: logging.Logger = None,
                       level: int = logging.INFO,
                       threshold_ms: float = 0):
    """
    Decorator to log function execution time.
    
    Args:
        logger: Logger instance
        level: Log level
        threshold_ms: Only log if execution time exceeds this (ms)
    """
    import time
    
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            
            try:
                return func(*args, **kwargs)
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                
                if duration_ms >= threshold_ms:
                    logger.log(
                        level,
                        f"{func.__name__} completed in {duration_ms:.2f}ms",
                        extra={"duration_ms": duration_ms}
                    )
        
        return wrapper
    return decorator


# ============================================================================
# FLASK INTEGRATION
# ============================================================================

def setup_flask_logging(app, service_name: str = None):
    """
    Setup logging for Flask application.
    
    Args:
        app: Flask application
        service_name: Service name for logs
    """
    from flask import request, g
    import time
    
    service_name = service_name or app.name
    logger = get_logger(service_name)
    
    @app.before_request
    def before_request():
        """Set request context and start timer."""
        g.start_time = time.perf_counter()
        
        # Get or generate request ID
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())[:8]
        RequestContext.set_request_id(request_id)
        
        # Store additional context
        RequestContext.set('method', request.method)
        RequestContext.set('path', request.path)
        RequestContext.set('remote_addr', request.remote_addr)
    
    @app.after_request
    def after_request(response):
        """Log request completion."""
        duration_ms = (time.perf_counter() - g.get('start_time', 0)) * 1000
        
        logger.info(
            f"{request.method} {request.path} {response.status_code}",
            extra={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "content_length": response.content_length
            }
        )
        
        # Add request ID to response headers
        response.headers['X-Request-ID'] = RequestContext.get_request_id()
        
        return response
    
    @app.teardown_request
    def teardown_request(exception):
        """Clear request context."""
        if exception:
            logger.exception(f"Request failed: {exception}")
        RequestContext.clear()
    
    return logger
