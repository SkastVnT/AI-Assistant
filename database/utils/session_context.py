"""
Session Context Manager

Provides context manager for database sessions with automatic commit/rollback
"""

from contextlib import contextmanager
from typing import Generator
from sqlalchemy.orm import Session
from database.utils.engine import get_session
import logging

logger = logging.getLogger(__name__)


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions
    
    Automatically handles:
    - Session creation
    - Commit on success
    - Rollback on error
    - Session cleanup
    
    Usage:
        with db_session() as session:
            user = UserRepository().create(session, username="john")
            # Automatically committed
        
        # Session closed, changes committed
    
    Raises:
        Exception: Re-raises any exception after rollback
    """
    session = None
    try:
        # Get session from pool
        session = next(get_session())
        
        # Yield session for use
        yield session
        
        # Commit if no exception
        session.commit()
        logger.debug("Database transaction committed successfully")
        
    except Exception as e:
        # Rollback on any error
        if session:
            session.rollback()
            logger.error(f"Database transaction rolled back due to error: {e}")
        raise
        
    finally:
        # Always close session
        if session:
            session.close()
            logger.debug("Database session closed")


@contextmanager
def db_session_no_commit() -> Generator[Session, None, None]:
    """
    Context manager for read-only database sessions
    
    Does NOT commit changes automatically.
    Use for queries where you don't want automatic commits.
    
    Usage:
        with db_session_no_commit() as session:
            users = UserRepository().get_all(session)
            # No commit, session closed
    """
    session = None
    try:
        session = next(get_session())
        yield session
        
    except Exception as e:
        if session:
            session.rollback()
            logger.error(f"Database error in read-only session: {e}")
        raise
        
    finally:
        if session:
            session.close()
