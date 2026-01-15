"""
MongoDB Database Initialization Script for ChatBot Service
Creates collections, indexes, and validation rules
Run this script once to set up the database

Usage:
    python scripts/init_mongodb.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pymongo import ASCENDING, DESCENDING, IndexModel
from config.mongodb_config import get_db, test_connection
from datetime import datetime


def create_collections_with_validation(db):
    """Create collections with schema validation"""
    
    print("📦 Creating collections with validation rules...")
    
    # 1. Conversations collection
    try:
        db.create_collection("conversations", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "model", "created_at"],
                "properties": {
                    "user_id": {"bsonType": "string"},
                    "model": {"bsonType": "string"},
                    "title": {"bsonType": "string"},
                    "system_prompt": {"bsonType": ["string", "null"]},
                    "total_messages": {"bsonType": "int", "minimum": 0},
                    "total_tokens": {"bsonType": "int", "minimum": 0},
                    "is_archived": {"bsonType": "bool"},
                    "metadata": {"bsonType": "object"},
                    "created_at": {"bsonType": "date"},
                    "updated_at": {"bsonType": "date"}
                }
            }
        })
        print("  ✅ Created: conversations")
    except Exception as e:
        print(f"  ⚠️  conversations already exists or error: {e}")
    
    # 2. Messages collection
    try:
        db.create_collection("messages", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["conversation_id", "role", "content", "created_at"],
                "properties": {
                    "conversation_id": {"bsonType": "objectId"},
                    "role": {"enum": ["user", "assistant", "system"]},
                    "content": {"bsonType": "string"},
                    "images": {"bsonType": "array"},
                    "files": {"bsonType": "array"},
                    "metadata": {"bsonType": "object"},
                    "version": {"bsonType": "int", "minimum": 1},
                    "parent_message_id": {"bsonType": ["objectId", "null"]},
                    "is_edited": {"bsonType": "bool"},
                    "is_stopped": {"bsonType": "bool"},
                    "created_at": {"bsonType": "date"}
                }
            }
        })
        print("  ✅ Created: messages")
    except Exception as e:
        print(f"  ⚠️  messages already exists or error: {e}")
    
    # 3. Chatbot memory collection
    try:
        db.create_collection("chatbot_memory", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "question", "answer", "created_at"],
                "properties": {
                    "user_id": {"bsonType": "string"},
                    "conversation_id": {"bsonType": ["objectId", "null"]},
                    "question": {"bsonType": "string"},
                    "answer": {"bsonType": "string"},
                    "context": {"bsonType": ["string", "null"]},
                    "images": {"bsonType": "array"},
                    "rating": {"bsonType": ["int", "null"], "minimum": 1, "maximum": 5},
                    "tags": {"bsonType": "array"},
                    "is_public": {"bsonType": "bool"},
                    "metadata": {"bsonType": "object"},
                    "created_at": {"bsonType": "date"}
                }
            }
        })
        print("  ✅ Created: chatbot_memory")
    except Exception as e:
        print(f"  ⚠️  chatbot_memory already exists or error: {e}")
    
    # 4. Uploaded files collection
    try:
        db.create_collection("uploaded_files", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "original_filename", "file_path", "created_at"],
                "properties": {
                    "user_id": {"bsonType": "string"},
                    "conversation_id": {"bsonType": ["objectId", "null"]},
                    "original_filename": {"bsonType": "string"},
                    "stored_filename": {"bsonType": "string"},
                    "file_path": {"bsonType": "string"},
                    "file_type": {"bsonType": "string"},
                    "file_size": {"bsonType": "int", "minimum": 0},
                    "mime_type": {"bsonType": "string"},
                    "analysis_result": {"bsonType": ["string", "null"]},
                    "metadata": {"bsonType": "object"},
                    "created_at": {"bsonType": "date"}
                }
            }
        })
        print("  ✅ Created: uploaded_files")
    except Exception as e:
        print(f"  ⚠️  uploaded_files already exists or error: {e}")
    
    # 5. Users collection (optional)
    try:
        db.create_collection("users", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["username", "email", "created_at"],
                "properties": {
                    "username": {"bsonType": "string"},
                    "email": {"bsonType": "string"},
                    "password_hash": {"bsonType": ["string", "null"]},
                    "full_name": {"bsonType": ["string", "null"]},
                    "avatar_url": {"bsonType": ["string", "null"]},
                    "role": {"enum": ["user", "admin", "developer"]},
                    "is_active": {"bsonType": "bool"},
                    "api_quota_daily": {"bsonType": "int", "minimum": 0},
                    "preferences": {"bsonType": "object"},
                    "created_at": {"bsonType": "date"},
                    "last_login": {"bsonType": ["date", "null"]},
                    "last_ip": {"bsonType": ["string", "null"]}
                }
            }
        })
        print("  ✅ Created: users")
    except Exception as e:
        print(f"  ⚠️  users already exists or error: {e}")
    
    # 6. User settings collection
    try:
        db.create_collection("user_settings", validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "updated_at"],
                "properties": {
                    "user_id": {"bsonType": "string"},
                    "chatbot_settings": {"bsonType": "object"},
                    "ui_settings": {"bsonType": "object"},
                    "notification_settings": {"bsonType": "object"},
                    "updated_at": {"bsonType": "date"}
                }
            }
        })
        print("  ✅ Created: user_settings")
    except Exception as e:
        print(f"  ⚠️  user_settings already exists or error: {e}")


def create_indexes(db):
    """Create indexes for optimal query performance"""
    
    print("\n🔍 Creating indexes...")
    
    # Conversations indexes
    conversations_indexes = [
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("user_id", ASCENDING), ("is_archived", ASCENDING)]),
        IndexModel([("updated_at", DESCENDING)]),
        IndexModel([("model", ASCENDING)])
    ]
    result = db.conversations.create_indexes(conversations_indexes)
    print(f"  ✅ conversations: {len(result)} indexes")
    
    # Messages indexes
    messages_indexes = [
        IndexModel([("conversation_id", ASCENDING), ("created_at", ASCENDING)]),
        IndexModel([("role", ASCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("parent_message_id", ASCENDING)])  # For versioning
    ]
    result = db.messages.create_indexes(messages_indexes)
    print(f"  ✅ messages: {len(result)} indexes")
    
    # Chatbot memory indexes
    memory_indexes = [
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("tags", ASCENDING)]),  # Multi-key index for array
        IndexModel([("conversation_id", ASCENDING)]),
        IndexModel([("rating", DESCENDING)]),
        IndexModel([("is_public", ASCENDING)])
    ]
    result = db.chatbot_memory.create_indexes(memory_indexes)
    print(f"  ✅ chatbot_memory: {len(result)} indexes")
    
    # Uploaded files indexes
    files_indexes = [
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("conversation_id", ASCENDING)]),
        IndexModel([("file_type", ASCENDING)]),
        IndexModel([("original_filename", ASCENDING)])
    ]
    result = db.uploaded_files.create_indexes(files_indexes)
    print(f"  ✅ uploaded_files: {len(result)} indexes")
    
    # Users indexes
    users_indexes = [
        IndexModel([("username", ASCENDING)], unique=True),
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("role", ASCENDING)])
    ]
    result = db.users.create_indexes(users_indexes)
    print(f"  ✅ users: {len(result)} indexes")
    
    # User settings indexes
    settings_indexes = [
        IndexModel([("user_id", ASCENDING)], unique=True)
    ]
    result = db.user_settings.create_indexes(settings_indexes)
    print(f"  ✅ user_settings: {len(result)} indexes")


def insert_sample_data(db):
    """Insert sample data for testing"""
    
    print("\n📝 Inserting sample data...")
    
    # Sample conversation
    conversation = {
        "user_id": "demo_user_001",
        "model": "grok-3",
        "title": "Welcome to ChatBot v2.0",
        "system_prompt": "You are a helpful AI assistant.",
        "total_messages": 2,
        "total_tokens": 150,
        "is_archived": False,
        "metadata": {
            "temperature": 0.7,
            "max_tokens": 2048
        },
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    conv_id = db.conversations.insert_one(conversation).inserted_id
    print(f"  ✅ Created sample conversation: {conv_id}")
    
    # Sample messages
    messages = [
        {
            "conversation_id": conv_id,
            "role": "user",
            "content": "Hello! What can you do?",
            "images": [],
            "files": [],
            "metadata": {},
            "version": 1,
            "parent_message_id": None,
            "is_edited": False,
            "is_stopped": False,
            "created_at": datetime.utcnow()
        },
        {
            "conversation_id": conv_id,
            "role": "assistant",
            "content": "Hello! I'm ChatBot v2.0. I can help you with:\n\n1. 💬 Natural conversations\n2. 📁 File analysis (PDFs, images, code)\n3. 🎨 Image generation (via Stable Diffusion)\n4. 🧠 Memory and learning\n5. 🔧 Multiple AI models (GROK, GPT, Qwen)\n\nHow can I assist you today?",
            "images": [],
            "files": [],
            "metadata": {
                "model": "grok-3",
                "tokens": 120,
                "temperature": 0.7,
                "finish_reason": "stop",
                "generation_time_ms": 1500
            },
            "version": 1,
            "parent_message_id": None,
            "is_edited": False,
            "is_stopped": False,
            "created_at": datetime.utcnow()
        }
    ]
    db.messages.insert_many(messages)
    print(f"  ✅ Created {len(messages)} sample messages")
    
    # Sample memory
    memory = {
        "user_id": "demo_user_001",
        "conversation_id": conv_id,
        "question": "What is ChatBot v2.0?",
        "answer": "ChatBot v2.0 is an AI-powered chatbot with multi-model support, file analysis, image generation, and memory capabilities.",
        "context": "Introduction conversation",
        "images": [],
        "rating": 5,
        "tags": ["introduction", "features", "chatbot"],
        "is_public": True,
        "metadata": {
            "model_used": "grok-3",
            "tokens": 80,
            "confidence_score": 0.98
        },
        "created_at": datetime.utcnow()
    }
    mem_id = db.chatbot_memory.insert_one(memory).inserted_id
    print(f"  ✅ Created sample memory: {mem_id}")
    
    # Sample user settings
    settings = {
        "user_id": "demo_user_001",
        "chatbot_settings": {
            "default_model": "grok-3",
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
    settings_id = db.user_settings.insert_one(settings).inserted_id
    print(f"  ✅ Created sample user settings: {settings_id}")


def print_database_stats(db):
    """Print database statistics"""
    
    print("\n📊 Database Statistics:")
    print("=" * 50)
    
    collections = [
        "conversations",
        "messages",
        "chatbot_memory",
        "uploaded_files",
        "users",
        "user_settings"
    ]
    
    for coll_name in collections:
        count = db[coll_name].count_documents({})
        indexes = len(db[coll_name].list_indexes())
        print(f"  📦 {coll_name:20} | Documents: {count:5} | Indexes: {indexes}")
    
    print("=" * 50)


def main():
    """Main initialization function"""
    
    print("🚀 MongoDB Database Initialization for ChatBot Service")
    print("=" * 60)
    
    # Test connection
    print("\n1️⃣  Testing connection...")
    if not test_connection():
        print("❌ Connection failed! Please check your MongoDB URI.")
        return
    
    # Get database
    db = get_db()
    
    # Create collections with validation
    print("\n2️⃣  Setting up collections...")
    create_collections_with_validation(db)
    
    # Create indexes
    print("\n3️⃣  Creating indexes...")
    create_indexes(db)
    
    # Insert sample data
    print("\n4️⃣  Inserting sample data...")
    insert_sample_data(db)
    
    # Print statistics
    print_database_stats(db)
    
    print("\n✨ Database initialization complete!")
    print("\n📖 Next steps:")
    print("  1. Test the connection: python -c 'from config.mongodb_config import test_connection; test_connection()'")
    print("  2. View sample data: Connect to MongoDB Atlas and browse collections")
    print("  3. Update app.py to use MongoDB instead of SQLite")
    print("  4. Install required packages: pip install pymongo motor (for async support)")


if __name__ == "__main__":
    main()
