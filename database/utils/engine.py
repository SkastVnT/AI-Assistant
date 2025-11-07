"""
Database Engine and Session Management

Provides singleton database engine with connection pooling and session management
"""

import os
import logging
from typing import Generator, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool, NullPool

logger = logging.getLogger(__name__)


class DatabaseEngine:
    """
    Singleton database engine manager with connection pooling
    
    Usage:
        engine = DatabaseEngine.get_engine()
        session = DatabaseEngine.get_session()
    """
    
    _instance: Optional['DatabaseEngine'] = None
    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None
    _scoped_session: Optional[scoped_session] = None
    
    def __new__(cls):
        """Singleton pattern - only one instance"""
        if cls._instance is None:
            cls._instance = super(DatabaseEngine, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(
        cls,
        database_url: Optional[str] = None,
        echo: bool = False,
        pool_size: int = 20,
        max_overflow: int = 30,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        use_null_pool: bool = False
    ) -> Engine:
        """
        Initialize database engine with optimized connection pooling for production
        
        Args:
            database_url: PostgreSQL connection string (default from env)
            echo: Whether to log SQL statements
            pool_size: Number of connections to maintain (default: 20 for production)
            max_overflow: Maximum overflow connections (default: 30 for production)
            pool_timeout: Seconds to wait for connection
            pool_recycle: Recycle connections after N seconds (default: 1800 for stability)
            use_null_pool: Use NullPool (for testing/serverless)
        
        Returns:
            SQLAlchemy Engine instance
        
        Production Recommendations:
            - pool_size: 20-50 depending on concurrent users
            - max_overflow: 1.5x pool_size for burst traffic
            - pool_recycle: 1800 (30min) to prevent stale connections
            - pool_pre_ping: True to verify connections
        """
        if cls._engine is not None:
            logger.warning("Database engine already initialized")
            return cls._engine
        
        # Get database URL from environment or parameter
        if database_url is None:
            database_url = os.getenv(
                "DATABASE_URL",
                "postgresql://postgres:postgres@localhost:5432/ai_assistant"
            )
        
        # Convert postgres:// to postgresql:// (for compatibility)
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        logger.info(f"Initializing database engine: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
        
        # Connection arguments
        connect_args = {
            "connect_timeout": 10,
            "options": "-c timezone=utc"
        }
        
        # Pool class selection
        poolclass = NullPool if use_null_pool else QueuePool
        
        # Create engine
        cls._engine = create_engine(
            database_url,
            echo=echo,
            poolclass=poolclass,
            pool_size=pool_size if not use_null_pool else 0,
            max_overflow=max_overflow if not use_null_pool else 0,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            pool_pre_ping=True,  # Verify connections before using
            connect_args=connect_args,
            future=True  # SQLAlchemy 2.0 style
        )
        
        # Setup event listeners
        cls._setup_event_listeners(cls._engine)
        
        # Create session factory
        cls._session_factory = sessionmaker(
            bind=cls._engine,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        
        # Create scoped session for thread-safety
        cls._scoped_session = scoped_session(cls._session_factory)
        
        logger.info("Database engine initialized successfully")
        return cls._engine
    
    @classmethod
    def _setup_event_listeners(cls, engine: Engine) -> None:
        """Setup SQLAlchemy event listeners"""
        
        @event.listens_for(engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Handle new database connections"""
            logger.debug("New database connection established")
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Handle connection checkout from pool"""
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Handle connection return to pool"""
            logger.debug("Connection returned to pool")
    
    @classmethod
    def get_engine(cls) -> Engine:
        """
        Get database engine (initialize if not exists)
        
        Returns:
            SQLAlchemy Engine instance
        """
        if cls._engine is None:
            cls.initialize()
        return cls._engine
    
    @classmethod
    def get_session_factory(cls) -> sessionmaker:
        """
        Get session factory
        
        Returns:
            SQLAlchemy sessionmaker instance
        """
        if cls._session_factory is None:
            cls.initialize()
        return cls._session_factory
    
    @classmethod
    def get_scoped_session(cls) -> scoped_session:
        """
        Get scoped session (thread-local)
        
        Returns:
            Scoped session instance
        """
        if cls._scoped_session is None:
            cls.initialize()
        return cls._scoped_session
    
    @classmethod
    def dispose(cls) -> None:
        """Close all connections and dispose engine"""
        if cls._engine is not None:
            logger.info("Disposing database engine")
            cls._scoped_session.remove() if cls._scoped_session else None
            cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None
            cls._scoped_session = None
    
    @classmethod
    def get_pool_status(cls) -> dict:
        """
        Get connection pool status
        
        Returns:
            Dictionary with pool statistics
        """
        if cls._engine is None or isinstance(cls._engine.pool, NullPool):
            return {"pool_type": "NullPool", "status": "No pooling"}
        
        pool = cls._engine.pool
        return {
            "pool_type": pool.__class__.__name__,
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow()
        }


class SessionManager:
    """
    Context manager for database sessions
    
    Usage:
        with SessionManager() as session:
            user = session.query(User).first()
    """
    
    def __init__(self, auto_commit: bool = True):
        """
        Initialize session manager
        
        Args:
            auto_commit: Whether to auto-commit on successful exit
        """
        self.auto_commit = auto_commit
        self.session: Optional[Session] = None
    
    def __enter__(self) -> Session:
        """Enter context - create session"""
        session_factory = DatabaseEngine.get_session_factory()
        self.session = session_factory()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - commit or rollback"""
        if self.session is None:
            return
        
        try:
            if exc_type is None and self.auto_commit:
                # No exception - commit
                self.session.commit()
                logger.debug("Session committed successfully")
            else:
                # Exception occurred - rollback
                self.session.rollback()
                logger.warning("Session rolled back due to exception")
        except Exception as e:
            logger.error(f"Error during session cleanup: {e}")
            self.session.rollback()
        finally:
            self.session.close()


@contextmanager
def get_session(auto_commit: bool = True) -> Generator[Session, None, None]:
    """
    Get database session as context manager
    
    Usage:
        with get_session() as session:
            user = session.query(User).first()
    
    Args:
        auto_commit: Whether to auto-commit on success
    
    Yields:
        SQLAlchemy Session instance
    """
    session_factory = DatabaseEngine.get_session_factory()
    session = session_factory()
    
    try:
        yield session
        
        if auto_commit:
            session.commit()
            logger.debug("Session committed")
    except Exception as e:
        session.rollback()
        logger.error(f"Session error: {e}")
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for FastAPI/Flask
    
    Usage (FastAPI):
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    
    Yields:
        SQLAlchemy Session instance
    """
    session_factory = DatabaseEngine.get_session_factory()
    session = session_factory()
    
    try:
        yield session
    finally:
        session.close()


# Convenience function
def init_db(database_url: Optional[str] = None, **kwargs) -> Engine:
    """
    Initialize database with optional parameters
    
    Args:
        database_url: PostgreSQL connection string
        **kwargs: Additional engine parameters
    
    Returns:
        SQLAlchemy Engine instance
    """
    return DatabaseEngine.initialize(database_url=database_url, **kwargs)
