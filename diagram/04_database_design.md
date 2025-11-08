# 4️⃣ DATABASE DESIGN

> **Thiết kế cơ sở dữ liệu cho hệ thống AI-Assistant**  
> Đề xuất migrate từ file-based storage sang PostgreSQL

---

## 📋 Tổng quan

### Hiện trạng:
❌ **Không có database tập trung**  
- ChatBot: JSON files trong `ChatBot/Storage/`
- Text2SQL: JSON Lines trong `Text2SQL Services/data/knowledge_base/`
- Speech2Text: Output files only
- Stable Diffusion: Image files only

### Đề xuất:
✅ **PostgreSQL 14+** - Centralized database  
✅ **SQLAlchemy ORM** - Python integration  
✅ **Alembic** - Database migrations  
✅ **Redis** - Caching layer  

---

## 🗄️ Database Schema

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
    model VARCHAR(50) NOT NULL, -- 'gemini-2.0', 'gpt-4', etc.
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
