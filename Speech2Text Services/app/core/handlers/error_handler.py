"""
Centralized Error Handling for VistralS2T
Custom exceptions and error handling utilities
"""

import traceback
import logging
from typing import Optional, Any
from pathlib import Path


# Custom Exceptions
class VistralError(Exception):
    """Base exception for VistralS2T"""
    pass


class ModelError(VistralError):
    """Exception raised for model loading/inference errors"""
    pass


class AudioError(VistralError):
    """Exception raised for audio processing errors"""
    pass


class ConfigError(VistralError):
    """Exception raised for configuration errors"""
    pass


# Error Handler Functions
def handle_error(
    error: Exception,
    context: str = "",
    fallback_value: Any = None,
    raise_error: bool = False,
) -> Any:
    """
    Handle errors with logging and optional fallback
    
    Args:
        error: The exception that occurred
        context: Context description for better error messages
        fallback_value: Value to return if not raising error
        raise_error: Whether to re-raise the error after logging
        
    Returns:
        fallback_value if raise_error is False, otherwise raises
    """
    error_msg = f"[ERROR] {context}: {str(error)}" if context else f"[ERROR] {str(error)}"
    print(error_msg)
    
    # Print traceback for debugging
    traceback.print_exc()
    
    # Log to file if logger is configured
    try:
        logger = logging.getLogger("vistral")
        logger.error(error_msg, exc_info=True)
    except:
        pass  # Logger not configured
    
    if raise_error:
        raise error
    
    return fallback_value


def log_error(
    message: str,
    error: Optional[Exception] = None,
    log_file: Optional[str] = None,
):
    """
    Log error message to console and file
    
    Args:
        message: Error message to log
        error: Optional exception object
        log_file: Optional custom log file path
    """
    # Print to console
    print(f"[ERROR] {message}")
    
    if error:
        print(f"[ERROR] Exception: {str(error)}")
        traceback.print_exc()
    
    # Log to file
    if log_file:
        try:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n[ERROR] {message}\n")
                if error:
                    f.write(f"[ERROR] Exception: {str(error)}\n")
                    f.write(traceback.format_exc())
        except Exception as e:
            print(f"[WARN] Failed to write to log file: {e}")


def safe_execute(
    func,
    *args,
    context: str = "",
    fallback_value: Any = None,
    **kwargs
):
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        *args: Positional arguments for func
        context: Context description for error messages
        fallback_value: Value to return on error
        **kwargs: Keyword arguments for func
        
    Returns:
        Function result or fallback_value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return handle_error(e, context=context, fallback_value=fallback_value)


def validate_audio_path(audio_path: str) -> Path:
    """
    Validate audio file path
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Validated Path object
        
    Raises:
        AudioError: If path is invalid or file doesn't exist
    """
    if not audio_path:
        raise AudioError("Audio path is empty")
    
    path = Path(audio_path)
    
    if not path.exists():
        raise AudioError(f"Audio file not found: {audio_path}")
    
    if not path.is_file():
        raise AudioError(f"Audio path is not a file: {audio_path}")
    
    # Check file extension
    valid_extensions = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".mp4"}
    if path.suffix.lower() not in valid_extensions:
        raise AudioError(
            f"Unsupported audio format: {path.suffix}. "
            f"Supported formats: {', '.join(valid_extensions)}"
        )
    
    return path


def validate_config(config_dict: dict, required_keys: list) -> None:
    """
    Validate configuration dictionary
    
    Args:
        config_dict: Configuration dictionary to validate
        required_keys: List of required keys
        
    Raises:
        ConfigError: If any required key is missing
    """
    missing_keys = [key for key in required_keys if key not in config_dict]
    
    if missing_keys:
        raise ConfigError(
            f"Missing required configuration keys: {', '.join(missing_keys)}"
        )


__all__ = [
    "VistralError",
    "ModelError",
    "AudioError",
    "ConfigError",
    "handle_error",
    "log_error",
    "safe_execute",
    "validate_audio_path",
    "validate_config",
]
