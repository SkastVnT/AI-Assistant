"""
Conversation Controller

Handles conversation management operations.
"""

import logging
from typing import Dict, Any, Optional

from ..services.conversation_service import ConversationService
from ..services.learning_service import LearningService

logger = logging.getLogger(__name__)


class ConversationController:
    """Controller for conversation operations"""
    
    def __init__(self):
        self.conversation_service = ConversationService()
        self.learning_service = LearningService()
    
    def list_conversations(
        self,
        user_id: str,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List conversations for a user
        
        Returns:
            Dict with conversations list and total count
        """
        try:
            conversations = self.conversation_service.list_by_user(
                user_id=user_id,
                include_archived=include_archived,
                limit=limit,
                offset=offset
            )
            
            total = self.conversation_service.count_by_user(
                user_id=user_id,
                include_archived=include_archived
            )
            
            return {
                'conversations': conversations,
                'total': total,
                'limit': limit,
                'offset': offset
            }
            
        except Exception as e:
            logger.error(f"❌ Error listing conversations: {e}")
            raise
    
    def get_conversation(
        self,
        conversation_id: str,
        message_limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Get a conversation with its messages
        
        Returns:
            Conversation dict with messages, or None if not found
        """
        try:
            conv = self.conversation_service.get(conversation_id)
            
            if not conv:
                return None
            
            messages = self.conversation_service.get_messages(
                conversation_id=conversation_id,
                limit=message_limit
            )
            
            conv['messages'] = messages
            return conv
            
        except Exception as e:
            logger.error(f"❌ Error getting conversation: {e}")
            raise
    
    def create_conversation(
        self,
        user_id: str,
        title: str = 'New Chat',
        model: str = 'grok'
    ) -> Dict[str, Any]:
        """Create a new conversation"""
        try:
            conv = self.conversation_service.create(
                user_id=user_id,
                model=model,
                title=title
            )
            
            logger.info(f"✅ Created conversation: {conv.get('_id')}")
            return conv
            
        except Exception as e:
            logger.error(f"❌ Error creating conversation: {e}")
            raise
    
    def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        is_archived: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Update conversation metadata"""
        try:
            updates = {}
            
            if title is not None:
                updates['title'] = title
            
            if is_archived is not None:
                updates['is_archived'] = is_archived
            
            if not updates:
                return self.conversation_service.get(conversation_id)
            
            conv = self.conversation_service.update(conversation_id, updates)
            
            logger.info(f"✅ Updated conversation: {conversation_id}")
            return conv
            
        except Exception as e:
            logger.error(f"❌ Error updating conversation: {e}")
            raise
    
    def delete_conversation(
        self,
        conversation_id: str,
        save_for_learning: bool = True
    ) -> Dict[str, Any]:
        """
        Delete a conversation
        
        If save_for_learning is True, the conversation is archived
        to local_data for AI learning review.
        """
        try:
            # Get conversation with messages before deletion
            conv = self.get_conversation(conversation_id)
            
            if not conv:
                raise ValueError("Conversation not found")
            
            # Archive for learning if enabled
            if save_for_learning and len(conv.get('messages', [])) > 2:
                self.learning_service.archive_conversation(conv)
                logger.info(f"📚 Archived conversation for learning: {conversation_id}")
            
            # Delete from database
            self.conversation_service.delete(conversation_id)
            
            logger.info(f"✅ Deleted conversation: {conversation_id}")
            
            return {
                'deleted': True,
                'conversation_id': conversation_id,
                'archived_for_learning': save_for_learning
            }
            
        except Exception as e:
            logger.error(f"❌ Error deleting conversation: {e}")
            raise
