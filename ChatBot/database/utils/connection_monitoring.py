"""
Database connection pool monitoring utilities.

Provides monitoring and diagnostics for SQLAlchemy connection pools.
"""
from typing import Dict, Any, List
from sqlalchemy import text, inspect
from sqlalchemy.pool import Pool
from datetime import datetime

from ..database import db
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionPoolMonitor:
    """Monitor database connection pool health and performance."""
    
    @staticmethod
    def get_pool_status() -> Dict[str, Any]:
        """
        Get current connection pool status.
        
        Returns:
            Dictionary with pool statistics
        """
        pool: Pool = db.engine.pool
        
        return {
            'size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'total_connections': pool.size() + pool.overflow(),
            'timestamp': datetime.utcnow().isoformat(),
        }
    
    @staticmethod
    def get_pool_settings() -> Dict[str, Any]:
        """
        Get connection pool configuration.
        
        Returns:
            Dictionary with pool settings
        """
        pool: Pool = db.engine.pool
        
        return {
            'pool_size': pool.size(),
            'max_overflow': pool._max_overflow,
            'timeout': pool._timeout,
            'pool_recycle': pool._recycle,
            'pool_pre_ping': hasattr(pool, '_pre_ping') and pool._pre_ping,
        }
    
    @staticmethod
    def get_active_connections() -> int:
        """
        Get number of active database connections.
        
        Returns:
            Number of active connections
        """
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                    AND state = 'active'
                """))
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to get active connections: {e}")
            return -1
    
    @staticmethod
    def get_connection_info() -> List[Dict[str, Any]]:
        """
        Get detailed information about all connections.
        
        Returns:
            List of connection details
        """
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        pid,
                        usename,
                        application_name,
                        client_addr,
                        state,
                        query,
                        state_change,
                        EXTRACT(EPOCH FROM (now() - state_change)) as duration_seconds
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                    ORDER BY state_change DESC
                """))
                
                connections = []
                for row in result:
                    connections.append({
                        'pid': row.pid,
                        'user': row.usename,
                        'application': row.application_name,
                        'client_addr': str(row.client_addr) if row.client_addr else None,
                        'state': row.state,
                        'query': row.query,
                        'state_change': row.state_change.isoformat() if row.state_change else None,
                        'duration_seconds': float(row.duration_seconds) if row.duration_seconds else 0,
                    })
                
                return connections
        except Exception as e:
            logger.error(f"Failed to get connection info: {e}")
            return []
    
    @staticmethod
    def get_idle_connections() -> int:
        """
        Get number of idle connections.
        
        Returns:
            Number of idle connections
        """
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT count(*) 
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                    AND state = 'idle'
                """))
                return result.scalar() or 0
        except Exception as e:
            logger.error(f"Failed to get idle connections: {e}")
            return -1
    
    @staticmethod
    def get_long_running_queries(min_duration_seconds: int = 60) -> List[Dict[str, Any]]:
        """
        Get queries running longer than specified duration.
        
        Args:
            min_duration_seconds: Minimum query duration in seconds
            
        Returns:
            List of long-running queries
        """
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        pid,
                        usename,
                        query,
                        state,
                        EXTRACT(EPOCH FROM (now() - query_start)) as duration_seconds,
                        query_start
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                    AND state = 'active'
                    AND query_start IS NOT NULL
                    AND EXTRACT(EPOCH FROM (now() - query_start)) > :min_duration
                    ORDER BY query_start
                """), {'min_duration': min_duration_seconds})
                
                queries = []
                for row in result:
                    queries.append({
                        'pid': row.pid,
                        'user': row.usename,
                        'query': row.query,
                        'state': row.state,
                        'duration_seconds': float(row.duration_seconds),
                        'query_start': row.query_start.isoformat() if row.query_start else None,
                    })
                
                return queries
        except Exception as e:
            logger.error(f"Failed to get long running queries: {e}")
            return []
    
    @staticmethod
    def kill_connection(pid: int) -> bool:
        """
        Kill a database connection by PID.
        
        Args:
            pid: Process ID of connection to kill
            
        Returns:
            True if successful
        """
        try:
            with db.engine.connect() as conn:
                conn.execute(text("SELECT pg_terminate_backend(:pid)"), {'pid': pid})
                logger.warning(f"Killed connection with PID {pid}")
                return True
        except Exception as e:
            logger.error(f"Failed to kill connection {pid}: {e}")
            return False
    
    @staticmethod
    def get_pool_health_score() -> float:
        """
        Calculate connection pool health score (0-100).
        
        Returns:
            Health score (100 = healthy, 0 = unhealthy)
        """
        status = ConnectionPoolMonitor.get_pool_status()
        settings = ConnectionPoolMonitor.get_pool_settings()
        
        total_connections = status['total_connections']
        max_connections = settings['pool_size'] + settings['max_overflow']
        
        # Calculate utilization (0-100%)
        utilization = (total_connections / max_connections * 100) if max_connections > 0 else 0
        
        # Health score inversely proportional to utilization
        # 0-50% utilization = 100 score
        # 50-80% utilization = 80-50 score
        # 80-100% utilization = 50-0 score
        
        if utilization <= 50:
            score = 100.0
        elif utilization <= 80:
            score = 100 - ((utilization - 50) * 1.67)  # Linear decrease
        else:
            score = 50 - ((utilization - 80) * 2.5)  # Faster decrease
        
        return max(0.0, min(100.0, score))
    
    @staticmethod
    def log_pool_status() -> None:
        """Log current pool status and health."""
        status = ConnectionPoolMonitor.get_pool_status()
        health_score = ConnectionPoolMonitor.get_pool_health_score()
        
        logger.info(
            f"Connection Pool Status: "
            f"checked_in={status['checked_in']}, "
            f"checked_out={status['checked_out']}, "
            f"overflow={status['overflow']}, "
            f"health={health_score:.1f}/100"
        )
    
    @staticmethod
    def is_pool_healthy(min_health_score: float = 50.0) -> bool:
        """
        Check if connection pool is healthy.
        
        Args:
            min_health_score: Minimum acceptable health score
            
        Returns:
            True if pool is healthy
        """
        health_score = ConnectionPoolMonitor.get_pool_health_score()
        return health_score >= min_health_score


# Monitoring decorator
def monitor_connections(func):
    """
    Decorator to monitor connection pool before/after function execution.
    
    Usage:
        @monitor_connections
        def my_database_function():
            pass
    """
    def wrapper(*args, **kwargs):
        # Log before
        logger.debug(f"Before {func.__name__}: {ConnectionPoolMonitor.get_pool_status()}")
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Log after
            logger.debug(f"After {func.__name__}: {ConnectionPoolMonitor.get_pool_status()}")
    
    return wrapper
