"""
Logging Utilities for VistralS2T
Structured logging with file and console output
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = "vistral",
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console: bool = True,
) -> logging.Logger:
    """
    Setup logger with file and console handlers
    
    Args:
        name: Logger name
        log_file: Path to log file (None = app/logs/vistral.log)
        level: Logging level
        console: Whether to add console handler
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    if log_file is None:
        log_file = f"app/logs/vistral_{datetime.now().strftime('%Y%m%d')}.log"
    
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = "vistral") -> logging.Logger:
    """
    Get existing logger or create new one
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # Setup if not configured
    if not logger.handlers:
        setup_logger(name)
    
    return logger


class LogContext:
    """
    Context manager for logging operations
    """
    
    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time = None
        
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"Starting: {self.operation}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type is None:
            self.logger.info(f"Completed: {self.operation} ({duration:.2f}s)")
        else:
            self.logger.error(
                f"Failed: {self.operation} ({duration:.2f}s) - {exc_val}",
                exc_info=True
            )
        
        return False  # Don't suppress exceptions


# Example usage
def log_model_loading(model_name: str, load_time: float):
    """Log model loading event"""
    logger = get_logger()
    logger.info(f"Model loaded: {model_name} in {load_time:.2f}s")


def log_transcription(model_name: str, audio_file: str, duration: float, chars: int):
    """Log transcription event"""
    logger = get_logger()
    logger.info(
        f"Transcription: {model_name} | {Path(audio_file).name} | "
        f"{duration:.2f}s | {chars} chars"
    )


def log_fusion(model_name: str, duration: float, output_chars: int):
    """Log fusion event"""
    logger = get_logger()
    logger.info(
        f"Fusion: {model_name} | {duration:.2f}s | {output_chars} chars"
    )


__all__ = [
    "setup_logger",
    "get_logger",
    "LogContext",
    "log_model_loading",
    "log_transcription",
    "log_fusion",
]
