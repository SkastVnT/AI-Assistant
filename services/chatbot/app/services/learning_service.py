"""
Learning Service

Handles AI self-learning from conversations and user feedback.
Stores learning data locally and in database for future fine-tuning.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class LearningService:
    """Service for AI self-learning capabilities"""
    
    def __init__(self):
        # Local storage path for learning data
        self.local_data_path = Path(__file__).parent.parent.parent / 'local_data' / 'learning'
        self.local_data_path.mkdir(parents=True, exist_ok=True)
        
        # Archived conversations path
        self.archive_path = self.local_data_path / 'archived_conversations'
        self.archive_path.mkdir(parents=True, exist_ok=True)
        
        # Learning data path
        self.qa_data_path = self.local_data_path / 'qa_pairs'
        self.qa_data_path.mkdir(parents=True, exist_ok=True)
        
        # Quality thresholds
        self.min_quality_auto_approve = float(os.getenv('LEARNING_MIN_QUALITY', '0.8'))
        self.min_response_length = 100  # Minimum response length to consider
    
    def submit(
        self,
        source: str,
        category: str,
        data: Dict[str, Any],
        quality_score: float = 0.5
    ) -> Dict[str, Any]:
        """
        Submit new learning data
        
        Args:
            source: Data source (conversation, manual, feedback)
            category: Category (qa, knowledge, preference)
            data: The learning data
            quality_score: Initial quality score (0-1)
        
        Returns:
            Created learning data entry
        """
        entry = {
            '_id': str(uuid.uuid4()),
            'source': source,
            'category': category,
            'data': data,
            'quality_score': quality_score,
            'is_approved': quality_score >= self.min_quality_auto_approve,
            'created_at': datetime.now().isoformat(),
            'reviewed_at': None,
            'rejection_reason': None
        }
        
        # Save to local file
        self._save_learning_entry(entry)
        
        # Also save to MongoDB if available
        self._save_to_database(entry)
        
        logger.info(f"📚 Learning data submitted: {entry['_id']} (quality: {quality_score})")
        
        return entry
    
    def submit_qa_pair(
        self,
        question: str,
        answer: str,
        source: str,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """Submit a Q&A pair for learning"""
        # Calculate quality score based on heuristics
        quality = self._calculate_qa_quality(question, answer)
        
        return self.submit(
            source=source,
            category='qa',
            data={
                'question': question,
                'answer': answer
            },
            quality_score=quality
        )
    
    def archive_conversation(self, conversation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Archive a deleted conversation for potential learning
        
        Args:
            conversation: Full conversation with messages
        
        Returns:
            Archived conversation entry
        """
        # Determine if conversation should be used for learning
        should_learn = self._should_learn_from_conversation(conversation)
        
        archive_entry = {
            '_id': str(uuid.uuid4()),
            'original_id': str(conversation.get('_id', '')),
            'original_user_id': conversation.get('user_id'),
            'title': conversation.get('title'),
            'model': conversation.get('model'),
            'messages': conversation.get('messages', []),
            'message_count': len(conversation.get('messages', [])),
            'deleted_at': datetime.now().isoformat(),
            'should_learn': should_learn,
            'learning_extracted': False
        }
        
        # Save to local file
        archive_file = self.archive_path / f"{archive_entry['_id']}.json"
        with open(archive_file, 'w', encoding='utf-8') as f:
            json.dump(archive_entry, f, ensure_ascii=False, indent=2)
        
        logger.info(f"📁 Conversation archived: {archive_entry['_id']} (learn: {should_learn})")
        
        return archive_entry
    
    def extract_qa_pairs(
        self,
        messages: List[Dict],
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        Extract Q&A pairs from conversation messages
        
        Args:
            messages: List of conversation messages
            auto_approve: Auto-approve high quality pairs
        
        Returns:
            Dict with count and extracted items
        """
        extracted = []
        
        # Group messages into user-assistant pairs
        i = 0
        while i < len(messages) - 1:
            if messages[i].get('role') == 'user' and messages[i+1].get('role') == 'assistant':
                question = messages[i].get('content', '')
                answer = messages[i+1].get('content', '')
                
                # Check quality
                quality = self._calculate_qa_quality(question, answer)
                
                if quality >= 0.5:  # Only extract decent quality pairs
                    entry = self.submit(
                        source='conversation_extraction',
                        category='qa',
                        data={'question': question, 'answer': answer},
                        quality_score=quality
                    )
                    extracted.append(entry)
                
                i += 2
            else:
                i += 1
        
        return {
            'count': len(extracted),
            'items': extracted
        }
    
    def list_data(
        self,
        category: Optional[str] = None,
        is_approved: Optional[bool] = None,
        min_quality: float = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List learning data entries"""
        entries = []
        
        # Load from local files
        for file_path in self.qa_data_path.glob('*.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                    
                    # Apply filters
                    if category and entry.get('category') != category:
                        continue
                    if is_approved is not None and entry.get('is_approved') != is_approved:
                        continue
                    if entry.get('quality_score', 0) < min_quality:
                        continue
                    
                    entries.append(entry)
            except Exception as e:
                logger.warning(f"Error loading learning data {file_path}: {e}")
        
        # Sort by quality and date
        entries.sort(key=lambda x: (x.get('quality_score', 0), x.get('created_at', '')), reverse=True)
        
        return entries[:limit]
    
    def approve(self, data_id: str) -> Dict[str, Any]:
        """Approve learning data"""
        return self._update_entry(data_id, {
            'is_approved': True,
            'reviewed_at': datetime.now().isoformat()
        })
    
    def reject(self, data_id: str, reason: str) -> Dict[str, Any]:
        """Reject learning data"""
        return self._update_entry(data_id, {
            'is_approved': False,
            'rejection_reason': reason,
            'reviewed_at': datetime.now().isoformat()
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning system statistics"""
        total = 0
        approved = 0
        pending = 0
        rejected = 0
        by_category = {}
        avg_quality = 0
        
        for file_path in self.qa_data_path.glob('*.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    entry = json.load(f)
                    total += 1
                    avg_quality += entry.get('quality_score', 0)
                    
                    if entry.get('is_approved'):
                        approved += 1
                    elif entry.get('rejection_reason'):
                        rejected += 1
                    else:
                        pending += 1
                    
                    cat = entry.get('category', 'unknown')
                    by_category[cat] = by_category.get(cat, 0) + 1
            except Exception as e:
                # Skip invalid entries
                logger.debug(f"Skipping invalid learning entry: {e}")
                pass
        
        archived_count = len(list(self.archive_path.glob('*.json')))
        
        return {
            'total_entries': total,
            'approved': approved,
            'pending': pending,
            'rejected': rejected,
            'by_category': by_category,
            'average_quality': avg_quality / total if total > 0 else 0,
            'archived_conversations': archived_count
        }
    
    def list_archived_conversations(
        self,
        should_learn: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """List archived deleted conversations"""
        conversations = []
        
        for file_path in self.archive_path.glob('*.json'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    conv = json.load(f)
                    
                    if should_learn is not None and conv.get('should_learn') != should_learn:
                        continue
                    
                    # Return summary, not full messages
                    conversations.append({
                        '_id': conv.get('_id'),
                        'original_id': conv.get('original_id'),
                        'title': conv.get('title'),
                        'model': conv.get('model'),
                        'message_count': conv.get('message_count'),
                        'deleted_at': conv.get('deleted_at'),
                        'should_learn': conv.get('should_learn'),
                        'learning_extracted': conv.get('learning_extracted')
                    })
            except Exception as e:
                logger.warning(f"Error loading archived conversation: {e}")
        
        return sorted(conversations, key=lambda x: x.get('deleted_at', ''), reverse=True)
    
    def _calculate_qa_quality(self, question: str, answer: str) -> float:
        """Calculate quality score for a Q&A pair"""
        score = 0.5  # Base score
        
        # Length checks
        if len(question) > 20:
            score += 0.1
        if len(answer) > self.min_response_length:
            score += 0.1
        if len(answer) > 500:
            score += 0.1
        
        # Content quality indicators
        if '```' in answer:  # Has code blocks
            score += 0.1
        if any(word in answer.lower() for word in ['ví dụ', 'example', 'để', 'because']):
            score += 0.05
        
        # Negative indicators
        if answer.startswith('Lỗi') or answer.startswith('Error'):
            score -= 0.3
        if 'không thể' in answer.lower() or "can't" in answer.lower():
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _should_learn_from_conversation(self, conversation: Dict[str, Any]) -> bool:
        """Determine if conversation is worth learning from"""
        messages = conversation.get('messages', [])
        
        # Minimum messages required
        if len(messages) < 4:
            return False
        
        # Check for quality responses
        quality_count = 0
        for msg in messages:
            if msg.get('role') == 'assistant':
                content = msg.get('content', '')
                if len(content) > 200 and not content.startswith('Lỗi'):
                    quality_count += 1
        
        return quality_count >= 2
    
    def _save_learning_entry(self, entry: Dict[str, Any]) -> None:
        """Save learning entry to local file"""
        file_path = self.qa_data_path / f"{entry['_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
    
    def _update_entry(self, data_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a learning entry"""
        file_path = self.qa_data_path / f"{data_id}.json"
        
        if not file_path.exists():
            raise ValueError(f"Learning data not found: {data_id}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            entry = json.load(f)
        
        entry.update(updates)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
        
        return entry
    
    def _save_to_database(self, entry: Dict[str, Any]) -> None:
        """Save learning entry to MongoDB (if available)"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                db.learning_data.insert_one(entry)
        except Exception as e:
            logger.debug(f"Could not save to database: {e}")
