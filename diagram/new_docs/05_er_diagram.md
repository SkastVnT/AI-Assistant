# 5️⃣ ENTITY RELATIONSHIP (ER) DIAGRAM - MongoDB

> **Biểu đồ quan hệ thực thể cho MongoDB ChatBot Database**  
> MongoDB Atlas - Document-based database với 6 collections

---

## 📋 Mô tả

ER Diagram cho MongoDB thể hiện:
- **Collections (Documents):** 6 collections chính
- **Relationships:** Referenced (ObjectId) và Embedded documents
- **Cardinality:** 1:1, 1:N, M:N
- **Indexes:** Performance optimization

---

## 🎯 Database Overview

```
Database: chatbot_db (MongoDB Atlas)
Type: Document-based NoSQL
Collections: 6
Documents: ~1000 - 1M+ (scalable)
Indexes: 15+ for performance
```

---

## 📊 ER Diagram - Full Schema

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : creates
    USERS ||--o{ CHATBOT_MEMORY : has
    USERS ||--o{ USER_SETTINGS : has
    
    CONVERSATIONS ||--o{ MESSAGES : contains
    CONVERSATIONS ||--o{ UPLOADED_FILES : has
    CONVERSATIONS ||--o{ CHATBOT_MEMORY : saved_from
    
    MESSAGES ||--o{ MESSAGES : version_of
    
    USERS {
        ObjectId _id PK
        string username UK "Unique username"
        string email UK "Unique email"
        string password_hash "Bcrypt hashed"
        string full_name
        string avatar_url
        string role "user/admin/developer"
        bool is_active
        int api_quota_daily
        object preferences
        ISODate created_at
        ISODate last_login
        string last_ip
    }
    
    CONVERSATIONS {
        ObjectId _id PK
        string user_id FK "Reference to USERS or session ID"
        string model "gemini-2.0-flash, gpt-4o, etc."
        string title "Auto-generated from first message"
        string system_prompt "Custom prompt (optional)"
        int total_messages "Message count"
        int total_tokens "Total tokens used"
        bool is_archived "Soft delete flag"
        object metadata "temperature, max_tokens, top_p, etc."
        ISODate created_at
        ISODate updated_at
    }
    
    MESSAGES {
        ObjectId _id PK
        ObjectId conversation_id FK "Reference to CONVERSATIONS"
        string role "user/assistant/system"
        string content "Message text (markdown supported)"
        array images "Embedded Image documents"
        array files "Embedded File documents"
        object metadata "model, tokens, finish_reason, etc."
        int version "Message version number"
        ObjectId parent_message_id FK "Reference to parent MESSAGES"
        bool is_edited "Edit flag"
        bool is_stopped "Stop generation flag"
        ISODate created_at
    }
    
    CHATBOT_MEMORY {
        ObjectId _id PK
        string user_id FK "Reference to USERS"
        ObjectId conversation_id FK "Reference to CONVERSATIONS (optional)"
        string question "User's question"
        string answer "AI's answer"
        string context "Additional context"
        array images "Embedded Image references"
        int rating "1-5 stars"
        array tags "Array of strings for categorization"
        bool is_public "Share with other users"
        object metadata "model_used, tokens, confidence_score"
        ISODate created_at
    }
    
    UPLOADED_FILES {
        ObjectId _id PK
        string user_id FK "Reference to USERS"
        ObjectId conversation_id FK "Reference to CONVERSATIONS"
        string original_filename "User's filename"
        string stored_filename "Hash-based filename"
        string file_path "Full path in storage"
        string file_type "Extension: pdf, png, py, etc."
        int file_size "Size in bytes"
        string mime_type "MIME type"
        string analysis_result "AI analysis summary"
        object metadata "upload_time_ms, analysis_time_ms, etc."
        ISODate created_at
    }
    
    USER_SETTINGS {
        ObjectId _id PK
        string user_id FK "Reference to USERS (unique)"
        object chatbot_settings "default_model, temperature, etc."
        object ui_settings "theme, font_size, etc."
        object notification_settings "enable_notifications, etc."
        ISODate updated_at
    }
```

---

## 🔑 Embedded Documents Structure

### Messages.images[] (Embedded Array)

```javascript
{
  "images": [
    {
      "url": "/static/Storage/Image_Gen/img_123.png",  // Local path
      "cloud_url": "https://i.postimg.cc/xyz789/img_123.png",  // PostImages CDN
      "delete_url": "https://postimg.cc/delete/abc123",  // Delete link
      "caption": "A beautiful AI-generated sunset",
      "size": 245680,  // Bytes
      "mime_type": "image/png",
      "generated": true,  // AI-generated or uploaded
      "service": "postimages"  // Cloud service used
    }
  ]
}
```

### Messages.files[] (Embedded Array)

```javascript
{
  "files": [
    {
      "name": "report.pdf",
      "path": "/Storage/uploads/upload_20251110_abc123_report.pdf",
      "type": "pdf",
      "size": 2456789,
      "mime_type": "application/pdf",
      "analysis_result": "This PDF contains a financial report..."
    }
  ]
}
```

### Conversations.metadata (Embedded Object)

```javascript
{
  "metadata": {
    "temperature": 0.7,
    "max_tokens": 2048,
    "top_p": 0.95,
    "top_k": 40,
    "custom_settings": {
      "enable_tools": true,
      "enable_memory": true
    }
  }
}
```

---

## 🔗 Relationships (MongoDB Style)

### 1️⃣ One-to-Many (Referenced)

**USERS → CONVERSATIONS** (1:N)
```javascript
// User document
{
  "_id": ObjectId("673e5f8a9b1d2c3f4a5b6c7d"),
  "username": "john_doe",
  "email": "john@example.com"
}

// Conversation documents (many)
{
  "_id": ObjectId("673e5f8a9b1d2c3f4a5b6c7e"),
  "user_id": "john_doe",  // ← Reference
  "model": "gemini-2.0-flash",
  "title": "Python Tutorial"
}
```

**CONVERSATIONS → MESSAGES** (1:N)
```javascript
// Conversation document
{
  "_id": ObjectId("673e5f8a9b1d2c3f4a5b6c7e"),
  "title": "Python Tutorial",
  "total_messages": 10
}

// Message documents (many)
{
  "_id": ObjectId("673e5f8a9b1d2c3f4a5b6c7f"),
  "conversation_id": ObjectId("673e5f8a9b1d2c3f4a5b6c7e"),  // ← Reference
  "role": "user",
  "content": "How to use async in Python?"
}
```

---

### 2️⃣ Self-Referencing (Message Versioning)

**MESSAGES → MESSAGES** (parent-child)
```javascript
// Original message
{
  "_id": ObjectId("673e5f8a9b1d2c3f4a5b6c80"),
  "content": "Original content",
  "version": 1,
  "parent_message_id": null,
  "is_edited": false
}

// Edited version (new document)
{
  "_id": ObjectId("673e5f8a9b1d2c3f4a5b6c81"),
  "content": "Edited content",
  "version": 2,
  "parent_message_id": ObjectId("673e5f8a9b1d2c3f4a5b6c80"),  // ← Reference to original
  "is_edited": true
}
```

**Query to get all versions:**
```javascript
db.messages.find({
  $or: [
    {"_id": ObjectId("673e5f8a9b1d2c3f4a5b6c80")},
    {"parent_message_id": ObjectId("673e5f8a9b1d2c3f4a5b6c80")}
  ]
}).sort({"version": 1})
```

---

### 3️⃣ Many-to-Many (Via Arrays)

**CHATBOT_MEMORY ↔ TAGS** (M:N via array)
```javascript
{
  "_id": ObjectId("673e5f8a9b1d2c3f4a5b6c82"),
  "question": "How to optimize Python code?",
  "answer": "Use profiling tools...",
  "tags": ["python", "performance", "optimization"]  // ← Array of tags
}

// Query: Find all memories with tag "python"
db.chatbot_memory.find({
  "tags": "python"
})

// Query: Find memories with multiple tags
db.chatbot_memory.find({
  "tags": {"$all": ["python", "performance"]}
})
```

---

## 📈 Indexes Strategy

### Primary Indexes (Auto-created)
```javascript
// Every collection has _id index by default
{
  "_id": 1  // Unique, ascending
}
```

### Secondary Indexes (Performance)

#### CONVERSATIONS Collection
```javascript
db.conversations.createIndex({"user_id": 1})  // Find user's conversations
db.conversations.createIndex({"created_at": -1})  // Sort by latest
db.conversations.createIndex({"is_archived": 1})  // Filter archived
db.conversations.createIndex({"user_id": 1, "updated_at": -1})  // Compound
```

#### MESSAGES Collection
```javascript
db.messages.createIndex({"conversation_id": 1})  // Find conversation messages
db.messages.createIndex({"created_at": -1})  // Sort by time
db.messages.createIndex({"role": 1})  // Filter by role
db.messages.createIndex({"parent_message_id": 1})  // Find versions
```

#### CHATBOT_MEMORY Collection
```javascript
db.chatbot_memory.createIndex({"user_id": 1})
db.chatbot_memory.createIndex({"conversation_id": 1})
db.chatbot_memory.createIndex({"tags": 1})  // Array index
db.chatbot_memory.createIndex({"created_at": -1})

// Text search index
db.chatbot_memory.createIndex({
  "question": "text",
  "answer": "text"
})
```

#### UPLOADED_FILES Collection
```javascript
db.uploaded_files.createIndex({"user_id": 1})
db.uploaded_files.createIndex({"conversation_id": 1})
db.uploaded_files.createIndex({"created_at": -1})
db.uploaded_files.createIndex({"file_type": 1})
```

---

## 🔍 Common Query Patterns

### 1. Get Conversation with All Messages (Aggregation)

```javascript
db.conversations.aggregate([
  // Match specific conversation
  {
    $match: {
      _id: ObjectId("673e5f8a9b1d2c3f4a5b6c7e")
    }
  },
  
  // Lookup messages
  {
    $lookup: {
      from: "messages",
      localField: "_id",
      foreignField: "conversation_id",
      as: "messages"
    }
  },
  
  // Sort messages by time
  {
    $project: {
      _id: 1,
      title: 1,
      model: 1,
      total_messages: 1,
      messages: {
        $sortArray: {
          input: "$messages",
          sortBy: {"created_at": 1}
        }
      }
    }
  }
])
```

**Result:**
```javascript
{
  "_id": ObjectId("..."),
  "title": "Python Tutorial",
  "model": "gemini-2.0-flash",
  "total_messages": 10,
  "messages": [
    {"role": "user", "content": "...", "created_at": "..."},
    {"role": "assistant", "content": "...", "created_at": "..."},
    // ... sorted by time
  ]
}
```

---

### 2. Get User's Recent Conversations

```javascript
db.conversations.find({
  "user_id": "john_doe",
  "is_archived": false
})
.sort({"updated_at": -1})
.limit(20)
```

---

### 3. Search Memory by Tags

```javascript
db.chatbot_memory.find({
  "user_id": "john_doe",
  "tags": {"$in": ["python", "async"]}
})
.sort({"created_at": -1})
```

---

### 4. Get Conversation Statistics

```javascript
db.conversations.aggregate([
  {
    $match: {
      "user_id": "john_doe"
    }
  },
  {
    $group: {
      _id: "$model",
      total_conversations: {$sum: 1},
      total_messages: {$sum: "$total_messages"},
      total_tokens: {$sum: "$total_tokens"}
    }
  },
  {
    $sort: {"total_conversations": -1}
  }
])
```

**Result:**
```javascript
[
  {
    "_id": "gemini-2.0-flash",
    "total_conversations": 25,
    "total_messages": 300,
    "total_tokens": 45000
  },
  {
    "_id": "gpt-4o",
    "total_conversations": 10,
    "total_messages": 150,
    "total_tokens": 30000
  }
]
```

---

### 5. Delete Conversation (Cascade)

```javascript
// 1. Delete all messages
db.messages.deleteMany({
  "conversation_id": ObjectId("673e5f8a9b1d2c3f4a5b6c7e")
})

// 2. Delete conversation
db.conversations.deleteOne({
  "_id": ObjectId("673e5f8a9b1d2c3f4a5b6c7e")
})

// Optional: Delete uploaded files
db.uploaded_files.deleteMany({
  "conversation_id": ObjectId("673e5f8a9b1d2c3f4a5b6c7e")
})
```

---

## 📊 Data Growth Estimates

### Assumptions:
- **Active Users:** 100 users
- **Usage:** Daily active for 6 months
- **Activity:** 5 conversations/user/month, 15 messages/conversation

### Calculations:

| Collection | Documents | Size/Doc | Total Size |
|:-----------|:----------|:---------|:-----------|
| **conversations** | 3,000 | 500 bytes | 1.5 MB |
| **messages** | 45,000 | 1 KB | 45 MB |
| **chatbot_memory** | 5,000 | 2 KB | 10 MB |
| **uploaded_files** | 1,000 | 500 bytes | 500 KB |
| **users** | 100 | 500 bytes | 50 KB |
| **user_settings** | 100 | 300 bytes | 30 KB |
| **Total** | 54,200 | - | **57 MB** |

**With Indexes:** +20% = ~70 MB  
**After 1 year:** ~140 MB  
**After 5 years:** ~700 MB

**MongoDB Atlas Free Tier:** 512 MB ✅ Đủ cho 5+ years!

---

## 🔄 Data Lifecycle

### Create Flow
```
User creates conversation
    ↓
Insert to CONVERSATIONS collection
    ↓
User sends message
    ↓
Insert to MESSAGES collection
    ↓
Update CONVERSATIONS.total_messages, total_tokens
```

### Update Flow
```
User edits message
    ↓
Create new MESSAGES document (version++)
    ↓
Set parent_message_id to original
    ↓
Mark is_edited = true
```

### Archive Flow
```
User archives conversation
    ↓
Update CONVERSATIONS.is_archived = true
    ↓
Messages remain (not deleted)
    ↓
Can be restored later
```

### Delete Flow (Cascade)
```
User deletes conversation
    ↓
Delete all MESSAGES (conversation_id match)
    ↓
Delete all UPLOADED_FILES (conversation_id match)
    ↓
Delete CONVERSATION
    ↓
Optional: Keep in CHATBOT_MEMORY if saved
```

---

## 🚀 Performance Optimization

### 1. Index Usage
```javascript
// GOOD: Uses index on user_id + updated_at
db.conversations.find({
  "user_id": "john_doe"
}).sort({"updated_at": -1})

// BAD: Full collection scan
db.conversations.find({
  "title": {"$regex": /python/i}  // ← No index!
})
```

### 2. Projection (Select Fields)
```javascript
// GOOD: Only fetch needed fields
db.conversations.find(
  {"user_id": "john_doe"},
  {"title": 1, "model": 1, "updated_at": 1}  // ← Projection
)

// BAD: Fetch all fields (including large metadata)
db.conversations.find({"user_id": "john_doe"})
```

### 3. Limit Results
```javascript
// GOOD: Limit to 20 results
db.conversations.find({"user_id": "john_doe"}).limit(20)

// BAD: Fetch all conversations
db.conversations.find({"user_id": "john_doe"})
```

### 4. Aggregation Pipeline Optimization
```javascript
// GOOD: Filter first, then lookup
db.conversations.aggregate([
  {$match: {"user_id": "john_doe"}},  // ← Filter first
  {$lookup: {from: "messages", ...}},
  {$limit: 10}
])

// BAD: Lookup all, then filter
db.conversations.aggregate([
  {$lookup: {from: "messages", ...}},  // ← Expensive!
  {$match: {"user_id": "john_doe"}}
])
```

---

## 📝 Schema Validation (Optional)

MongoDB supports schema validation for data integrity:

```javascript
db.createCollection("conversations", {
  validator: {
    $jsonSchema: {
      bsonType: "object",
      required: ["user_id", "model", "created_at"],
      properties: {
        user_id: {
          bsonType: "string",
          description: "must be a string and is required"
        },
        model: {
          bsonType: "string",
          description: "must be a string and is required"
        },
        total_messages: {
          bsonType: "int",
          minimum: 0,
          description: "must be an integer >= 0"
        },
        is_archived: {
          bsonType: "bool",
          description: "must be a boolean"
        }
      }
    }
  }
})
```

**File reference:** `ChatBot/config/mongodb_schema.py` → `create_validation_rules()`

---

## 🔐 Security Considerations

### 1. Connection String
```python
# ❌ BAD: Hardcoded credentials
MONGODB_URI = "mongodb+srv://user:password@cluster.mongodb.net/"

# ✅ GOOD: Use environment variables
MONGODB_URI = os.getenv('MONGODB_URI')
```

### 2. Input Validation
```python
# ✅ Validate ObjectId before query
from bson import ObjectId
from bson.errors import InvalidId

try:
    conversation_id = ObjectId(user_input)
except InvalidId:
    return {"error": "Invalid conversation ID"}
```

### 3. User Isolation
```python
# ✅ Always filter by user_id
db.conversations.find({
    "_id": ObjectId(conversation_id),
    "user_id": current_user_id  # ← Prevent unauthorized access
})
```

---

<div align="center">

**Database:** MongoDB Atlas (chatbot_db)  
**Collections:** 6  
**Indexes:** 15+  
**Total Size:** ~70 MB (1 year, 100 users)

[⬅️ Back: Class Diagram](04_class_diagram.md) | [➡️ Next: Data Structure](06_mongodb_data_structure.md)

</div>
