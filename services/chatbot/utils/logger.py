"""
Enhanced Logging Module

Provides structured JSON logging with rotation for production.
"""

import logging
import logging.handlers
import os
import sys
import json
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    Outputs logs in JSON format for easy parsing by log aggregators.
    """
    
    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra
        self._skip_fields = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs',
            'pathname', 'process', 'processName', 'relativeCreated',
            'stack_info', 'exc_info', 'exc_text', 'thread', 'threadName',
            'message', 'asctime'
        }
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if self.include_extra:
            for key, value in record.__dict__.items():
                if key not in self._skip_fields:
                    try:
                        json.dumps(value)  # Test if serializable
                        log_data[key] = value
                    except (TypeError, ValueError):
                        log_data[key] = str(value)
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for console output (development).
    """
    
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


class ChatbotLogger:
    """
    Chatbot-specific logger configuration.
    """
    
    _initialized = False
    _log_dir = None
    
    @classmethod
    def setup(
        cls,
        log_dir: str = "logs",
        log_level: str = "INFO",
        json_output: bool = True,
        console_output: bool = True,
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ) -> logging.Logger:
        """
        Setup the chatbot logger with file rotation and console output.
        
        Args:
            log_dir: Directory for log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            json_output: Use JSON format for file logs
            console_output: Also log to console
            max_bytes: Max size per log file before rotation
            backup_count: Number of backup files to keep
        
        Returns:
            Configured logger
        """
        if cls._initialized:
            return logging.getLogger("chatbot")
        
        # Create log directory
        cls._log_dir = Path(log_dir)
        cls._log_dir.mkdir(parents=True, exist_ok=True)
        
        # Get root logger for chatbot
        logger = logging.getLogger("chatbot")
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        logger.handlers.clear()  # Clear any existing handlers
        
        # File handler with rotation (JSON format)
        if json_output:
            file_handler = logging.handlers.RotatingFileHandler(
                cls._log_dir / "chatbot.json.log",
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(JsonFormatter())
            logger.addHandler(file_handler)
        else:
            file_handler = logging.handlers.RotatingFileHandler(
                cls._log_dir / "chatbot.log",
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(file_handler)
        
        # Error file handler (separate file for errors)
        error_handler = logging.handlers.RotatingFileHandler(
            cls._log_dir / "chatbot.error.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JsonFormatter() if json_output else logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(error_handler)
        
        # Console handler
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            
            # Use colored output for development, JSON for production
            if os.environ.get('ENVIRONMENT', 'development') == 'production':
                console_handler.setFormatter(JsonFormatter())
            else:
                console_handler.setFormatter(ColoredFormatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                ))
            logger.addHandler(console_handler)
        
        # Also configure database and cache loggers
        for sub_logger in ['database', 'cache', 'api', 'services']:
            sub = logging.getLogger(f"chatbot.{sub_logger}")
            sub.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        cls._initialized = True
        logger.info("Chatbot logger initialized", extra={
            "log_dir": str(cls._log_dir),
            "log_level": log_level,
            "json_output": json_output
        })
        
        return logger
    
    @classmethod
    def get_logger(cls, name: str = "chatbot") -> logging.Logger:
        """Get a logger instance"""
        if not cls._initialized:
            cls.setup()
        return logging.getLogger(name)


def get_logger(name: str = "chatbot") -> logging.Logger:
    """Convenience function to get a logger"""
    return ChatbotLogger.get_logger(name)


def setup_logger(**kwargs) -> logging.Logger:
    """Convenience function to setup the logger"""
    return ChatbotLogger.setup(**kwargs)


# Context manager for operation logging
class LogOperation:
    """
    Context manager for logging operations with timing.
    
    Usage:
        with LogOperation("Creating conversation", user_id=user_id):
            # do something
    """
    
    def __init__(self, operation: str, logger: Optional[logging.Logger] = None, **extra):
        self.operation = operation
        self.logger = logger or get_logger()
        self.extra = extra
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.utcnow()
        self.logger.debug(f"Starting: {self.operation}", extra={
            **self.extra,
            "operation": self.operation,
            "status": "started"
        })
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (datetime.utcnow() - self.start_time).total_seconds() * 1000
        
        if exc_type:
            self.logger.error(f"Failed: {self.operation}", extra={
                **self.extra,
                "operation": self.operation,
                "status": "failed",
                "duration_ms": round(duration_ms, 2),
                "error": str(exc_val)
            })
        else:
            self.logger.info(f"Completed: {self.operation}", extra={
                **self.extra,
                "operation": self.operation,
                "status": "completed",
                "duration_ms": round(duration_ms, 2)
            })
        
        return False  # Don't suppress exceptions


# Pre-configured logging events
class LogEvents:
    """Pre-defined logging events for consistent logging"""
    
    @staticmethod
    def conversation_created(logger: logging.Logger, user_id: str, conversation_id: str, model: str):
        logger.info("Conversation created", extra={
            "event": "conversation_created",
            "user_id": user_id,
            "conversation_id": conversation_id,
            "model": model
        })
    
    @staticmethod
    def message_sent(logger: logging.Logger, conversation_id: str, role: str, length: int):
        logger.info("Message sent", extra={
            "event": "message_sent",
            "conversation_id": conversation_id,
            "role": role,
            "message_length": length
        })
    
    @staticmethod
    def cache_hit(logger: logging.Logger, cache_key: str):
        logger.debug("Cache hit", extra={
            "event": "cache_hit",
            "cache_key": cache_key
        })
    
    @staticmethod
    def cache_miss(logger: logging.Logger, cache_key: str):
        logger.debug("Cache miss", extra={
            "event": "cache_miss",
            "cache_key": cache_key
        })
    
    @staticmethod
    def db_query(logger: logging.Logger, collection: str, operation: str, duration_ms: float):
        logger.debug("Database query", extra={
            "event": "db_query",
            "collection": collection,
            "operation": operation,
            "duration_ms": round(duration_ms, 2)
        })
    
    @staticmethod
    def api_request(logger: logging.Logger, endpoint: str, method: str, status: int, duration_ms: float):
        logger.info("API request", extra={
            "event": "api_request",
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "duration_ms": round(duration_ms, 2)
        })
    
    @staticmethod
    def error(logger: logging.Logger, error_type: str, message: str, **extra):
        logger.error(f"{error_type}: {message}", extra={
            "event": "error",
            "error_type": error_type,
            **extra
        })
