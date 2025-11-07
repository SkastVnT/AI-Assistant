"""
API Dependencies

Provides dependency injection for FastAPI routes
"""

from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.utils.engine import get_session


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency for getting database session
    
    Usage:
        @app.get("/users")
        def get_users(session: Session = Depends(get_db_session)):
            ...
    """
    session = None
    try:
        session = next(get_session())
        yield session
        session.commit()
    except Exception as e:
        if session:
            session.rollback()
        raise
    finally:
        if session:
            session.close()
