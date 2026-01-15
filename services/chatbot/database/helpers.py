"""
Database Helpers

Helper functions to integrate database repositories with existing app.py code.
Provides backward-compatible functions that work with both file-based and DB storage.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Check if MongoDB is enabled
MONGODB_ENABLED = os.getenv('MONGODB_ENABLED', 'false').lower() == 'true'

# Import database components if available
try:
    from .repositories.conversation_repository import ConversationRepository
    from .repositories.message_repository import MessageRepository
    from .repositories.memory_repository import MemoryRepository
    from .cache.chatbot_cache import ChatbotCache
    from .utils.session import DatabaseSession, get_db_session
    
    DB_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Database modules not available: {e}")
    DB_AVAILABLE = False


def get_db():
    """Get database instance"""
    if not DB_AVAILABLE:
        return None
    return DatabaseSession().get_database()


def get_conversation_repo() -> Optional[ConversationRepository]:
    """Get ConversationRepository instance"""
    db = get_db()
    if db is None:
        return None
    return ConversationRepository(db)


def get_message_repo() -> Optional[MessageRepository]:
    """Get MessageRepository instance"""
    db = get_db()
    if db is None:
        return None
    return MessageRepository(db)


def get_memory_repo() -> Optional[MemoryRepository]:
    """Get MemoryRepository instance"""
    db = get_db()
    if db is None:
        return None
    return MemoryRepository(db)


# ============================================================================
# Conversation Functions (backward compatible)
# ============================================================================

def load_conversation(
    conversation_id: str,
    fallback_path: Path = None
) -> Optional[Dict[str, Any]]:
    """
    Load conversation from database (with file fallback).
    
    Args:
        conversation_id: Conversation ID
        fallback_path: Path to JSON file for fallback
        
    Returns:
        Conversation dict or None
    """
    # Try cache first
    if DB_AVAILABLE:
        cached = ChatbotCache.get_conversation(conversation_id)
        if cached:
            return cached
    
    # Try database
    repo = get_conversation_repo()
    if repo:
        try:
            conv = repo.get_by_id_with_messages(conversation_id)
            if conv:
                # Cache it
                ChatbotCache.set_conversation(conversation_id, conv)
                return conv
        except Exception as e:
            logger.error(f"Error loading conversation from DB: {e}")
    
    # File fallback
    if fallback_path and fallback_path.exists():
        try:
            with open(fallback_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading conversation from file: {e}")
    
    return None


def save_conversation(
    conversation_id: str,
    data: Dict[str, Any],
    fallback_path: Path = None
) -> bool:
    """
    Save conversation to database (with file fallback).
    
    Args:
        conversation_id: Conversation ID
        data: Conversation data
        fallback_path: Path to JSON file for fallback
        
    Returns:
        True if saved successfully
    """
    # Try database
    repo = get_conversation_repo()
    if repo:
        try:
            existing = repo.get_by_id(conversation_id)
            if existing:
                repo.update(conversation_id, data)
            else:
                data['_id'] = conversation_id
                repo.create(data)
            
            # Invalidate cache
            ChatbotCache.invalidate_conversation(conversation_id)
            return True
            
        except Exception as e:
            logger.error(f"Error saving conversation to DB: {e}")
    
    # File fallback
    if fallback_path:
        try:
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            with open(fallback_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving conversation to file: {e}")
    
    return False


def create_conversation(
    user_id: str,
    title: str = 'New Chat',
    model: str = 'grok',
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Create a new conversation.
    
    Args:
        user_id: User ID
        title: Conversation title
        model: AI model
        **kwargs: Additional fields
        
    Returns:
        Created conversation or None
    """
    repo = get_conversation_repo()
    if repo:
        try:
            conv = repo.create_conversation(
                user_id=user_id,
                title=title,
                model=model,
                **kwargs
            )
            return conv
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
    
    # Fallback: return in-memory object
    import uuid
    return {
        '_id': str(uuid.uuid4()),
        'user_id': user_id,
        'title': title,
        'model': model,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        **kwargs
    }


def delete_conversation(conversation_id: str, fallback_path: Path = None) -> bool:
    """
    Delete a conversation.
    
    Args:
        conversation_id: Conversation ID
        fallback_path: File path for fallback
        
    Returns:
        True if deleted
    """
    repo = get_conversation_repo()
    if repo:
        try:
            repo.delete_conversation_cascade(conversation_id)
            ChatbotCache.invalidate_conversation(conversation_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
    
    # File fallback
    if fallback_path and fallback_path.exists():
        try:
            fallback_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Error deleting conversation file: {e}")
    
    return False


def list_conversations(
    user_id: str,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False
) -> List[Dict[str, Any]]:
    """
    List conversations for a user.
    
    Args:
        user_id: User ID
        skip: Pagination offset
        limit: Max results
        include_archived: Include archived
        
    Returns:
        List of conversations
    """
    # Try cache
    if not include_archived and skip == 0:
        cached = ChatbotCache.get_user_conversations(user_id)
        if cached:
            return cached[:limit]
    
    repo = get_conversation_repo()
    if repo:
        try:
            conversations = repo.get_user_conversations(
                user_id=user_id,
                skip=skip,
                limit=limit,
                include_archived=include_archived
            )
            
            # Cache if first page
            if skip == 0 and not include_archived:
                ChatbotCache.set_user_conversations(user_id, conversations)
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error listing conversations: {e}")
    
    return []


# ============================================================================
# Message Functions
# ============================================================================

def add_message(
    conversation_id: str,
    role: str,
    content: str,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Add a message to a conversation.
    
    Args:
        conversation_id: Conversation ID
        role: 'user', 'assistant', or 'system'
        content: Message content
        **kwargs: Additional fields (metadata, images, etc.)
        
    Returns:
        Created message or None
    """
    repo = get_message_repo()
    if repo:
        try:
            message = repo.add_message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                **kwargs
            )
            
            # Update conversation
            conv_repo = get_conversation_repo()
            if conv_repo:
                conv_repo.increment_message_count(conversation_id)
            
            # Invalidate message cache
            ChatbotCache.invalidate_messages(conversation_id)
            
            return message
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
    
    return None


def get_messages(
    conversation_id: str,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get messages for a conversation.
    
    Args:
        conversation_id: Conversation ID
        limit: Max messages
        
    Returns:
        List of messages
    """
    # Try cache
    cached = ChatbotCache.get_messages(conversation_id)
    if cached:
        return cached[-limit:]
    
    repo = get_message_repo()
    if repo:
        try:
            messages = repo.get_conversation_messages(
                conversation_id=conversation_id,
                limit=limit
            )
            
            # Cache messages
            ChatbotCache.set_messages(conversation_id, messages)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
    
    return []


def get_conversation_history(
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
    repo = get_message_repo()
    if repo:
        try:
            return repo.get_conversation_history_for_ai(
                conversation_id=conversation_id,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Error getting history: {e}")
    
    return []


# ============================================================================
# Memory Functions
# ============================================================================

def save_memory_to_db(
    user_id: str,
    content: str,
    title: str = None,
    category: str = 'general',
    tags: List[str] = None,
    importance: float = 0.5,
    conversation_id: str = None,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    Save a memory to database.
    
    Args:
        user_id: User ID
        content: Memory content
        title: Memory title
        category: Category
        tags: List of tags
        importance: Importance score
        conversation_id: Related conversation
        **kwargs: Additional fields
        
    Returns:
        Created memory or None
    """
    repo = get_memory_repo()
    if repo:
        try:
            memory = repo.save_memory(
                user_id=user_id,
                content=content,
                title=title,
                category=category,
                tags=tags,
                importance=importance,
                conversation_id=conversation_id,
                **kwargs
            )
            
            # Invalidate user memory cache
            ChatbotCache.invalidate_user_memories(user_id)
            
            return memory
            
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
    
    return None


def get_memories(
    user_id: str,
    category: str = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Get memories for a user.
    
    Args:
        user_id: User ID
        category: Filter by category
        limit: Max results
        
    Returns:
        List of memories
    """
    # Try cache
    if not category:
        cached = ChatbotCache.get_user_memories(user_id)
        if cached:
            return cached[:limit]
    
    repo = get_memory_repo()
    if repo:
        try:
            memories = repo.get_user_memories(
                user_id=user_id,
                category=category,
                limit=limit
            )
            
            # Cache if no category filter
            if not category:
                ChatbotCache.set_user_memories(user_id, memories)
            
            return memories
            
        except Exception as e:
            logger.error(f"Error getting memories: {e}")
    
    return []


def search_memories(
    user_id: str,
    query: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search memories by content.
    
    Args:
        user_id: User ID
        query: Search query
        limit: Max results
        
    Returns:
        Matching memories
    """
    repo = get_memory_repo()
    if repo:
        try:
            return repo.search_memories(
                user_id=user_id,
                query=query,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
    
    return []


def delete_memory(memory_id: str, user_id: str = None) -> bool:
    """
    Delete a memory.
    
    Args:
        memory_id: Memory ID
        user_id: User ID (for cache invalidation)
        
    Returns:
        True if deleted
    """
    repo = get_memory_repo()
    if repo:
        try:
            result = repo.delete(memory_id)
            
            if user_id:
                ChatbotCache.invalidate_user_memories(user_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
    
    return False


# ============================================================================
# Utility Functions
# ============================================================================

def check_database_health() -> Dict[str, Any]:
    """
    Check database health status.
    
    Returns:
        Health status dict
    """
    if not DB_AVAILABLE:
        return {'status': 'unavailable', 'reason': 'modules_not_loaded'}
    
    session = DatabaseSession()
    return session.health_check()


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Cache stats dict
    """
    if not DB_AVAILABLE:
        return {'status': 'unavailable'}
    
    return ChatbotCache.get_stats()


def clear_user_cache(user_id: str) -> int:
    """
    Clear all cache for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Number of cleared entries
    """
    if DB_AVAILABLE:
        return ChatbotCache.clear_user_cache(user_id)
    return 0
