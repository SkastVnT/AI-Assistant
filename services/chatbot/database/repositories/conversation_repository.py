"""
Conversation Repository

Repository for conversation CRUD operations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from pymongo import DESCENDING, ASCENDING

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ConversationRepository(BaseRepository):
    """Repository for conversation management"""
    
    @property
    def collection_name(self) -> str:
        return 'conversations'
    
    # =========================================================================
    # Custom Query Methods
    # =========================================================================
    
    def get_user_conversations(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user.
        
        Args:
            user_id: User ID
            skip: Pagination offset
            limit: Max results
            include_archived: Include archived conversations
            include_deleted: Include soft-deleted conversations
            
        Returns:
            List of conversations sorted by updated_at desc
        """
        query = {'user_id': user_id}
        
        if not include_archived:
            query['is_archived'] = {'$ne': True}
        
        if not include_deleted:
            query['is_deleted'] = {'$ne': True}
        
        return self.get_many(
            query=query,
            sort=[('updated_at', DESCENDING)],
            skip=skip,
            limit=limit
        )
    
    def get_by_session_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get conversation by session ID.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Conversation dict or None
        """
        return self.get_one({'session_id': session_id, 'is_deleted': {'$ne': True}})
    
    def get_by_id_with_messages(
        self,
        conversation_id: str,
        message_limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Get conversation with its messages (using aggregation).
        
        Args:
            conversation_id: Conversation ID
            message_limit: Max messages to include
            
        Returns:
            Conversation with embedded messages
        """
        try:
            pipeline = [
                {'$match': {'_id': self._parse_id(conversation_id)}},
                {
                    '$lookup': {
                        'from': 'messages',
                        'localField': '_id',
                        'foreignField': 'conversation_id',
                        'pipeline': [
                            {'$sort': {'created_at': ASCENDING}},
                            {'$limit': message_limit}
                        ],
                        'as': 'messages'
                    }
                }
            ]
            
            results = self.aggregate(pipeline)
            return results[0] if results else None
            
        except Exception as e:
            logger.error(f"Error getting conversation with messages: {e}")
            return None
    
    def search_conversations(
        self,
        user_id: str,
        query: str,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search conversations by title or content.
        
        Args:
            user_id: User ID
            query: Search query string
            skip: Pagination offset
            limit: Max results
            
        Returns:
            Matching conversations
        """
        search_query = {
            'user_id': user_id,
            'is_deleted': {'$ne': True},
            '$or': [
                {'title': {'$regex': query, '$options': 'i'}},
                {'summary': {'$regex': query, '$options': 'i'}}
            ]
        }
        
        return self.get_many(
            query=search_query,
            sort=[('updated_at', DESCENDING)],
            skip=skip,
            limit=limit
        )
    
    def archive_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Archive a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Updated conversation
        """
        return self.update(conversation_id, {
            'is_archived': True,
            'archived_at': datetime.utcnow()
        })
    
    def unarchive_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Unarchive a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Updated conversation
        """
        return self.update(conversation_id, {
            'is_archived': False,
            'archived_at': None
        })
    
    def create_conversation(
        self,
        user_id: str,
        title: str = 'New Chat',
        model: str = 'grok',
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation with proper defaults.
        
        Args:
            user_id: User ID
            title: Conversation title
            model: AI model being used
            session_id: Optional session ID
            metadata: Additional metadata
            
        Returns:
            Created conversation
        """
        conv_id = str(uuid.uuid4())
        
        data = {
            '_id': conv_id,
            'user_id': user_id,
            'title': title,
            'model': model,
            'session_id': session_id or conv_id,
            'is_archived': False,
            'is_deleted': False,
            'message_count': 0,
            'metadata': metadata or {}
        }
        
        return self.create(data)
    
    def update_title(self, conversation_id: str, title: str) -> Optional[Dict[str, Any]]:
        """
        Update conversation title.
        
        Args:
            conversation_id: Conversation ID
            title: New title
            
        Returns:
            Updated conversation
        """
        return self.update(conversation_id, {'title': title})
    
    def increment_message_count(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Increment message count for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Updated conversation
        """
        try:
            return self.collection.find_one_and_update(
                {'_id': self._parse_id(conversation_id)},
                {
                    '$inc': {'message_count': 1},
                    '$set': {'updated_at': datetime.utcnow()}
                },
                return_document=True
            )
        except Exception as e:
            logger.error(f"Error incrementing message count: {e}")
            return None
    
    def get_user_conversation_count(
        self,
        user_id: str,
        include_archived: bool = False
    ) -> int:
        """
        Count conversations for a user.
        
        Args:
            user_id: User ID
            include_archived: Include archived
            
        Returns:
            Count of conversations
        """
        query = {'user_id': user_id, 'is_deleted': {'$ne': True}}
        
        if not include_archived:
            query['is_archived'] = {'$ne': True}
        
        return self.count(query)
    
    def get_recent_conversations(
        self,
        user_id: str,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recently active conversations.
        
        Args:
            user_id: User ID
            days: Look back period
            limit: Max results
            
        Returns:
            Recent conversations
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        query = {
            'user_id': user_id,
            'is_deleted': {'$ne': True},
            'updated_at': {'$gte': cutoff}
        }
        
        return self.get_many(
            query=query,
            sort=[('updated_at', DESCENDING)],
            limit=limit
        )
    
    def delete_conversation_cascade(self, conversation_id: str) -> bool:
        """
        Delete conversation and all related messages.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if deleted
        """
        try:
            # Delete messages first
            self.db['messages'].delete_many({
                'conversation_id': self._parse_id(conversation_id)
            })
            
            # Delete conversation
            return self.delete(conversation_id)
            
        except Exception as e:
            logger.error(f"Error in cascade delete: {e}")
            raise
