"""
Database Package for Chatbot Service

Repository pattern implementation for MongoDB.
"""

from .cache.chatbot_cache import ChatbotCache

# Helper functions for backward compatibility
from .helpers import (
    add_message,
    check_database_health,
    clear_user_cache,
    create_conversation,
    delete_conversation,
    delete_memory,
    get_cache_stats,
    get_conversation_history,
    get_memories,
    get_messages,
    list_conversations,
    load_conversation,
    save_conversation,
    save_memory_to_db,
    search_memories,
)
from .repositories.base_repository import BaseRepository
from .repositories.conversation_repository import ConversationRepository
from .repositories.memory_repository import MemoryRepository
from .repositories.message_repository import MessageRepository
from .utils.session import DatabaseSession, RepositoryFactory, get_db_session

__all__ = [
    # Repositories
    "BaseRepository",
    "ConversationRepository",
    "MessageRepository",
    "MemoryRepository",
    # Cache
    "ChatbotCache",
    # Session
    "get_db_session",
    "DatabaseSession",
    "RepositoryFactory",
    # Helper functions
    "load_conversation",
    "save_conversation",
    "create_conversation",
    "delete_conversation",
    "list_conversations",
    "add_message",
    "get_messages",
    "get_conversation_history",
    "save_memory_to_db",
    "get_memories",
    "search_memories",
    "delete_memory",
    "check_database_health",
    "get_cache_stats",
    "clear_user_cache",
]
