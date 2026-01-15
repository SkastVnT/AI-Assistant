"""
Memory Repository

Repository for AI memory/knowledge base operations.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid
from pymongo import DESCENDING, ASCENDING, TEXT

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MemoryRepository(BaseRepository):
    """Repository for memory/knowledge base management"""
    
    @property
    def collection_name(self) -> str:
        return 'memories'
    
    # =========================================================================
    # Custom Query Methods
    # =========================================================================
    
    def search_memories(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search memories by content using text search.
        
        Args:
            user_id: User ID
            query: Search query
            limit: Max results
            min_importance: Minimum importance score
            
        Returns:
            Matching memories sorted by relevance
        """
        try:
            # Try text search first
            search_query = {
                'user_id': user_id,
                '$text': {'$search': query},
                'importance': {'$gte': min_importance}
            }
            
            results = self.get_many(
                query=search_query,
                limit=limit,
                projection={'score': {'$meta': 'textScore'}}
            )
            
            if results:
                return results
                
        except Exception:
            # Fallback to regex search if text index not available
            pass
        
        # Regex fallback
        return self.get_many(
            query={
                'user_id': user_id,
                'importance': {'$gte': min_importance},
                '$or': [
                    {'content': {'$regex': query, '$options': 'i'}},
                    {'title': {'$regex': query, '$options': 'i'}},
                    {'tags': {'$in': [query.lower()]}}
                ]
            },
            sort=[('importance', DESCENDING)],
            limit=limit
        )
    
    def get_user_memories(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        category: str = None,
        min_importance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Get all memories for a user.
        
        Args:
            user_id: User ID
            skip: Pagination offset
            limit: Max results
            category: Filter by category
            min_importance: Minimum importance
            
        Returns:
            User's memories sorted by importance
        """
        query = {
            'user_id': user_id,
            'importance': {'$gte': min_importance}
        }
        
        if category:
            query['category'] = category
        
        return self.get_many(
            query=query,
            sort=[('importance', DESCENDING), ('created_at', DESCENDING)],
            skip=skip,
            limit=limit
        )
    
    def save_memory(
        self,
        user_id: str,
        content: str,
        title: str = None,
        category: str = 'general',
        tags: List[str] = None,
        importance: float = 0.5,
        source: str = 'user',
        conversation_id: str = None,
        metadata: Dict[str, Any] = None,
        expires_at: datetime = None
    ) -> Dict[str, Any]:
        """
        Save a new memory entry.
        
        Args:
            user_id: User ID
            content: Memory content
            title: Memory title
            category: Category (general, fact, preference, etc.)
            tags: List of tags
            importance: Importance score (0.0-1.0)
            source: Source of memory (user, conversation, system)
            conversation_id: Related conversation
            metadata: Additional metadata
            expires_at: Expiration datetime
            
        Returns:
            Created memory
        """
        memory = {
            '_id': str(uuid.uuid4()),
            'user_id': user_id,
            'title': title or content[:50] + '...' if len(content) > 50 else content,
            'content': content,
            'category': category,
            'tags': [t.lower() for t in (tags or [])],
            'importance': min(1.0, max(0.0, importance)),
            'source': source,
            'conversation_id': conversation_id,
            'metadata': metadata or {},
            'access_count': 0,
            'last_accessed': None,
            'expires_at': expires_at
        }
        
        return self.create(memory)
    
    def save_qa_memory(
        self,
        user_id: str,
        conversation_id: str,
        question: str,
        answer: str,
        importance: float = 0.5
    ) -> Dict[str, Any]:
        """
        Save a Q&A pair as memory.
        
        Args:
            user_id: User ID
            conversation_id: Related conversation
            question: User's question
            answer: AI's answer
            importance: Importance score
            
        Returns:
            Created memory
        """
        content = f"Q: {question}\n\nA: {answer}"
        
        return self.save_memory(
            user_id=user_id,
            content=content,
            title=question[:100],
            category='qa',
            source='conversation',
            conversation_id=conversation_id,
            importance=importance,
            metadata={
                'question': question,
                'answer': answer
            }
        )
    
    def update_importance(
        self,
        memory_id: str,
        importance: float
    ) -> Optional[Dict[str, Any]]:
        """
        Update memory importance score.
        
        Args:
            memory_id: Memory ID
            importance: New importance (0.0-1.0)
            
        Returns:
            Updated memory
        """
        return self.update(memory_id, {
            'importance': min(1.0, max(0.0, importance))
        })
    
    def increment_access_count(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Increment access count when memory is used.
        
        Args:
            memory_id: Memory ID
            
        Returns:
            Updated memory
        """
        try:
            return self.collection.find_one_and_update(
                {'_id': self._parse_id(memory_id)},
                {
                    '$inc': {'access_count': 1},
                    '$set': {
                        'last_accessed': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                },
                return_document=True
            )
        except Exception as e:
            logger.error(f"Error incrementing access count: {e}")
            return None
    
    def get_by_category(
        self,
        user_id: str,
        category: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get memories by category.
        
        Args:
            user_id: User ID
            category: Memory category
            limit: Max results
            
        Returns:
            Memories in category
        """
        return self.get_many(
            query={'user_id': user_id, 'category': category},
            sort=[('importance', DESCENDING)],
            limit=limit
        )
    
    def get_by_tags(
        self,
        user_id: str,
        tags: List[str],
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get memories by tags.
        
        Args:
            user_id: User ID
            tags: List of tags to match
            limit: Max results
            
        Returns:
            Memories with any matching tag
        """
        return self.get_many(
            query={
                'user_id': user_id,
                'tags': {'$in': [t.lower() for t in tags]}
            },
            sort=[('importance', DESCENDING)],
            limit=limit
        )
    
    def get_important_memories(
        self,
        user_id: str,
        threshold: float = 0.7,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get high-importance memories.
        
        Args:
            user_id: User ID
            threshold: Minimum importance
            limit: Max results
            
        Returns:
            Important memories
        """
        return self.get_many(
            query={
                'user_id': user_id,
                'importance': {'$gte': threshold}
            },
            sort=[('importance', DESCENDING)],
            limit=limit
        )
    
    def get_recent_memories(
        self,
        user_id: str,
        days: int = 7,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recently created memories.
        
        Args:
            user_id: User ID
            days: Look back period
            limit: Max results
            
        Returns:
            Recent memories
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        return self.get_many(
            query={
                'user_id': user_id,
                'created_at': {'$gte': cutoff}
            },
            sort=[('created_at', DESCENDING)],
            limit=limit
        )
    
    def get_frequently_accessed(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most frequently accessed memories.
        
        Args:
            user_id: User ID
            limit: Max results
            
        Returns:
            Most accessed memories
        """
        return self.get_many(
            query={'user_id': user_id, 'access_count': {'$gt': 0}},
            sort=[('access_count', DESCENDING)],
            limit=limit
        )
    
    def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get memory statistics for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Stats dict with counts by category
        """
        pipeline = [
            {'$match': {'user_id': user_id}},
            {
                '$group': {
                    '_id': '$category',
                    'count': {'$sum': 1},
                    'avg_importance': {'$avg': '$importance'}
                }
            }
        ]
        
        results = self.aggregate(pipeline)
        
        stats = {
            'total': self.count({'user_id': user_id}),
            'by_category': {r['_id']: r['count'] for r in results},
            'avg_importance_by_category': {
                r['_id']: round(r['avg_importance'], 2) for r in results
            }
        }
        
        return stats
    
    def cleanup_expired(self) -> int:
        """
        Remove expired memories.
        
        Returns:
            Count of removed memories
        """
        return self.delete_many({
            'expires_at': {'$lte': datetime.utcnow()}
        })
    
    def decay_old_memories(
        self,
        user_id: str,
        days: int = 30,
        decay_factor: float = 0.9
    ) -> int:
        """
        Reduce importance of old, unused memories.
        
        Args:
            user_id: User ID
            days: Age threshold
            decay_factor: Multiply importance by this
            
        Returns:
            Count of updated memories
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            result = self.collection.update_many(
                {
                    'user_id': user_id,
                    'last_accessed': {'$lt': cutoff},
                    'importance': {'$gt': 0.1}
                },
                [
                    {
                        '$set': {
                            'importance': {'$multiply': ['$importance', decay_factor]},
                            'updated_at': datetime.utcnow()
                        }
                    }
                ]
            )
            
            return result.modified_count
            
        except Exception as e:
            logger.error(f"Error decaying memories: {e}")
            return 0
