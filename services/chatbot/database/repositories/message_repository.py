"""
Message Repository

Repository for message CRUD operations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from pymongo import ASCENDING, DESCENDING

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MessageRepository(BaseRepository):
    """Repository for message management"""
    
    @property
    def collection_name(self) -> str:
        return 'messages'
    
    # =========================================================================
    # Custom Query Methods
    # =========================================================================
    
    def get_conversation_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        skip: int = 0,
        order: str = 'asc'
    ) -> List[Dict[str, Any]]:
        """
        Get all messages for a conversation.
        
        Args:
            conversation_id: Conversation ID
            limit: Max messages
            skip: Pagination offset
            order: 'asc' or 'desc' by created_at
            
        Returns:
            List of messages
        """
        sort_dir = ASCENDING if order == 'asc' else DESCENDING
        
        return self.get_many(
            query={'conversation_id': conversation_id},
            sort=[('created_at', sort_dir)],
            skip=skip,
            limit=limit
        )
    
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Dict[str, Any] = None,
        images: List[str] = None,
        tokens: int = None
    ) -> Dict[str, Any]:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: Conversation ID
            role: 'user', 'assistant', or 'system'
            content: Message content
            metadata: Additional metadata
            images: List of image URLs/paths
            tokens: Token count
            
        Returns:
            Created message
        """
        message = {
            '_id': str(uuid.uuid4()),
            'conversation_id': conversation_id,
            'role': role,
            'content': content,
            'metadata': metadata or {},
            'images': images or [],
            'tokens': tokens,
            'is_edited': False,
            'edit_history': []
        }
        
        return self.create(message)
    
    def edit_message(
        self,
        message_id: str,
        new_content: str,
        reason: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Edit a message and save history.
        
        Args:
            message_id: Message ID
            new_content: New content
            reason: Edit reason
            
        Returns:
            Updated message
        """
        try:
            # Get current message
            current = self.get_by_id(message_id)
            if not current:
                return None
            
            # Create edit history entry
            edit_entry = {
                'old_content': current.get('content'),
                'edited_at': datetime.utcnow(),
                'reason': reason
            }
            
            # Update with history
            return self.collection.find_one_and_update(
                {'_id': self._parse_id(message_id)},
                {
                    '$set': {
                        'content': new_content,
                        'is_edited': True,
                        'updated_at': datetime.utcnow()
                    },
                    '$push': {'edit_history': edit_entry}
                },
                return_document=True
            )
            
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            raise
    
    def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most recent messages for context.
        
        Args:
            conversation_id: Conversation ID
            limit: Max messages
            
        Returns:
            Recent messages in chronological order
        """
        # Get in desc order then reverse
        messages = self.get_many(
            query={'conversation_id': conversation_id},
            sort=[('created_at', DESCENDING)],
            limit=limit
        )
        
        return list(reversed(messages))
    
    def get_messages_by_role(
        self,
        conversation_id: str,
        role: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get messages filtered by role.
        
        Args:
            conversation_id: Conversation ID
            role: Message role
            limit: Max messages
            
        Returns:
            Messages with specified role
        """
        return self.get_many(
            query={
                'conversation_id': conversation_id,
                'role': role
            },
            sort=[('created_at', ASCENDING)],
            limit=limit
        )
    
    def get_message_count(self, conversation_id: str) -> int:
        """
        Count messages in a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Message count
        """
        return self.count({'conversation_id': conversation_id})
    
    def get_last_message(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent message.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Last message or None
        """
        messages = self.get_many(
            query={'conversation_id': conversation_id},
            sort=[('created_at', DESCENDING)],
            limit=1
        )
        
        return messages[0] if messages else None
    
    def get_last_user_message(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent user message.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Last user message or None
        """
        messages = self.get_many(
            query={
                'conversation_id': conversation_id,
                'role': 'user'
            },
            sort=[('created_at', DESCENDING)],
            limit=1
        )
        
        return messages[0] if messages else None
    
    def delete_conversation_messages(self, conversation_id: str) -> int:
        """
        Delete all messages for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Count of deleted messages
        """
        return self.delete_many({'conversation_id': conversation_id})
    
    def search_messages(
        self,
        conversation_id: str,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search messages by content.
        
        Args:
            conversation_id: Conversation ID
            query: Search query
            limit: Max results
            
        Returns:
            Matching messages
        """
        return self.get_many(
            query={
                'conversation_id': conversation_id,
                'content': {'$regex': query, '$options': 'i'}
            },
            sort=[('created_at', ASCENDING)],
            limit=limit
        )
    
    def get_messages_with_images(
        self,
        conversation_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get messages that contain images.
        
        Args:
            conversation_id: Conversation ID
            limit: Max results
            
        Returns:
            Messages with images
        """
        return self.get_many(
            query={
                'conversation_id': conversation_id,
                'images': {'$exists': True, '$ne': []}
            },
            sort=[('created_at', DESCENDING)],
            limit=limit
        )
    
    def get_conversation_history_for_ai(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, str]]:
        """
        Get conversation history formatted for AI context.
        
        Args:
            conversation_id: Conversation ID
            limit: Max messages
            
        Returns:
            List of {role, content} dicts
        """
        messages = self.get_recent_messages(conversation_id, limit * 2)
        
        history = []
        for msg in messages[-limit * 2:]:
            history.append({
                'role': msg.get('role', 'user'),
                'content': msg.get('content', '')
            })
        
        return history
    
    def get_token_count(self, conversation_id: str) -> int:
        """
        Get total token count for a conversation.
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            Total tokens
        """
        pipeline = [
            {'$match': {'conversation_id': conversation_id}},
            {'$group': {'_id': None, 'total': {'$sum': '$tokens'}}}
        ]
        
        results = self.aggregate(pipeline)
        return results[0]['total'] if results else 0
