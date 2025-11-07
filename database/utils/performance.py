"""
Database performance monitoring and query logging utilities.

Provides:
- Slow query detection and logging
- Query performance metrics
- Connection pool statistics
- Database health monitoring
"""

import time
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

SLOW_QUERY_THRESHOLD = 1.0  # seconds
LOG_ALL_QUERIES = False  # Set to True for debug mode


# ============================================================
# QUERY PERFORMANCE TRACKING
# ============================================================

class QueryStats:
    """Track query performance statistics"""
    
    def __init__(self):
        self.total_queries = 0
        self.slow_queries = 0
        self.total_time = 0.0
        self.queries = []
    
    def add_query(self, statement: str, duration: float, is_slow: bool = False):
        """Record query execution"""
        self.total_queries += 1
        self.total_time += duration
        
        if is_slow:
            self.slow_queries += 1
            self.queries.append({
                'statement': statement[:200],  # Truncate long queries
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        return {
            'total_queries': self.total_queries,
            'slow_queries': self.slow_queries,
            'total_time': round(self.total_time, 2),
            'avg_time': round(self.total_time / self.total_queries, 3) if self.total_queries > 0 else 0,
            'recent_slow_queries': self.queries[-10:]  # Last 10 slow queries
        }
    
    def reset(self):
        """Reset statistics"""
        self.total_queries = 0
        self.slow_queries = 0
        self.total_time = 0.0
        self.queries = []


# Global query stats instance
query_stats = QueryStats()


# ============================================================
# SQLALCHEMY EVENT LISTENERS
# ============================================================

def setup_query_logging(engine: Engine):
    """
    Setup SQLAlchemy event listeners for query monitoring
    
    Args:
        engine: SQLAlchemy engine instance
    """
    
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time"""
        conn.info.setdefault('query_start_time', []).append(time.time())
    
    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Log query execution time"""
        total = time.time() - conn.info['query_start_time'].pop()
        
        is_slow = total > SLOW_QUERY_THRESHOLD
        
        # Add to statistics
        query_stats.add_query(statement, total, is_slow)
        
        # Log slow queries
        if is_slow:
            logger.warning(
                f"SLOW QUERY ({total:.2f}s): {statement[:200]}..."
            )
        elif LOG_ALL_QUERIES:
            logger.debug(f"Query ({total:.3f}s): {statement[:100]}...")
    
    @event.listens_for(engine, "connect")
    def connect(dbapi_conn, connection_record):
        """Log new database connections"""
        logger.debug("New database connection established")
    
    @event.listens_for(engine, "checkout")
    def checkout(dbapi_conn, connection_record, connection_proxy):
        """Log connection checkout from pool"""
        logger.debug("Connection checked out from pool")
    
    @event.listens_for(engine, "checkin")
    def checkin(dbapi_conn, connection_record):
        """Log connection return to pool"""
        logger.debug("Connection returned to pool")
    
    logger.info("✅ Query performance monitoring enabled")


# ============================================================
# CONNECTION POOL MONITORING
# ============================================================

def get_pool_stats(engine: Engine) -> Dict[str, Any]:
    """
    Get connection pool statistics
    
    Args:
        engine: SQLAlchemy engine instance
    
    Returns:
        Dictionary with pool statistics
    """
    pool = engine.pool
    
    return {
        'pool_size': pool.size(),
        'checked_in': pool.checkedin(),
        'checked_out': pool.checkedout(),
        'overflow': pool.overflow(),
        'total_connections': pool.size() + pool.overflow()
    }


def log_pool_stats(engine: Engine):
    """
    Log current connection pool statistics
    
    Args:
        engine: SQLAlchemy engine instance
    """
    stats = get_pool_stats(engine)
    logger.info(
        f"Pool Stats - Size: {stats['pool_size']}, "
        f"In: {stats['checked_in']}, Out: {stats['checked_out']}, "
        f"Overflow: {stats['overflow']}, Total: {stats['total_connections']}"
    )


# ============================================================
# QUERY TIMER CONTEXT MANAGER
# ============================================================

@contextmanager
def query_timer(operation_name: str, threshold: float = 1.0):
    """
    Context manager to time database operations
    
    Args:
        operation_name: Name of the operation being timed
        threshold: Time threshold in seconds to log warning
    
    Usage:
        with query_timer("fetch_users"):
            users = session.query(User).all()
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        if duration > threshold:
            logger.warning(f"⏱️  {operation_name} took {duration:.2f}s (threshold: {threshold}s)")
        else:
            logger.debug(f"⏱️  {operation_name} completed in {duration:.3f}s")


# ============================================================
# DATABASE HEALTH CHECK
# ============================================================

def check_database_health(engine: Engine) -> Dict[str, Any]:
    """
    Perform comprehensive database health check
    
    Args:
        engine: SQLAlchemy engine instance
    
    Returns:
        Health check results
    """
    health = {
        'status': 'unknown',
        'timestamp': datetime.now().isoformat(),
        'details': {}
    }
    
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            result.fetchone()
        
        health['status'] = 'healthy'
        health['details']['connection'] = 'ok'
        
        # Get pool stats
        health['details']['pool'] = get_pool_stats(engine)
        
        # Get query stats
        health['details']['queries'] = query_stats.get_stats()
        
        # Check for warnings
        warnings = []
        pool_stats = health['details']['pool']
        query_data = health['details']['queries']
        
        # Pool warnings
        if pool_stats['checked_out'] > pool_stats['pool_size'] * 0.8:
            warnings.append("High connection pool usage (>80%)")
        
        if pool_stats['overflow'] > 0:
            warnings.append(f"Using overflow connections: {pool_stats['overflow']}")
        
        # Query warnings
        if query_data['slow_queries'] > 0:
            warnings.append(f"{query_data['slow_queries']} slow queries detected")
        
        health['details']['warnings'] = warnings
        
    except Exception as e:
        health['status'] = 'unhealthy'
        health['details']['error'] = str(e)
        logger.error(f"Database health check failed: {e}")
    
    return health


# ============================================================
# PERFORMANCE REPORT
# ============================================================

def generate_performance_report(engine: Engine) -> str:
    """
    Generate human-readable performance report
    
    Args:
        engine: SQLAlchemy engine instance
    
    Returns:
        Formatted performance report
    """
    health = check_database_health(engine)
    
    report = [
        "=" * 60,
        "DATABASE PERFORMANCE REPORT",
        "=" * 60,
        f"Status: {health['status'].upper()}",
        f"Timestamp: {health['timestamp']}",
        "",
        "CONNECTION POOL:",
        f"  Pool Size: {health['details']['pool']['pool_size']}",
        f"  Checked In: {health['details']['pool']['checked_in']}",
        f"  Checked Out: {health['details']['pool']['checked_out']}",
        f"  Overflow: {health['details']['pool']['overflow']}",
        f"  Total: {health['details']['pool']['total_connections']}",
        "",
        "QUERY STATISTICS:",
        f"  Total Queries: {health['details']['queries']['total_queries']}",
        f"  Slow Queries: {health['details']['queries']['slow_queries']}",
        f"  Total Time: {health['details']['queries']['total_time']}s",
        f"  Average Time: {health['details']['queries']['avg_time']}s",
        ""
    ]
    
    # Add warnings
    warnings = health['details'].get('warnings', [])
    if warnings:
        report.append("WARNINGS:")
        for warning in warnings:
            report.append(f"  ⚠️  {warning}")
        report.append("")
    
    # Add recent slow queries
    slow_queries = health['details']['queries'].get('recent_slow_queries', [])
    if slow_queries:
        report.append("RECENT SLOW QUERIES:")
        for i, query in enumerate(slow_queries[-5:], 1):
            report.append(f"  {i}. Duration: {query['duration']:.2f}s")
            report.append(f"     {query['statement']}")
        report.append("")
    
    report.append("=" * 60)
    
    return "\n".join(report)


# ============================================================
# EXPORT
# ============================================================

__all__ = [
    'setup_query_logging',
    'get_pool_stats',
    'log_pool_stats',
    'query_timer',
    'check_database_health',
    'generate_performance_report',
    'query_stats',
    'SLOW_QUERY_THRESHOLD',
    'LOG_ALL_QUERIES'
]
