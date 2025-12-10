# MongoDB Integration Guide

## 📋 Overview

ChatBot v2.0 now supports MongoDB Atlas for persistent conversation storage. This allows:
- ✅ Conversations persist across sessions
- ✅ Multiple conversation threads
- ✅ Full message history
- ✅ User-specific data
- ✅ Archive/delete conversations

---

## 🔧 Configuration

### 1. MongoDB is Automatically Connected

MongoDB connection is initialized when the app starts:

```python
# In app.py
mongodb_client.connect()
MONGODB_ENABLED = True
```

If MongoDB fails to connect, the app falls back to session-based storage.

### 2. Environment Variables

Make sure `.env` has:

```env
MONGODB_URI=mongodb+srv://admin:XHk24ypeQsuhGbSA@ai-assistant.aspuqwb.mongodb.net/
MONGODB_DATABASE=chatbot_db
```

---

## 🎯 How It Works

### **Conversation Flow**

```
1. User opens ChatBot
   ↓
2. get_chatbot() creates ChatbotAgent
   ↓
3. Get/create MongoDB conversation
   ↓
4. Load conversation history from DB
   ↓
5. User sends message
   ↓
6. Save user message to MongoDB
   ↓
7. Get AI response
   ↓
8. Save assistant message to MongoDB
   ↓
9. Update conversation metadata (token count, timestamp)
```

### **Data Structure**

#### **Conversations Collection**
```json
{
  "_id": ObjectId("..."),
  "user_id": "anonymous_abc123",
  "model": "gemini-2.0-flash",
  "title": "Python Programming Help",
  "total_messages": 10,
  "total_tokens": 2500,
  "is_archived": false,
  "created_at": ISODate("2025-11-09T..."),
  "updated_at": ISODate("2025-11-09T...")
}
```

#### **Messages Collection**
```json
{
  "_id": ObjectId("..."),
  "conversation_id": ObjectId("..."),
  "role": "user",
  "content": "How to use MongoDB with Python?",
  "images": [],
  "files": [],
  "metadata": {
    "model": "gemini-2.0-flash",
    "context": "programming",
    "deep_thinking": false
  },
  "version": 1,
  "is_edited": false,
  "created_at": ISODate("2025-11-09T...")
}
```

---

## 📚 API Endpoints

### **1. Get All Conversations**

```http
GET /api/conversations
```

**Response:**
```json
{
  "conversations": [
    {
      "_id": "673e5f8a9b1d2c3f4a5b6c7d",
      "title": "Python Help",
      "model": "gemini-2.0-flash",
      "total_messages": 5,
      "created_at": "2025-11-09T10:30:00Z"
    }
  ],
  "count": 1
}
```

### **2. Get Specific Conversation**

```http
GET /api/conversations/{conversation_id}
```

**Response:**
```json
{
  "_id": "673e5f8a9b1d2c3f4a5b6c7d",
  "title": "Python Help",
  "messages": [
    {
      "_id": "...",
      "role": "user",
      "content": "Hello",
      "created_at": "..."
    },
    {
      "_id": "...",
      "role": "assistant",
      "content": "Hi! How can I help?",
      "created_at": "..."
    }
  ]
}
```

### **3. Create New Conversation**

```http
POST /api/conversations/new
Content-Type: application/json

{
  "model": "gemini-2.0-flash",
  "title": "New Chat"
}
```

### **4. Delete Conversation**

```http
DELETE /api/conversations/{conversation_id}
```

### **5. Archive Conversation**

```http
POST /api/conversations/{conversation_id}/archive
```

---

## 🔄 Migration from Session-based to MongoDB

### **Automatic Migration**

When MongoDB is enabled, the app automatically:
1. Creates a conversation on first message
2. Migrates in-memory history to MongoDB
3. Loads history from MongoDB on session restore

### **Manual Migration**

If you have existing JSON conversation files, run:

```python
# scripts/migrate_json_to_mongodb.py (to be created)
from config.mongodb_helpers import ConversationDB, MessageDB
import json
from pathlib import Path

def migrate_json_conversations():
    """Migrate JSON conversations to MongoDB"""
    storage_dir = Path("ChatBot/Storage")
    
    for json_file in storage_dir.glob("conversation_*.json"):
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Create conversation
        conv = ConversationDB.create_conversation(
            user_id=data['user_id'],
            model=data['model'],
            title=data.get('title', 'Migrated Chat')
        )
        
        # Add messages
        for msg in data['messages']:
            MessageDB.add_message(
                conversation_id=str(conv['_id']),
                role=msg['role'],
                content=msg['content']
            )
        
        print(f"✅ Migrated {json_file}")

if __name__ == "__main__":
    migrate_json_conversations()
```

---

## 🧪 Testing MongoDB Integration

### **1. Test Connection**

```bash
cd ChatBot
python -c "from config.mongodb_config import test_connection; test_connection()"
```

### **2. Run Full Test Suite**

```bash
python scripts/test_mongodb.py
```

Expected output:
```
✅ Connection
✅ Conversations
✅ Messages
✅ Memory
✅ Files
✅ Settings
✅ Statistics
✅ Cleanup

🎯 Results: 8/8 tests passed
```

### **3. Test via API**

```bash
# Start server
python app.py

# In another terminal
curl http://localhost:5000/api/conversations
```

---

## 🔍 Debugging

### **Check MongoDB Status**

```python
from config.mongodb_config import mongodb_client

# Check connection
mongodb_client.connect()

# Get database
db = mongodb_client.db

# Count conversations
print(f"Conversations: {db.conversations.count_documents({})}")

# Count messages
print(f"Messages: {db.messages.count_documents({})}")
```

### **View Logs**

```bash
# App logs will show MongoDB operations
✅ MongoDB connection established
✅ Created new conversation: 673e5f8a...
✅ Saved message to DB: 673e5f8b...
```

### **Common Issues**

| Issue | Solution |
|:------|:---------|
| `MongoDB not enabled` | Check `.env` has `MONGODB_URI` |
| `Connection timeout` | Check internet connection, MongoDB Atlas IP whitelist |
| `Authentication failed` | Verify username/password in URI |
| `Database not found` | Run `python scripts/init_mongodb.py` |
| `Indexes missing` | MongoDB will auto-create on first use |

---

## 🚀 Performance Tips

### **1. Connection Pooling**

MongoDB driver automatically handles connection pooling:
```python
# In mongodb_config.py
client = MongoClient(
    MONGODB_URI,
    maxPoolSize=50,  # Default: 100
    minPoolSize=10
)
```

### **2. Query Optimization**

Use indexes for common queries:
```python
# Already created by init_mongodb.py
- conversations: user_id + created_at
- messages: conversation_id + created_at
- chatbot_memory: user_id + tags
```

### **3. Limit Results**

```python
# Don't load all messages
messages = MessageDB.get_conversation_messages(conv_id, limit=50)

# Don't load all conversations
convs = ConversationDB.get_user_conversations(user_id, limit=20)
```

---

## 📊 Monitoring

### **Database Statistics**

```python
from config.mongodb_helpers import get_user_statistics

stats = get_user_statistics("user_123")
print(f"Total Conversations: {stats['total_conversations']}")
print(f"Total Messages: {stats['total_messages']}")
print(f"Total Storage: {stats['total_storage_mb']} MB")
```

### **MongoDB Atlas Dashboard**

1. Go to https://cloud.mongodb.com
2. Click on cluster "AI-Assistant"
3. View:
   - Real-time operations
   - Storage usage
   - Query performance
   - Slow queries

---

## 🔐 Security Best Practices

### **1. Use Environment Variables**

```env
# .env
MONGODB_URI=mongodb+srv://admin:password@cluster.mongodb.net/
```

**Never commit credentials to Git!**

### **2. IP Whitelist**

In MongoDB Atlas:
- Network Access → IP Access List
- Add your IP or `0.0.0.0/0` (development only)

### **3. User Permissions**

Create separate database user with limited permissions:
```javascript
// In MongoDB Atlas
db.createUser({
  user: "chatbot_app",
  pwd: "secure_password",
  roles: [
    { role: "readWrite", db: "chatbot_db" }
  ]
})
```

---

## 📖 Next Steps

1. ✅ MongoDB is integrated and working
2. 🔄 Test conversation persistence
3. 🎨 Update frontend to show conversation list
4. 📱 Add mobile-responsive UI
5. 🔍 Implement full-text search
6. 📊 Add analytics dashboard

---

## 🆘 Support

- Documentation: `docs/MONGODB_SETUP.md`
- Schema Reference: `config/mongodb_schema.py`
- Helper Functions: `config/mongodb_helpers.py`
- Test Suite: `scripts/test_mongodb.py`

---

## 📝 Changelog

### v2.1.0 (2025-11-09)
- ✅ Added MongoDB Atlas integration
- ✅ Persistent conversation storage
- ✅ API endpoints for conversation management
- ✅ Automatic conversation archiving
- ✅ Backward compatibility with session storage

---

**✨ MongoDB integration is complete and ready to use!**
