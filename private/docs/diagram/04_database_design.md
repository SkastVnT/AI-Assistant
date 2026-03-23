# 4️⃣ DATABASE DESIGN

> **Thiết kế cơ sở dữ liệu cho hệ thống AI-Assistant v2.0**  
> **Cập nhật:** 11/11/2025  
> Sử dụng MongoDB Atlas (Production) + PostgreSQL (Text2SQL) + ClickHouse (Analytics)

---

## 📋 Tổng quan Database Architecture

### ✅ Production Databases (Hiện tại):

| Database | Service | Purpose | Status | Size |
|:---------|:--------|:--------|:-------|:-----|
| **MongoDB Atlas** | ChatBot | Conversations, Messages, Memory | ✅ Production | 512MB Free Tier |
| **PostgreSQL** | Text2SQL | Knowledge Base, Schemas, Queries | ✅ Production | Local/Cloud |
| **ClickHouse** | Text2SQL | Analytics, Query Logs | ✅ Production | Local/Cloud |
| **File Storage** | All | Images, Audio, Files | ✅ Local + Cloud | Variable |
| **ImgBB Cloud** | ChatBot, SD | Image hosting | ✅ Production | Unlimited Free |

### 🎯 Database Distribution:

```
ChatBot Service:
  ├─ MongoDB Atlas (6 collections, 26 indexes)
  ├─ Local Storage (ChatBot/Storage/)
  └─ ImgBB Cloud (Generated images)

Text2SQL Service:
  ├─ PostgreSQL (Knowledge Base)
  ├─ ClickHouse (Query analytics)
  └─ JSON Files (Backup)

Speech2Text Service:
  ├─ File Storage (Audio + Transcripts)
  └─ Future: MongoDB (History)

Stable Diffusion:
  ├─ File Storage (Generated images)
  ├─ ImgBB Cloud (Auto-upload)
  └─ MongoDB (Metadata via ChatBot)
```

---

## 📚 CHI TIẾT MONGODB SCHEMA - PRODUCTION

> **⚠️ ĐÂY LÀ SCHEMA THỰC TẾ ĐANG CHẠY**  
> **Database:** `chatbot_db` trên MongoDB Atlas  
> **Cluster:** `ai-assistant.aspuqwb.mongodb.net`  
> **Version:** v2.1 (Post ImgBB Integration - Nov 10, 2025)

### 🔗 Tài liệu chi tiết MongoDB:

**📖 [MongoDB Schema - Complete Documentation](../docs/archives/2025-11-10/MONGODB_SCHEMA_UPDATED_1110.md)**

Tài liệu này chứa:
- ✅ **6 Collections:** conversations, messages, chatbot_memory, uploaded_files, users, user_settings
- ✅ **26 Indexes:** Performance optimized cho queries
- ✅ **ImgBB Cloud Storage:** 
  - Auto-save images to cloud
  - Persistent shareable URLs
  - Delete URLs for cleanup
- ✅ **Hybrid Storage Strategy:**
  - Local: `ChatBot/Storage/` (backup, fast access)
  - Cloud: ImgBB (permanent, shareable)
  - Database: MongoDB (metadata + URLs)
- ✅ **Complete Examples:** Real documents with cloud URLs
- ✅ **Query Examples:** Aggregation pipelines
- ✅ **Connection Config:** PyMongo setup

**Cập nhật:** November 10, 2025

---

## 🗂️ LEGACY POSTGRESQL DESIGN (REFERENCE ONLY)

> **Note:** Phần dưới đây là thiết kế PostgreSQL ban đầu, KHÔNG phải implementation hiện tại.  
> Giữ lại cho reference purposes. Production system sử dụng MongoDB Atlas.  

---

## � Database Schema Diagrams

### Overview: Full Database Schema (18 Tables)

```mermaid
erDiagram
    %% Users & Authentication
    users ||--o{ user_api_keys : "has"
    users ||--o{ conversations : "creates"
    users ||--o{ chatbot_memory : "learns"
    users ||--o{ uploaded_files : "uploads"
    users ||--o{ sql_knowledge_base : "creates"
    users ||--o{ database_connections : "manages"
    users ||--o{ query_history : "executes"
    users ||--o{ transcriptions : "generates"
    users ||--o{ image_generations : "creates"
    users ||--o{ api_usage : "tracks"

    %% ChatBot Service
    conversations ||--o{ messages : "contains"
    conversations ||--o{ chatbot_memory : "referenced"
    conversations ||--o{ uploaded_files : "linked"
    conversations ||--o{ image_generations : "linked"
    messages ||--o{ messages : "self-reference (parent)"

    %% Text2SQL Service
    database_connections ||--o{ query_history : "uses"
    database_connections ||--o{ database_schemas : "has"
    sql_knowledge_base ||--o{ query_history : "matches"

    %% Speech2Text Service
    transcriptions ||--o{ speakers : "identifies"

    %% System Monitoring
    %% (No foreign keys for system_logs, api_usage, system_metrics)

    %% Table Definitions
    users {
        int id PK
        string username UK
        string email UK
        string password_hash
        string full_name
        string role
        boolean is_active
        int api_quota_daily
        timestamp created_at
    }

    user_api_keys {
        int id PK
        int user_id FK
        string key_name
        string key_hash UK
        boolean is_active
        timestamp expires_at
    }

    conversations {
        uuid id PK
        int user_id FK
        string model
        string title
        text system_prompt
        int total_messages
        int total_tokens
        boolean is_archived
    }

    messages {
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
    }

    chatbot_memory {
        int id PK
        int user_id FK
        uuid conversation_id FK
        text question
        text answer
        int rating
        text[] tags
        boolean is_public
    }

    uploaded_files {
        int id PK
        int user_id FK
        uuid conversation_id FK
        string original_filename
        string file_path
        bigint file_size
        text analysis_result
    }

    sql_knowledge_base {
        int id PK
        text question
        text sql_query
        string database_type
        string schema_hash
        boolean is_correct
        int usage_count
        decimal success_rate
        int created_by FK
    }

    database_connections {
        int id PK
        int user_id FK
        string name
        string type
        string host
        int port
        string password_encrypted
        boolean is_active
    }

    query_history {
        int id PK
        int user_id FK
        int connection_id FK
        text question
        text sql_query
        int execution_time_ms
        string status
        int kb_match_id FK
    }

    database_schemas {
        int id PK
        int connection_id FK
        jsonb schema_json
        string schema_hash UK
        int table_count
    }

    transcriptions {
        int id PK
        int user_id FK
        string file_path
        int duration_seconds
        text transcript_raw
        text transcript_enhanced
        jsonb speaker_timeline
        int num_speakers
    }

    speakers {
        int id PK
        int transcription_id FK
        string speaker_id
        string speaker_label
        int total_duration_seconds
    }

    image_generations {
        int id PK
        int user_id FK
        uuid conversation_id FK
        text prompt
        string model
        jsonb lora_models
        string image_url
        string image_hash
    }

    lora_models {
        int id PK
        string model_name UK
        string category
        text[] trigger_words
        int usage_count
    }

    system_logs {
        int id PK
        string service
        string level
        text message
        jsonb metadata
    }

    api_usage {
        int id PK
        string service
        string endpoint
        int user_id FK
        int status_code
        int response_time_ms
    }

    system_metrics {
        int id PK
        string service
        string metric_name
        decimal metric_value
        timestamp timestamp
    }
```

---

### Service-Based Schema Views

#### 1️⃣ ChatBot Service Schema

```mermaid
erDiagram
    users ||--o{ conversations : "1:N"
    users ||--o{ chatbot_memory : "1:N"
    users ||--o{ uploaded_files : "1:N"
    
    conversations ||--o{ messages : "1:N"
    conversations ||--o{ chatbot_memory : "1:N"
    conversations ||--o{ uploaded_files : "1:N"
    
    messages ||--o{ messages : "parent-child"

    users {
        int id PK "Primary Key"
        string username UK "Unique"
        string email UK "Unique"
        string role "user/admin/developer"
    }

    conversations {
        uuid id PK "UUID v4"
        int user_id FK "→ users.id"
        string model "grok-3/gpt-4"
        string title "Conversation title"
        int total_messages "Message count"
        int total_tokens "Token usage"
        boolean is_archived "Archive status"
    }

    messages {
        int id PK "Auto-increment"
        uuid conversation_id FK "→ conversations.id"
        string role "user/assistant/system"
        text content "Message text"
        jsonb images "Image attachments"
        jsonb files "File attachments"
        int parent_message_id FK "→ messages.id"
        int version "Version number"
    }

    chatbot_memory {
        int id PK
        int user_id FK "→ users.id"
        uuid conversation_id FK "→ conversations.id"
        text question "User question"
        text answer "AI answer"
        int rating "1-5 stars"
        text[] tags "Categories"
        boolean is_public "Share knowledge"
    }

    uploaded_files {
        int id PK
        int user_id FK "→ users.id"
        uuid conversation_id FK "→ conversations.id"
        string file_path "Storage path"
        bigint file_size "Bytes"
        text analysis_result "AI analysis"
    }
```

#### 2️⃣ Text2SQL Service Schema

```mermaid
erDiagram
    users ||--o{ sql_knowledge_base : "creates"
    users ||--o{ database_connections : "manages"
    users ||--o{ query_history : "executes"
    
    database_connections ||--o{ query_history : "uses"
    database_connections ||--o{ database_schemas : "caches"
    
    sql_knowledge_base ||--o{ query_history : "matches"

    sql_knowledge_base {
        int id PK
        text question "Natural language"
        text sql_query "Generated SQL"
        string database_type "clickhouse/mongodb/postgresql"
        string schema_hash "MD5 hash"
        int usage_count "Times used"
        decimal success_rate "0-100%"
        text[] tags "Categories"
    }

    database_connections {
        int id PK
        int user_id FK
        string name "Connection name"
        string type "DB type"
        string host "Server address"
        int port "Port number"
        string password_encrypted "AES-256"
        jsonb connection_params "Extra params"
    }

    query_history {
        int id PK
        int user_id FK
        int connection_id FK
        text question "User question"
        text sql_query "Executed SQL"
        int execution_time_ms "Performance"
        string status "success/error/timeout"
        jsonb result_preview "First 10 rows"
        int kb_match_id FK "→ sql_knowledge_base.id"
    }

    database_schemas {
        int id PK
        int connection_id FK
        jsonb schema_json "Full schema structure"
        string schema_hash UK "MD5 hash"
        int table_count "Number of tables"
    }
```

#### 3️⃣ Speech2Text Service Schema

```mermaid
erDiagram
    users ||--o{ transcriptions : "generates"
    transcriptions ||--o{ speakers : "identifies"

    transcriptions {
        int id PK
        int user_id FK
        string file_path "Audio file location"
        bigint file_size "Bytes"
        int duration_seconds "Audio length"
        string audio_format "mp3/wav/m4a/flac"
        int sample_rate "Hz"
        string language "vi/en/etc"
        int num_speakers "Speaker count"
        text transcript_raw "Whisper output"
        text transcript_enhanced "Qwen-enhanced"
        jsonb speaker_timeline "Diarization result"
        jsonb models_used "Model info"
        decimal accuracy_score "0-100%"
    }

    speakers {
        int id PK
        int transcription_id FK
        string speaker_id "SPEAKER_00/01/etc"
        string speaker_label "User-assigned name"
        int total_duration_seconds "Speaking time"
        int word_count "Words spoken"
        decimal avg_confidence "0-100%"
    }
```

#### 4️⃣ Stable Diffusion Service Schema

```mermaid
erDiagram
    users ||--o{ image_generations : "creates"
    conversations ||--o{ image_generations : "linked from chatbot"
    lora_models ||--o{ image_generations : "used in (via JSONB)"

    image_generations {
        int id PK
        int user_id FK
        uuid conversation_id FK "Optional ChatBot link"
        text prompt "Positive prompt"
        text negative_prompt "Negative prompt"
        string model "sd-v1-5/sdxl/etc"
        jsonb lora_models "Array of LoRA used"
        string sampler "DPM++/Euler/etc"
        int steps "Generation steps"
        decimal cfg_scale "Guidance scale"
        bigint seed "Random seed"
        int width "Image width"
        int height "Image height"
        string image_url "Storage path"
        string image_hash "MD5 deduplication"
        int generation_time_ms "Performance"
    }

    lora_models {
        int id PK
        string model_name UK "Unique filename"
        string display_name "Friendly name"
        string category "character/style/concept"
        string file_path "Model location"
        text[] trigger_words "Activation words"
        int usage_count "Times used"
        decimal rating "User rating 0-5"
    }
```

#### 5️⃣ System Monitoring Schema

```mermaid
erDiagram
    users ||--o{ api_usage : "tracked"

    system_logs {
        int id PK
        string service "chatbot/text2sql/etc"
        string level "DEBUG/INFO/WARNING/ERROR/CRITICAL"
        text message "Log message"
        jsonb metadata "stack_trace, user_id, etc"
        string source "File/function name"
        timestamp created_at "Log time"
    }

    api_usage {
        int id PK
        string service "Service name"
        string endpoint "API endpoint"
        int user_id FK "Optional user"
        string method "GET/POST/etc"
        int status_code "HTTP status"
        int response_time_ms "Latency"
        int request_size_bytes "Request size"
        int response_size_bytes "Response size"
        string ip_address "Client IP"
    }

    system_metrics {
        int id PK
        string service "Service name"
        string metric_name "cpu_usage/memory_usage/etc"
        decimal metric_value "Metric value"
        string unit "percent/mb/count"
        timestamp timestamp "Metric time"
    }
```

---

### Data Flow Diagram

```mermaid
graph TB
    subgraph "User Layer"
        User[👤 User]
        API[🔑 API Keys]
    end

    subgraph "ChatBot Service"
        Conv[💬 Conversations]
        Msg[📝 Messages]
        Mem[🧠 Memory]
        Files[📎 Uploaded Files]
    end

    subgraph "Text2SQL Service"
        KB[📚 Knowledge Base]
        DBConn[🔌 DB Connections]
        Query[🔍 Query History]
        Schema[📋 DB Schemas]
    end

    subgraph "Speech2Text Service"
        Trans[🎤 Transcriptions]
        Spk[👥 Speakers]
    end

    subgraph "Stable Diffusion Service"
        ImgGen[🖼️ Image Generations]
        LoRA[🎨 LoRA Models]
    end

    subgraph "System Monitoring"
        Logs[📊 System Logs]
        Usage[📈 API Usage]
        Metrics[⚙️ System Metrics]
    end

    %% User connections
    User --> Conv
    User --> Mem
    User --> Files
    User --> KB
    User --> DBConn
    User --> Query
    User --> Trans
    User --> ImgGen
    User --> API
    User --> Usage

    %% ChatBot flows
    Conv --> Msg
    Conv --> Mem
    Conv --> Files
    Conv --> ImgGen
    Msg -.parent.-> Msg

    %% Text2SQL flows
    KB -.match.-> Query
    DBConn --> Query
    DBConn --> Schema
    Query --> Logs

    %% Speech2Text flows
    Trans --> Spk

    %% Image Generation flows
    ImgGen -.uses.-> LoRA

    %% Monitoring flows
    Conv --> Logs
    Query --> Logs
    Trans --> Logs
    ImgGen --> Logs
    API --> Usage

    %% Styling
    classDef userClass fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef chatClass fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    classDef sqlClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef s2tClass fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef sdClass fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef sysClass fill:#eceff1,stroke:#263238,stroke-width:2px

    class User,API userClass
    class Conv,Msg,Mem,Files chatClass
    class KB,DBConn,Query,Schema sqlClass
    class Trans,Spk s2tClass
    class ImgGen,LoRA sdClass
    class Logs,Usage,Metrics sysClass
```

---

### Index Strategy Overview

```mermaid
graph LR
    subgraph "Primary Indexes (18 tables)"
        PK[🔑 Primary Keys<br/>18 tables]
    end

    subgraph "Foreign Key Indexes (26 indexes)"
        FK1[👤 User References<br/>10 indexes]
        FK2[💬 Conversation References<br/>4 indexes]
        FK3[🔌 Connection References<br/>3 indexes]
        FK4[📚 Knowledge Base References<br/>1 index]
        FK5[🎤 Transcription References<br/>1 index]
        FK6[📝 Message References<br/>1 index]
    end

    subgraph "Unique Indexes (8 indexes)"
        UK1[📧 Email/Username<br/>2 indexes]
        UK2[🔑 API Key Hash<br/>1 index]
        UK3[📋 Schema Hash<br/>2 indexes]
        UK4[🖼️ Image Hash<br/>1 index]
        UK5[🎨 Model Name<br/>1 index]
    end

    subgraph "Performance Indexes (18 indexes)"
        Perf1[⏰ Timestamps<br/>6 indexes]
        Perf2[🔍 Search<br/>2 GIN indexes]
        Perf3[📊 Analytics<br/>4 indexes]
        Perf4[🏷️ Categories<br/>3 indexes]
        Perf5[📈 Usage Tracking<br/>3 indexes]
    end

    PK --> FK1 & FK2 & FK3 & FK4 & FK5 & FK6
    FK1 & FK2 --> UK1 & UK2 & UK3 & UK4 & UK5
    UK1 & UK2 --> Perf1 & Perf2 & Perf3 & Perf4 & Perf5

    style PK fill:#4caf50,stroke:#1b5e20,color:#fff
    style FK1 fill:#2196f3,stroke:#0d47a1,color:#fff
    style FK2 fill:#2196f3,stroke:#0d47a1,color:#fff
    style FK3 fill:#2196f3,stroke:#0d47a1,color:#fff
    style FK4 fill:#2196f3,stroke:#0d47a1,color:#fff
    style FK5 fill:#2196f3,stroke:#0d47a1,color:#fff
    style FK6 fill:#2196f3,stroke:#0d47a1,color:#fff
    style UK1 fill:#ff9800,stroke:#e65100,color:#fff
    style UK2 fill:#ff9800,stroke:#e65100,color:#fff
    style UK3 fill:#ff9800,stroke:#e65100,color:#fff
    style UK4 fill:#ff9800,stroke:#e65100,color:#fff
    style UK5 fill:#ff9800,stroke:#e65100,color:#fff
    style Perf1 fill:#9c27b0,stroke:#4a148c,color:#fff
    style Perf2 fill:#9c27b0,stroke:#4a148c,color:#fff
    style Perf3 fill:#9c27b0,stroke:#4a148c,color:#fff
    style Perf4 fill:#9c27b0,stroke:#4a148c,color:#fff
    style Perf5 fill:#9c27b0,stroke:#4a148c,color:#fff
```

**Total Indexes: 50+ indexes** across 18 tables for optimal query performance.

---

## �🗄️ Database Schema

### 1. Users & Authentication

```sql
-- Users table (for future multi-user system)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    avatar_url TEXT,
    role VARCHAR(20) DEFAULT 'user', -- 'user', 'admin', 'developer'
    is_active BOOLEAN DEFAULT true,
    api_quota_daily INTEGER DEFAULT 1000, -- API calls per day
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    last_ip VARCHAR(45),
    CONSTRAINT valid_role CHECK (role IN ('user', 'admin', 'developer'))
);

-- User API keys (for programmatic access)
CREATE TABLE user_api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    key_name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_used TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_api_keys_user ON user_api_keys(user_id);
CREATE INDEX idx_api_keys_hash ON user_api_keys(key_hash);
```

---

### 2. ChatBot Service Tables

```sql
-- Conversations
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    model VARCHAR(50) NOT NULL, -- 'grok-3', 'gpt-4', etc.
    title VARCHAR(255),
    system_prompt TEXT,
    total_messages INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Messages
CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    images JSONB, -- Array: [{url, caption, size}]
    files JSONB, -- Array: [{name, path, type, size}]
    metadata JSONB, -- {tokens, model, temperature, etc.}
    version INTEGER DEFAULT 1, -- Message versioning (v2.0 feature)
    parent_message_id INTEGER REFERENCES messages(id),
    is_edited BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant', 'system'))
);

-- ChatBot memory (AI learning from conversations)
CREATE TABLE chatbot_memory (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    context TEXT, -- Additional context
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    tags TEXT[], -- Array of tags for categorization
    is_public BOOLEAN DEFAULT false, -- Share with other users?
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Uploaded files metadata
CREATE TABLE uploaded_files (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id),
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(50),
    file_size BIGINT,
    mime_type VARCHAR(100),
    analysis_result TEXT, -- AI analysis of file
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_created ON conversations(created_at DESC);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_memory_user ON chatbot_memory(user_id);
CREATE INDEX idx_memory_tags ON chatbot_memory USING GIN(tags);
CREATE INDEX idx_files_user ON uploaded_files(user_id);
```

---

### 3. Text2SQL Service Tables

```sql
-- SQL Knowledge Base (AI learning system)
CREATE TABLE sql_knowledge_base (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    database_type VARCHAR(50) NOT NULL, -- 'clickhouse', 'mongodb', 'postgresql'
    schema_name VARCHAR(100),
    schema_hash VARCHAR(64), -- MD5 hash of schema for matching
    is_correct BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    avg_execution_time_ms INTEGER,
    success_rate DECIMAL(5,2), -- Percentage
    tags TEXT[], -- Array of tags
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP
);

-- Database connections (user-saved connections)
CREATE TABLE database_connections (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'clickhouse', 'mongodb', 'postgresql', 'mysql'
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database_name VARCHAR(100),
    username VARCHAR(100),
    password_encrypted TEXT, -- AES encrypted
    ssl_enabled BOOLEAN DEFAULT false,
    connection_params JSONB, -- Additional params
    is_active BOOLEAN DEFAULT true,
    last_tested TIMESTAMP,
    last_test_result TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_db_type CHECK (type IN ('clickhouse', 'mongodb', 'postgresql', 'mysql', 'oracle'))
);

-- Query execution history
CREATE TABLE query_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    connection_id INTEGER REFERENCES database_connections(id) ON DELETE SET NULL,
    question TEXT NOT NULL,
    sql_query TEXT NOT NULL,
    execution_time_ms INTEGER,
    rows_returned INTEGER,
    status VARCHAR(20), -- 'success', 'error', 'timeout'
    error_message TEXT,
    result_preview JSONB, -- First 10 rows
    kb_match_id INTEGER REFERENCES sql_knowledge_base(id), -- If from KB
    feedback VARCHAR(20), -- 'correct', 'wrong', 'partial'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Database schemas (cached)
CREATE TABLE database_schemas (
    id SERIAL PRIMARY KEY,
    connection_id INTEGER REFERENCES database_connections(id) ON DELETE CASCADE,
    schema_json JSONB NOT NULL, -- Full schema structure
    schema_hash VARCHAR(64) UNIQUE NOT NULL,
    table_count INTEGER,
    total_columns INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_kb_question ON sql_knowledge_base USING gin(to_tsvector('english', question));
CREATE INDEX idx_kb_schema_hash ON sql_knowledge_base(schema_hash);
CREATE INDEX idx_kb_usage ON sql_knowledge_base(usage_count DESC);
CREATE INDEX idx_kb_type ON sql_knowledge_base(database_type);
CREATE INDEX idx_kb_tags ON sql_knowledge_base USING GIN(tags);
CREATE INDEX idx_connections_user ON database_connections(user_id);
CREATE INDEX idx_query_history_user ON query_history(user_id);
CREATE INDEX idx_query_history_created ON query_history(created_at DESC);
CREATE INDEX idx_schemas_hash ON database_schemas(schema_hash);
```

---

### 4. Speech2Text Service Tables

```sql
-- Transcriptions
CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    duration_seconds INTEGER,
    audio_format VARCHAR(20), -- 'mp3', 'wav', 'm4a', 'flac'
    sample_rate INTEGER,
    language VARCHAR(10) DEFAULT 'vi',
    num_speakers INTEGER,
    transcript_raw TEXT, -- Raw merged transcript
    transcript_enhanced TEXT, -- Qwen-enhanced
    speaker_timeline JSONB, -- [{speaker, start, end, text, confidence}]
    models_used JSONB, -- {whisper: 'large-v3', phowhisper: 'base', etc.}
    processing_time_ms INTEGER,
    accuracy_score DECIMAL(5,2), -- Estimated accuracy
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Speaker information (for diarization results)
CREATE TABLE speakers (
    id SERIAL PRIMARY KEY,
    transcription_id INTEGER REFERENCES transcriptions(id) ON DELETE CASCADE,
    speaker_id VARCHAR(20) NOT NULL, -- 'SPEAKER_00', 'SPEAKER_01', etc.
    speaker_label VARCHAR(100), -- User-assigned name
    total_duration_seconds INTEGER,
    word_count INTEGER,
    avg_confidence DECIMAL(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_transcriptions_user ON transcriptions(user_id);
CREATE INDEX idx_transcriptions_created ON transcriptions(created_at DESC);
CREATE INDEX idx_transcriptions_language ON transcriptions(language);
CREATE INDEX idx_speakers_transcription ON speakers(transcription_id);
```

---

### 5. Stable Diffusion Service Tables

```sql
-- Image generations
CREATE TABLE image_generations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    conversation_id UUID REFERENCES conversations(id), -- Link to ChatBot if generated from chat
    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    model VARCHAR(100) NOT NULL, -- 'sd-v1-5', 'sdxl', etc.
    lora_models JSONB, -- [{name, weight}, ...]
    vae_model VARCHAR(100),
    sampler VARCHAR(50),
    steps INTEGER,
    cfg_scale DECIMAL(3,1),
    seed BIGINT,
    width INTEGER,
    height INTEGER,
    image_url TEXT, -- Stored image path
    image_hash VARCHAR(64), -- MD5 hash for deduplication
    generation_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- LoRA models (track available and usage)
CREATE TABLE lora_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(100),
    description TEXT,
    category VARCHAR(50), -- 'character', 'style', 'concept'
    file_path TEXT NOT NULL,
    file_size BIGINT,
    trigger_words TEXT[], -- Array of trigger words
    usage_count INTEGER DEFAULT 0,
    rating DECIMAL(3,2), -- User ratings
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_image_gen_user ON image_generations(user_id);
CREATE INDEX idx_image_gen_created ON image_generations(created_at DESC);
CREATE INDEX idx_image_gen_model ON image_generations(model);
CREATE INDEX idx_image_gen_hash ON image_generations(image_hash);
CREATE INDEX idx_lora_category ON lora_models(category);
CREATE INDEX idx_lora_usage ON lora_models(usage_count DESC);
```

---

### 6. System Tables (Monitoring & Analytics)

```sql
-- System logs
CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    service VARCHAR(50) NOT NULL, -- 'chatbot', 'text2sql', etc.
    level VARCHAR(20) NOT NULL, -- 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    message TEXT NOT NULL,
    metadata JSONB, -- {stack_trace, user_id, request_id, etc.}
    source VARCHAR(100), -- File/function name
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_level CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
);

-- API usage statistics
CREATE TABLE api_usage (
    id SERIAL PRIMARY KEY,
    service VARCHAR(50) NOT NULL,
    endpoint VARCHAR(255) NOT NULL,
    user_id INTEGER REFERENCES users(id),
    method VARCHAR(10), -- 'GET', 'POST', etc.
    status_code INTEGER,
    response_time_ms INTEGER,
    request_size_bytes INTEGER,
    response_size_bytes INTEGER,
    ip_address VARCHAR(45),
    user_agent TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System metrics (for monitoring)
CREATE TABLE system_metrics (
    id SERIAL PRIMARY KEY,
    service VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL, -- 'cpu_usage', 'memory_usage', 'active_users'
    metric_value DECIMAL(10,2),
    unit VARCHAR(20), -- 'percent', 'mb', 'count'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_logs_service_level ON system_logs(service, level);
CREATE INDEX idx_logs_created ON system_logs(created_at DESC);
CREATE INDEX idx_api_usage_service ON api_usage(service);
CREATE INDEX idx_api_usage_user ON api_usage(user_id);
CREATE INDEX idx_api_usage_created ON api_usage(created_at DESC);
CREATE INDEX idx_metrics_service ON system_metrics(service, metric_name);
CREATE INDEX idx_metrics_timestamp ON system_metrics(timestamp DESC);

-- Partition by month for better performance
CREATE TABLE api_usage_2025_11 PARTITION OF api_usage
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
```

---

## 🔐 Database Functions & Triggers

### Auto-update timestamps:

```sql
-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_kb_updated_at
    BEFORE UPDATE ON sql_knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### Increment usage count:

```sql
-- Function to increment KB usage
CREATE OR REPLACE FUNCTION increment_kb_usage()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.kb_match_id IS NOT NULL THEN
        UPDATE sql_knowledge_base
        SET usage_count = usage_count + 1,
            last_used = CURRENT_TIMESTAMP
        WHERE id = NEW.kb_match_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger
CREATE TRIGGER increment_kb_on_query
    AFTER INSERT ON query_history
    FOR EACH ROW
    EXECUTE FUNCTION increment_kb_usage();
```

---

## 📊 Database Statistics

| Table Category | Tables | Estimated Size (1K users, 1 year) |
|:--------------|:-------|:----------------------------------|
| **Users & Auth** | 2 | ~50 MB |
| **ChatBot** | 4 | ~2 GB |
| **Text2SQL** | 5 | ~500 MB |
| **Speech2Text** | 2 | ~3 GB |
| **Stable Diffusion** | 2 | ~5 GB |
| **System** | 3 | ~10 GB |
| **TOTAL** | **18 tables** | **~20.5 GB** |

---

## 🚀 Migration Plan

### Phase 1: Setup (Week 1)
1. Install PostgreSQL 14+
2. Create database: `ai_assistant_db`
3. Run schema creation scripts
4. Setup SQLAlchemy ORM

### Phase 2: ChatBot Migration (Week 2)
1. Create migration script: `ChatBot/Storage/` → `conversations` table
2. Test data integrity
3. Update `ChatBot/app.py` to use PostgreSQL
4. Keep JSON as backup for 1 month

### Phase 3: Text2SQL Migration (Week 3)
1. Migrate knowledge base: JSON Lines → `sql_knowledge_base` table
2. Add connection management UI
3. Update query generation to use DB
4. Implement learning algorithm improvements

### Phase 4: Other Services (Week 4)
1. Add Speech2Text history
2. Add Stable Diffusion metadata
3. Implement admin dashboard

---

## 📝 Connection Examples

### Python (SQLAlchemy):

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database URL
DATABASE_URL = "postgresql://user:password@localhost:5432/ai_assistant_db"

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Usage
def get_conversation(conv_id):
    db = SessionLocal()
    try:
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        return conv
    finally:
        db.close()
```

---

<div align="center">

[⬅️ Previous: Sequence Diagrams](03_sequence_diagrams.md) | [Back to Index](README.md) | [➡️ Next: ER Diagram](05_er_diagram.md)

</div>

---

## 📸 DATABASE DIAGRAMS (Chia Nhỏ Để Chụp)

> **Các biểu đồ dưới đây được chia nhỏ theo từng database/service để dễ dàng chụp màn hình**

---

### 1️⃣ MongoDB Atlas - ChatBot Collections

```mermaid
erDiagram
    conversations ||--o{ messages : "contains"
    conversations ||--o{ chatbot_memory : "referenced"
    conversations ||--o{ uploaded_files : "linked"
    users ||--o{ conversations : "creates"
    users ||--o{ user_settings : "has"
    
    conversations {
        ObjectId _id PK
        String user_id
        String model
        String title
        Number total_messages
        Number total_tokens
        Boolean is_archived
        ISODate created_at
        ISODate updated_at
    }
    
    messages {
        ObjectId _id PK
        ObjectId conversation_id FK
        String role
        String content
        Array images
        Array files
        Object metadata
        Number version
        ISODate created_at
    }
    
    chatbot_memory {
        ObjectId _id PK
        String user_id
        ObjectId conversation_id FK
        String question
        String answer
        Number rating
        Array tags
        ISODate created_at
    }
    
    uploaded_files {
        ObjectId _id PK
        String user_id
        ObjectId conversation_id FK
        String filename
        String file_path
        Number file_size
        String analysis_result
        ISODate created_at
    }
```

---

### 2️⃣ MongoDB Messages Collection - Image Storage

```mermaid
graph TB
    A[💬 Message] --> B{📎 Has Images?}
    
    B -->|Yes| C[🖼️ images Array]
    B -->|No| D[💬 Text Only]
    
    C --> E[📁 Local Storage<br/>ChatBot/Storage/Image_Gen/]
    C --> F[☁️ Cloud Storage<br/>ImgBB URLs]
    C --> G[💾 MongoDB Metadata<br/>cloud_url, delete_url]
    
    E --> H[🔄 Backup<br/>Fast Access]
    F --> I[🌐 Permanent<br/>Shareable Links]
    G --> J[📊 Query<br/>Find Images]
    
    style A fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style C fill:#10B981,stroke:#059669,color:#fff
    style E fill:#3B82F6,stroke:#2563EB,color:#fff
    style F fill:#EC4899,stroke:#DB2777,color:#fff
    style G fill:#F59E0B,stroke:#D97706,color:#fff
```

---

### 3️⃣ PostgreSQL - Text2SQL Schema

```mermaid
erDiagram
    knowledge_base ||--o{ query_history : "matches"
    db_connections ||--o{ query_history : "uses"
    db_connections ||--o{ db_schemas : "caches"
    
    knowledge_base {
        int id PK
        text question
        text sql_query
        string database_type
        string schema_hash
        boolean is_correct
        int usage_count
        decimal success_rate
        timestamp created_at
    }
    
    db_connections {
        int id PK
        string name
        string type
        string host
        int port
        string database_name
        boolean is_active
        timestamp created_at
    }
    
    query_history {
        int id PK
        int connection_id FK
        text question
        text sql_query
        int execution_time_ms
        string status
        int kb_match_id FK
        timestamp created_at
    }
    
    db_schemas {
        int id PK
        int connection_id FK
        jsonb schema_json
        string schema_hash
        int table_count
        timestamp created_at
    }
```

---

### 4️⃣ ClickHouse - Analytics Schema

```mermaid
erDiagram
    query_logs {
        uint64 id PK
        datetime timestamp
        string user_id
        string question
        string sql_query
        uint32 execution_time_ms
        string status
        string database_type
        uint32 rows_returned
    }
    
    performance_stats {
        uint64 id PK
        datetime date
        string metric_name
        float64 metric_value
        string service
    }
    
    user_analytics {
        uint64 id PK
        datetime timestamp
        string user_id
        string service
        string action
        jsonb metadata
    }
```

---

### 5️⃣ Hybrid Storage Architecture

```mermaid
graph TB
    subgraph "ChatBot Service"
        CB[🤖 ChatBot App]
    end
    
    subgraph "Storage Layers"
        L1[📁 Local Storage<br/>ChatBot/Storage/]
        L2[☁️ ImgBB Cloud<br/>Unlimited Free]
        L3[💾 MongoDB Atlas<br/>512MB Free Tier]
    end
    
    subgraph "Data Types"
        D1[🖼️ Generated Images]
        D2[📎 Uploaded Files]
        D3[💬 Conversations]
        D4[🧠 AI Memory]
    end
    
    CB --> D1
    CB --> D2
    CB --> D3
    CB --> D4
    
    D1 --> L1
    D1 --> L2
    D1 --> L3
    
    D2 --> L1
    D2 --> L3
    
    D3 --> L3
    D4 --> L3
    
    style CB fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style L1 fill:#3B82F6,stroke:#2563EB,color:#fff
    style L2 fill:#EC4899,stroke:#DB2777,color:#fff
    style L3 fill:#10B981,stroke:#059669,color:#fff
```

---

### 6️⃣ Database Connection Flow

```mermaid
graph LR
    A[🤖 ChatBot Service] -->|PyMongo| B[(🍃 MongoDB Atlas<br/>chatbot_db)]
    C[📊 Text2SQL Service] -->|psycopg2| D[(🗄️ PostgreSQL<br/>text2sql_db)]
    C -->|clickhouse-driver| E[(📊 ClickHouse<br/>analytics_db)]
    F[🎙️ Speech2Text] -->|File System| G[📁 Local Storage]
    H[🎨 Stable Diffusion] -->|requests| I[☁️ ImgBB API]
    H -->|File System| G
    
    B -.Backup.-> J[💾 Local JSON]
    D -.Export.-> J
    
    style A fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style C fill:#3B82F6,stroke:#2563EB,color:#fff
    style F fill:#EF4444,stroke:#DC2626,color:#fff
    style H fill:#EC4899,stroke:#DB2777,color:#fff
    style B fill:#10B981,stroke:#059669,color:#fff
    style D fill:#3B82F6,stroke:#2563EB,color:#fff
    style E fill:#F59E0B,stroke:#D97706,color:#fff
```

---

### 7️⃣ MongoDB Collections Overview

```mermaid
graph TB
    subgraph "MongoDB Atlas - chatbot_db"
        C1[conversations<br/>~3,000 docs<br/>7 indexes]
        C2[messages<br/>~45,000 docs<br/>8 indexes]
        C3[chatbot_memory<br/>~5,000 docs<br/>5 indexes]
        C4[uploaded_files<br/>~1,000 docs<br/>4 indexes]
        C5[users<br/>~100 docs<br/>2 indexes]
        C6[user_settings<br/>~100 docs<br/>1 index]
    end
    
    Total[📊 Total Storage<br/>~70 MB<br/>26 Indexes]
    
    C1 --> Total
    C2 --> Total
    C3 --> Total
    C4 --> Total
    C5 --> Total
    C6 --> Total
    
    style C1 fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style C2 fill:#3B82F6,stroke:#2563EB,color:#fff
    style C3 fill:#10B981,stroke:#059669,color:#fff
    style C4 fill:#F59E0B,stroke:#D97706,color:#fff
    style C5 fill:#EC4899,stroke:#DB2777,color:#fff
    style C6 fill:#6366F1,stroke:#4F46E5,color:#fff
    style Total fill:#10B981,stroke:#059669,color:#fff
```

---

### 8️⃣ Data Backup Strategy

```mermaid
graph TB
    A[💾 Production Data] --> B{🔄 Backup Type}
    
    B -->|Daily| C[☁️ MongoDB Atlas<br/>Auto Backup]
    B -->|Weekly| D[📁 Local JSON Export<br/>ChatBot/Storage/]
    B -->|Monthly| E[💿 Full Database Dump<br/>mongodump]
    
    C --> F[📊 Point-in-Time Recovery<br/>24 hours retention]
    D --> G[🔍 Easy Debugging<br/>Human-readable]
    E --> H[💾 Disaster Recovery<br/>Long-term archive]
    
    F --> I[✅ Restore Options]
    G --> I
    H --> I
    
    style A fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style B fill:#6366F1,stroke:#4F46E5,color:#fff
    style C fill:#10B981,stroke:#059669,color:#fff
    style D fill:#3B82F6,stroke:#2563EB,color:#fff
    style E fill:#F59E0B,stroke:#D97706,color:#fff
    style I fill:#10B981,stroke:#059669,color:#fff
```

---

### 9️⃣ Query Performance Optimization

```mermaid
graph LR
    A[📊 Query Request] --> B{🔍 Index Available?}
    
    B -->|Yes| C[⚡ Index Scan<br/>Fast - ms]
    B -->|No| D[🐌 Collection Scan<br/>Slow - seconds]
    
    C --> E[26 Indexes Total]
    
    E --> F1[🔑 Primary: _id]
    E --> F2[📅 Time: created_at]
    E --> F3[👤 User: user_id]
    E --> F4[🏷️ Compound Indexes]
    
    F1 --> G[✅ Query Result]
    F2 --> G
    F3 --> G
    F4 --> G
    D --> H[❌ Slow Performance]
    
    style A fill:#6366F1,stroke:#4F46E5,color:#fff
    style B fill:#F59E0B,stroke:#D97706,color:#fff
    style C fill:#10B981,stroke:#059669,color:#fff
    style D fill:#EF4444,stroke:#DC2626,color:#fff
    style E fill:#8B5CF6,stroke:#7C3AED,color:#fff
    style G fill:#10B981,stroke:#059669,color:#fff
```

---

## 📝 Hướng Dẫn Sử Dụng Diagrams

### Để chụp và đưa vào Word/PowerPoint:

1. **Mở file trên GitHub** (diagrams tự render)
2. **Chụp từng diagram** (Win + Shift + S)
3. **Paste vào document** (Ctrl + V)
4. **Resize** cho phù hợp

### Hoặc export PNG chất lượng cao:

1. Copy code mermaid
2. Mở https://mermaid.live
3. Paste code
4. Click "Download PNG" hoặc "Download SVG"
5. Insert vào Word/PowerPoint

### Kích thước khuyến nghị:
- **ER Diagrams:** 12-14cm width
- **Flow Diagrams:** 10-12cm width  
- **Architecture Diagrams:** 14-16cm width (full page)

---

## 📊 Database Statistics Summary

| Category | MongoDB | PostgreSQL | ClickHouse | Total |
|:---------|:--------|:-----------|:-----------|:------|
| **Collections/Tables** | 6 | 5 | 3 | 14 |
| **Indexes** | 26 | 15+ | 10+ | 51+ |
| **Current Size** | ~70 MB | ~100 MB | ~50 MB | ~220 MB |
| **Estimated (1 year)** | ~500 MB | ~200 MB | ~300 MB | ~1 GB |
| **Documents/Rows** | ~54,200 | ~10,000 | ~50,000 | ~114,200 |

---

<div align="center">

**📐 Database Design Updated: November 11, 2025**

[⬅️ Previous: Sequence Diagrams](03_sequence_diagrams.md) | [Back to Index](README.md) | [➡️ Next: ER Diagram](05_er_diagram.md)

</div>
