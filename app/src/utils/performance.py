"""
Performance Monitoring
Timing, metrics, and performance utilities
"""

import time
import logging
import functools
from typing import Dict, List, Any, Callable
from threading import Lock
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TimingStats:
    """Statistics for timing measurements."""
    count: int = 0
    total: float = 0.0
    min: float = float('inf')
    max: float = 0.0
    last: float = 0.0
    
    def add(self, duration: float) -> None:
        """Add a timing measurement."""
        self.count += 1
        self.total += duration
        self.min = min(self.min, duration)
        self.max = max(self.max, duration)
        self.last = duration
    
    @property
    def avg(self) -> float:
        """Get average duration."""
        return self.total / self.count if self.count > 0 else 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'count': self.count,
            'total_ms': round(self.total * 1000, 2),
            'avg_ms': round(self.avg * 1000, 2),
            'min_ms': round(self.min * 1000, 2) if self.min != float('inf') else 0,
            'max_ms': round(self.max * 1000, 2),
            'last_ms': round(self.last * 1000, 2)
        }


class PerformanceMonitor:
    """
    Performance monitoring and metrics collection.
    """
    
    def __init__(self, enable_logging: bool = True):
        self.enable_logging = enable_logging
        self._timings: Dict[str, TimingStats] = defaultdict(TimingStats)
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._lock = Lock()
    
    def record_timing(self, name: str, duration: float) -> None:
        """Record a timing measurement."""
        with self._lock:
            self._timings[name].add(duration)
        
        if self.enable_logging and duration > 1.0:  # Log slow operations
            logger.warning(f"Slow operation: {name} took {duration*1000:.2f}ms")
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        with self._lock:
            self._counters[name] += value
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value."""
        with self._lock:
            self._gauges[name] = value
    
    def get_timing(self, name: str) -> TimingStats:
        """Get timing stats for a name."""
        return self._timings.get(name, TimingStats())
    
    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self._counters.get(name, 0)
    
    def get_gauge(self, name: str) -> float:
        """Get gauge value."""
        return self._gauges.get(name, 0.0)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            return {
                'timings': {k: v.to_dict() for k, v in self._timings.items()},
                'counters': dict(self._counters),
                'gauges': dict(self._gauges)
            }
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._timings.clear()
            self._counters.clear()
            self._gauges.clear()
    
    def timer(self, name: str):
        """Context manager for timing."""
        return Timer(self, name)


class Timer:
    """Context manager for timing operations."""
    
    def __init__(self, monitor: PerformanceMonitor, name: str):
        self.monitor = monitor
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        duration = time.perf_counter() - self.start_time
        self.monitor.record_timing(self.name, duration)


def timing_decorator(name: str = None, monitor: PerformanceMonitor = None):
    """
    Decorator to time function execution.
    
    Args:
        name: Custom name for timing (defaults to function name)
        monitor: PerformanceMonitor instance
    """
    def decorator(func: Callable) -> Callable:
        timing_name = name or f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start
                
                if monitor:
                    monitor.record_timing(timing_name, duration)
                else:
                    logger.debug(f"{timing_name} took {duration*1000:.2f}ms")
        
        return wrapper
    return decorator


# Global monitor instance
_global_monitor = None


def get_monitor() -> PerformanceMonitor:
    """Get global performance monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def timed(name: str = None):
    """Decorator using global monitor."""
    return timing_decorator(name=name, monitor=get_monitor())
