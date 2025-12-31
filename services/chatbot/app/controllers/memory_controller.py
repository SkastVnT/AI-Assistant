"""
Memory Controller

Handles memory/knowledge base operations.
"""

import logging
from typing import Dict, Any, List, Optional

from ..services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class MemoryController:
    """Controller for memory operations"""
    
    def __init__(self):
        self.memory_service = MemoryService()
    
    def list_memories(
        self,
        user_id: str,
        category: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """List memories for a user"""
        try:
            memories = self.memory_service.list_by_user(
                user_id=user_id,
                category=category,
                limit=limit
            )
            
            return {
                'memories': memories,
                'total': len(memories)
            }
            
        except Exception as e:
            logger.error(f"❌ Error listing memories: {e}")
            raise
    
    def create_memory(
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
            memory = self.memory_service.create(
                user_id=user_id,
                title=title,
                content=content,
                category=category,
                tags=tags or [],
                importance=importance
            )
            
            logger.info(f"✅ Created memory: {memory.get('_id')}")
            return memory
            
        except Exception as e:
            logger.error(f"❌ Error creating memory: {e}")
            raise
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a memory by ID"""
        try:
            return self.memory_service.get(memory_id)
        except Exception as e:
            logger.error(f"❌ Error getting memory: {e}")
            raise
    
    def update_memory(
        self,
        memory_id: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        importance: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update a memory entry"""
        try:
            updates = {}
            
            if title is not None:
                updates['title'] = title
            if content is not None:
                updates['content'] = content
            if category is not None:
                updates['category'] = category
            if tags is not None:
                updates['tags'] = tags
            if importance is not None:
                updates['importance'] = importance
            
            memory = self.memory_service.update(memory_id, updates)
            
            logger.info(f"✅ Updated memory: {memory_id}")
            return memory
            
        except Exception as e:
            logger.error(f"❌ Error updating memory: {e}")
            raise
    
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a memory entry"""
        try:
            self.memory_service.delete(memory_id)
            
            logger.info(f"✅ Deleted memory: {memory_id}")
            return {'deleted': True, 'memory_id': memory_id}
            
        except Exception as e:
            logger.error(f"❌ Error deleting memory: {e}")
            raise
    
    def search_memories(
        self,
        user_id: str,
        query: str = '',
        tags: List[str] = None
    ) -> Dict[str, Any]:
        """Search memories by text or tags"""
        try:
            memories = self.memory_service.search(
                user_id=user_id,
                query=query,
                tags=tags or []
            )
            
            return {
                'memories': memories,
                'total': len(memories),
                'query': query,
                'tags': tags
            }
            
        except Exception as e:
            logger.error(f"❌ Error searching memories: {e}")
            raise
