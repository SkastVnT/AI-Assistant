"""
Reliability Module for RAG Services
Provides retry logic, circuit breaker, and error handling
"""
import time
import logging
from typing import Callable, Any, Optional, Dict, Type
from functools import wraps
from enum import Enum
import traceback

logger = logging.getLogger(__name__)

# Try to import tenacity (optional but recommended)
try:
    from tenacity import (
        retry,
        stop_after_attempt,
        wait_exponential,
        retry_if_exception_type,
        before_sleep_log
    )
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    logger.warning("tenacity not available, using basic retry logic")


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation
    Prevents cascading failures by failing fast when error threshold exceeded
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        # Check if circuit is OPEN
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                logger.info("Circuit breaker entering HALF_OPEN state (testing recovery)")
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(
                    f"Circuit breaker OPEN: Service unavailable "
                    f"(retry in {int(self.recovery_timeout - (time.time() - self.last_failure_time))}s)"
                )
        
        try:
            # Execute function
            result = func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker CLOSED (service recovered)")
                self.state = CircuitState.CLOSED
            
            self.failure_count = 0
            return result
            
        except self.expected_exception as e:
            # Failure - increment count
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.error(f"Circuit breaker failure {self.failure_count}/{self.failure_threshold}: {e}")
            
            # Check if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                logger.error(f"Circuit breaker OPEN (threshold {self.failure_threshold} exceeded)")
                self.state = CircuitState.OPEN
            
            raise
    
    def reset(self):
        """Manually reset circuit breaker"""
        logger.info("Circuit breaker manually reset")
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def get_state(self) -> Dict[str, Any]:
        """Get circuit breaker state"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time,
            'time_until_retry': int(self.recovery_timeout - (time.time() - self.last_failure_time))
                                if self.state == CircuitState.OPEN and self.last_failure_time
                                else 0
        }


def retry_with_backoff(
    max_attempts: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 10.0,
    multiplier: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_wait: Initial wait time in seconds
        max_wait: Maximum wait time in seconds
        multiplier: Backoff multiplier
        exceptions: Tuple of exceptions to retry on
    
    Usage:
        @retry_with_backoff(max_attempts=3, initial_wait=1, exceptions=(APIError,))
        def call_api():
            return api.get_data()
    """
    
    if TENACITY_AVAILABLE:
        # Use tenacity if available (more robust)
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=multiplier, min=initial_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING)
        )
    
    # Fallback: basic retry implementation
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            wait_time = initial_wait
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(f"Max retries ({max_attempts}) exceeded: {e}")
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
                    wait_time = min(wait_time * multiplier, max_wait)
            
            return None  # Should never reach here
        
        return wrapper
    return decorator


class RateLimitError(Exception):
    """Custom exception for rate limit errors"""
    pass


class APIError(Exception):
    """Custom exception for API errors"""
    pass


def handle_gemini_errors(func):
    """
    Decorator to handle common Gemini API errors
    Converts Gemini errors to custom exceptions
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Rate limit errors
            if '429' in error_str or 'rate limit' in error_str or 'quota' in error_str:
                logger.warning("Gemini rate limit exceeded, will retry with backoff")
                raise RateLimitError(f"Gemini rate limit exceeded: {e}")
            
            # Authentication errors
            elif '401' in error_str or 'unauthorized' in error_str or 'api key' in error_str:
                logger.error("Gemini authentication error")
                raise APIError(f"Gemini authentication failed: {e}")
            
            # Bad request errors
            elif '400' in error_str or 'bad request' in error_str:
                logger.error("Gemini bad request error")
                raise APIError(f"Gemini bad request: {e}")
            
            # Server errors (retriable)
            elif '500' in error_str or '503' in error_str or 'server error' in error_str:
                logger.warning("Gemini server error, will retry")
                raise APIError(f"Gemini server error: {e}")
            
            # Connection errors (retriable)
            elif 'timeout' in error_str or 'connection' in error_str:
                logger.warning("Gemini connection error, will retry")
                raise APIError(f"Gemini connection error: {e}")
            
            # Unknown errors
            else:
                logger.error(f"Unknown Gemini error: {e}")
                raise APIError(f"Gemini error: {e}")
    
    return wrapper


# Global circuit breakers for different services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60
) -> CircuitBreaker:
    """Get or create circuit breaker for a service"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    return _circuit_breakers[name]


def with_circuit_breaker(name: str, **circuit_kwargs):
    """
    Decorator to protect function with circuit breaker
    
    Usage:
        @with_circuit_breaker('gemini', failure_threshold=5, recovery_timeout=60)
        def call_gemini_api():
            return gemini.generate_content(prompt)
    """
    def decorator(func):
        breaker = get_circuit_breaker(name, **circuit_kwargs)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


# Combined decorator for robust API calls
def robust_api_call(
    service_name: str,
    max_retries: int = 3,
    initial_wait: float = 1.0,
    circuit_threshold: int = 5,
    circuit_timeout: int = 60
):
    """
    Combined decorator: retry + circuit breaker + error handling
    
    Usage:
        @robust_api_call('gemini', max_retries=3, circuit_threshold=5)
        def call_gemini(prompt):
            return genai.GenerativeModel('gemini-1.5-flash').generate_content(prompt)
    """
    def decorator(func):
        # Apply decorators in order: error handling -> retry -> circuit breaker
        protected_func = handle_gemini_errors(func)
        retried_func = retry_with_backoff(
            max_attempts=max_retries,
            initial_wait=initial_wait,
            exceptions=(RateLimitError, APIError)
        )(protected_func)
        circuit_func = with_circuit_breaker(
            service_name,
            failure_threshold=circuit_threshold,
            recovery_timeout=circuit_timeout
        )(retried_func)
        
        return circuit_func
    
    return decorator


def get_all_circuit_states() -> Dict[str, Dict[str, Any]]:
    """Get state of all circuit breakers"""
    return {
        name: breaker.get_state()
        for name, breaker in _circuit_breakers.items()
    }


def reset_all_circuits():
    """Reset all circuit breakers"""
    for breaker in _circuit_breakers.values():
        breaker.reset()
    logger.info("All circuit breakers reset")
