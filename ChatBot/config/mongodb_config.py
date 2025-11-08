"""
MongoDB Configuration for ChatBot Service
Database: AI-Assistant MongoDB Atlas
Created: 2025-11-09
"""

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Atlas URI
MONGODB_URI = os.getenv(
    'MONGODB_URI'
)

# Database name
DATABASE_NAME = "chatbot_db"

# Collection names
COLLECTIONS = {
    'conversations': 'conversations',
    'messages': 'messages',
    'memory': 'chatbot_memory',
    'uploaded_files': 'uploaded_files',
    'users': 'users',
    'settings': 'user_settings'
}


class MongoDBClient:
    """MongoDB Client Singleton"""
    
    _instance = None
    _client = None
    _db = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MongoDBClient, cls).__new__(cls)
        return cls._instance
    
    def connect(self):
        """Establish MongoDB connection"""
        if self._client is None:
            try:
                self._client = MongoClient(MONGODB_URI, server_api=ServerApi('1'))
                # Test connection
                self._client.admin.command('ping')
                self._db = self._client[DATABASE_NAME]
                print(f"✅ Successfully connected to MongoDB Atlas - Database: {DATABASE_NAME}")
                self._create_indexes()
                return True
            except Exception as e:
                print(f"❌ MongoDB connection failed: {e}")
                return False
        return True
    
    def _create_indexes(self):
        """Create indexes for better performance"""
        db = self._db
        
        # Conversations indexes
        db.conversations.create_index([("user_id", 1)])
        db.conversations.create_index([("created_at", -1)])
        db.conversations.create_index([("is_archived", 1)])
        
        # Messages indexes
        db.messages.create_index([("conversation_id", 1)])
        db.messages.create_index([("created_at", -1)])
        db.messages.create_index([("role", 1)])
        
        # Memory indexes
        db.chatbot_memory.create_index([("user_id", 1)])
        db.chatbot_memory.create_index([("conversation_id", 1)])
        db.chatbot_memory.create_index([("tags", 1)])
        db.chatbot_memory.create_index([("created_at", -1)])
        
        # Uploaded files indexes
        db.uploaded_files.create_index([("user_id", 1)])
        db.uploaded_files.create_index([("conversation_id", 1)])
        db.uploaded_files.create_index([("created_at", -1)])
        
        print("✅ MongoDB indexes created successfully")
    
    @property
    def db(self):
        """Get database instance"""
        if self._db is None:
            self.connect()
        return self._db
    
    @property
    def conversations(self):
        """Get conversations collection"""
        return self.db[COLLECTIONS['conversations']]
    
    @property
    def messages(self):
        """Get messages collection"""
        return self.db[COLLECTIONS['messages']]
    
    @property
    def memory(self):
        """Get memory collection"""
        return self.db[COLLECTIONS['memory']]
    
    @property
    def uploaded_files(self):
        """Get uploaded files collection"""
        return self.db[COLLECTIONS['uploaded_files']]
    
    @property
    def users(self):
        """Get users collection"""
        return self.db[COLLECTIONS['users']]
    
    @property
    def settings(self):
        """Get settings collection"""
        return self.db[COLLECTIONS['settings']]
    
    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            print("✅ MongoDB connection closed")


# Global instance
mongodb_client = MongoDBClient()


def get_db():
    """Get database instance (helper function)"""
    return mongodb_client.db


def test_connection():
    """Test MongoDB connection"""
    try:
        mongodb_client.connect()
        # Insert test document
        test_collection = mongodb_client.db.test
        test_doc = {
            "test": "connection",
            "timestamp": datetime.utcnow()
        }
        result = test_collection.insert_one(test_doc)
        print(f"✅ Test document inserted with ID: {result.inserted_id}")
        
        # Delete test document
        test_collection.delete_one({"_id": result.inserted_id})
        print("✅ Test document deleted")
        
        # Drop test collection
        mongodb_client.db.drop_collection('test')
        print("✅ Test collection dropped")
        
        return True
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Testing MongoDB Connection...")
    print("=" * 50)
    test_connection()
    mongodb_client.close()
