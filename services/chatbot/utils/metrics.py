"""
Metrics Collection Module

Provides metrics collection for monitoring and observability.
Supports Prometheus-compatible metrics export.
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from functools import wraps
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class Counter:
    """
    A simple counter metric.
    Thread-safe implementation.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0
        self._lock = threading.Lock()
    
    def inc(self, amount: int = 1):
        """Increment the counter"""
        with self._lock:
            self._value += amount
    
    def get(self) -> int:
        """Get current value"""
        with self._lock:
            return self._value
    
    def reset(self):
        """Reset counter to 0"""
        with self._lock:
            self._value = 0


class Gauge:
    """
    A gauge metric that can go up and down.
    Thread-safe implementation.
    """
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._value = 0.0
        self._lock = threading.Lock()
    
    def set(self, value: float):
        """Set gauge value"""
        with self._lock:
            self._value = value
    
    def inc(self, amount: float = 1.0):
        """Increment gauge"""
        with self._lock:
            self._value += amount
    
    def dec(self, amount: float = 1.0):
        """Decrement gauge"""
        with self._lock:
            self._value -= amount
    
    def get(self) -> float:
        """Get current value"""
        with self._lock:
            return self._value


class Histogram:
    """
    A histogram metric for measuring distributions.
    Tracks count, sum, and bucket distributions.
    """
    
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    
    def __init__(self, name: str, description: str = "", buckets: tuple = None):
        self.name = name
        self.description = description
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._count = 0
        self._sum = 0.0
        self._bucket_counts = {b: 0 for b in self.buckets}
        self._bucket_counts[float('inf')] = 0
        self._lock = threading.Lock()
    
    def observe(self, value: float):
        """Record an observation"""
        with self._lock:
            self._count += 1
            self._sum += value
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1
            self._bucket_counts[float('inf')] += 1
    
    def get(self) -> Dict[str, Any]:
        """Get histogram data"""
        with self._lock:
            return {
                "count": self._count,
                "sum": self._sum,
                "avg": self._sum / self._count if self._count > 0 else 0,
                "buckets": dict(self._bucket_counts)
            }
    
    def reset(self):
        """Reset histogram"""
        with self._lock:
            self._count = 0
            self._sum = 0.0
            self._bucket_counts = {b: 0 for b in self.buckets}
            self._bucket_counts[float('inf')] = 0


class MetricsRegistry:
    """
    Central registry for all metrics.
    Singleton pattern for global access.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._metrics = {}
            cls._instance._start_time = datetime.utcnow()
        return cls._instance
    
    def register(self, metric):
        """Register a metric"""
        self._metrics[metric.name] = metric
    
    def get(self, name: str):
        """Get a metric by name"""
        return self._metrics.get(name)
    
    def all(self) -> Dict[str, Any]:
        """Get all metrics as dict"""
        result = {}
        for name, metric in self._metrics.items():
            if isinstance(metric, Counter):
                result[name] = {"type": "counter", "value": metric.get()}
            elif isinstance(metric, Gauge):
                result[name] = {"type": "gauge", "value": metric.get()}
            elif isinstance(metric, Histogram):
                result[name] = {"type": "histogram", **metric.get()}
        return result
    
    def prometheus_format(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        
        for name, metric in self._metrics.items():
            if isinstance(metric, Counter):
                lines.append(f"# HELP {name} {metric.description}")
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {metric.get()}")
            
            elif isinstance(metric, Gauge):
                lines.append(f"# HELP {name} {metric.description}")
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {metric.get()}")
            
            elif isinstance(metric, Histogram):
                data = metric.get()
                lines.append(f"# HELP {name} {metric.description}")
                lines.append(f"# TYPE {name} histogram")
                for bucket, count in data["buckets"].items():
                    if bucket == float('inf'):
                        lines.append(f'{name}_bucket{{le="+Inf"}} {count}')
                    else:
                        lines.append(f'{name}_bucket{{le="{bucket}"}} {count}')
                lines.append(f"{name}_sum {data['sum']}")
                lines.append(f"{name}_count {data['count']}")
        
        return "\n".join(lines)


# Global metrics registry
registry = MetricsRegistry()


# ============================================================================
# Pre-defined Chatbot Metrics
# ============================================================================

# Counters
conversations_created = Counter("chatbot_conversations_created_total", "Total conversations created")
messages_sent = Counter("chatbot_messages_sent_total", "Total messages sent")
messages_received = Counter("chatbot_messages_received_total", "Total messages received from AI")
cache_hits = Counter("chatbot_cache_hits_total", "Cache hits")
cache_misses = Counter("chatbot_cache_misses_total", "Cache misses")
db_queries = Counter("chatbot_db_queries_total", "Database queries executed")
errors_total = Counter("chatbot_errors_total", "Total errors")
api_requests = Counter("chatbot_api_requests_total", "Total API requests")

# Gauges
active_conversations = Gauge("chatbot_active_conversations", "Currently active conversations")
active_users = Gauge("chatbot_active_users", "Currently active users")
cache_size = Gauge("chatbot_cache_size", "Current cache size (keys)")
db_connections = Gauge("chatbot_db_connections", "Active database connections")

# Histograms
response_time = Histogram("chatbot_response_time_seconds", "Response time in seconds")
db_query_time = Histogram("chatbot_db_query_time_seconds", "Database query time in seconds")
ai_response_time = Histogram("chatbot_ai_response_time_seconds", "AI model response time")
cache_operation_time = Histogram("chatbot_cache_operation_time_seconds", "Cache operation time")

# Register all metrics
for metric in [
    conversations_created, messages_sent, messages_received,
    cache_hits, cache_misses, db_queries, errors_total, api_requests,
    active_conversations, active_users, cache_size, db_connections,
    response_time, db_query_time, ai_response_time, cache_operation_time
]:
    registry.register(metric)


# ============================================================================
# Decorators for automatic metrics collection
# ============================================================================

def track_time(histogram: Histogram):
    """Decorator to track function execution time"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start
                histogram.observe(elapsed)
        return wrapper
    return decorator


def count_calls(counter: Counter):
    """Decorator to count function calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            counter.inc()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def track_errors(counter: Counter = None):
    """Decorator to track errors"""
    error_counter = counter or errors_total
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_counter.inc()
                raise
        return wrapper
    return decorator


# ============================================================================
# Flask Blueprint for metrics endpoint
# ============================================================================

def create_metrics_blueprint():
    """Create Flask blueprint for metrics endpoints"""
    try:
        from flask import Blueprint, Response, jsonify
        
        metrics_bp = Blueprint('metrics', __name__)
        
        @metrics_bp.route('/metrics', methods=['GET'])
        def prometheus_metrics():
            """Prometheus-compatible metrics endpoint"""
            return Response(
                registry.prometheus_format(),
                mimetype='text/plain; version=0.0.4; charset=utf-8'
            )
        
        @metrics_bp.route('/metrics/json', methods=['GET'])
        def json_metrics():
            """JSON format metrics endpoint"""
            return jsonify({
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": registry.all()
            })
        
        return metrics_bp
    except ImportError:
        logger.warning("Flask not available, metrics blueprint not created")
        return None


# ============================================================================
# Utility functions
# ============================================================================

def get_all_metrics() -> Dict[str, Any]:
    """Get all metrics as dictionary"""
    return registry.all()


def get_prometheus_metrics() -> str:
    """Get metrics in Prometheus format"""
    return registry.prometheus_format()


def reset_all_metrics():
    """Reset all metrics (useful for testing)"""
    for metric in registry._metrics.values():
        if hasattr(metric, 'reset'):
            metric.reset()
