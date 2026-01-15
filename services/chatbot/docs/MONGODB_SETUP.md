# MongoDB Database Setup for ChatBot v2.0

## 📋 Overview

ChatBot service uses **MongoDB Atlas** (cloud-hosted) for storing conversations, messages, AI memory, uploaded files, and user settings.

**Database**: `chatbot_db`  
**Connection**: MongoDB Atlas cluster `AI-Assistant`

---

## 🗄️ Database Schema

### Collections (6 total)

1. **conversations** - Chat conversations
2. **messages** - Individual messages in conversations
3. **chatbot_memory** - AI learning and memory storage
4. **uploaded_files** - File upload metadata
5. **users** - User information (optional)
6. **user_settings** - User preferences and settings

### Detailed Schema

#### 1. conversations
```javascript
{
  _id: ObjectId,
  user_id: string,
  model: string,  // 'grok-3', 'gpt-4', etc.
  title: string,
  system_prompt: string,
  total_messages: int,
  total_tokens: int,
  is_archived: bool,
  metadata: {
    temperature: float,
    max_tokens: int,
    custom_settings: object
  },
  created_at: ISODate,
  updated_at: ISODate
}
```

**Indexes**:
- `user_id + created_at` (descending)
- `user_id + is_archived`
- `updated_at` (descending)

#### 2. messages
```javascript
{
  _id: ObjectId,
  conversation_id: ObjectId,  // References conversations._id
  role: string,  // 'user', 'assistant', 'system'
  content: string,
  images: [
    {
      url: string,
      caption: string,
      size: int,
      mime_type: string,
      generated: bool
    }
  ],
  files: [
    {
      name: string,
      path: string,
      type: string,
      size: int
    }
  ],
  metadata: {
    model: string,
    tokens: int,
    finish_reason: string,
    generation_time_ms: int
  },
  version: int,  // For message versioning
  parent_message_id: ObjectId,
  is_edited: bool,
  is_stopped: bool,
  created_at: ISODate
}
```

**Indexes**:
- `conversation_id + created_at` (ascending)
- `role`
- `parent_message_id` (for versioning)

#### 3. chatbot_memory
```javascript
{
  _id: ObjectId,
  user_id: string,
  conversation_id: ObjectId,
  question: string,
  answer: string,
  context: string,
  images: [],
  rating: int,  // 1-5 stars
  tags: [string],
  is_public: bool,
  metadata: {
    model_used: string,
    tokens: int,
    confidence_score: float
  },
  created_at: ISODate
}
```

**Indexes**:
- `user_id + created_at` (descending)
- `tags` (multi-key index)
- `rating` (descending)

#### 4. uploaded_files
```javascript
{
  _id: ObjectId,
  user_id: string,
  conversation_id: ObjectId,
  original_filename: string,
  stored_filename: string,
  file_path: string,
  file_type: string,
  file_size: int,
  mime_type: string,
  analysis_result: string,
  metadata: {
    upload_time_ms: int,
    analysis_time_ms: int,
    extracted_text: string,
    page_count: int
  },
  created_at: ISODate
}
```

**Indexes**:
- `user_id + created_at` (descending)
- `conversation_id`
- `file_type`

#### 5. users (Optional - for multi-user support)
```javascript
{
  _id: ObjectId,
  username: string,
  email: string,
  password_hash: string,
  full_name: string,
  avatar_url: string,
  role: string,  // 'user', 'admin', 'developer'
  is_active: bool,
  preferences: object,
  created_at: ISODate,
  last_login: ISODate
}
```

**Indexes**:
- `username` (unique)
- `email` (unique)

#### 6. user_settings
```javascript
{
  _id: ObjectId,
  user_id: string,
  chatbot_settings: {
    default_model: string,
    temperature: float,
    max_tokens: int,
    enable_memory: bool
  },
  ui_settings: {
    theme: string,
    font_size: string
  },
  updated_at: ISODate
}
```

**Indexes**:
- `user_id` (unique)

---

## 🚀 Setup Instructions

### 1. Install Dependencies

```bash
# Basic MongoDB driver
pip install pymongo

# Optional: Async support (recommended for production)
pip install motor

# Optional: ODM (Object Document Mapper)
pip install mongoengine
```

### 2. Configure Connection

MongoDB Atlas URI is already configured in `config/mongodb_config.py`:

```python
MONGODB_URI = "mongodb+srv://admin:XHk24ypeQsuhGbSA@ai-assistant.aspuqwb.mongodb.net/"
DATABASE_NAME = "chatbot_db"
```

**Environment Variables** (recommended for production):
```bash
# Create .env file
MONGODB_URI=mongodb+srv://admin:XHk24ypeQsuhGbSA@ai-assistant.aspuqwb.mongodb.net/
MONGODB_DATABASE=chatbot_db
```

### 3. Initialize Database

Run the initialization script to create collections and indexes:

```bash
cd ChatBot
python scripts/init_mongodb.py
```

This will:
- ✅ Create 6 collections with validation rules
- ✅ Create indexes for optimal performance
- ✅ Insert sample data for testing
- ✅ Display database statistics

### 4. Test Connection

```bash
python scripts/test_mongodb.py
```

This will run comprehensive tests:
- Connection test
- CRUD operations for all collections
- User statistics
- Automatic cleanup

---

## 📚 Usage Examples

### Basic Usage

```python
from config.mongodb_helpers import ConversationDB, MessageDB

# Create conversation
conv = ConversationDB.create_conversation(
    user_id="user_123",
    model="grok-3",
    title="New Chat"
)

# Add message
msg = MessageDB.add_message(
    conversation_id=str(conv["_id"]),
    role="user",
    content="Hello AI!"
)

# Get conversation with messages
full_conv = ConversationDB.get_conversation_with_messages(
    str(conv["_id"])
)
```

### Advanced Queries

```python
from config.mongodb_helpers import MemoryDB, FileDB, get_user_statistics

# Search memories by tags
memories = MemoryDB.get_user_memories(
    user_id="user_123",
    tags=["python", "coding"],
    limit=20
)

# Get user files
files = FileDB.get_user_files(
    user_id="user_123",
    file_type="pdf"
)

# Get statistics
stats = get_user_statistics("user_123")
print(f"Total conversations: {stats['total_conversations']}")
print(f"Total messages: {stats['total_messages']}")
print(f"Storage used: {stats['total_storage_mb']} MB")
```

### Direct MongoDB Queries

```python
from config.mongodb_config import get_database

db = get_database()

# Get all conversations
conversations = db.conversations.find({"user_id": "user_123"})

# Aggregation query
pipeline = [
    {"$match": {"user_id": "user_123"}},
    {"$group": {
        "_id": "$model",
        "count": {"$sum": 1}
    }}
]
model_stats = db.conversations.aggregate(pipeline)
```

---

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| `config/mongodb_config.py` | Connection setup, database/collection config |
| `config/mongodb_schema.py` | Detailed schema definitions and examples |
| `config/mongodb_helpers.py` | CRUD helper functions for all collections |
| `scripts/init_mongodb.py` | Database initialization script |
| `scripts/test_mongodb.py` | Comprehensive test suite |

---

## 📊 Database Features

### 1. Schema Validation
All collections have JSON schema validation to ensure data integrity:
- Required fields are enforced
- Data types are validated
- Enum values are restricted

### 2. Indexes
Optimized indexes for common queries:
- User-based queries (user_id)
- Time-based sorting (created_at, updated_at)
- Tag-based search (tags multi-key index)
- Full-text search (text indexes)

### 3. Relationships
- `messages.conversation_id` → `conversations._id`
- `chatbot_memory.conversation_id` → `conversations._id`
- `uploaded_files.conversation_id` → `conversations._id`

### 4. Message Versioning
Messages support versioning for edit history:
- Original message: `version=1, parent_message_id=None`
- Edited message: `version=2, parent_message_id=original_id`

---

## 🔐 Security Considerations

### Current Setup
- ✅ MongoDB Atlas with authentication
- ✅ SSL/TLS encrypted connections
- ✅ Database user with limited permissions

### Recommended Improvements
1. **Environment Variables**: Store credentials in `.env` file
2. **IP Whitelist**: Configure MongoDB Atlas IP whitelist
3. **Role-Based Access**: Create separate DB users for different services
4. **Encryption**: Enable encryption at rest in MongoDB Atlas

### Migration from SQLite

```python
# Example migration script
import sqlite3
from config.mongodb_helpers import ConversationDB, MessageDB

# Read from SQLite
sqlite_conn = sqlite3.connect("chatbot.db")
cursor = sqlite_conn.cursor()
cursor.execute("SELECT * FROM conversations")

# Migrate to MongoDB
for row in cursor.fetchall():
    ConversationDB.create_conversation(
        user_id=row[1],
        model=row[2],
        title=row[3]
    )
```

---

## 📈 Performance Tips

1. **Use Indexes**: All common queries are indexed
2. **Limit Results**: Use `.limit()` for large collections
3. **Projection**: Only fetch needed fields
4. **Aggregation Pipeline**: Use for complex queries
5. **Connection Pooling**: MongoDB driver handles this automatically

---

## 🐛 Troubleshooting

### Connection Issues
```python
from config.mongodb_config import test_connection
test_connection()  # Will show detailed error
```

### Common Errors

1. **"Authentication failed"**
   - Check username/password in URI
   - Verify database user has correct permissions

2. **"Network timeout"**
   - Check internet connection
   - Verify MongoDB Atlas cluster is running
   - Check IP whitelist in Atlas

3. **"Database/Collection not found"**
   - Run `python scripts/init_mongodb.py` first

---

## 📖 References

- [MongoDB Documentation](https://docs.mongodb.com/)
- [PyMongo Documentation](https://pymongo.readthedocs.io/)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
- [Motor (Async Driver)](https://motor.readthedocs.io/)

---

## 📝 TODO / Future Enhancements

- [ ] Add async support with Motor
- [ ] Implement connection pooling optimization
- [ ] Add MongoDB Change Streams for real-time updates
- [ ] Create backup/restore scripts
- [ ] Add data migration tools (SQLite → MongoDB)
- [ ] Implement sharding for scalability
- [ ] Add MongoDB Atlas Search for advanced text search
- [ ] Create monitoring dashboard with MongoDB Charts

---

## 📄 License

Same as main project license.
