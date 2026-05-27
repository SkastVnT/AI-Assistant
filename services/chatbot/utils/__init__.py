"""
Chatbot Utilities Package

Provides common utilities for the chatbot service:
- Health checks (liveness, readiness, detailed)
- Structured logging with rotation
- Metrics collection for monitoring
"""

from .health import (
    HealthChecker,
    HealthStatus,
    create_health_blueprint,
    get_health_checker,
    require_healthy,
)
from .logger import (
    ChatbotLogger,
    ColoredFormatter,
    JsonFormatter,
    LogEvents,
    LogOperation,
    get_logger,
    setup_logger,
)
from .metrics import (
    Counter,
    Gauge,
    Histogram,
    MetricsRegistry,
    active_conversations,
    active_users,
    ai_response_time,
    api_requests,
    cache_hits,
    cache_misses,
    cache_operation_time,
    cache_size,
    # Pre-defined metrics
    conversations_created,
    count_calls,
    create_metrics_blueprint,
    db_connections,
    db_queries,
    db_query_time,
    errors_total,
    # Functions
    get_all_metrics,
    get_prometheus_metrics,
    messages_received,
    messages_sent,
    registry,
    response_time,
    track_errors,
    track_time,
)

__all__ = [
    # Health
    "HealthChecker",
    "HealthStatus",
    "get_health_checker",
    "create_health_blueprint",
    "require_healthy",
    # Logger
    "ChatbotLogger",
    "JsonFormatter",
    "ColoredFormatter",
    "LogOperation",
    "LogEvents",
    "get_logger",
    "setup_logger",
    # Metrics
    "Counter",
    "Gauge",
    "Histogram",
    "MetricsRegistry",
    "registry",
    "get_all_metrics",
    "get_prometheus_metrics",
    "create_metrics_blueprint",
    "track_time",
    "count_calls",
    "track_errors",
    # Pre-defined metrics
    "conversations_created",
    "messages_sent",
    "messages_received",
    "cache_hits",
    "cache_misses",
    "db_queries",
    "errors_total",
    "api_requests",
    "active_conversations",
    "active_users",
    "cache_size",
    "db_connections",
    "response_time",
    "db_query_time",
    "ai_response_time",
    "cache_operation_time",
]
