"""
ChatBot Database Service

High-level service layer for ChatBot operations with Redis caching
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from database.utils.session_context import db_session
from database.repositories import (
    UserRepository,
    ConversationRepository,
    MessageRepository,
    ChatbotMemoryRepository,
    UploadedFileRepository
)
from database.models.chatbot import MessageRole

# Import caching utilities
try:
    from database.utils.cache import (
        UserCache, ConversationCache, MessageCache, MemoryCache,
        cache_client, get_cache
    )
    CACHE_ENABLED = True
except Exception as e:
    CACHE_ENABLED = False
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ Cache not available: {e}")

logger = logging.getLogger(__name__)


class ChatBotService:
    """
    Service layer for ChatBot operations
    
    Provides high-level methods that combine multiple repository operations
    and handle business logic.
    """
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.conv_repo = ConversationRepository()
        self.msg_repo = MessageRepository()
        self.memory_repo = ChatbotMemoryRepository()
        self.file_repo = UploadedFileRepository()
    
    # ========================================================================
    # User Management
    # ========================================================================
    
    def get_or_create_user(
        self,
        username: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get existing user or create new one (with caching)
        
        Args:
            username: Username
            email: Optional email
            full_name: Optional full name
            
        Returns:
            User dict with id, username, email, etc.
        """
        # Try cache first
        if CACHE_ENABLED and cache_client:
            try:
                cached = cache_client.get(UserCache.get_username_key(username))
                if cached:
                    import json
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        with db_session() as session:
            # Try to find existing user
            user = self.user_repo.get_by_username(session, username)
            
            if not user:
                # Create new user
                user = self.user_repo.create(
                    session,
                    username=username,
                    email=email,
                    full_name=full_name
                )
                logger.info(f"Created new user: {username} (ID: {user.id})")
            else:
                # Update last login
                self.user_repo.update_last_login(session, user.id)
            
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "last_login": user.last_login
            }
            
            # Cache the result
            if CACHE_ENABLED and cache_client:
                try:
                    UserCache.cache_user(user_data, ttl=3600)
                except Exception as e:
                    logger.warning(f"Cache write error: {e}")
            
            return user_data
    
    # ========================================================================
    # Conversation Management
    # ========================================================================
    
    def create_conversation(
        self,
        user_id: int,
        title: str = "New Conversation",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create new conversation
        
        Args:
            user_id: User ID
            title: Conversation title
            tags: Optional tags
            metadata: Optional metadata
            
        Returns:
            Conversation dict with id, uuid, title, etc.
        """
        with db_session() as session:
            conversation = self.conv_repo.create(
                session,
                user_id=user_id,
                title=title,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            logger.info(f"Created conversation {conversation.id} for user {user_id}")
            
            return {
                "id": conversation.id,
                "uuid": str(conversation.conversation_uuid),
                "user_id": conversation.user_id,
                "title": conversation.title,
                "tags": conversation.tags,
                "metadata": conversation.metadata,
                "created_at": conversation.created_at.isoformat(),
                "message_count": 0
            }
    
    def get_conversation(
        self,
        conversation_id: int,
        include_messages: bool = False,
        message_limit: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get conversation by ID (with caching)
        
        Args:
            conversation_id: Conversation ID
            include_messages: Include messages in response
            message_limit: Limit number of messages
            
        Returns:
            Conversation dict or None
        """
        # Try cache for conversation without messages
        if not include_messages and CACHE_ENABLED and cache_client:
            try:
                import json
                cached = cache_client.get(ConversationCache.get_conversation_key(conversation_id))
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        with db_session() as session:
            if include_messages:
                conversation = self.conv_repo.get_with_messages(
                    session,
                    conversation_id,
                    message_limit=message_limit
                )
            else:
                conversation = self.conv_repo.get(session, conversation_id)
            
            if not conversation:
                return None
            
            result = {
                "id": conversation.id,
                "uuid": str(conversation.conversation_uuid),
                "user_id": conversation.user_id,
                "title": conversation.title,
                "tags": conversation.tags,
                "metadata": conversation.metadata,
                "is_archived": conversation.is_archived,
                "is_pinned": conversation.is_pinned,
                "created_at": conversation.created_at.isoformat(),
                "updated_at": conversation.updated_at.isoformat(),
                "message_count": conversation.message_count
            }
            
            if include_messages:
                result["messages"] = [
                    {
                        "id": msg.id,
                        "role": msg.role.value,
                        "content": msg.content,
                        "sequence_number": msg.sequence_number,
                        "created_at": msg.created_at.isoformat()
                    }
                    for msg in conversation.messages
                ]
            else:
                # Cache conversation without messages
                if CACHE_ENABLED and cache_client:
                    try:
                        ConversationCache.cache_conversation(result, ttl=1800)
                    except Exception as e:
                        logger.warning(f"Cache write error: {e}")
            
            return result
    
    def list_user_conversations(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """
        List conversations for a user
        
        Args:
            user_id: User ID
            skip: Number to skip
            limit: Max to return
            include_archived: Include archived conversations
            
        Returns:
            List of conversation dicts
        """
        with db_session() as session:
            conversations = self.conv_repo.get_by_user_id(
                session,
                user_id=user_id,
                skip=skip,
                limit=limit,
                include_archived=include_archived
            )
            
            return [
                {
                    "id": conv.id,
                    "uuid": str(conv.conversation_uuid),
                    "title": conv.title,
                    "tags": conv.tags,
                    "is_archived": conv.is_archived,
                    "is_pinned": conv.is_pinned,
                    "created_at": conv.created_at.isoformat(),
                    "updated_at": conv.updated_at.isoformat(),
                    "message_count": conv.message_count
                }
                for conv in conversations
            ]
    
    def delete_conversation(self, conversation_id: int) -> bool:
        """
        Delete conversation (cascade deletes messages, etc.) and invalidate cache
        
        Args:
            conversation_id: Conversation ID
            
        Returns:
            True if deleted
        """
        with db_session() as session:
            success = self.conv_repo.delete(session, conversation_id, soft_delete=False)
            if success:
                # Invalidate cache
                if CACHE_ENABLED and cache_client:
                    try:
                        ConversationCache.invalidate_conversation(conversation_id)
                        MessageCache.invalidate_messages(conversation_id)
                    except Exception as e:
                        logger.warning(f"Cache invalidation error: {e}")
                
                logger.info(f"Deleted conversation {conversation_id}")
            return success
    
    def archive_conversation(self, conversation_id: int) -> bool:
        """Archive conversation"""
        with db_session() as session:
            return self.conv_repo.archive_conversation(session, conversation_id, archive=True)
    
    def pin_conversation(self, conversation_id: int) -> bool:
        """Pin conversation"""
        with db_session() as session:
            return self.conv_repo.pin_conversation(session, conversation_id, pin=True)
    
    # ========================================================================
    # Message Management
    # ========================================================================
    
    def save_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Save message to conversation (invalidates cache)
        
        Args:
            conversation_id: Conversation ID
            role: Message role (user/assistant/system)
            content: Message content
            model: Optional model name
            metadata: Optional metadata
            tool_results: Optional tool execution results
            
        Returns:
            Message dict
        """
        with db_session() as session:
            # Get next sequence number
            seq_num = self.msg_repo.get_next_sequence_number(session, conversation_id)
            
            # Create message
            message = self.msg_repo.create(
                session,
                conversation_id=conversation_id,
                role=MessageRole(role),
                content=content,
                model=model,
                sequence_number=seq_num,
                metadata=metadata or {},
                tool_results=tool_results or []
            )
            
            # Update conversation message count
            self.conv_repo.update_message_count(session, conversation_id)
            
            # Invalidate conversation cache
            if CACHE_ENABLED and cache_client:
                try:
                    ConversationCache.invalidate_conversation(conversation_id)
                    MessageCache.invalidate_messages(conversation_id)
                except Exception as e:
                    logger.warning(f"Cache invalidation error: {e}")
            
            logger.info(f"Saved message {message.id} to conversation {conversation_id}")
            
            return {
                "id": message.id,
                "conversation_id": message.conversation_id,
                "role": message.role.value,
                "content": message.content,
                "model": message.model,
                "sequence_number": message.sequence_number,
                "tool_results": message.tool_results,
                "created_at": message.created_at.isoformat()
            }
    
    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages for conversation
        
        Args:
            conversation_id: Conversation ID
            limit: Optional limit (gets most recent if specified)
            
        Returns:
            List of message dicts
        """
        with db_session() as session:
            if limit:
                messages = self.msg_repo.get_recent_messages(session, conversation_id, limit)
            else:
                messages = self.msg_repo.get_by_conversation_id(session, conversation_id)
            
            return [
                {
                    "id": msg.id,
                    "role": msg.role.value,
                    "content": msg.content,
                    "model": msg.model,
                    "sequence_number": msg.sequence_number,
                    "created_at": msg.created_at.isoformat()
                }
                for msg in messages
            ]
    
    # ========================================================================
    # Memory Management
    # ========================================================================
    
    def save_memory(
        self,
        user_id: int,
        question: str,
        answer: str,
        conversation_id: Optional[int] = None,
        importance: int = 5,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Save memory for user
        
        Args:
            user_id: User ID
            question: Question/topic
            answer: Answer/learned information
            conversation_id: Optional conversation ID
            importance: Importance score (1-10)
            tags: Optional tags
            
        Returns:
            Memory dict
        """
        with db_session() as session:
            memory = self.memory_repo.create(
                session,
                user_id=user_id,
                conversation_id=conversation_id,
                question=question,
                answer=answer,
                importance=importance,
                tags=tags or []
            )
            
            logger.info(f"Saved memory {memory.id} for user {user_id}")
            
            return {
                "id": memory.id,
                "user_id": memory.user_id,
                "question": memory.question,
                "answer": memory.answer,
                "importance": memory.importance,
                "tags": memory.tags,
                "created_at": memory.created_at.isoformat()
            }
    
    def search_memories(
        self,
        user_id: int,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search user memories
        
        Args:
            user_id: User ID
            query: Search query
            limit: Max results
            
        Returns:
            List of memory dicts
        """
        with db_session() as session:
            memories = self.memory_repo.search_memories(
                session,
                user_id=user_id,
                query=query,
                limit=limit
            )
            
            return [
                {
                    "id": mem.id,
                    "question": mem.question,
                    "answer": mem.answer,
                    "importance": mem.importance,
                    "tags": mem.tags,
                    "created_at": mem.created_at.isoformat()
                }
                for mem in memories
            ]
    
    def get_user_memories(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get all user memories"""
        with db_session() as session:
            memories = self.memory_repo.get_by_user_id(
                session,
                user_id=user_id,
                skip=skip,
                limit=limit
            )
            
            return [
                {
                    "id": mem.id,
                    "question": mem.question,
                    "answer": mem.answer,
                    "importance": mem.importance,
                    "tags": mem.tags,
                    "created_at": mem.created_at.isoformat()
                }
                for mem in memories
            ]
    
    # ========================================================================
    # File Management
    # ========================================================================
    
    def track_uploaded_file(
        self,
        user_id: int,
        conversation_id: int,
        filename: str,
        file_path: str,
        file_type: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Track uploaded file
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            filename: Original filename
            file_path: Storage path
            file_type: MIME type
            file_size: File size in bytes
            
        Returns:
            File dict
        """
        with db_session() as session:
            file_record = self.file_repo.create(
                session,
                user_id=user_id,
                conversation_id=conversation_id,
                filename=filename,
                file_path=file_path,
                file_type=file_type,
                file_size=file_size
            )
            
            logger.info(f"Tracked file {file_record.id}: {filename}")
            
            return {
                "id": file_record.id,
                "filename": file_record.filename,
                "file_path": file_record.file_path,
                "file_type": file_record.file_type,
                "file_size": file_record.file_size,
                "is_processed": file_record.is_processed,
                "created_at": file_record.created_at.isoformat()
            }
    
    def mark_file_processed(
        self,
        file_id: int,
        analysis_result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark file as processed"""
        with db_session() as session:
            return self.file_repo.mark_processed(session, file_id, analysis_result)


# Singleton instance
chatbot_service = ChatBotService()
