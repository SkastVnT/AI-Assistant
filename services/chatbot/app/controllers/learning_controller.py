"""
Learning Controller

Handles AI self-learning operations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..services.learning_service import LearningService

logger = logging.getLogger(__name__)


class LearningController:
    """Controller for AI learning operations"""
    
    def __init__(self):
        self.learning_service = LearningService()
    
    def list_learning_data(
        self,
        category: Optional[str] = None,
        is_approved: Optional[bool] = None,
        min_quality: float = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """List learning data entries"""
        try:
            data = self.learning_service.list_data(
                category=category,
                is_approved=is_approved,
                min_quality=min_quality,
                limit=limit
            )
            
            return {
                'data': data,
                'total': len(data)
            }
            
        except Exception as e:
            logger.error(f"❌ Error listing learning data: {e}")
            raise
    
    def submit_learning_data(
        self,
        source: str,
        category: str,
        data: Dict[str, Any],
        quality_score: float = 0.5
    ) -> Dict[str, Any]:
        """Submit new learning data"""
        try:
            result = self.learning_service.submit(
                source=source,
                category=category,
                data=data,
                quality_score=quality_score
            )
            
            logger.info(f"✅ Submitted learning data: {result.get('_id')}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error submitting learning data: {e}")
            raise
    
    def approve_learning_data(self, data_id: str) -> Dict[str, Any]:
        """Approve learning data for use"""
        try:
            result = self.learning_service.approve(data_id)
            logger.info(f"✅ Approved learning data: {data_id}")
            return result
        except Exception as e:
            logger.error(f"❌ Error approving learning data: {e}")
            raise
    
    def reject_learning_data(
        self,
        data_id: str,
        reason: str = 'Manual rejection'
    ) -> Dict[str, Any]:
        """Reject learning data"""
        try:
            result = self.learning_service.reject(data_id, reason)
            logger.info(f"✅ Rejected learning data: {data_id} - {reason}")
            return result
        except Exception as e:
            logger.error(f"❌ Error rejecting learning data: {e}")
            raise
    
    def extract_from_conversation(
        self,
        conversation_id: str,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """Extract learning data from a conversation"""
        try:
            from .conversation_controller import ConversationController
            conv_controller = ConversationController()
            
            # Get conversation with messages
            conv = conv_controller.get_conversation(conversation_id)
            
            if not conv:
                raise ValueError("Conversation not found")
            
            # Extract Q&A pairs
            extracted = self.learning_service.extract_qa_pairs(
                messages=conv.get('messages', []),
                auto_approve=auto_approve
            )
            
            logger.info(f"✅ Extracted {extracted['count']} learning items from conversation")
            
            return {
                'conversation_id': conversation_id,
                'extracted_count': extracted['count'],
                'items': extracted['items']
            }
            
        except Exception as e:
            logger.error(f"❌ Error extracting learning data: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning system statistics"""
        try:
            return self.learning_service.get_stats()
        except Exception as e:
            logger.error(f"❌ Error getting learning stats: {e}")
            raise
    
    def list_deleted_conversations(
        self,
        should_learn: Optional[bool] = None
    ) -> Dict[str, Any]:
        """List archived deleted conversations"""
        try:
            conversations = self.learning_service.list_archived_conversations(
                should_learn=should_learn
            )
            
            return {
                'conversations': conversations,
                'total': len(conversations)
            }
            
        except Exception as e:
            logger.error(f"❌ Error listing deleted conversations: {e}")
            raise
