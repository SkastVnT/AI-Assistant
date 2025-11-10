# 📊 MONGODB SCHEMA - PRODUCTION STATE

> **Current MongoDB Atlas implementation for AI-Assistant ChatBot**  
> **Date:** November 10, 2025  
> **Version:** 2.1 (Post ImgBB Integration)  
> **Type:** Technical Documentation  
> **Status:** Production Ready

---

## 📋 EXECUTIVE SUMMARY

MongoDB Atlas được sử dụng làm persistent storage cho ChatBot Service với 6 collections và 26 indexes được tối ưu hóa. Hệ thống đã tích hợp ImgBB cloud storage cho image management.

### Key Points
- ✅ **Production Database:** MongoDB Atlas M0 (Free Tier - 512MB)
- ✅ **6 Collections:** conversations, messages, chatbot_memory, uploaded_files, users, user_settings
- ✅ **26 Indexes:** Optimized for query performance
- ✅ **ImgBB Integration:** Cloud storage cho generated images
- ✅ **Auto-save:** Images tự động lưu vào MongoDB after generation

### Database Info
```yaml
Service: MongoDB Atlas (Cloud)
Cluster: ai-assistant.aspuqwb.mongodb.net
Database: chatbot_db
Driver: pymongo >= 4.6.0
Connection: mongodb+srv:// (SRV DNS seedlist)
API Version: Server API v1
Tier: M0 Free (512MB storage)
Location: Module mongodb_config.py
```

---

## 🗄️ COLLECTION SCHEMAS (PRODUCTION)

### 1. conversations Collection

**Purpose:** Store chat sessions/conversations

**Schema:**
```javascript
{
  _id: ObjectId,                // Primary key
  user_id: String,              // Session ID or user ID
  model: String,                // 'gemini-2.0-flash', 'gpt-4', 'deepseek', etc.
  title: String,                // Auto-generated from first message
  system_prompt: String,        // Custom system prompt (default: "You are a helpful AI assistant.")
  total_messages: Number,       // Message count
  total_tokens: Number,         // Total tokens used
  is_archived: Boolean,         // Archive status (default: false)
  metadata: {
    temperature: Number,        // Model temperature
    max_tokens: Number,         // Max tokens per response
    top_p: Number,              // Nucleus sampling
    custom_settings: Object     // Additional settings
  },
  created_at: ISODate,         // Creation timestamp
  updated_at: ISODate          // Last update timestamp
}
```

**Indexes (7 total):**
```javascript
1. _id_ (default primary key)
2. user_id_1
3. created_at_-1
4. is_archived_1
5. user_created_idx: {user_id: 1, created_at: -1}
6. user_archived_idx: {user_id: 1, is_archived: 1}
7. updated_idx: {updated_at: -1}
```

**Example Document:**
```javascript
{
  _id: ObjectId("673e5f8a9b1d2c3f4a5b6c7d"),
  user_id: "anonymous_session_abc123xyz",
  model: "gemini-2.0-flash-thinking-exp",
  title: "Python Code Review Discussion",
  system_prompt: "You are a helpful AI assistant specialized in code review.",
  total_messages: 15,
  total_tokens: 8500,
  is_archived: false,
  metadata: {
    temperature: 0.7,
    max_tokens: 2048,
    top_p: 0.95,
    custom_settings: {}
  },
  created_at: ISODate("2025-11-09T10:30:00.000Z"),
  updated_at: ISODate("2025-11-10T14:20:15.000Z")
}
```

**Query Examples:**
```javascript
// Get user's recent conversations
db.conversations.find({
  user_id: "user_123",
  is_archived: false
}).sort({created_at: -1}).limit(20)

// Get conversation by ID
db.conversations.findOne({_id: ObjectId("673e5f8a...")})

// Archive conversation
db.conversations.updateOne(
  {_id: ObjectId("...")},
  {$set: {is_archived: true, updated_at: new Date()}}
)
```

---

### 2. messages Collection ⭐ (UPDATED with ImgBB Cloud Storage)

**Purpose:** Store individual messages within conversations

**Schema:**
```javascript
{
  _id: ObjectId,                // Primary key
  conversation_id: ObjectId,    // Reference to conversations._id
  role: String,                 // 'user', 'assistant', 'system'
  content: String,              // Message text content
  
  // ⭐ IMAGES ARRAY - Updated with Cloud Storage Support
  images: [
    {
      url: String,              // Local path: "/static/Storage/Image_Gen/generated_xxx.png"
      cloud_url: String,        // ⭐ NEW: ImgBB URL: "https://i.ibb.co/xyz789/image.png"
      delete_url: String,       // ⭐ NEW: ImgBB delete URL for cleanup
      caption: String,          // Image description
      size: Number,             // File size in bytes
      mime_type: String,        // "image/png", "image/jpeg", etc.
      generated: Boolean,       // true if AI-generated, false if user-uploaded
      service: String           // ⭐ NEW: "imgbb" or "local"
    }
  ],
  
  // FILES ARRAY
  files: [
    {
      name: String,             // Original filename
      path: String,             // Storage path
      type: String,             // File extension
      size: Number,             // File size in bytes
      mime_type: String,        // MIME type
      analysis_result: String   // AI analysis of file content
    }
  ],
  
  // METADATA
  metadata: {
    model: String,              // Model used for generation
    tokens: Number,             // Tokens used
    temperature: Number,        // Temperature setting
    finish_reason: String,      // 'stop', 'length', 'interrupted'
    generation_time_ms: Number, // Generation time in milliseconds
    
    // ⭐ Image Generation Metadata
    prompt: String,             // Positive prompt (for image gen)
    negative_prompt: String,    // Negative prompt (for image gen)
    cloud_service: String,      // ⭐ NEW: 'imgbb' or 'local'
    num_images: Number          // Number of images generated
  },
  
  version: Number,              // Message version (for edit history, default: 1)
  parent_message_id: ObjectId,  // For message versioning
  is_edited: Boolean,           // Edit status
  is_stopped: Boolean,          // True if generation stopped by user
  created_at: ISODate          // Creation timestamp
}
```

**Indexes (5 total):**
```javascript
1. _id_ (default primary key)
2. conversation_id_1
3. created_at_-1
4. role_1
5. conv_created_idx: {conversation_id: 1, created_at: -1}
```

**Example Document (Text2Img with ImgBB):**
```javascript
{
  _id: ObjectId("690fb03ec34891b651f72772"),
  conversation_id: ObjectId("690f9bcaa0c9f1cdd8168204"),
  role: "assistant",
  content: "✅ Generated image with prompt: masterpiece, best quality, beautiful anime girl",
  
  images: [
    {
      url: "/static/Storage/Image_Gen/generated_20251110_143052_0.png",
      cloud_url: "https://i.ibb.co/xyzAbc123/generated_20251110_143052_0.png",
      delete_url: "https://ibb.co/delete/abc123def456ghi789",
      caption: "Generated: beautiful anime girl",
      size: 945680,
      mime_type: "image/png",
      generated: true,
      service: "imgbb"
    }
  ],
  
  files: [],
  
  metadata: {
    model: "stable-diffusion",
    prompt: "masterpiece, best quality, beautiful anime girl, detailed face",
    negative_prompt: "bad quality, blurry, distorted, ugly, worst quality",
    cloud_service: "imgbb",
    num_images: 1,
    generation_time_ms: 3245
  },
  
  version: 1,
  parent_message_id: null,
  is_edited: false,
  is_stopped: false,
  created_at: ISODate("2025-11-10T14:30:52.123Z")
}
```

**Example Document (Img2Img with ImgBB):**
```javascript
{
  _id: ObjectId("690fc12abc34567def890123"),
  conversation_id: ObjectId("690f9bcaa0c9f1cdd8168204"),
  role: "assistant",
  content: "✅ Generated Img2Img with prompt: add flowers background",
  
  images: [
    {
      url: "/static/Storage/Image_Gen/img2img_20251110_152030_0.png",
      cloud_url: "https://i.ibb.co/defGhi456/img2img_20251110_152030_0.png",
      delete_url: "https://ibb.co/delete/xyz987uvw654stu321",
      caption: "Img2Img: add flowers background",
      size: 1024560,
      mime_type: "image/png",
      generated: true,
      service: "imgbb"
    }
  ],
  
  files: [],
  
  metadata: {
    model: "stable-diffusion-img2img",
    prompt: "add beautiful flowers background, vibrant colors",
    negative_prompt: "blurry, low quality",
    denoising_strength: 0.8,
    cloud_service: "imgbb",
    num_images: 1,
    generation_time_ms: 4120
  },
  
  version: 1,
  parent_message_id: null,
  is_edited: false,
  is_stopped: false,
  created_at: ISODate("2025-11-10T15:20:30.456Z")
}
```

**Query Examples:**
```javascript
// Get conversation messages with images
db.messages.find({
  conversation_id: ObjectId("690f9bcaa0c9f1cdd8168204"),
  "images.0": {$exists: true}
}).sort({created_at: 1})

// Find messages with cloud URLs
db.messages.find({
  "images.cloud_url": {$exists: true}
})

// Get recent generated images
db.messages.find({
  "images.generated": true,
  "images.service": "imgbb"
}).sort({created_at: -1}).limit(10)

// Get messages from specific model
db.messages.find({
  "metadata.model": "stable-diffusion"
})
```

---

### 3. chatbot_memory Collection

**Purpose:** AI learning and memory storage

**Schema:**
```javascript
{
  _id: ObjectId,
  user_id: String,
  conversation_id: ObjectId,
  memory_type: String,          // 'fact', 'preference', 'context'
  content: String,              // Memory content
  importance: Number,           // 1-10 scale
  tags: [String],               // Array of tags for categorization
  context: String,              // Additional context
  metadata: Object,
  created_at: ISODate,
  updated_at: ISODate,
  expires_at: ISODate           // Optional TTL
}
```

**Indexes (4 total):**
```javascript
1. _id_ (default)
2. user_id_1
3. conversation_id_1
4. tags_1
```

---

### 4. uploaded_files Collection

**Purpose:** File upload metadata and analysis

**Schema:**
```javascript
{
  _id: ObjectId,
  user_id: String,
  conversation_id: ObjectId,
  file_name: String,
  file_path: String,
  file_type: String,
  file_size: Number,
  mime_type: String,
  analysis_result: String,      // AI analysis of file
  metadata: Object,
  created_at: ISODate
}
```

**Indexes (4 total):**
```javascript
1. _id_ (default)
2. user_id_1
3. conversation_id_1
4. created_at_-1
```

---

### 5. users Collection

**Purpose:** User information (future multi-user system)

**Schema:**
```javascript
{
  _id: ObjectId,
  username: String,             // Unique
  email: String,                // Unique
  password_hash: String,
  profile: {
    display_name: String,
    avatar_url: String,
    bio: String
  },
  metadata: Object,
  is_active: Boolean,
  created_at: ISODate,
  last_login_at: ISODate
}
```

**Indexes (4 total):**
```javascript
1. _id_ (default)
2. username_idx: {username: 1} [UNIQUE]
3. email_idx: {email: 1} [UNIQUE]
4. active_idx: {is_active: 1}
```

---

### 6. user_settings Collection

**Purpose:** User preferences and settings

**Schema:**
```javascript
{
  _id: ObjectId,
  user_id: String,              // Reference to users._id (UNIQUE)
  settings: {
    default_model: String,
    temperature: Number,
    max_tokens: Number,
    theme: String,
    language: String,
    custom: Object
  },
  created_at: ISODate,
  updated_at: ISODate
}
```

**Indexes (2 total):**
```javascript
1. _id_ (default)
2. user_id_idx: {user_id: 1} [UNIQUE]
```

---

## 🎨 IMAGE STORAGE ARCHITECTURE

### Hybrid Storage Strategy (Production)

```
┌──────────────────────────────────────────────────────────────┐
│               IMAGE GENERATION & STORAGE FLOW                │
└──────────────────────────────────────────────────────────────┘

   User Request (Text2Img / Img2Img)
            │
            ▼
   ┌────────────────────┐
   │ Frontend API Call  │
   │ - prompt           │
   │ - negative_prompt  │
   │ - save_to_storage  │ ← ⭐ Always true (auto-enabled)
   └────────────────────┘
            │
            ▼
   ┌──────────────────────────────────┐
   │  Backend Endpoint                │
   │  /api/generate-image (Text2Img)  │
   │  /api/img2img (Img2Img)          │
   └──────────────────────────────────┘
            │
            ▼
   ┌─────────────────────────┐
   │ Stable Diffusion API    │
   │ Generate Image (Base64) │
   └─────────────────────────┘
            │
            ▼
   ┌─────────────────────────────────┐
   │ Save Local Storage              │
   │ Location: Storage/Image_Gen/    │
   │ - generated_YYYYMMDD_HHMMSS.png │
   │ - img2img_YYYYMMDD_HHMMSS.png   │
   └─────────────────────────────────┘
            │
            ▼
   ┌───────────────────────────────────┐
   │ Upload to ImgBB Cloud ☁️          │
   │ - API Key: 77d36ef945...          │
   │ - Max size: 32MB                  │
   │ - Free tier: Unlimited uploads    │
   └───────────────────────────────────┘
            │
            ▼
   ┌───────────────────────────────────┐
   │ ImgBB Response                    │
   │ - url: https://i.ibb.co/xxx       │
   │ - delete_url: https://ibb.co/...  │
   │ - thumb: https://i.ibb.co/xxx/t   │
   │ - medium: https://i.ibb.co/xxx/m  │
   └───────────────────────────────────┘
            │
            ▼
   ┌───────────────────────────────────┐
   │ Save Metadata JSON                │
   │ Location: Storage/Image_Gen/      │
   │ - generated_xxx.json              │
   │ - Contains: cloud_url, delete_url │
   └───────────────────────────────────┘
            │
            ▼
   ┌────────────────────────────────────┐
   │ Auto-Save to MongoDB 💾            │
   │ Collection: messages               │
   │ images: [{                         │
   │   url: "/static/...",              │
   │   cloud_url: "https://i.ibb.co..", │
   │   delete_url: "https://ibb.co/..", │
   │   service: "imgbb",                │
   │   generated: true                  │
   │ }]                                 │
   └────────────────────────────────────┘
            │
            ▼
   ┌───────────────────────────┐
   │ Return to Frontend        │
   │ - Base64 image (preview)  │
   │ - Cloud URL               │
   │ - Filenames               │
   │ - saved_to_db: true       │
   └───────────────────────────┘
```

### Storage Locations

| Storage | Location | Purpose | Retention | Status |
|---------|----------|---------|-----------|--------|
| **Local** | `ChatBot/Storage/Image_Gen/` | Backup, fast access | Manual cleanup | ✅ Active |
| **Cloud** | ImgBB (i.ibb.co) | Permanent, shareable URLs | Unlimited (free tier) | ✅ Active |
| **Database** | MongoDB messages.images[] | Metadata, references | Permanent | ✅ Active |
| **Metadata** | JSON files (*.json) | Parameters, URLs, settings | Manual cleanup | ✅ Active |

### Benefits of Hybrid Storage

**✅ Local Storage Benefits:**
- ⚡ Fast access for recent images
- 🔒 No internet required for viewing
- 🎨 Full quality preservation
- 📦 Backup if cloud service down

**✅ Cloud Storage (ImgBB) Benefits:**
- 🌐 Permanent shareable URLs (no expiration)
- 📤 External access without VPN/port forwarding
- 💾 Reduces local disk usage long-term
- 🆓 Free tier: 32MB per image, unlimited uploads
- 🗑️ Delete URLs for cleanup

**✅ MongoDB Storage Benefits:**
- 🔍 Query images by prompt, user, date
- 💬 Conversation context preserved
- 📊 Analytics & usage tracking
- 🔗 Cross-reference with messages
- 🗄️ Structured metadata storage

---

## 📊 DATABASE STATISTICS

### Current Usage (as of Nov 10, 2025)

| Collection | Documents | Avg Size | Total Size | Indexes |
|-----------|-----------|----------|------------|---------|
| conversations | ~50 | 500 bytes | ~25 KB | 7 |
| messages | ~30 | 1-2 KB | ~50 KB | 5 |
| chatbot_memory | 0 | - | 0 | 4 |
| uploaded_files | 0 | - | 0 | 4 |
| users | 0 | - | 0 | 4 |
| user_settings | 0 | - | 0 | 2 |
| **TOTAL** | **~80** | - | **~75 KB** | **26** |

### Projected Usage (1K users, 1 year)

| Collection | Est. Docs | Est. Size per Doc | Total Size |
|-----------|-----------|-------------------|------------|
| conversations | 10,000 | 500 bytes | ~5 MB |
| messages | 500,000 | 1 KB | ~500 MB |
| chatbot_memory | 100,000 | 300 bytes | ~30 MB |
| uploaded_files | 50,000 | 200 bytes | ~10 MB |
| users | 1,000 | 500 bytes | ~500 KB |
| user_settings | 1,000 | 300 bytes | ~300 KB |
| **TOTAL** | **661,000** | - | **~545 MB** |

**Note:** M0 Free Tier limit is 512MB. Upgrade to M2 ($9/month, 2GB) recommended when approaching 400MB.

---

## 🔧 IMPLEMENTATION DETAILS

### Connection Configuration

**File:** `ChatBot/config/mongodb_config.py`

```python
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB Atlas URI
MONGODB_URI = os.getenv('MONGODB_URI')
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
                self._client.admin.command('ping')
                self._db = self._client[DATABASE_NAME]
                print(f"✅ Successfully connected to MongoDB Atlas - Database: {DATABASE_NAME}")
                self._create_indexes()
                return True
            except Exception as e:
                print(f"❌ MongoDB connection failed: {e}")
                return False
        return True
```

### Image Generation with Auto-Save

**File:** `ChatBot/app.py` (Lines 1210-1400)

```python
@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    """Generate image with auto-save to MongoDB"""
    
    # ... Generate image via SD API ...
    
    # Save to local storage
    if save_to_storage:
        for idx, image_base64 in enumerate(base64_images):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"generated_{timestamp}_{idx}.png"
            filepath = IMAGE_STORAGE_DIR / filename
            
            # Save local
            image_data = base64.b64decode(image_base64)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            # Upload to ImgBB
            if CLOUD_UPLOAD_ENABLED:
                uploader = ImgBBUploader()
                upload_result = uploader.upload_image(
                    str(filepath),
                    title=f"AI Generated: {prompt[:50]}"
                )
                
                if upload_result:
                    cloud_url = upload_result['url']
                    delete_url = upload_result.get('delete_url', '')
                    cloud_urls.append(cloud_url)
    
    # Auto-save to MongoDB
    if MONGODB_ENABLED and save_to_storage and saved_filenames:
        # Get or create conversation
        if not conversation_id:
            conversation = ConversationDB.create_conversation(
                user_id=user_id,
                model='stable-diffusion',
                title=f"Text2Image: {prompt[:30]}..."
            )
            conversation_id = str(conversation['_id'])
        
        # Prepare images array
        images_data = []
        for idx, filename in enumerate(saved_filenames):
            cloud_url = cloud_urls[idx] if idx < len(cloud_urls) else None
            
            images_data.append({
                'url': f"/static/Storage/Image_Gen/{filename}",
                'cloud_url': cloud_url,
                'delete_url': delete_url if cloud_url else None,
                'caption': f"Generated: {prompt[:50]}",
                'generated': True,
                'service': 'imgbb' if cloud_url else 'local',
                'mime_type': 'image/png'
            })
        
        # Save message with images
        save_message_to_db(
            conversation_id=conversation_id,
            role='assistant',
            content=f"✅ Generated image with prompt: {prompt}",
            images=images_data,
            metadata={
                'model': 'stable-diffusion',
                'prompt': prompt,
                'negative_prompt': params['negative_prompt'],
                'cloud_service': 'imgbb' if cloud_urls else 'local',
                'num_images': len(saved_filenames)
            }
        )
        
        logger.info(f"💾 Saved image message to MongoDB with {len(cloud_urls)} cloud URLs")
```

### Frontend Integration

**File:** `ChatBot/static/js/modules/api-service.js`

```javascript
async generateImage(params) {
    // Always enable save_to_storage for MongoDB persistence
    const enhancedParams = {
        ...params,
        save_to_storage: true  // ⭐ Auto-enabled
    };
    
    const response = await fetch('/api/generate-image', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(enhancedParams)
    });

    return await response.json();
}
```

---

## 🔍 QUERY EXAMPLES

### Get Recent Images with Cloud URLs

```javascript
db.messages.aggregate([
  // Match messages with images
  { $match: { 
      "images.0": { $exists: true },
      "images.service": "imgbb"
  }},
  
  // Unwind images array
  { $unwind: "$images" },
  
  // Filter ImgBB images
  { $match: { "images.service": "imgbb" }},
  
  // Project fields
  { $project: {
      conversation_id: 1,
      created_at: 1,
      prompt: "$metadata.prompt",
      cloud_url: "$images.cloud_url",
      local_url: "$images.url",
      caption: "$images.caption"
  }},
  
  // Sort by recent
  { $sort: { created_at: -1 }},
  
  // Limit
  { $limit: 10 }
])
```

### Get Conversation with All Messages and Images

```javascript
db.conversations.aggregate([
  // Match conversation
  { $match: { _id: ObjectId("690f9bcaa0c9f1cdd8168204") }},
  
  // Lookup messages
  { $lookup: {
      from: "messages",
      localField: "_id",
      foreignField: "conversation_id",
      as: "messages"
  }},
  
  // Sort messages
  { $addFields: {
      messages: {
          $sortArray: {
              input: "$messages",
              sortBy: { created_at: 1 }
          }
      }
  }},
  
  // Count images
  { $addFields: {
      total_images: {
          $sum: {
              $map: {
                  input: "$messages",
                  as: "msg",
                  in: { $size: { $ifNull: ["$$msg.images", []] }}
              }
          }
      }
  }}
])
```

### Find Images by Prompt Keywords

```javascript
db.messages.find({
  "metadata.prompt": { $regex: "anime girl", $options: "i" },
  "images.0": { $exists: true }
}).sort({ created_at: -1 })
```

---

## 📚 RELATED DOCUMENTATION

### Internal Docs
- [MongoDB Connector Documentation](../MONGODB_CONNECTOR_0911.md) - Complete connector analysis
- [MongoDB Schema](../../../ChatBot/config/mongodb_schema.py) - Python schema definitions
- [MongoDB Helpers](../../../ChatBot/config/mongodb_helpers.py) - CRUD operations
- [ImgBB Setup Guide](../../POSTIMAGES_SETUP.md) - Cloud storage setup

### External Resources
- [MongoDB Atlas Documentation](https://www.mongodb.com/docs/atlas/)
- [PyMongo Tutorial](https://pymongo.readthedocs.io/en/stable/tutorial.html)
- [ImgBB API Documentation](https://api.imgbb.com/)

---

## 🚧 FUTURE IMPROVEMENTS

### Phase 1: Performance (Weeks 1-2)
- [ ] Add Redis caching for frequent queries
- [ ] Implement connection pooling optimization
- [ ] Add query result caching with TTL
- [ ] Monitor slow queries and add indexes

### Phase 2: Features (Weeks 3-4)
- [ ] Implement image deduplication (hash-based)
- [ ] Add image tagging system
- [ ] Implement image search by visual similarity
- [ ] Add batch image operations

### Phase 3: Storage Optimization (Weeks 5-6)
- [ ] Implement automatic local cleanup (keep last 30 days)
- [ ] Add cloud storage sync verification
- [ ] Implement image compression for thumbnails
- [ ] Add storage analytics dashboard

### Phase 4: Security (Weeks 7-8)
- [ ] Rotate MongoDB credentials
- [ ] Implement IP whitelist
- [ ] Add Azure Key Vault for secrets
- [ ] Implement audit logging

---

<div align="center">

## 📊 DOCUMENT INFO

| Property | Value |
|----------|-------|
| **Document Type** | Technical Documentation |
| **Version** | 2.1 |
| **Author** | SkastVnT |
| **Created** | November 10, 2025 |
| **Last Updated** | November 10, 2025 |
| **Status** | Production Ready |
| **Location** | docs/archives/2025-11-10/ |
| **Related Docs** | [MongoDB Connector](../2025-11-09/MONGODB_CONNECTOR_0911.md), [Database Design](../../../diagram/04_database_design.md) |
| **Tags** | #mongodb #schema #imgbb #cloud-storage #production |

---

**📅 Next Review Date:** December 10, 2025  
**👥 Reviewers:** Backend Team  
**🔗 Related Issues:** #mongodb-schema, #image-storage, #imgbb-integration

---

**🎉 MONGODB SCHEMA DOCUMENTATION COMPLETE**

Updated với ImgBB cloud storage integration và auto-save functionality

[📖 View Main Docs](../../README.md) | [📂 View Archives](../) | [🔧 MongoDB Config](../../../ChatBot/config/mongodb_config.py)

</div>
