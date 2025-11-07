"""
User Repository

Provides data access layer for User model
"""

import logging
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database.models.user import User
from database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    """
    Repository for User model
    
    Provides specialized methods:
    - get_by_username: Find user by username
    - get_by_email: Find user by email
    - update_last_login: Update last login timestamp
    - search_users: Search users by username/email/name
    - get_active_users: Get all active users
    - get_admin_users: Get all admin users
    """
    
    def __init__(self):
        """Initialize User repository"""
        super().__init__(User)
    
    def get_by_username(
        self,
        session: Session,
        username: str
    ) -> Optional[User]:
        """
        Get user by username
        
        Args:
            session: Database session
            username: Username to search for
            
        Returns:
            User or None if not found
        """
        try:
            stmt = select(User).where(User.username == username)
            result = session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by username '{username}': {e}")
            return None
    
    def get_by_email(
        self,
        session: Session,
        email: str
    ) -> Optional[User]:
        """
        Get user by email
        
        Args:
            session: Database session
            email: Email to search for
            
        Returns:
            User or None if not found
        """
        try:
            stmt = select(User).where(User.email == email)
            result = session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by email '{email}': {e}")
            return None
    
    def update_last_login(
        self,
        session: Session,
        user_id: int
    ) -> bool:
        """
        Update user's last login timestamp
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            True if updated, False otherwise
        """
        try:
            user = self.get(session, user_id)
            if not user:
                return False
            
            user.last_login = datetime.utcnow()
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            session.rollback()
            return False
    
    def search_users(
        self,
        session: Session,
        query: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[User]:
        """
        Search users by username, email, or full name
        
        Args:
            session: Database session
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching users
        """
        try:
            search_pattern = f"%{query}%"
            stmt = select(User).where(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.full_name.ilike(search_pattern)
                )
            ).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error searching users with query '{query}': {e}")
            return []
    
    def get_active_users(
        self,
        session: Session,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """
        Get all active users
        
        Args:
            session: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active users
        """
        try:
            stmt = select(User).where(
                User.is_active == True
            ).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def get_admin_users(
        self,
        session: Session
    ) -> List[User]:
        """
        Get all admin users
        
        Args:
            session: Database session
            
        Returns:
            List of admin users
        """
        try:
            stmt = select(User).where(User.is_admin == True)
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting admin users: {e}")
            return []
    
    def deactivate_user(
        self,
        session: Session,
        user_id: int
    ) -> bool:
        """
        Deactivate user account
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            True if deactivated, False otherwise
        """
        try:
            user = self.get(session, user_id)
            if not user:
                return False
            
            user.is_active = False
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deactivating user {user_id}: {e}")
            session.rollback()
            return False
    
    def activate_user(
        self,
        session: Session,
        user_id: int
    ) -> bool:
        """
        Activate user account
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            True if activated, False otherwise
        """
        try:
            user = self.get(session, user_id)
            if not user:
                return False
            
            user.is_active = True
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error activating user {user_id}: {e}")
            session.rollback()
            return False
    
    def count_active_users(
        self,
        session: Session
    ) -> int:
        """
        Count active users
        
        Args:
            session: Database session
            
        Returns:
            Number of active users
        """
        try:
            stmt = select(func.count()).select_from(User).where(
                User.is_active == True
            )
            result = session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting active users: {e}")
            return 0
