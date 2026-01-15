// Initialize MongoDB with required collections and indexes
// This script runs automatically when MongoDB container starts

db = db.getSiblingDB('ai_assistant');

// Create collections
db.createCollection('users');
db.createCollection('conversations');
db.createCollection('messages');
db.createCollection('memories');
db.createCollection('files');
db.createCollection('user_settings');
db.createCollection('learning_data');
db.createCollection('deleted_conversations');

// Create indexes for users
db.users.createIndex({ "email": 1 }, { unique: true, sparse: true });
db.users.createIndex({ "username": 1 }, { unique: true, sparse: true });
db.users.createIndex({ "created_at": 1 });

// Create indexes for conversations
db.conversations.createIndex({ "user_id": 1 });
db.conversations.createIndex({ "created_at": -1 });
db.conversations.createIndex({ "updated_at": -1 });
db.conversations.createIndex({ "is_archived": 1, "user_id": 1 });
db.conversations.createIndex({ "model": 1 });

// Create indexes for messages
db.messages.createIndex({ "conversation_id": 1 });
db.messages.createIndex({ "created_at": -1 });
db.messages.createIndex({ "role": 1 });
db.messages.createIndex({ "conversation_id": 1, "created_at": 1 });

// Create indexes for memories (AI learning)
db.memories.createIndex({ "user_id": 1 });
db.memories.createIndex({ "category": 1 });
db.memories.createIndex({ "created_at": -1 });
db.memories.createIndex({ "importance": -1 });
db.memories.createIndex({ "tags": 1 });

// Create indexes for files
db.files.createIndex({ "user_id": 1 });
db.files.createIndex({ "conversation_id": 1 });
db.files.createIndex({ "uploaded_at": -1 });
db.files.createIndex({ "file_type": 1 });

// Create indexes for learning_data (AI self-learning)
db.learning_data.createIndex({ "source": 1 });
db.learning_data.createIndex({ "category": 1 });
db.learning_data.createIndex({ "quality_score": -1 });
db.learning_data.createIndex({ "created_at": -1 });
db.learning_data.createIndex({ "is_approved": 1 });

// Create indexes for deleted_conversations (archive before delete)
db.deleted_conversations.createIndex({ "original_user_id": 1 });
db.deleted_conversations.createIndex({ "deleted_at": -1 });
db.deleted_conversations.createIndex({ "should_learn": 1 });

// Create TTL index for auto-cleanup of old deleted data (optional - 90 days)
db.deleted_conversations.createIndex(
    { "deleted_at": 1 }, 
    { expireAfterSeconds: 7776000 }  // 90 days
);

print('✅ AI-Assistant MongoDB initialized successfully!');
print('📊 Collections created: users, conversations, messages, memories, files, learning_data, deleted_conversations');
print('🔍 Indexes created for optimal query performance');
