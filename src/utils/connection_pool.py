"""
Connection Pool
Database and Redis connection pooling
"""

import time
import logging
from typing import Any, Optional, Callable
from threading import Lock, Semaphore
from queue import Queue, Empty
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class PooledConnection:
    """Wrapper for pooled connections."""
    
    def __init__(self, connection: Any, pool: 'ConnectionPool', created_at: float = None):
        self.connection = connection
        self.pool = pool
        self.created_at = created_at or time.time()
        self.last_used = time.time()
        self.use_count = 0
    
    def is_stale(self, max_age: float) -> bool:
        """Check if connection is stale."""
        return time.time() - self.created_at > max_age
    
    def is_idle_timeout(self, idle_timeout: float) -> bool:
        """Check if connection has exceeded idle timeout."""
        return time.time() - self.last_used > idle_timeout
    
    def touch(self) -> None:
        """Update last used time."""
        self.last_used = time.time()
        self.use_count += 1


class ConnectionPool:
    """
    Generic connection pool with health checking.
    """
    
    def __init__(self,
                 factory: Callable[[], Any],
                 max_size: int = 10,
                 min_size: int = 2,
                 max_age: float = 3600,
                 idle_timeout: float = 300,
                 health_check: Callable[[Any], bool] = None,
                 on_close: Callable[[Any], None] = None):
        """
        Initialize connection pool.
        
        Args:
            factory: Function to create new connections
            max_size: Maximum pool size
            min_size: Minimum pool size (pre-created)
            max_age: Maximum connection age in seconds
            idle_timeout: Idle timeout in seconds
            health_check: Function to check connection health
            on_close: Function to close connection
        """
        self.factory = factory
        self.max_size = max_size
        self.min_size = min_size
        self.max_age = max_age
        self.idle_timeout = idle_timeout
        self.health_check = health_check
        self.on_close = on_close
        
        self._pool: Queue = Queue(maxsize=max_size)
        self._size = 0
        self._lock = Lock()
        self._semaphore = Semaphore(max_size)
        
        # Pre-create minimum connections
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        """Initialize pool with minimum connections."""
        for _ in range(self.min_size):
            try:
                conn = self._create_connection()
                if conn:
                    self._pool.put(conn)
            except Exception as e:
                logger.warning(f"Failed to pre-create connection: {e}")
    
    def _create_connection(self) -> Optional[PooledConnection]:
        """Create a new pooled connection."""
        with self._lock:
            if self._size >= self.max_size:
                return None
            
            try:
                conn = self.factory()
                self._size += 1
                return PooledConnection(conn, self)
            except Exception as e:
                logger.error(f"Failed to create connection: {e}")
                return None
    
    def _is_healthy(self, pooled_conn: PooledConnection) -> bool:
        """Check if connection is healthy."""
        if pooled_conn.is_stale(self.max_age):
            return False
        
        if pooled_conn.is_idle_timeout(self.idle_timeout):
            return False
        
        if self.health_check:
            try:
                return self.health_check(pooled_conn.connection)
            except Exception:
                return False
        
        return True
    
    def _close_connection(self, pooled_conn: PooledConnection) -> None:
        """Close a connection."""
        with self._lock:
            self._size -= 1
        
        if self.on_close:
            try:
                self.on_close(pooled_conn.connection)
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
    
    @contextmanager
    def get_connection(self, timeout: float = 30):
        """
        Get a connection from the pool.
        
        Args:
            timeout: Timeout waiting for connection
        
        Yields:
            Connection from pool
        """
        if not self._semaphore.acquire(timeout=timeout):
            raise TimeoutError("Timeout waiting for connection from pool")
        
        pooled_conn = None
        
        try:
            # Try to get existing connection
            while True:
                try:
                    pooled_conn = self._pool.get_nowait()
                    
                    if self._is_healthy(pooled_conn):
                        break
                    else:
                        self._close_connection(pooled_conn)
                        pooled_conn = None
                
                except Empty:
                    break
            
            # Create new if needed
            if pooled_conn is None:
                pooled_conn = self._create_connection()
                
                if pooled_conn is None:
                    raise RuntimeError("Failed to create connection")
            
            pooled_conn.touch()
            yield pooled_conn.connection
        
        finally:
            if pooled_conn:
                try:
                    self._pool.put_nowait(pooled_conn)
                except:
                    self._close_connection(pooled_conn)
            
            self._semaphore.release()
    
    def close_all(self) -> None:
        """Close all connections in pool."""
        while True:
            try:
                pooled_conn = self._pool.get_nowait()
                self._close_connection(pooled_conn)
            except Empty:
                break
    
    @property
    def size(self) -> int:
        """Get current pool size."""
        return self._size
    
    @property
    def available(self) -> int:
        """Get available connections."""
        return self._pool.qsize()
    
    def stats(self) -> dict:
        """Get pool statistics."""
        return {
            'size': self._size,
            'available': self.available,
            'max_size': self.max_size,
            'min_size': self.min_size
        }


class MongoDBPool(ConnectionPool):
    """MongoDB connection pool."""
    
    def __init__(self, uri: str, database: str, **kwargs):
        from pymongo import MongoClient
        
        self.uri = uri
        self.database = database
        
        def factory():
            client = MongoClient(uri)
            return client[database]
        
        def health_check(db):
            db.command('ping')
            return True
        
        def on_close(db):
            db.client.close()
        
        super().__init__(
            factory=factory,
            health_check=health_check,
            on_close=on_close,
            **kwargs
        )


class RedisPool(ConnectionPool):
    """Redis connection pool."""
    
    def __init__(self, host: str = 'localhost', port: int = 6379, 
                 password: str = None, db: int = 0, **kwargs):
        import redis
        
        def factory():
            return redis.Redis(
                host=host,
                port=port,
                password=password,
                db=db,
                decode_responses=True
            )
        
        def health_check(client):
            return client.ping()
        
        def on_close(client):
            client.close()
        
        super().__init__(
            factory=factory,
            health_check=health_check,
            on_close=on_close,
            **kwargs
        )
