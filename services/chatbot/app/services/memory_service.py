"""
Memory Service

Handles AI memory/knowledge base management.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for memory/knowledge base management"""
    
    def __init__(self):
        # In-memory storage fallback
        self._memories: Dict[str, Dict] = {}
    
    def create(
        self,
        user_id: str,
        title: str,
        content: str,
        category: str = 'general',
        tags: List[str] = None,
        importance: float = 0.5
    ) -> Dict[str, Any]:
        """Create a new memory entry"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            memory = {
                '_id': str(uuid.uuid4()),
                'user_id': user_id,
                'title': title,
                'content': content,
                'category': category,
                'tags': tags or [],
                'importance': importance,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            if client:
                db = client.get_database('ai_assistant')
                db.memories.insert_one(memory)
            else:
                self._memories[memory['_id']] = memory
            
            return memory
            
        except Exception as e:
            logger.error(f"Error creating memory: {e}")
            raise
    
    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory by ID"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                return db.memories.find_one({'_id': memory_id})
            else:
                return self._memories.get(memory_id)
                
        except Exception as e:
            logger.error(f"Error getting memory: {e}")
            return None
    
    def list_by_user(
        self,
        user_id: str,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List memories for a user"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                query = {'user_id': user_id}
                if category:
                    query['category'] = category
                
                cursor = db.memories.find(query).sort('importance', -1).limit(limit)
                return list(cursor)
            else:
                memories = [m for m in self._memories.values() if m['user_id'] == user_id]
                if category:
                    memories = [m for m in memories if m.get('category') == category]
                memories.sort(key=lambda x: x.get('importance', 0), reverse=True)
                return memories[:limit]
                
        except Exception as e:
            logger.error(f"Error listing memories: {e}")
            return []
    
    def update(self, memory_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a memory"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            updates['updated_at'] = datetime.now().isoformat()
            
            if client:
                db = client.get_database('ai_assistant')
                db.memories.update_one({'_id': memory_id}, {'$set': updates})
                return db.memories.find_one({'_id': memory_id})
            else:
                if memory_id in self._memories:
                    self._memories[memory_id].update(updates)
                    return self._memories[memory_id]
                raise ValueError("Memory not found")
                
        except Exception as e:
            logger.error(f"Error updating memory: {e}")
            raise
    
    def delete(self, memory_id: str) -> bool:
        """Delete a memory"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                db.memories.delete_one({'_id': memory_id})
            else:
                if memory_id in self._memories:
                    del self._memories[memory_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            raise
    
    def search(
        self,
        user_id: str,
        query: str = '',
        tags: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Search memories by text or tags"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                
                pipeline = [{'$match': {'user_id': user_id}}]
                
                if query:
                    pipeline.append({
                        '$match': {
                            '$or': [
                                {'title': {'$regex': query, '$options': 'i'}},
                                {'content': {'$regex': query, '$options': 'i'}}
                            ]
                        }
                    })
                
                if tags:
                    pipeline.append({'$match': {'tags': {'$in': tags}}})
                
                pipeline.append({'$sort': {'importance': -1}})
                pipeline.append({'$limit': 50})
                
                return list(db.memories.aggregate(pipeline))
            else:
                memories = [m for m in self._memories.values() if m['user_id'] == user_id]
                
                if query:
                    query_lower = query.lower()
                    memories = [
                        m for m in memories
                        if query_lower in m.get('title', '').lower() 
                        or query_lower in m.get('content', '').lower()
                    ]
                
                if tags:
                    memories = [
                        m for m in memories
                        if any(tag in m.get('tags', []) for tag in tags)
                    ]
                
                memories.sort(key=lambda x: x.get('importance', 0), reverse=True)
                return memories[:50]
                
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []
    
    def search_relevant(
        self,
        user_id: str,
        message: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find memories relevant to a message (for AI context)"""
        # Simple keyword matching for now
        # TODO: Implement semantic search with embeddings
        
        words = message.lower().split()
        if not words:
            return []
        
        # Search for memories containing message keywords
        all_memories = self.list_by_user(user_id, limit=100)
        
        scored_memories = []
        for memory in all_memories:
            score = 0
            content = f"{memory.get('title', '')} {memory.get('content', '')}".lower()
            
            for word in words:
                if len(word) > 3 and word in content:
                    score += 1
            
            if score > 0:
                scored_memories.append((score, memory))
        
        # Sort by relevance score
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        return [m[1] for m in scored_memories[:limit]]
