# 5️⃣ ENTITY RELATIONSHIP (ER) DIAGRAM

> **Biểu đồ thực thể - liên kết hệ thống AI-Assistant**  
> Mô tả quan hệ giữa các bảng trong database

---

## 📋 Mô tả

ER Diagram thể hiện:
- **Entities (Bảng):** 18 bảng chính
- **Relationships:** One-to-Many, Many-to-Many
- **Cardinality:** 1:1, 1:N, M:N
- **Attributes:** Primary Keys, Foreign Keys, Important fields

---

## 🎯 Biểu đồ tổng quan

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : has
    USERS ||--o{ DATABASE_CONNECTIONS : creates
    USERS ||--o{ TRANSCRIPTIONS : creates
    USERS ||--o{ IMAGE_GENERATIONS : generates
    USERS ||--o{ USER_API_KEYS : owns
    USERS ||--o{ CHATBOT_MEMORY : stores
    USERS ||--o{ QUERY_HISTORY : executes
    USERS ||--o{ SQL_KNOWLEDGE_BASE : contributes
    
    CONVERSATIONS ||--|{ MESSAGES : contains
    CONVERSATIONS ||--o{ CHATBOT_MEMORY : stores
    CONVERSATIONS ||--o{ UPLOADED_FILES : includes
    CONVERSATIONS ||--o{ IMAGE_GENERATIONS : links
    
    DATABASE_CONNECTIONS ||--o{ QUERY_HISTORY : executes
    DATABASE_CONNECTIONS ||--o{ DATABASE_SCHEMAS : has
    
    SQL_KNOWLEDGE_BASE }o--|| QUERY_HISTORY : matches
    
    TRANSCRIPTIONS ||--o{ SPEAKERS : has
    
    LORA_MODELS }o--o{ IMAGE_GENERATIONS : uses
    
    USERS {
        int id PK
        string username UK
        string email UK
        string password_hash
        string full_name
        string avatar_url
        string role
        boolean is_active
        int api_quota_daily
        timestamp created_at
        timestamp last_login
        string last_ip
    }
    
    USER_API_KEYS {
        int id PK
        int user_id FK
        string key_name
        string key_hash UK
        boolean is_active
        timestamp last_used
        timestamp expires_at
        timestamp created_at
    }
    
    CONVERSATIONS {
        uuid id PK
        int user_id FK
        string model
        string title
        text system_prompt
        int total_messages
        int total_tokens
        boolean is_archived
        timestamp created_at
        timestamp updated_at
    }
    
    MESSAGES {
        int id PK
        uuid conversation_id FK
        string role
        text content
        jsonb images
        jsonb files
        jsonb metadata
        int version
        int parent_message_id FK
        boolean is_edited
        timestamp created_at
    }
    
    CHATBOT_MEMORY {
        int id PK
        int user_id FK
        uuid conversation_id FK
        text question
        text answer
        text context
        int rating
        text_array tags
        boolean is_public
        timestamp created_at
    }
    
    UPLOADED_FILES {
        int id PK
        int user_id FK
        uuid conversation_id FK
        string original_filename
        string stored_filename
        text file_path
        string file_type
        bigint file_size
        string mime_type
        text analysis_result
        timestamp created_at
    }
    
    SQL_KNOWLEDGE_BASE {
        int id PK
        text question
        text sql_query
        string database_type
        string schema_name
        string schema_hash
        boolean is_correct
        int usage_count
        int avg_execution_time_ms
        decimal success_rate
        text_array tags
        int created_by FK
        timestamp created_at
        timestamp updated_at
        timestamp last_used
    }
    
    DATABASE_CONNECTIONS {
        int id PK
        int user_id FK
        string name
        string type
        string host
        int port
        string database_name
        string username
        text password_encrypted
        boolean ssl_enabled
        jsonb connection_params
        boolean is_active
        timestamp last_tested
        text last_test_result
        timestamp created_at
    }
    
    QUERY_HISTORY {
        int id PK
        int user_id FK
        int connection_id FK
        text question
        text sql_query
        int execution_time_ms
        int rows_returned
        string status
        text error_message
        jsonb result_preview
        int kb_match_id FK
        string feedback
        timestamp created_at
    }
    
    DATABASE_SCHEMAS {
        int id PK
        int connection_id FK
        jsonb schema_json
        string schema_hash UK
        int table_count
        int total_columns
        timestamp last_updated
        timestamp created_at
    }
    
    TRANSCRIPTIONS {
        int id PK
        int user_id FK
        string original_filename
        string stored_filename
        text file_path
        bigint file_size
        int duration_seconds
        string audio_format
        int sample_rate
        string language
        int num_speakers
        text transcript_raw
        text transcript_enhanced
        jsonb speaker_timeline
        jsonb models_used
        int processing_time_ms
        decimal accuracy_score
        timestamp created_at
    }
    
    SPEAKERS {
        int id PK
        int transcription_id FK
        string speaker_id
        string speaker_label
        int total_duration_seconds
        int word_count
        decimal avg_confidence
        timestamp created_at
    }
    
    IMAGE_GENERATIONS {
        int id PK
        int user_id FK
        uuid conversation_id FK
        text prompt
        text negative_prompt
        string model
        jsonb lora_models
        string vae_model
        string sampler
        int steps
        decimal cfg_scale
        bigint seed
        int width
        int height
        text image_url
        string image_hash
        int generation_time_ms
        timestamp created_at
    }
    
    LORA_MODELS {
        int id PK
        string model_name UK
        string display_name
        text description
        string category
        text file_path
        bigint file_size
        text_array trigger_words
        int usage_count
        decimal rating
        boolean is_active
        timestamp created_at
    }
    
    SYSTEM_LOGS {
        int id PK
        string service
        string level
        text message
        jsonb metadata
        string source
        timestamp created_at
    }
    
    API_USAGE {
        int id PK
        string service
        string endpoint
        int user_id FK
        string method
        int status_code
        int response_time_ms
        int request_size_bytes
        int response_size_bytes
        string ip_address
        text user_agent
        text error_message
        timestamp created_at
    }
    
    SYSTEM_METRICS {
        int id PK
        string service
        string metric_name
        decimal metric_value
        string unit
        timestamp timestamp
    }
```

---

## 📊 Chi tiết quan hệ

### 1. User-Centric Relationships (1:N)

| Parent Table | Child Table | Relationship | Description |
|:------------|:------------|:------------|:------------|
| **USERS** | CONVERSATIONS | 1:N | User có nhiều conversations |
| **USERS** | DATABASE_CONNECTIONS | 1:N | User lưu nhiều DB connections |
| **USERS** | TRANSCRIPTIONS | 1:N | User tạo nhiều transcriptions |
| **USERS** | IMAGE_GENERATIONS | 1:N | User generate nhiều images |
| **USERS** | USER_API_KEYS | 1:N | User có nhiều API keys |
| **USERS** | CHATBOT_MEMORY | 1:N | User có nhiều memories |
| **USERS** | QUERY_HISTORY | 1:N | User execute nhiều queries |

**Total:** 1 User → N Records (across 7 tables)

---

### 2. Conversation-Centric Relationships (1:N)

| Parent Table | Child Table | Relationship | Description |
|:------------|:------------|:------------|:------------|
| **CONVERSATIONS** | MESSAGES | 1:N | Conversation chứa nhiều messages |
| **CONVERSATIONS** | CHATBOT_MEMORY | 1:N (optional) | Conversation có thể saved to memory |
| **CONVERSATIONS** | UPLOADED_FILES | 1:N (optional) | Conversation có thể chứa files |
| **CONVERSATIONS** | IMAGE_GENERATIONS | 1:N (optional) | Images generated trong conversation |

**Total:** 1 Conversation → N Messages (required) + N Files/Images (optional)

---

### 3. Database Connection Relationships (1:N)

| Parent Table | Child Table | Relationship | Description |
|:------------|:------------|:------------|:------------|
| **DATABASE_CONNECTIONS** | QUERY_HISTORY | 1:N | Connection execute nhiều queries |
| **DATABASE_CONNECTIONS** | DATABASE_SCHEMAS | 1:1 or 1:N | Connection có schema (cached) |

**Total:** 1 Connection → N Queries + 1-N Schemas

---

### 4. Speech2Text Relationships (1:N)

| Parent Table | Child Table | Relationship | Description |
|:------------|:------------|:------------|:------------|
| **TRANSCRIPTIONS** | SPEAKERS | 1:N | Transcription có nhiều speakers |

**Total:** 1 Transcription → N Speakers (typically 1-5)

---

### 5. Knowledge Base Relationships (N:1)

| Child Table | Parent Table | Relationship | Description |
|:-----------|:------------|:------------|:------------|
| **QUERY_HISTORY** | SQL_KNOWLEDGE_BASE | N:1 (optional) | Query có thể match với KB entry |

**Total:** N Queries → 1 KB Entry (reuse)

---

### 6. LoRA Usage (M:N - through JSONB)

| Table A | Table B | Relationship | Description |
|:--------|:--------|:------------|:------------|
| **IMAGE_GENERATIONS** | LORA_MODELS | M:N | Image có thể dùng nhiều LoRAs |

**Implementation:** JSONB array trong `IMAGE_GENERATIONS.lora_models`

```json
{
  "lora_models": [
    {"name": "anime_style_v1", "weight": 0.8},
    {"name": "detailed_face", "weight": 0.6}
  ]
}
```

---

## 🔑 Key Constraints

### Primary Keys (PK):
- **SERIAL:** Auto-increment integer (most tables)
- **UUID:** Globally unique (CONVERSATIONS)
- **Composite:** None (using surrogate keys for simplicity)

### Foreign Keys (FK):
- **ON DELETE CASCADE:** Child records deleted when parent deleted
  - Examples: `MESSAGES`, `DOCUMENT_ANALYSIS`, `SPEAKERS`
- **ON DELETE SET NULL:** Keep child, but clear FK
  - Examples: `CONVERSATIONS.user_id`, `QUERY_HISTORY.connection_id`

### Unique Constraints (UK):
- `USERS.username`
- `USERS.email`
- `USER_API_KEYS.key_hash`
- `SQL_KNOWLEDGE_BASE.(question, database_type)` - Composite
- `DATABASE_SCHEMAS.schema_hash`
- `LORA_MODELS.model_name`

---

## 📈 Cardinality Summary

| Relationship Type | Count | Examples |
|:-----------------|:------|:---------|
| **1:N (Mandatory)** | 10 | User→Conversations, Conversation→Messages |
| **1:N (Optional)** | 7 | Conversation→Files, Query→KB_Match |
| **1:1** | 1 | Connection→Schema (cached) |
| **M:N** | 1 | Image_Gen↔LoRA_Models (via JSONB) |
| **Self-referencing** | 1 | MESSAGES.parent_message_id |

**Total Relationships:** 20

---

## 🔄 Common Query Patterns

### 1. Get user's recent conversations with messages:
```sql
SELECT c.*, array_agg(m.* ORDER BY m.created_at) as messages
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.user_id = ? AND c.is_archived = false
GROUP BY c.id
ORDER BY c.updated_at DESC
LIMIT 10;
```

### 2. Search Knowledge Base for similar question:
```sql
SELECT * FROM sql_knowledge_base
WHERE database_type = 'clickhouse'
  AND schema_hash = ?
  AND to_tsvector('english', question) @@ to_tsquery('monthly sales')
ORDER BY usage_count DESC, success_rate DESC
LIMIT 5;
```

### 3. Get transcription with speakers:
```sql
SELECT t.*, json_agg(s.*) as speakers
FROM transcriptions t
LEFT JOIN speakers s ON t.id = s.transcription_id
WHERE t.id = ?
GROUP BY t.id;
```

### 4. Get popular LoRA models:
```sql
SELECT 
    lm.*,
    COUNT(ig.id) as usage_in_images
FROM lora_models lm
LEFT JOIN image_generations ig ON ig.lora_models::text LIKE '%' || lm.model_name || '%'
WHERE lm.is_active = true
GROUP BY lm.id
ORDER BY usage_in_images DESC, lm.rating DESC
LIMIT 20;
```

---

## 📊 Data Growth Estimates

### Assumptions:
- **Users:** 1,000 active users
- **Usage:** Daily active for 1 year
- **ChatBot:** 10 conversations/user/month, 20 messages/conversation
- **Text2SQL:** 50 queries/user/month
- **Speech2Text:** 2 transcriptions/user/month
- **Images:** 10 images/user/month

### Growth Projection:

| Table | Records/Year | Size/Year | Growth Rate |
|:------|:------------|:----------|:------------|
| **USERS** | 1,000 | 1 MB | Slow |
| **CONVERSATIONS** | 120K | 100 MB | Moderate |
| **MESSAGES** | 2.4M | 1.5 GB | Fast |
| **CHATBOT_MEMORY** | 50K | 50 MB | Slow |
| **SQL_KNOWLEDGE_BASE** | 10K | 20 MB | Slow (reuse) |
| **QUERY_HISTORY** | 600K | 300 MB | Fast |
| **TRANSCRIPTIONS** | 24K | 2 GB | Moderate |
| **IMAGE_GENERATIONS** | 120K | 4 GB | Fast |
| **API_USAGE** | 10M | 8 GB | Very Fast |
| **SYSTEM_LOGS** | 50M | 10 GB | Very Fast |

**Total Estimated:** ~25 GB/year (excluding file storage)

### File Storage (separate from DB):
- **Uploaded files:** ~200 GB/year
- **Images:** ~300 GB/year
- **Transcription audio:** ~200 GB/year

**Grand Total:** ~925 GB/year (DB + Files)

---

## 🚀 Optimization Strategies

### 1. Partitioning (for large tables):
```sql
-- Partition API_USAGE by month
CREATE TABLE api_usage (
    -- columns...
) PARTITION BY RANGE (created_at);

CREATE TABLE api_usage_2025_11 PARTITION OF api_usage
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

### 2. Archiving old data:
- Move conversations older than 1 year to `conversations_archive`
- Move logs older than 3 months to cold storage

### 3. Indexing strategy:
- **B-Tree indexes:** For exact matches, ranges (timestamps, IDs)
- **GIN indexes:** For full-text search, JSONB, arrays
- **Hash indexes:** For equality checks (rare)

### 4. Materialized views:
```sql
-- User stats summary
CREATE MATERIALIZED VIEW user_stats AS
SELECT 
    u.id,
    COUNT(DISTINCT c.id) as total_conversations,
    COUNT(DISTINCT qh.id) as total_queries,
    COUNT(DISTINCT pd.id) as total_documents
FROM users u
LEFT JOIN conversations c ON u.id = c.user_id
LEFT JOIN query_history qh ON u.id = qh.user_id
LEFT JOIN processed_documents pd ON u.id = pd.user_id
GROUP BY u.id;

-- Refresh daily
REFRESH MATERIALIZED VIEW user_stats;
```

---

## 📝 Normalization Analysis

### Current Normalization: **3NF (Third Normal Form)**

**Compliance:**
✅ **1NF:** All attributes atomic (no repeating groups)  
✅ **2NF:** No partial dependencies (all FKs depend on full PK)  
✅ **3NF:** No transitive dependencies  

**JSONB fields (denormalized):**
- `MESSAGES.images` - Array of image objects
- `MESSAGES.metadata` - Flexible metadata
- `IMAGE_GENERATIONS.lora_models` - Array of LoRA configs
- `PROCESSED_DOCUMENTS.extracted_info` - Flexible extracted data

**Reason:** PostgreSQL's JSONB provides fast queries while maintaining flexibility for semi-structured data.

---

## 🔐 Security Considerations

### 1. Sensitive Data Encryption:
- `DATABASE_CONNECTIONS.password_encrypted` - AES-256 encryption
- `USER_API_KEYS.key_hash` - bcrypt hashing

### 2. Row-Level Security (RLS):
```sql
-- Enable RLS on conversations
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own conversations
CREATE POLICY user_conversations_policy ON conversations
    FOR SELECT
    USING (user_id = current_setting('app.current_user_id')::int);
```

### 3. Audit Trail:
- All tables have `created_at` timestamp
- Important tables have `updated_at` trigger
- `SYSTEM_LOGS` tracks all actions

---

<div align="center">

[⬅️ Previous: Database Design](04_database_design.md) | [Back to Index](README.md)

---

**🎉 ALL DIAGRAMS COMPLETE!**

Ready to migrate to production database 🚀

</div>
