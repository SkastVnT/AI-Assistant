"""
Conversation Repository

Provides data access layer for Conversation model
"""

import logging
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError

from database.models.chatbot import Conversation
from database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ConversationRepository(BaseRepository[Conversation]):
    """
    Repository for Conversation model
    
    Provides specialized methods:
    - get_by_uuid: Find conversation by UUID
    - get_by_user_id: Get all conversations for a user
    - get_active_conversations: Get non-archived conversations
    - get_pinned_conversations: Get pinned conversations
    - get_with_messages: Load conversation with all messages
    - update_metadata: Update conversation metadata
    - archive_conversation: Archive a conversation
    - pin_conversation: Pin/unpin a conversation
    """
    
    def __init__(self):
        """Initialize Conversation repository"""
        super().__init__(Conversation)
    
    def get_by_uuid(
        self,
        session: Session,
        conversation_uuid: UUID
    ) -> Optional[Conversation]:
        """
        Get conversation by UUID
        
        Args:
            session: Database session
            conversation_uuid: Conversation UUID
            
        Returns:
            Conversation or None if not found
        """
        try:
            stmt = select(Conversation).where(
                Conversation.conversation_uuid == conversation_uuid
            )
            result = session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting conversation by UUID '{conversation_uuid}': {e}")
            return None
    
    def get_by_user_id(
        self,
        session: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False
    ) -> List[Conversation]:
        """
        Get all conversations for a user
        
        Args:
            session: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            include_archived: Include archived conversations
            
        Returns:
            List of conversations
        """
        try:
            stmt = select(Conversation).where(Conversation.user_id == user_id)
            
            if not include_archived:
                stmt = stmt.where(Conversation.is_archived == False)
            
            # Order by pinned first, then by most recent
            stmt = stmt.order_by(
                desc(Conversation.is_pinned),
                desc(Conversation.updated_at)
            ).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting conversations for user {user_id}: {e}")
            return []
    
    def get_active_conversations(
        self,
        session: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Conversation]:
        """
        Get active (non-archived) conversations for a user
        
        Args:
            session: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active conversations
        """
        return self.get_by_user_id(
            session=session,
            user_id=user_id,
            skip=skip,
            limit=limit,
            include_archived=False
        )
    
    def get_pinned_conversations(
        self,
        session: Session,
        user_id: int
    ) -> List[Conversation]:
        """
        Get pinned conversations for a user
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            List of pinned conversations
        """
        try:
            stmt = select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.is_pinned == True
            ).order_by(desc(Conversation.updated_at))
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting pinned conversations for user {user_id}: {e}")
            return []
    
    def get_with_messages(
        self,
        session: Session,
        conversation_id: int,
        message_limit: Optional[int] = None
    ) -> Optional[Conversation]:
        """
        Load conversation with all messages (eager loading)
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            message_limit: Optional limit on number of messages to load
            
        Returns:
            Conversation with messages or None if not found
        """
        try:
            stmt = select(Conversation).where(
                Conversation.id == conversation_id
            ).options(joinedload(Conversation.messages))
            
            result = session.execute(stmt)
            conversation = result.unique().scalar_one_or_none()
            
            # If message limit specified, slice the messages
            if conversation and message_limit:
                conversation.messages = conversation.messages[-message_limit:]
            
            return conversation
        except SQLAlchemyError as e:
            logger.error(f"Error getting conversation {conversation_id} with messages: {e}")
            return None
    
    def update_metadata(
        self,
        session: Session,
        conversation_id: int,
        metadata: Dict[str, Any]
    ) -> Optional[Conversation]:
        """
        Update conversation metadata
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            metadata: Metadata dictionary to update
            
        Returns:
            Updated conversation or None if not found
        """
        try:
            conversation = self.get(session, conversation_id)
            if not conversation:
                return None
            
            # Merge with existing metadata
            if conversation.metadata:
                conversation.metadata.update(metadata)
            else:
                conversation.metadata = metadata
            
            session.flush()
            session.refresh(conversation)
            return conversation
        except SQLAlchemyError as e:
            logger.error(f"Error updating metadata for conversation {conversation_id}: {e}")
            session.rollback()
            return None
    
    def archive_conversation(
        self,
        session: Session,
        conversation_id: int,
        archive: bool = True
    ) -> bool:
        """
        Archive or unarchive a conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            archive: True to archive, False to unarchive
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conversation = self.get(session, conversation_id)
            if not conversation:
                return False
            
            conversation.is_archived = archive
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error archiving conversation {conversation_id}: {e}")
            session.rollback()
            return False
    
    def pin_conversation(
        self,
        session: Session,
        conversation_id: int,
        pin: bool = True
    ) -> bool:
        """
        Pin or unpin a conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            pin: True to pin, False to unpin
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conversation = self.get(session, conversation_id)
            if not conversation:
                return False
            
            conversation.is_pinned = pin
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error pinning conversation {conversation_id}: {e}")
            session.rollback()
            return False
    
    def update_message_count(
        self,
        session: Session,
        conversation_id: int
    ) -> bool:
        """
        Update cached message count for conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from database.models.chatbot import Message
            
            stmt = select(func.count()).select_from(Message).where(
                Message.conversation_id == conversation_id
            )
            count = session.execute(stmt).scalar() or 0
            
            conversation = self.get(session, conversation_id)
            if not conversation:
                return False
            
            conversation.message_count = count
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating message count for conversation {conversation_id}: {e}")
            session.rollback()
            return False
    
    def get_by_tags(
        self,
        session: Session,
        user_id: int,
        tags: List[str],
        skip: int = 0,
        limit: int = 50
    ) -> List[Conversation]:
        """
        Get conversations by tags
        
        Args:
            session: Database session
            user_id: User ID
            tags: List of tags to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching conversations
        """
        try:
            # Use PostgreSQL array overlap operator
            stmt = select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.tags.overlap(tags)
            ).order_by(desc(Conversation.updated_at)).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting conversations by tags for user {user_id}: {e}")
            return []
    
    def count_user_conversations(
        self,
        session: Session,
        user_id: int,
        include_archived: bool = False
    ) -> int:
        """
        Count conversations for a user
        
        Args:
            session: Database session
            user_id: User ID
            include_archived: Include archived conversations
            
        Returns:
            Count of conversations
        """
        try:
            stmt = select(func.count()).select_from(Conversation).where(
                Conversation.user_id == user_id
            )
            
            if not include_archived:
                stmt = stmt.where(Conversation.is_archived == False)
            
            result = session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting conversations for user {user_id}: {e}")
            return 0
