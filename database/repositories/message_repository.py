"""
Message Repository

Provides data access layer for Message model
"""

import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import select, desc, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database.models.chatbot import Message, MessageRole
from database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class MessageRepository(BaseRepository[Message]):
    """
    Repository for Message model
    
    Provides specialized methods:
    - get_by_conversation_id: Get all messages in a conversation
    - get_recent_messages: Get most recent messages
    - search_by_content: Search messages by content
    - bulk_create: Create multiple messages at once
    - get_by_role: Get messages by role (user/assistant/system)
    - get_next_sequence_number: Get next sequence number for conversation
    """
    
    def __init__(self):
        """Initialize Message repository"""
        super().__init__(Message)
    
    def get_by_conversation_id(
        self,
        session: Session,
        conversation_id: int,
        skip: int = 0,
        limit: Optional[int] = None,
        order_desc: bool = False
    ) -> List[Message]:
        """
        Get all messages in a conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            skip: Number of records to skip
            limit: Maximum number of records to return (None for all)
            order_desc: Order by sequence number descending
            
        Returns:
            List of messages
        """
        try:
            stmt = select(Message).where(
                Message.conversation_id == conversation_id
            )
            
            # Order by sequence number
            if order_desc:
                stmt = stmt.order_by(desc(Message.sequence_number))
            else:
                stmt = stmt.order_by(Message.sequence_number)
            
            # Apply pagination
            stmt = stmt.offset(skip)
            if limit:
                stmt = stmt.limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting messages for conversation {conversation_id}: {e}")
            return []
    
    def get_recent_messages(
        self,
        session: Session,
        conversation_id: int,
        limit: int = 50
    ) -> List[Message]:
        """
        Get most recent messages in a conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            limit: Maximum number of messages to return
            
        Returns:
            List of recent messages (ordered oldest to newest)
        """
        try:
            # Get most recent messages in descending order
            stmt = select(Message).where(
                Message.conversation_id == conversation_id
            ).order_by(desc(Message.sequence_number)).limit(limit)
            
            result = session.execute(stmt)
            messages = list(result.scalars().all())
            
            # Reverse to get oldest to newest
            return list(reversed(messages))
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent messages for conversation {conversation_id}: {e}")
            return []
    
    def search_by_content(
        self,
        session: Session,
        query: str,
        conversation_id: Optional[int] = None,
        role: Optional[MessageRole] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Message]:
        """
        Search messages by content
        
        Args:
            session: Database session
            query: Search query string
            conversation_id: Optional conversation ID to filter
            role: Optional role filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching messages
        """
        try:
            search_pattern = f"%{query}%"
            stmt = select(Message).where(
                Message.content.ilike(search_pattern)
            )
            
            # Apply filters
            if conversation_id:
                stmt = stmt.where(Message.conversation_id == conversation_id)
            if role:
                stmt = stmt.where(Message.role == role)
            
            # Order by most recent first
            stmt = stmt.order_by(desc(Message.created_at)).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error searching messages with query '{query}': {e}")
            return []
    
    def bulk_create(
        self,
        session: Session,
        messages_data: List[Dict[str, Any]]
    ) -> List[Message]:
        """
        Create multiple messages at once
        
        Args:
            session: Database session
            messages_data: List of message data dictionaries
            
        Returns:
            List of created messages
        """
        try:
            messages = []
            for data in messages_data:
                message = Message(**data)
                messages.append(message)
            
            session.add_all(messages)
            session.flush()
            
            # Refresh all to get IDs
            for message in messages:
                session.refresh(message)
            
            return messages
        except SQLAlchemyError as e:
            logger.error(f"Error bulk creating messages: {e}")
            session.rollback()
            return []
    
    def get_by_role(
        self,
        session: Session,
        conversation_id: int,
        role: MessageRole,
        skip: int = 0,
        limit: int = 100
    ) -> List[Message]:
        """
        Get messages by role in a conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            role: Message role (user/assistant/system)
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of messages with specified role
        """
        try:
            stmt = select(Message).where(
                Message.conversation_id == conversation_id,
                Message.role == role
            ).order_by(Message.sequence_number).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting messages by role '{role}' for conversation {conversation_id}: {e}")
            return []
    
    def get_next_sequence_number(
        self,
        session: Session,
        conversation_id: int
    ) -> int:
        """
        Get next sequence number for conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            
        Returns:
            Next sequence number
        """
        try:
            stmt = select(func.max(Message.sequence_number)).where(
                Message.conversation_id == conversation_id
            )
            result = session.execute(stmt).scalar()
            return (result or 0) + 1
        except SQLAlchemyError as e:
            logger.error(f"Error getting next sequence number for conversation {conversation_id}: {e}")
            return 1
    
    def get_message_count(
        self,
        session: Session,
        conversation_id: int,
        role: Optional[MessageRole] = None
    ) -> int:
        """
        Count messages in conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            role: Optional role filter
            
        Returns:
            Message count
        """
        try:
            stmt = select(func.count()).select_from(Message).where(
                Message.conversation_id == conversation_id
            )
            
            if role:
                stmt = stmt.where(Message.role == role)
            
            result = session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting messages for conversation {conversation_id}: {e}")
            return 0
    
    def get_edited_messages(
        self,
        session: Session,
        conversation_id: int
    ) -> List[Message]:
        """
        Get all edited messages in a conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            
        Returns:
            List of edited messages
        """
        try:
            stmt = select(Message).where(
                Message.conversation_id == conversation_id,
                Message.is_edited == True
            ).order_by(Message.sequence_number)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting edited messages for conversation {conversation_id}: {e}")
            return []
    
    def delete_conversation_messages(
        self,
        session: Session,
        conversation_id: int
    ) -> bool:
        """
        Delete all messages in a conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            messages = self.get_by_conversation_id(session, conversation_id)
            for message in messages:
                session.delete(message)
            
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting messages for conversation {conversation_id}: {e}")
            session.rollback()
            return False
