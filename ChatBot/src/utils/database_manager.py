"""
MongoDB Database Manager - Performance Optimization
Handles all database operations with connection pooling and query optimization
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, List, Any
import os
from functools import wraps
import time

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    MongoDB database manager with optimized queries and connection pooling
    
    Features:
    - Connection pooling
    - Automatic reconnection
    - Query optimization with indexes
    - Batch operations
    - Performance monitoring
    """
    
    def __init__(self, connection_string: str = None):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB URI (default: from env)
        """
        self.connection_string = connection_string or os.getenv(
            'MONGODB_URI',
            'mongodb+srv://thanhnguyen:tXH6O1Ai2I7dKUJB@mongodb.qexrzvn.mongodb.net/?appName=mongodb'
        )
        
        try:
            # Connection pooling configuration
            self.client = MongoClient(
                self.connection_string,
                maxPoolSize=50,  # Max 50 connections
                minPoolSize=10,  # Min 10 connections
                maxIdleTimeMS=60000,  # Close idle connections after 60s
                serverSelectionTimeoutMS=5000,  # 5s timeout
                connectTimeoutMS=10000,  # 10s connection timeout
                retryWrites=True,  # Retry failed writes
                retryReads=True,  # Retry failed reads
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Database and collections
            self.db = self.client['ai_assistant']
            self.conversations = self.db['conversations']
            self.messages = self.db['messages']
            self.users = self.db['users']
            self.sessions = self.db['sessions']
            self.analytics = self.db['analytics']
            
            # Create indexes for performance
            self._create_indexes()
            
            self.enabled = True
            logger.info("✅ MongoDB connected successfully")
            
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            self.client = None
            self.enabled = False
    
    def _create_indexes(self):
        """Create database indexes for optimized queries"""
        try:
            # Conversations indexes
            self.conversations.create_index([('session_id', ASCENDING)])
            self.conversations.create_index([('created_at', DESCENDING)])
            self.conversations.create_index([
                ('session_id', ASCENDING),
                ('created_at', DESCENDING)
            ])
            
            # Messages indexes
            self.messages.create_index([('conversation_id', ASCENDING)])
            self.messages.create_index([('timestamp', DESCENDING)])
            self.messages.create_index([
                ('conversation_id', ASCENDING),
                ('timestamp', ASCENDING)
            ])
            self.messages.create_index([('session_id', ASCENDING)])
            
            # Sessions indexes
            self.sessions.create_index([('session_id', ASCENDING)], unique=True)
            self.sessions.create_index([('last_active', DESCENDING)])
            
            # Analytics indexes
            self.analytics.create_index([('date', DESCENDING)])
            self.analytics.create_index([('event_type', ASCENDING)])
            
            logger.info("✅ Database indexes created")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    def _timing_decorator(self, func):
        """Decorator to measure query execution time"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration = (time.time() - start) * 1000  # Convert to ms
            
            if duration > 100:  # Log slow queries (>100ms)
                logger.warning(f"⚠️ Slow query: {func.__name__} took {duration:.2f}ms")
            else:
                logger.debug(f"⚡ Query: {func.__name__} took {duration:.2f}ms")
            
            return result
        return wrapper
    
    # ============================================================================
    # CONVERSATION OPERATIONS
    # ============================================================================
    
    def create_conversation(
        self,
        session_id: str,
        title: str = "New Chat",
        metadata: Dict = None
    ) -> Optional[str]:
        """
        Create a new conversation
        
        Args:
            session_id: Session ID
            title: Conversation title
            metadata: Additional metadata
        
        Returns:
            Conversation ID or None
        """
        if not self.enabled:
            return None
        
        try:
            conversation = {
                'session_id': session_id,
                'title': title,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'message_count': 0,
                'metadata': metadata or {}
            }
            
            result = self.conversations.insert_one(conversation)
            logger.info(f"✅ Conversation created: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return None
    
    @_timing_decorator
    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation by ID"""
        if not self.enabled:
            return None
        
        try:
            from bson import ObjectId
            conv = self.conversations.find_one({'_id': ObjectId(conversation_id)})
            if conv:
                conv['_id'] = str(conv['_id'])
            return conv
        except Exception as e:
            logger.error(f"Error getting conversation: {e}")
            return None
    
    @_timing_decorator
    def get_conversations(
        self,
        session_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict]:
        """
        Get conversations for a session (paginated)
        
        Args:
            session_id: Session ID
            limit: Max conversations to return
            skip: Number to skip (for pagination)
        
        Returns:
            List of conversations
        """
        if not self.enabled:
            return []
        
        try:
            cursor = self.conversations.find(
                {'session_id': session_id}
            ).sort('updated_at', DESCENDING).skip(skip).limit(limit)
            
            conversations = []
            for conv in cursor:
                conv['_id'] = str(conv['_id'])
                conversations.append(conv)
            
            return conversations
            
        except Exception as e:
            logger.error(f"Error getting conversations: {e}")
            return []
    
    def update_conversation(
        self,
        conversation_id: str,
        update: Dict
    ) -> bool:
        """Update conversation fields"""
        if not self.enabled:
            return False
        
        try:
            from bson import ObjectId
            
            # Add updated_at timestamp
            update['updated_at'] = datetime.utcnow()
            
            result = self.conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {'$set': update}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating conversation: {e}")
            return False
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation and all its messages"""
        if not self.enabled:
            return False
        
        try:
            from bson import ObjectId
            
            # Delete messages first
            self.messages.delete_many({'conversation_id': conversation_id})
            
            # Delete conversation
            result = self.conversations.delete_one({'_id': ObjectId(conversation_id)})
            
            logger.info(f"🗑️ Conversation deleted: {conversation_id}")
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting conversation: {e}")
            return False
    
    # ============================================================================
    # MESSAGE OPERATIONS
    # ============================================================================
    
    def add_message(
        self,
        conversation_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: Dict = None
    ) -> Optional[str]:
        """
        Add message to conversation
        
        Args:
            conversation_id: Conversation ID
            session_id: Session ID
            role: Message role (user/assistant/system)
            content: Message content
            metadata: Additional metadata (model, tokens, etc.)
        
        Returns:
            Message ID or None
        """
        if not self.enabled:
            return None
        
        try:
            message = {
                'conversation_id': conversation_id,
                'session_id': session_id,
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow(),
                'metadata': metadata or {}
            }
            
            result = self.messages.insert_one(message)
            
            # Update conversation message count and timestamp
            self.conversations.update_one(
                {'_id': ObjectId(conversation_id)},
                {
                    '$inc': {'message_count': 1},
                    '$set': {'updated_at': datetime.utcnow()}
                }
            )
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return None
    
    @_timing_decorator
    def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict]:
        """
        Get messages for a conversation
        
        Args:
            conversation_id: Conversation ID
            limit: Max messages to return
            skip: Number to skip
        
        Returns:
            List of messages
        """
        if not self.enabled:
            return []
        
        try:
            cursor = self.messages.find(
                {'conversation_id': conversation_id}
            ).sort('timestamp', ASCENDING).skip(skip).limit(limit)
            
            messages = []
            for msg in cursor:
                msg['_id'] = str(msg['_id'])
                messages.append(msg)
            
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            return []
    
    @_timing_decorator
    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get recent messages for a session (for context)
        
        Args:
            session_id: Session ID
            limit: Number of recent messages
        
        Returns:
            List of recent messages
        """
        if not self.enabled:
            return []
        
        try:
            cursor = self.messages.find(
                {'session_id': session_id}
            ).sort('timestamp', DESCENDING).limit(limit)
            
            messages = []
            for msg in cursor:
                msg['_id'] = str(msg['_id'])
                messages.append(msg)
            
            # Reverse to chronological order
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []
    
    def batch_add_messages(
        self,
        messages: List[Dict]
    ) -> int:
        """
        Add multiple messages in batch (optimized)
        
        Args:
            messages: List of message dicts
        
        Returns:
            Number of messages added
        """
        if not self.enabled or not messages:
            return 0
        
        try:
            # Add timestamp if not present
            for msg in messages:
                if 'timestamp' not in msg:
                    msg['timestamp'] = datetime.utcnow()
            
            result = self.messages.insert_many(messages, ordered=False)
            return len(result.inserted_ids)
            
        except Exception as e:
            logger.error(f"Error batch adding messages: {e}")
            return 0
    
    # ============================================================================
    # SESSION OPERATIONS
    # ============================================================================
    
    def create_session(self, session_id: str, metadata: Dict = None) -> bool:
        """Create or update session"""
        if not self.enabled:
            return False
        
        try:
            session = {
                'session_id': session_id,
                'created_at': datetime.utcnow(),
                'last_active': datetime.utcnow(),
                'metadata': metadata or {}
            }
            
            self.sessions.update_one(
                {'session_id': session_id},
                {'$set': session},
                upsert=True
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return False
    
    def update_session_activity(self, session_id: str) -> bool:
        """Update session last active timestamp"""
        if not self.enabled:
            return False
        
        try:
            self.sessions.update_one(
                {'session_id': session_id},
                {'$set': {'last_active': datetime.utcnow()}}
            )
            return True
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return False
    
    # ============================================================================
    # ANALYTICS
    # ============================================================================
    
    def log_event(
        self,
        event_type: str,
        session_id: str,
        data: Dict = None
    ) -> bool:
        """
        Log analytics event
        
        Args:
            event_type: Event type (message, generation, error, etc.)
            session_id: Session ID
            data: Event data
        
        Returns:
            Success status
        """
        if not self.enabled:
            return False
        
        try:
            event = {
                'event_type': event_type,
                'session_id': session_id,
                'timestamp': datetime.utcnow(),
                'date': datetime.utcnow().date(),
                'data': data or {}
            }
            
            self.analytics.insert_one(event)
            return True
            
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            return False
    
    def get_analytics(
        self,
        start_date: datetime = None,
        end_date: datetime = None,
        event_type: str = None
    ) -> List[Dict]:
        """Get analytics data"""
        if not self.enabled:
            return []
        
        try:
            query = {}
            
            if start_date or end_date:
                query['timestamp'] = {}
                if start_date:
                    query['timestamp']['$gte'] = start_date
                if end_date:
                    query['timestamp']['$lte'] = end_date
            
            if event_type:
                query['event_type'] = event_type
            
            cursor = self.analytics.find(query).sort('timestamp', DESCENDING)
            
            events = []
            for event in cursor:
                event['_id'] = str(event['_id'])
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return []
    
    # ============================================================================
    # CLEANUP & MAINTENANCE
    # ============================================================================
    
    def cleanup_old_data(self, days: int = 30) -> Dict[str, int]:
        """
        Clean up old data
        
        Args:
            days: Delete data older than this many days
        
        Returns:
            Dict with counts of deleted items
        """
        if not self.enabled:
            return {}
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Delete old analytics
            analytics_result = self.analytics.delete_many({
                'timestamp': {'$lt': cutoff_date}
            })
            
            # Delete inactive sessions
            session_result = self.sessions.delete_many({
                'last_active': {'$lt': cutoff_date}
            })
            
            logger.info(f"🧹 Cleanup: {analytics_result.deleted_count} analytics, "
                       f"{session_result.deleted_count} sessions")
            
            return {
                'analytics': analytics_result.deleted_count,
                'sessions': session_result.deleted_count
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up data: {e}")
            return {}
    
    # ============================================================================
    # STATISTICS
    # ============================================================================
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        if not self.enabled:
            return {'enabled': False}
        
        try:
            stats = {
                'enabled': True,
                'conversations': self.conversations.count_documents({}),
                'messages': self.messages.count_documents({}),
                'sessions': self.sessions.count_documents({}),
                'analytics_events': self.analytics.count_documents({}),
                'database_size': self.db.command('dbstats')['dataSize'],
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {'enabled': True, 'error': str(e)}
    
    def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")


# ============================================================================
# GLOBAL DATABASE INSTANCE
# ============================================================================

_db_instance = None


def get_database_manager() -> DatabaseManager:
    """Get global database manager instance"""
    global _db_instance
    
    if _db_instance is None:
        _db_instance = DatabaseManager()
    
    return _db_instance
