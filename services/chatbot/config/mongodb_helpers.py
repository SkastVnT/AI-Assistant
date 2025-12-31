"""
MongoDB Database Helper Functions
CRUD operations for ChatBot service

Usage:
    from config.mongodb_helpers import ConversationDB, MessageDB, MemoryDB, FileDB
    
    # Create conversation
    conv = ConversationDB.create_conversation("user_123", "gemini-2.0-flash")
    
    # Add message
    msg = MessageDB.add_message(conv["_id"], "user", "Hello AI!")
"""

import logging
import sys
import importlib.util
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from bson import ObjectId
from pymongo import DESCENDING, ASCENDING

logger = logging.getLogger(__name__)

# Import get_db - will be injected from parent
# This allows importlib to load this module without package context
try:
    from .mongodb_config import get_db
except ImportError:
    # Fallback for importlib loading
    mongodb_config_path = Path(__file__).parent / 'mongodb_config.py'
    spec = importlib.util.spec_from_file_location("_mongodb_config", mongodb_config_path)
    _mongodb_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_mongodb_config)
    get_db = _mongodb_config.get_db

# Try to import caching layer
try:
    _chatbot_dir = str(Path(__file__).parent.parent)
    if _chatbot_dir not in sys.path:
        sys.path.insert(0, _chatbot_dir)
    from database.cache.chatbot_cache import ChatbotCache
    CACHE_AVAILABLE = True
    logger.info("Cache layer loaded successfully")
except ImportError as e:
    CACHE_AVAILABLE = False
    ChatbotCache = None
    logger.warning(f"Cache layer not available: {e}")
except Exception as e:
    CACHE_AVAILABLE = False
    ChatbotCache = None
    logger.warning(f"Cache layer error: {e}")


# ============================================================================
# CONVERSATION DATABASE OPERATIONS
# ============================================================================

class ConversationDB:
    """Database operations for conversations collection"""
    
    @staticmethod
    def create_conversation(
        user_id: str,
        model: str,
        title: str = "New Chat",
        system_prompt: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Create a new conversation"""
        db = get_db()
        
        if db is None or db.conversations is None:
            raise Exception("MongoDB not connected")
        
        conversation = {
            "user_id": user_id,
            "model": model,
            "title": title,
            "system_prompt": system_prompt or "You are a helpful AI assistant.",
            "total_messages": 0,
            "total_tokens": 0,
            "is_archived": False,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = db.conversations.insert_one(conversation)
        conversation["_id"] = result.inserted_id
        
        # Invalidate user conversation list cache
        if CACHE_AVAILABLE:
            ChatbotCache.invalidate_user_conversations(user_id)
        
        return conversation
    
    @staticmethod
    def get_conversation(conversation_id: str) -> Optional[Dict]:
        """Get conversation by ID"""
        # Try cache first
        if CACHE_AVAILABLE:
            cached = ChatbotCache.get_conversation(str(conversation_id))
            if cached:
                return cached
        
        db = get_db()
        
        if db is None or db.conversations is None:
            return None
        
        result = db.conversations.find_one({"_id": ObjectId(conversation_id)})
        
        # Cache the result
        if result and CACHE_AVAILABLE:
            ChatbotCache.set_conversation(str(conversation_id), result)
        
        return result
    
    @staticmethod
    def get_user_conversations(
        user_id: str,
        include_archived: bool = False,
        limit: int = 20
    ) -> List[Dict]:
        """Get all conversations for a user"""
        # Try cache first (only for default parameters)
        if CACHE_AVAILABLE and not include_archived and limit <= 50:
            cached = ChatbotCache.get_user_conversations(user_id)
            if cached:
                return cached[:limit]
        
        db = get_db()
        
        query = {"user_id": user_id}
        if not include_archived:
            query["is_archived"] = False
        
        conversations = db.conversations.find(query).sort(
            "updated_at", DESCENDING
        ).limit(limit)
        
        result = list(conversations)
        
        # Cache the result
        if CACHE_AVAILABLE and not include_archived:
            ChatbotCache.set_user_conversations(user_id, result)
        
        return result
    
    @staticmethod
    def update_conversation(
        conversation_id: str,
        update_data: Dict
    ) -> bool:
        """Update conversation"""
        db = get_db()
        
        update_data["updated_at"] = datetime.utcnow()
        result = db.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {"$set": update_data}
        )
        
        # Invalidate cache
        if CACHE_AVAILABLE:
            ChatbotCache.invalidate_conversation(str(conversation_id))
        
        return result.modified_count > 0
    
    @staticmethod
    def increment_message_count(
        conversation_id: str,
        tokens: int = 0
    ) -> bool:
        """Increment message count and tokens"""
        db = get_db()
        
        result = db.conversations.update_one(
            {"_id": ObjectId(conversation_id)},
            {
                "$inc": {
                    "total_messages": 1,
                    "total_tokens": tokens
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def archive_conversation(conversation_id: str) -> bool:
        """Archive a conversation"""
        return ConversationDB.update_conversation(
            conversation_id,
            {"is_archived": True}
        )
    
    @staticmethod
    def delete_conversation(conversation_id: str) -> bool:
        """Delete conversation and all its messages"""
        db = get_db()
        
        # Get conversation first to get user_id for cache invalidation
        conv = db.conversations.find_one({"_id": ObjectId(conversation_id)})
        user_id = conv.get("user_id") if conv else None
        
        # Delete all messages first
        db.messages.delete_many({"conversation_id": ObjectId(conversation_id)})
        
        # Delete conversation
        result = db.conversations.delete_one({"_id": ObjectId(conversation_id)})
        
        # Invalidate cache
        if CACHE_AVAILABLE:
            ChatbotCache.invalidate_conversation(str(conversation_id))
            ChatbotCache.invalidate_messages(str(conversation_id))
            if user_id:
                ChatbotCache.invalidate_user_conversations(user_id)
        
        return result.deleted_count > 0
    
    @staticmethod
    def get_conversation_with_messages(conversation_id: str) -> Optional[Dict]:
        """Get conversation with all messages using aggregation"""
        db = get_db()
        
        pipeline = [
            {"$match": {"_id": ObjectId(conversation_id)}},
            {"$lookup": {
                "from": "messages",
                "localField": "_id",
                "foreignField": "conversation_id",
                "as": "messages"
            }},
            {"$project": {
                "_id": 1,
                "user_id": 1,
                "model": 1,
                "title": 1,
                "system_prompt": 1,
                "total_messages": 1,
                "total_tokens": 1,
                "is_archived": 1,
                "metadata": 1,
                "created_at": 1,
                "updated_at": 1,
                "messages": {
                    "$sortArray": {
                        "input": "$messages",
                        "sortBy": {"created_at": 1}
                    }
                }
            }}
        ]
        
        result = list(db.conversations.aggregate(pipeline))
        return result[0] if result else None


# ============================================================================
# MESSAGE DATABASE OPERATIONS
# ============================================================================

class MessageDB:
    """Database operations for messages collection"""
    
    @staticmethod
    def add_message(
        conversation_id: str,
        role: str,
        content: str,
        images: Optional[List[Dict]] = None,
        files: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None,
        parent_message_id: Optional[str] = None
    ) -> Dict:
        """Add a new message to conversation"""
        db = get_db()
        
        message = {
            "conversation_id": ObjectId(conversation_id),
            "role": role,
            "content": content,
            "images": images or [],
            "files": files or [],
            "metadata": metadata or {},
            "version": 1,
            "parent_message_id": ObjectId(parent_message_id) if parent_message_id else None,
            "is_edited": False,
            "is_stopped": False,
            "created_at": datetime.utcnow()
        }
        
        result = db.messages.insert_one(message)
        message["_id"] = result.inserted_id
        
        # Update conversation
        tokens = metadata.get("tokens", 0) if metadata else 0
        ConversationDB.increment_message_count(conversation_id, tokens)
        
        # Invalidate message cache for this conversation
        if CACHE_AVAILABLE:
            ChatbotCache.invalidate_messages(str(conversation_id))
        
        return message
    
    @staticmethod
    def get_message(message_id: str) -> Optional[Dict]:
        """Get message by ID"""
        db = get_db()
        return db.messages.find_one({"_id": ObjectId(message_id)})
    
    @staticmethod
    def get_conversation_messages(
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Get all messages in a conversation"""
        # Try cache first (only for reasonable limits)
        if CACHE_AVAILABLE and (limit is None or limit >= 50):
            cached = ChatbotCache.get_messages(str(conversation_id))
            if cached:
                return cached[:limit] if limit else cached
        
        db = get_db()
        
        query = db.messages.find(
            {"conversation_id": ObjectId(conversation_id)}
        ).sort("created_at", ASCENDING)
        
        if limit:
            query = query.limit(limit)
        
        result = list(query)
        
        # Cache the result
        if CACHE_AVAILABLE and (limit is None or limit >= 50):
            ChatbotCache.set_messages(str(conversation_id), result)
        
        return result
    
    @staticmethod
    def update_message(
        message_id: str,
        content: str
    ) -> bool:
        """Update message content (creates new version)"""
        db = get_db()
        
        # Get original message
        original = MessageDB.get_message(message_id)
        if not original:
            return False
        
        # Create new version
        new_message = {
            **original,
            "_id": ObjectId(),  # New ID
            "content": content,
            "version": original.get("version", 1) + 1,
            "parent_message_id": ObjectId(message_id),
            "is_edited": True,
            "created_at": datetime.utcnow()
        }
        
        db.messages.insert_one(new_message)
        return True
    
    @staticmethod
    def mark_stopped(message_id: str) -> bool:
        """Mark message as stopped (generation interrupted)"""
        db = get_db()
        
        result = db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {"$set": {"is_stopped": True}}
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def delete_message(message_id: str) -> bool:
        """Delete a message"""
        db = get_db()
        result = db.messages.delete_one({"_id": ObjectId(message_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def get_message_versions(message_id: str) -> List[Dict]:
        """Get all versions of a message"""
        db = get_db()
        
        # Get all messages with this parent_message_id
        versions = db.messages.find(
            {"parent_message_id": ObjectId(message_id)}
        ).sort("version", ASCENDING)
        
        return list(versions)


# ============================================================================
# MEMORY DATABASE OPERATIONS
# ============================================================================

class MemoryDB:
    """Database operations for chatbot_memory collection"""
    
    @staticmethod
    def save_memory(
        user_id: str,
        question: str,
        answer: str,
        context: Optional[str] = None,
        conversation_id: Optional[str] = None,
        images: Optional[List[Dict]] = None,
        tags: Optional[List[str]] = None,
        is_public: bool = False,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Save a memory/learning entry"""
        db = get_db()
        
        memory = {
            "user_id": user_id,
            "conversation_id": ObjectId(conversation_id) if conversation_id else None,
            "question": question,
            "answer": answer,
            "context": context,
            "images": images or [],
            "rating": None,
            "tags": tags or [],
            "is_public": is_public,
            "metadata": metadata or {},
            "created_at": datetime.utcnow()
        }
        
        result = db.chatbot_memory.insert_one(memory)
        memory["_id"] = result.inserted_id
        return memory
    
    @staticmethod
    def get_user_memories(
        user_id: str,
        tags: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get user's memories, optionally filtered by tags"""
        db = get_db()
        
        query = {"user_id": user_id}
        if tags:
            query["tags"] = {"$in": tags}
        
        memories = db.chatbot_memory.find(query).sort(
            "created_at", DESCENDING
        ).limit(limit)
        
        return list(memories)
    
    @staticmethod
    def search_memories(
        user_id: str,
        search_text: str,
        limit: int = 20
    ) -> List[Dict]:
        """Search memories by text (requires text index)"""
        db = get_db()
        
        # Create text index if not exists
        try:
            db.chatbot_memory.create_index([
                ("question", "text"),
                ("answer", "text"),
                ("context", "text")
            ])
        except:
            pass
        
        memories = db.chatbot_memory.find(
            {
                "user_id": user_id,
                "$text": {"$search": search_text}
            },
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        
        return list(memories)
    
    @staticmethod
    def rate_memory(memory_id: str, rating: int) -> bool:
        """Rate a memory (1-5 stars)"""
        db = get_db()
        
        if not 1 <= rating <= 5:
            return False
        
        result = db.chatbot_memory.update_one(
            {"_id": ObjectId(memory_id)},
            {"$set": {"rating": rating}}
        )
        
        return result.modified_count > 0
    
    @staticmethod
    def get_public_memories(tags: Optional[List[str]] = None, limit: int = 50) -> List[Dict]:
        """Get public memories (shared by users)"""
        db = get_db()
        
        query = {"is_public": True}
        if tags:
            query["tags"] = {"$in": tags}
        
        memories = db.chatbot_memory.find(query).sort(
            [("rating", DESCENDING), ("created_at", DESCENDING)]
        ).limit(limit)
        
        return list(memories)
    
    @staticmethod
    def delete_memory(memory_id: str) -> bool:
        """Delete a memory"""
        db = get_db()
        result = db.chatbot_memory.delete_one({"_id": ObjectId(memory_id)})
        return result.deleted_count > 0


# ============================================================================
# FILE DATABASE OPERATIONS
# ============================================================================

class FileDB:
    """Database operations for uploaded_files collection"""
    
    @staticmethod
    def save_file_record(
        user_id: str,
        original_filename: str,
        stored_filename: str,
        file_path: str,
        file_type: str,
        file_size: int,
        mime_type: str,
        conversation_id: Optional[str] = None,
        analysis_result: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """Save file upload record"""
        db = get_db()
        
        file_record = {
            "user_id": user_id,
            "conversation_id": ObjectId(conversation_id) if conversation_id else None,
            "original_filename": original_filename,
            "stored_filename": stored_filename,
            "file_path": file_path,
            "file_type": file_type,
            "file_size": file_size,
            "mime_type": mime_type,
            "analysis_result": analysis_result,
            "metadata": metadata or {},
            "created_at": datetime.utcnow()
        }
        
        result = db.uploaded_files.insert_one(file_record)
        file_record["_id"] = result.inserted_id
        return file_record
    
    @staticmethod
    def get_file(file_id: str) -> Optional[Dict]:
        """Get file record by ID"""
        db = get_db()
        return db.uploaded_files.find_one({"_id": ObjectId(file_id)})
    
    @staticmethod
    def get_user_files(
        user_id: str,
        file_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get user's uploaded files"""
        db = get_db()
        
        query = {"user_id": user_id}
        if file_type:
            query["file_type"] = file_type
        
        files = db.uploaded_files.find(query).sort(
            "created_at", DESCENDING
        ).limit(limit)
        
        return list(files)
    
    @staticmethod
    def get_conversation_files(conversation_id: str) -> List[Dict]:
        """Get all files in a conversation"""
        db = get_db()
        
        files = db.uploaded_files.find(
            {"conversation_id": ObjectId(conversation_id)}
        ).sort("created_at", ASCENDING)
        
        return list(files)
    
    @staticmethod
    def delete_file(file_id: str) -> bool:
        """Delete file record"""
        db = get_db()
        result = db.uploaded_files.delete_one({"_id": ObjectId(file_id)})
        return result.deleted_count > 0
    
    @staticmethod
    def get_total_storage_size(user_id: str) -> int:
        """Get total storage size for user (in bytes)"""
        db = get_db()
        
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$group": {
                "_id": None,
                "total_size": {"$sum": "$file_size"}
            }}
        ]
        
        result = list(db.uploaded_files.aggregate(pipeline))
        return result[0]["total_size"] if result else 0


# ============================================================================
# USER SETTINGS OPERATIONS
# ============================================================================

class UserSettingsDB:
    """Database operations for user_settings collection"""
    
    @staticmethod
    def get_settings(user_id: str) -> Optional[Dict]:
        """Get user settings"""
        db = get_db()
        return db.user_settings.find_one({"user_id": user_id})
    
    @staticmethod
    def create_default_settings(user_id: str) -> Dict:
        """Create default settings for new user"""
        db = get_db()
        
        settings = {
            "user_id": user_id,
            "chatbot_settings": {
                "default_model": "gemini-2.0-flash-thinking-exp",
                "temperature": 0.7,
                "max_tokens": 2048,
                "system_prompt": "You are a helpful AI assistant.",
                "enable_memory": True,
                "enable_tools": True,
                "enable_image_gen": True
            },
            "ui_settings": {
                "theme": "dark",
                "font_size": "medium",
                "code_theme": "github-dark",
                "show_tokens": True,
                "auto_scroll": True
            },
            "notification_settings": {
                "enable_notifications": True,
                "email_notifications": False
            },
            "updated_at": datetime.utcnow()
        }
        
        db.user_settings.insert_one(settings)
        return settings
    
    @staticmethod
    def update_settings(user_id: str, settings_update: Dict) -> bool:
        """Update user settings"""
        db = get_db()
        
        settings_update["updated_at"] = datetime.utcnow()
        result = db.user_settings.update_one(
            {"user_id": user_id},
            {"$set": settings_update},
            upsert=True
        )
        
        return result.modified_count > 0 or result.upserted_id is not None


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_user_statistics(user_id: str) -> Dict:
    """Get comprehensive statistics for a user"""
    db = get_db()
    
    # Count conversations
    total_conversations = db.conversations.count_documents({"user_id": user_id})
    active_conversations = db.conversations.count_documents({
        "user_id": user_id,
        "is_archived": False
    })
    
    # Count messages
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": None,
            "total_messages": {"$sum": "$total_messages"},
            "total_tokens": {"$sum": "$total_tokens"}
        }}
    ]
    conv_stats = list(db.conversations.aggregate(pipeline))
    
    # Count memories
    total_memories = db.chatbot_memory.count_documents({"user_id": user_id})
    
    # Count files
    total_files = db.uploaded_files.count_documents({"user_id": user_id})
    total_storage = FileDB.get_total_storage_size(user_id)
    
    return {
        "total_conversations": total_conversations,
        "active_conversations": active_conversations,
        "total_messages": conv_stats[0]["total_messages"] if conv_stats else 0,
        "total_tokens": conv_stats[0]["total_tokens"] if conv_stats else 0,
        "total_memories": total_memories,
        "total_files": total_files,
        "total_storage_bytes": total_storage,
        "total_storage_mb": round(total_storage / (1024 * 1024), 2)
    }


def cleanup_old_data(days: int = 90):
    """Clean up old archived conversations and files"""
    db = get_db()
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Delete old archived conversations
    old_conversations = db.conversations.find({
        "is_archived": True,
        "updated_at": {"$lt": cutoff_date}
    })
    
    deleted_conv = 0
    deleted_msg = 0
    
    for conv in old_conversations:
        # Delete messages
        result = db.messages.delete_many({"conversation_id": conv["_id"]})
        deleted_msg += result.deleted_count
        
        # Delete conversation
        db.conversations.delete_one({"_id": conv["_id"]})
        deleted_conv += 1
    
    return {
        "deleted_conversations": deleted_conv,
        "deleted_messages": deleted_msg
    }
