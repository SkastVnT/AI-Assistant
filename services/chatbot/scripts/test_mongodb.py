"""
Quick Test Script for MongoDB ChatBot Database
Run this to verify MongoDB connection and basic operations

Usage:
    python ChatBot/scripts/test_mongodb.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.mongodb_config import test_connection, get_db
from config.mongodb_helpers import (
    ConversationDB,
    MessageDB,
    MemoryDB,
    FileDB,
    UserSettingsDB,
    get_user_statistics
)


def test_connection_only():
    """Test 1: Connection test"""
    print("\n" + "=" * 60)
    print("TEST 1: MongoDB Connection")
    print("=" * 60)
    
    if test_connection():
        print("✅ Connection successful!")
        return True
    else:
        print("❌ Connection failed!")
        return False


def test_conversation_operations():
    """Test 2: Conversation CRUD operations"""
    print("\n" + "=" * 60)
    print("TEST 2: Conversation Operations")
    print("=" * 60)
    
    try:
        # Create conversation
        print("\n📝 Creating test conversation...")
        conv = ConversationDB.create_conversation(
            user_id="test_user_001",
            model="grok-3",
            title="Test Conversation"
        )
        print(f"✅ Created conversation: {conv['_id']}")
        
        # Get conversation
        print("\n🔍 Retrieving conversation...")
        retrieved = ConversationDB.get_conversation(str(conv["_id"]))
        print(f"✅ Retrieved: {retrieved['title']}")
        
        # Update conversation
        print("\n✏️  Updating conversation title...")
        updated = ConversationDB.update_conversation(
            str(conv["_id"]),
            {"title": "Updated Test Conversation"}
        )
        print(f"✅ Updated: {updated}")
        
        # Get user conversations
        print("\n📋 Getting user conversations...")
        user_convs = ConversationDB.get_user_conversations("test_user_001")
        print(f"✅ Found {len(user_convs)} conversations")
        
        return str(conv["_id"])
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def test_message_operations(conversation_id: str):
    """Test 3: Message CRUD operations"""
    print("\n" + "=" * 60)
    print("TEST 3: Message Operations")
    print("=" * 60)
    
    try:
        # Add user message
        print("\n💬 Adding user message...")
        msg1 = MessageDB.add_message(
            conversation_id=conversation_id,
            role="user",
            content="Hello, this is a test message!"
        )
        print(f"✅ Created message: {msg1['_id']}")
        
        # Add assistant message
        print("\n🤖 Adding assistant message...")
        msg2 = MessageDB.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content="Hello! This is a test response.",
            metadata={
                "model": "grok-3",
                "tokens": 25,
                "generation_time_ms": 500
            }
        )
        print(f"✅ Created message: {msg2['_id']}")
        
        # Get all messages
        print("\n📨 Getting conversation messages...")
        messages = MessageDB.get_conversation_messages(conversation_id)
        print(f"✅ Found {len(messages)} messages")
        
        for i, msg in enumerate(messages, 1):
            print(f"   {i}. [{msg['role']}]: {msg['content'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_memory_operations():
    """Test 4: Memory operations"""
    print("\n" + "=" * 60)
    print("TEST 4: Memory Operations")
    print("=" * 60)
    
    try:
        # Save memory
        print("\n🧠 Saving memory...")
        memory = MemoryDB.save_memory(
            user_id="test_user_001",
            question="What is MongoDB?",
            answer="MongoDB is a NoSQL database that stores data in flexible, JSON-like documents.",
            tags=["mongodb", "database", "nosql"],
            is_public=True
        )
        print(f"✅ Saved memory: {memory['_id']}")
        
        # Get user memories
        print("\n🔍 Getting user memories...")
        memories = MemoryDB.get_user_memories("test_user_001")
        print(f"✅ Found {len(memories)} memories")
        
        # Rate memory
        print("\n⭐ Rating memory...")
        rated = MemoryDB.rate_memory(str(memory["_id"]), 5)
        print(f"✅ Rated: {rated}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_file_operations():
    """Test 5: File operations"""
    print("\n" + "=" * 60)
    print("TEST 5: File Operations")
    print("=" * 60)
    
    try:
        # Save file record
        print("\n📁 Saving file record...")
        file_record = FileDB.save_file_record(
            user_id="test_user_001",
            original_filename="test_document.pdf",
            stored_filename="upload_20251109_test.pdf",
            file_path="/Storage/uploads/upload_20251109_test.pdf",
            file_type="pdf",
            file_size=1024000,
            mime_type="application/pdf",
            analysis_result="Test PDF document"
        )
        print(f"✅ Saved file: {file_record['_id']}")
        
        # Get user files
        print("\n📂 Getting user files...")
        files = FileDB.get_user_files("test_user_001")
        print(f"✅ Found {len(files)} files")
        
        # Get storage size
        print("\n💾 Calculating storage size...")
        storage = FileDB.get_total_storage_size("test_user_001")
        print(f"✅ Total storage: {storage / 1024:.2f} KB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_settings_operations():
    """Test 6: User settings operations"""
    print("\n" + "=" * 60)
    print("TEST 6: User Settings Operations")
    print("=" * 60)
    
    try:
        # Create default settings
        print("\n⚙️  Creating default settings...")
        settings = UserSettingsDB.create_default_settings("test_user_001")
        print(f"✅ Created settings for user: test_user_001")
        
        # Update settings
        print("\n✏️  Updating settings...")
        updated = UserSettingsDB.update_settings(
            "test_user_001",
            {
                "ui_settings.theme": "light",
                "chatbot_settings.temperature": 0.9
            }
        )
        print(f"✅ Updated: {updated}")
        
        # Get settings
        print("\n🔍 Getting settings...")
        user_settings = UserSettingsDB.get_settings("test_user_001")
        print(f"✅ Retrieved settings")
        print(f"   Theme: {user_settings.get('ui_settings', {}).get('theme')}")
        print(f"   Temperature: {user_settings.get('chatbot_settings', {}).get('temperature')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_statistics():
    """Test 7: User statistics"""
    print("\n" + "=" * 60)
    print("TEST 7: User Statistics")
    print("=" * 60)
    
    try:
        print("\n📊 Getting user statistics...")
        stats = get_user_statistics("test_user_001")
        
        print("\n✅ Statistics:")
        print(f"   Total Conversations: {stats['total_conversations']}")
        print(f"   Active Conversations: {stats['active_conversations']}")
        print(f"   Total Messages: {stats['total_messages']}")
        print(f"   Total Tokens: {stats['total_tokens']}")
        print(f"   Total Memories: {stats['total_memories']}")
        print(f"   Total Files: {stats['total_files']}")
        print(f"   Total Storage: {stats['total_storage_mb']} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def cleanup_test_data():
    """Cleanup: Delete test data"""
    print("\n" + "=" * 60)
    print("CLEANUP: Deleting Test Data")
    print("=" * 60)
    
    try:
        db = get_db()
        
        # Delete test user data
        print("\n🗑️  Deleting test data...")
        
        result1 = db.conversations.delete_many({"user_id": "test_user_001"})
        print(f"   ✅ Deleted {result1.deleted_count} conversations")
        
        result2 = db.messages.delete_many({
            "conversation_id": {"$in": [
                doc["_id"] for doc in 
                db.conversations.find({"user_id": "test_user_001"})
            ]}
        })
        print(f"   ✅ Deleted {result2.deleted_count} messages")
        
        result3 = db.chatbot_memory.delete_many({"user_id": "test_user_001"})
        print(f"   ✅ Deleted {result3.deleted_count} memories")
        
        result4 = db.uploaded_files.delete_many({"user_id": "test_user_001"})
        print(f"   ✅ Deleted {result4.deleted_count} files")
        
        result5 = db.user_settings.delete_many({"user_id": "test_user_001"})
        print(f"   ✅ Deleted {result5.deleted_count} settings")
        
        print("\n✅ Cleanup complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🚀 MongoDB ChatBot Database Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Connection
    if not test_connection_only():
        print("\n❌ Connection failed! Cannot proceed with tests.")
        return
    results.append(("Connection", True))
    
    # Test 2: Conversations
    conversation_id = test_conversation_operations()
    results.append(("Conversations", conversation_id is not None))
    
    if not conversation_id:
        print("\n❌ Conversation test failed! Skipping dependent tests.")
        return
    
    # Test 3: Messages
    msg_result = test_message_operations(conversation_id)
    results.append(("Messages", msg_result))
    
    # Test 4: Memory
    mem_result = test_memory_operations()
    results.append(("Memory", mem_result))
    
    # Test 5: Files
    file_result = test_file_operations()
    results.append(("Files", file_result))
    
    # Test 6: Settings
    settings_result = test_settings_operations()
    results.append(("Settings", settings_result))
    
    # Test 7: Statistics
    stats_result = test_statistics()
    results.append(("Statistics", stats_result))
    
    # Cleanup
    cleanup_result = cleanup_test_data()
    results.append(("Cleanup", cleanup_result))
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} | {test_name}")
    
    print("=" * 60)
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✨ All tests passed! MongoDB is ready for ChatBot service.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    print("\n📖 Next steps:")
    print("  1. Run: python ChatBot/scripts/init_mongodb.py")
    print("  2. Update ChatBot/app.py to use MongoDB")
    print("  3. Install: pip install pymongo")


if __name__ == "__main__":
    main()
