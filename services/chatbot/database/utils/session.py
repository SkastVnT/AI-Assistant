"""
Database Session Manager

MongoDB connection and session management.
"""

import os
import logging
from typing import Optional, Generator
from contextlib import contextmanager
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


class DatabaseSession:
    """
    MongoDB session manager with connection pooling.
    
    Features:
    - Connection pooling
    - Automatic reconnection
    - Context manager support
    - Multiple database support
    """
    
    _instance: Optional['DatabaseSession'] = None
    _client: Optional[MongoClient] = None
    _default_db_name: str = 'ai_assistant'
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """Establish MongoDB connection"""
        try:
            mongo_uri = os.getenv(
                'MONGODB_URI',
                'mongodb://localhost:27017/ai_assistant'
            )
            
            self._client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                maxPoolSize=50,
                minPoolSize=5,
                retryWrites=True
            )
            
            # Test connection
            self._client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {mongo_uri.split('@')[-1]}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.warning(f"MongoDB connection failed: {e}")
            self._client = None
        except Exception as e:
            logger.error(f"MongoDB error: {e}")
            self._client = None
    
    @property
    def client(self) -> Optional[MongoClient]:
        """Get MongoDB client"""
        if self._client is None:
            self._connect()
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to MongoDB"""
        if self._client is None:
            return False
        try:
            self._client.admin.command('ping')
            return True
        except:
            return False
    
    def get_database(self, db_name: str = None) -> Optional[Database]:
        """
        Get database instance.
        
        Args:
            db_name: Database name (defaults to ai_assistant)
            
        Returns:
            MongoDB Database or None
        """
        if self.client is None:
            return None
        return self.client[db_name or self._default_db_name]
    
    def get_collection(self, collection_name: str, db_name: str = None):
        """
        Get collection instance.
        
        Args:
            collection_name: Collection name
            db_name: Database name
            
        Returns:
            MongoDB Collection or None
        """
        db = self.get_database(db_name)
        if db is None:
            return None
        return db[collection_name]
    
    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("MongoDB connection closed")
    
    def reconnect(self):
        """Force reconnection"""
        self.close()
        self._connect()
    
    def health_check(self) -> dict:
        """
        Check database health.
        
        Returns:
            Health status dict
        """
        try:
            if self._client is None:
                return {'status': 'disconnected', 'error': 'No client'}
            
            # Ping test
            start = __import__('time').time()
            self._client.admin.command('ping')
            latency = (__import__('time').time() - start) * 1000
            
            # Get server info
            server_info = self._client.server_info()
            
            return {
                'status': 'connected',
                'latency_ms': round(latency, 2),
                'version': server_info.get('version'),
                'uptime': server_info.get('uptime')
            }
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}


# =========================================================================
# Context Manager Functions
# =========================================================================

@contextmanager
def get_db_session(db_name: str = None) -> Generator[Database, None, None]:
    """
    Context manager for database session.
    
    Usage:
        with get_db_session() as db:
            db.conversations.find_one(...)
    
    Args:
        db_name: Optional database name
        
    Yields:
        MongoDB Database instance
    """
    session = DatabaseSession()
    db = session.get_database(db_name)
    
    if db is None:
        raise ConnectionError("Could not connect to MongoDB")
    
    try:
        yield db
    except Exception as e:
        logger.error(f"Database operation error: {e}")
        raise
    finally:
        # Connection pooling - don't close
        pass


def get_mongodb_client() -> Optional[MongoClient]:
    """
    Get MongoDB client instance.
    
    Returns:
        MongoClient or None
    """
    return DatabaseSession().client


def get_mongodb_database(db_name: str = None) -> Optional[Database]:
    """
    Get MongoDB database instance.
    
    Args:
        db_name: Database name
        
    Returns:
        Database or None
    """
    return DatabaseSession().get_database(db_name)


# =========================================================================
# Repository Factory
# =========================================================================

class RepositoryFactory:
    """Factory for creating repository instances"""
    
    @staticmethod
    def get_conversation_repository():
        """Get ConversationRepository instance"""
        from ..repositories.conversation_repository import ConversationRepository
        db = DatabaseSession().get_database()
        if db is None:
            raise ConnectionError("Database not available")
        return ConversationRepository(db)
    
    @staticmethod
    def get_message_repository():
        """Get MessageRepository instance"""
        from ..repositories.message_repository import MessageRepository
        db = DatabaseSession().get_database()
        if db is None:
            raise ConnectionError("Database not available")
        return MessageRepository(db)
    
    @staticmethod
    def get_memory_repository():
        """Get MemoryRepository instance"""
        from ..repositories.memory_repository import MemoryRepository
        db = DatabaseSession().get_database()
        if db is None:
            raise ConnectionError("Database not available")
        return MemoryRepository(db)


# Convenience function
def get_repositories():
    """
    Get all repositories.
    
    Returns:
        Tuple of (ConversationRepository, MessageRepository, MemoryRepository)
    """
    factory = RepositoryFactory()
    return (
        factory.get_conversation_repository(),
        factory.get_message_repository(),
        factory.get_memory_repository()
    )
