"""
MongoDB Configuration for ChatBot Service
Database: AI-Assistant MongoDB Atlas
Created: 2025-11-09
"""

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import os
from pathlib import Path
try:
    from services.shared_env import load_shared_env
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    for _parent in Path(__file__).resolve().parents:
        if (_parent / "services" / "shared_env.py").exists():
            if str(_parent) not in sys.path:
                sys.path.insert(0, str(_parent))
            break
    from services.shared_env import load_shared_env

load_shared_env(__file__)
# MongoDB Atlas URI
MONGODB_URI = os.getenv(
    'MONGODB_URI'
)
MONGODB_X509_ENABLED = os.getenv('MONGODB_X509_ENABLED', 'false').lower() == 'true'
MONGODB_X509_URI = os.getenv('MONGODB_X509_URI', '').strip()
MONGODB_X509_CERT_PATH = os.getenv('MONGODB_X509_CERT_PATH', '').strip()
MONGODB_TLS_ALLOW_INVALID_CERTIFICATES = os.getenv('MONGODB_TLS_ALLOW_INVALID_CERTIFICATES', 'true').lower() == 'true'

# Database name
DATABASE_NAME = os.getenv('MONGODB_DB_NAME', 'chatbot_db')

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
            uri = MONGODB_X509_URI if (MONGODB_X509_ENABLED and MONGODB_X509_URI) else MONGODB_URI
            # Skip if no URI configured
            if not uri:
                print("âš ï¸ MongoDB URI not configured, running without database")
                return False
            try:
                connect_kwargs = {
                    'server_api': ServerApi('1'),
                    'serverSelectionTimeoutMS': 5000,
                    'connectTimeoutMS': 5000,
                    'tls': True,
                    'tlsAllowInvalidCertificates': MONGODB_TLS_ALLOW_INVALID_CERTIFICATES,
                }

                if MONGODB_X509_ENABLED and MONGODB_X509_CERT_PATH:
                    cert_path = Path(MONGODB_X509_CERT_PATH)
                    if cert_path.exists():
                        connect_kwargs['tlsCertificateKeyFile'] = str(cert_path)
                        connect_kwargs['authMechanism'] = 'MONGODB-X509'
                        connect_kwargs['authSource'] = '$external'
                    else:
                        print(f"âš ï¸ X.509 cert file not found: {cert_path}")

                self._client = MongoClient(
                    uri,
                    **connect_kwargs
                )
                # Test connection
                self._client.admin.command('ping')
                self._db = self._client[DATABASE_NAME]
                print(f"âœ… Successfully connected to MongoDB Atlas - Database: {DATABASE_NAME}")
                return True
            except Exception as e:
                print(f"âš ï¸ MongoDB connection failed (app will run without DB): {str(e)[:100]}")
                self._client = None
                self._db = None
                return False

        # Create indexes after a successful connection (errors here are non-fatal)
        try:
            self._create_indexes()
        except Exception as e:
            print(f"âš ï¸ Index setup skipped (non-fatal): {str(e)[:120]}")
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
        
        print("âœ… MongoDB indexes created successfully")
    
    @property
    def db(self):
        """Get database instance"""
        if self._db is None:
            self.connect()
        return self._db
    
    @property
    def conversations(self):
        """Get conversations collection"""
        if self.db is None:
            return None
        return self.db[COLLECTIONS['conversations']]
    
    @property
    def messages(self):
        """Get messages collection"""
        if self.db is None:
            return None
        return self.db[COLLECTIONS['messages']]
    
    @property
    def memory(self):
        """Get memory collection"""
        if self.db is None:
            return None
        return self.db[COLLECTIONS['memory']]
    
    @property
    def uploaded_files(self):
        """Get uploaded files collection"""
        if self.db is None:
            return None
        return self.db[COLLECTIONS['uploaded_files']]
    
    @property
    def users(self):
        """Get users collection"""
        if self.db is None:
            return None
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
            print("âœ… MongoDB connection closed")


# Global instance
mongodb_client = MongoDBClient()


def get_db():
    """Get database instance (helper function)"""
    return mongodb_client.db


def test_connection():
    """Test MongoDB connection"""
    try:
        mongodb_client.connect()
        db = mongodb_client.db
        if db is None:
            print("âŒ Connection test failed: could not obtain database handle")
            return False
        # Insert test document
        test_collection = db.test
        test_doc = {
            "test": "connection",
            "timestamp": datetime.utcnow()
        }
        result = test_collection.insert_one(test_doc)
        print(f"âœ… Test document inserted with ID: {result.inserted_id}")
        
        # Delete test document
        test_collection.delete_one({"_id": result.inserted_id})
        print("âœ… Test document deleted")
        
        # Drop test collection
        db.drop_collection('test')
        print("âœ… Test collection dropped")
        
        return True
    except Exception as e:
        print(f"âŒ Connection test failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Testing MongoDB Connection...")
    print("=" * 50)
    test_connection()
    mongodb_client.close()


