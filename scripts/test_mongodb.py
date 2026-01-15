"""
Test MongoDB Connection and Insert Sample Chat Data
"""
import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_mongodb_connection():
    """Test MongoDB connection and insert sample chat data"""
    
    mongodb_uri = os.getenv('MONGODB_URI')
    
    if not mongodb_uri:
        print("❌ MONGODB_URI not found in .env file")
        return False
    
    print(f"🔗 MongoDB URI: {mongodb_uri[:50]}...")
    print()
    
    try:
        # Create MongoDB client
        print("📡 Connecting to MongoDB...")
        client = MongoClient(mongodb_uri, server_api=ServerApi('1'), serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        print("✅ MongoDB connection successful!")
        print()
        
        # Get database and collection (same as chatbot uses)
        db = client['ai_assistant']
        collection = db['chat_history']
        
        print(f"📊 Database: {db.name}")
        print(f"📁 Collection: {collection.name}")
        print()
        
        # Create sample chat data (same structure as chatbot)
        sample_chat = {
            "session_id": f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now(),
            "user_message": "Hello, this is a test message from MongoDB connection test",
            "ai_response": "Hello! I'm the AI assistant. This is a test response to verify MongoDB connection is working correctly.",
            "model": "grok",
            "metadata": {
                "test": True,
                "source": "test_mongodb.py",
                "chatbot_version": "2.2"
            }
        }
        
        print("💾 Inserting sample chat data...")
        print(f"   Session ID: {sample_chat['session_id']}")
        print(f"   User: {sample_chat['user_message'][:50]}...")
        print(f"   AI: {sample_chat['ai_response'][:50]}...")
        print()
        
        # Insert sample data
        result = collection.insert_one(sample_chat)
        
        print(f"✅ Data inserted successfully!")
        print(f"   Inserted ID: {result.inserted_id}")
        print()
        
        # Verify by reading back
        print("🔍 Verifying inserted data...")
        retrieved = collection.find_one({"_id": result.inserted_id})
        
        if retrieved:
            print("✅ Data retrieved successfully!")
            print(f"   Session ID: {retrieved['session_id']}")
            print(f"   Timestamp: {retrieved['timestamp']}")
            print(f"   Model: {retrieved['model']}")
            print()
        else:
            print("❌ Could not retrieve inserted data")
            return False
        
        # Show collection stats
        count = collection.count_documents({})
        print(f"📊 Collection Statistics:")
        print(f"   Total documents: {count}")
        print()
        
        # Optional: Clean up test data
        cleanup = input("🗑️  Do you want to delete this test data? (y/n): ").lower()
        if cleanup == 'y':
            collection.delete_one({"_id": result.inserted_id})
            print("✅ Test data deleted")
        else:
            print("ℹ️  Test data kept in database")
        
        print()
        print("=" * 60)
        print("✅ MongoDB Connection Test: SUCCESS")
        print("=" * 60)
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ MongoDB Connection Test: FAILED")
        print(f"Error: {str(e)}")
        print()
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 MongoDB Connection Test")
    print("=" * 60)
    print()
    
    test_mongodb_connection()
