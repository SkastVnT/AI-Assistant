"""
ChatBot Memory Repository

Provides data access layer for ChatbotMemory model
"""

import logging
from typing import Optional, List
from sqlalchemy import select, desc, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database.models.chatbot import ChatbotMemory
from database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ChatbotMemoryRepository(BaseRepository[ChatbotMemory]):
    """
    Repository for ChatbotMemory model
    
    Provides specialized methods:
    - get_by_user_id: Get all memories for a user
    - get_by_conversation_id: Get memories from a conversation
    - search_memories: Search memories by question/answer
    - get_by_importance: Get memories above importance threshold
    - get_by_tags: Get memories by tags
    - update_importance: Update memory importance score
    - clear_user_memory: Clear all memories for a user
    """
    
    def __init__(self):
        """Initialize ChatbotMemory repository"""
        super().__init__(ChatbotMemory)
    
    def get_by_user_id(
        self,
        session: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChatbotMemory]:
        """
        Get all memories for a user
        
        Args:
            session: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of memories
        """
        try:
            stmt = select(ChatbotMemory).where(
                ChatbotMemory.user_id == user_id
            ).order_by(desc(ChatbotMemory.importance), desc(ChatbotMemory.created_at)).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting memories for user {user_id}: {e}")
            return []
    
    def get_by_conversation_id(
        self,
        session: Session,
        conversation_id: int
    ) -> List[ChatbotMemory]:
        """
        Get memories from a specific conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            
        Returns:
            List of memories
        """
        try:
            stmt = select(ChatbotMemory).where(
                ChatbotMemory.conversation_id == conversation_id
            ).order_by(desc(ChatbotMemory.importance))
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting memories for conversation {conversation_id}: {e}")
            return []
    
    def search_memories(
        self,
        session: Session,
        user_id: int,
        query: str,
        skip: int = 0,
        limit: int = 50
    ) -> List[ChatbotMemory]:
        """
        Search memories by question or answer
        
        Args:
            session: Database session
            user_id: User ID
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching memories
        """
        try:
            search_pattern = f"%{query}%"
            stmt = select(ChatbotMemory).where(
                ChatbotMemory.user_id == user_id,
                or_(
                    ChatbotMemory.question.ilike(search_pattern),
                    ChatbotMemory.answer.ilike(search_pattern)
                )
            ).order_by(desc(ChatbotMemory.importance)).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error searching memories for user {user_id} with query '{query}': {e}")
            return []
    
    def get_by_importance(
        self,
        session: Session,
        user_id: int,
        min_importance: int = 5,
        skip: int = 0,
        limit: int = 100
    ) -> List[ChatbotMemory]:
        """
        Get memories above importance threshold
        
        Args:
            session: Database session
            user_id: User ID
            min_importance: Minimum importance score
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of important memories
        """
        try:
            stmt = select(ChatbotMemory).where(
                ChatbotMemory.user_id == user_id,
                ChatbotMemory.importance >= min_importance
            ).order_by(desc(ChatbotMemory.importance)).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting high importance memories for user {user_id}: {e}")
            return []
    
    def get_by_tags(
        self,
        session: Session,
        user_id: int,
        tags: List[str],
        skip: int = 0,
        limit: int = 50
    ) -> List[ChatbotMemory]:
        """
        Get memories by tags
        
        Args:
            session: Database session
            user_id: User ID
            tags: List of tags to filter by
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of matching memories
        """
        try:
            # Use PostgreSQL array overlap operator
            stmt = select(ChatbotMemory).where(
                ChatbotMemory.user_id == user_id,
                ChatbotMemory.tags.overlap(tags)
            ).order_by(desc(ChatbotMemory.importance)).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting memories by tags for user {user_id}: {e}")
            return []
    
    def update_importance(
        self,
        session: Session,
        memory_id: int,
        importance: int
    ) -> bool:
        """
        Update memory importance score
        
        Args:
            session: Database session
            memory_id: Memory ID
            importance: New importance score (1-10)
            
        Returns:
            True if updated, False otherwise
        """
        try:
            memory = self.get(session, memory_id)
            if not memory:
                return False
            
            # Clamp importance to 1-10
            importance = max(1, min(10, importance))
            memory.importance = importance
            
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error updating importance for memory {memory_id}: {e}")
            session.rollback()
            return False
    
    def clear_user_memory(
        self,
        session: Session,
        user_id: int,
        conversation_id: Optional[int] = None
    ) -> bool:
        """
        Clear all memories for a user or conversation
        
        Args:
            session: Database session
            user_id: User ID
            conversation_id: Optional conversation ID to limit deletion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if conversation_id:
                # Clear memories from specific conversation
                memories = self.get_by_conversation_id(session, conversation_id)
            else:
                # Clear all user memories
                memories = self.get_by_user_id(session, user_id, limit=10000)
            
            for memory in memories:
                session.delete(memory)
            
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error clearing memories for user {user_id}: {e}")
            session.rollback()
            return False
