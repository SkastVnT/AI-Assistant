# 5️⃣ ENTITY RELATIONSHIP (ER) DIAGRAM – FULL SYSTEM (MongoDB + PostgreSQL + Services)

> "Toàn cảnh cấu trúc dữ liệu & quan hệ liên dịch vụ"  
> Accurate production-aligned unified ER view (MongoDB + PostgreSQL + External Pipelines) – November 2025

---

## 🧭 HIERARCHY OVERVIEW

Level 0 (Root): Unified cross-service entities & data domains  
Level 1: Core domains (User Identity, ChatBot Context, Text2SQL Knowledge, Media Generation & Storage, Speech2Text Pipeline, Observability & Ops)  
Level 2: Collection/Table details per domain  
Level 3: Metadata & relationship patterns (embeddings, images, memory, history)

---

## 🌐 LEVEL 0 — FULL SYSTEM UNIFIED ER

```mermaid
erDiagram
    %% USER & IDENTITY
    USERS ||--o| USER_SETTINGS : "1:1 prefs"
    USERS ||--o{ CONVERSATIONS : "chat sessions"
    USERS ||--o{ DATABASE_CONNECTIONS : "manages DB"
    USERS ||--o{ QUERY_HISTORY : "executes queries"

    %% CHATBOT CORE
    CONVERSATIONS ||--|{ MESSAGES : "chat stream"
    CONVERSATIONS ||--o{ CHATBOT_MEMORY : "context mem"
    CONVERSATIONS ||--o{ UPLOADED_FILES : "attached files"
    MESSAGES ||--o{ MESSAGE_IMAGES : "embedded imgs (virtual)"

    %% TEXT2SQL DOMAIN
    DATABASE_CONNECTIONS ||--o{ DATABASE_SCHEMAS : "caches schema"
    SQL_KNOWLEDGE_BASE ||--o{ QUERY_HISTORY : "matched"

    %% MEDIA & GENERATION
    MESSAGES ||--o{ IMAGE_METADATA : "gen params"
    IMAGE_METADATA ||--o{ LORA_REFERENCES : "style refs"

    %% SPEECH 2 TEXT PIPELINE (LOGICAL)
    SPEECH_JOBS ||--o{ SPEECH_SEGMENTS : "diarization"
    SPEECH_JOBS ||--o{ TRANSCRIPTS : "final text"

    %% OBSERVABILITY / OPS
    USERS ||--o{ API_USAGE : "quota & usage"
    USERS ||--o{ SYSTEM_LOGS : "activity"
    SYSTEM_LOGS ||--o{ SYSTEM_METRICS : "aggregated"

    %% NOTES (NoSQL vs SQL)
    USERS { ObjectId _id PK }
    USER_SETTINGS { ObjectId _id PK }
    CONVERSATIONS { ObjectId _id PK }
    MESSAGES { ObjectId _id PK }
    CHATBOT_MEMORY { ObjectId _id PK }
    UPLOADED_FILES { ObjectId _id PK }

    DATABASE_CONNECTIONS { int id PK }
    DATABASE_SCHEMAS { int id PK }
    SQL_KNOWLEDGE_BASE { int id PK }
    QUERY_HISTORY { int id PK }

    API_USAGE { ObjectId _id PK }
    SYSTEM_LOGS { ObjectId _id PK }
    SYSTEM_METRICS { ObjectId _id PK }

    %% Virtual / Logical Entities (Not persisted 1:1)
    MESSAGE_IMAGES { string kind }
    IMAGE_METADATA { string kind }
    LORA_REFERENCES { string kind }
    SPEECH_JOBS { string storage }
    SPEECH_SEGMENTS { string format }
    TRANSCRIPTS { string format }
```

> Legend: MongoDB (ObjectId) • PostgreSQL (int PK) • Virtual (derived/embedded) • Filesystem/External (file+json)

---

## 🟩 LEVEL 1A — USER & IDENTITY DOMAIN

```mermaid
erDiagram
    USERS ||--o| USER_SETTINGS : "1:1 unique"
    USERS ||--o{ CONVERSATIONS : "owns"
    USERS ||--o{ DATABASE_CONNECTIONS : "db creds"
    USERS ||--o{ QUERY_HISTORY : "queries"
    USERS ||--o{ API_USAGE : "rate/quota"
    USERS ||--o{ SYSTEM_LOGS : "events"

    USERS {
        ObjectId _id PK
        string username UK
        string email UK
        string password_hash
        object profile
        bool is_active
        datetime created_at
        datetime last_login_at
    }

    USER_SETTINGS {
        ObjectId _id PK
        string user_id UK
        object settings
        datetime created_at
        datetime updated_at
    }

    API_USAGE {
        ObjectId _id PK
        string user_id
        number requests_today
        number tokens_today
        datetime last_reset
        datetime updated_at
    }

    SYSTEM_LOGS {
        ObjectId _id PK
        string user_id
        string action
        string service
        object context
        datetime created_at
    }
```

---

## 💬 LEVEL 1B — CHATBOT (MongoDB)

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : "1:N"
    CONVERSATIONS ||--|{ MESSAGES : "chronological"
    CONVERSATIONS ||--o{ CHATBOT_MEMORY : "optional"
    CONVERSATIONS ||--o{ UPLOADED_FILES : "optional"
    MESSAGES ||--o{ MESSAGE_IMAGES : "embedded[]"

    CONVERSATIONS {
        ObjectId _id PK
        string user_id
        string model
        string title
        string system_prompt
        number total_messages
        number total_tokens
        boolean is_archived
        object metadata
        datetime created_at
        datetime updated_at
    }

    MESSAGES {
        ObjectId _id PK
        ObjectId conversation_id
        string role
        string content
        array images
        array files
        object metadata
        number version
        ObjectId parent_message_id
        boolean is_edited
        boolean is_stopped
        datetime created_at
    }

    CHATBOT_MEMORY {
        ObjectId _id PK
        string user_id
        ObjectId conversation_id
        string memory_type
        string content
        number importance
        array tags
        string context
        object metadata
        datetime created_at
        datetime updated_at
        datetime expires_at
    }

    UPLOADED_FILES {
        ObjectId _id PK
        string user_id
        ObjectId conversation_id
        string file_name
        string file_path
        string file_type
        number file_size
        string mime_type
        string analysis_result
        object metadata
        datetime created_at
    }
```

---

## 🧠 LEVEL 2A — MESSAGE IMAGES (Embedded & Storage Flow)

```mermaid
graph TB
    MSG[Message Doc] --> IMGS{Images Array}
    IMGS --> IMG1[Image Object]
    IMG1 --> LOCAL[url]
    IMG1 --> CLOUD[cloud_url]
    IMG1 --> DEL[delete_url]
    IMG1 --> CAP[caption]
    IMG1 --> SIZE[size]
    IMG1 --> MIME[mime_type]
    IMG1 --> GEN[generated]
    IMG1 --> SRC[service]

    subgraph STORAGE
        LOCAL -.-> LOCAL_FS[Local Disk]
        CLOUD -.-> IMGBB[ImgBB CDN]
        DEL -.-> IMGBB_API[ImgBB Delete API]
    end
```

---

## 🗃️ LEVEL 1C — TEXT2SQL (PostgreSQL)

```mermaid
erDiagram
  USERS ||--o{ DATABASE_CONNECTIONS : "manages"
  DATABASE_CONNECTIONS ||--o{ DATABASE_SCHEMAS : "caches"
  USERS ||--o{ QUERY_HISTORY : "executes"
  DATABASE_CONNECTIONS ||--o{ QUERY_HISTORY : "via connection"
  SQL_KNOWLEDGE_BASE ||--o{ QUERY_HISTORY : "matched"

  DATABASE_CONNECTIONS {
    int id PK
    int user_id FK
    string name
    string type
    string host
    int port
  }

  DATABASE_SCHEMAS {
    int id PK
    int connection_id FK
    json schema_json
    string schema_hash UK
  }

  SQL_KNOWLEDGE_BASE {
    int id PK
    text question
    text sql_query
    string database_type
    string schema_hash
  }

  QUERY_HISTORY {
    int id PK
    int user_id FK
    int connection_id FK
    text question
    text sql_query
    int execution_time_ms
    string status
    int kb_match_id FK
  }
```

---

## 🎙️ LEVEL 1D — SPEECH2TEXT PIPELINE (Logical Model)

```mermaid
graph LR
    AUDIO_RAW[Audio File WAV] --> JOB[Speech Job JSON]
    JOB --> DIAR[Diarization Segments]
    DIAR --> SEG1[Segment start|end|speaker|text]
    JOB --> TRANS[Transcript TXT]
    TRANS --> REFUSE[Linked to Conversation]
    REFUSE -. optional mapping .- CONVERSATIONS

    style AUDIO_RAW fill:#37474F,stroke:#263238,color:#fff
    style JOB fill:#546E7A,stroke:#37474F,color:#fff
    style DIAR fill:#78909C,stroke:#455A64,color:#fff
    style SEG1 fill:#90A4AE,stroke:#546E7A
    style TRANS fill:#607D8B,stroke:#37474F,color:#fff
    style REFUSE fill:#90CAF9,stroke:#1976D2,color:#000
```

---

## 🖼️ LEVEL 1E — IMAGE GENERATION (Stable Diffusion + Metadata)

```mermaid
erDiagram
    MESSAGES ||--o{ IMAGE_METADATA : "generation meta"
    IMAGE_METADATA ||--o{ LORA_REFERENCES : "LoRA styles"

    IMAGE_METADATA {
        string model
        string prompt
        string negative_prompt
        number num_images
        number generation_time_ms
        number cfg_scale
        number steps
        number width
        number height
        string sampler
    }

    LORA_REFERENCES {
        string name
        string version
        number weight
        string source_url
    }
```

---

## 📊 LEVEL 2B — OBSERVABILITY & METRICS

```mermaid
erDiagram
    SYSTEM_LOGS ||--o{ SYSTEM_METRICS : "aggregates"

    SYSTEM_LOGS {
        ObjectId _id PK
        string user_id
        string action
        string service
        object context
        datetime created_at
    }

    SYSTEM_METRICS {
        ObjectId _id PK
        string period "hour/day"
        number total_requests
        number total_tokens
        number avg_latency_ms
        datetime collected_at
    }
```

---

## 🔗 LEVEL 2C — CROSS-SERVICE IDENTITY MAPPING

```mermaid
graph LR
  U_MDB((MongoDB users)) -. session/user mapping .- U_SQL[(PostgreSQL users)]
  U_MDB --> CONV_MDB[conversations]
  U_SQL --> CONN_SQL[database_connections]
  CONV_MDB -. generated queries context .- QUERY_HISTORY
  QUERY_HISTORY -. knowledge match .- SQL_KNOWLEDGE_BASE
```

---

## 🧩 RELATIONSHIP PATTERNS SUMMARY

| Pattern | Count | Example |
|---------|-------|---------|
| 1:1 | 1 | users → user_settings |
| 1:N (mandatory) | 1 | conversations → messages |
| 1:N (optional) | 6 | conversations → memory/files, user → conversations, user → query_history, user → database_connections, logs → metrics |
| M:N (implicit via arrays) | 2 | messages ↔ images, messages ↔ lora_refs |
| Virtual / Embedded | 4 | images[], metadata, lora_references, profile/settings |
| Cross-DB Mapping | 1 | Mongo users ↔ SQL users |

---

## 🚀 INDEX & PERFORMANCE SNAPSHOT

| Area | Key Index Strategy | Notes |
|------|--------------------|-------|
| Mongo Conversations | user_id, created_at desc, compound(user_id+created_at) | Recent session dashboard |
| Mongo Messages | conversation_id, created_at, images.cloud_url (sparse) | Image lookups / streaming |
| Mongo Memory | conversation_id TTL optional | Expirable context |
| SQL Query History | user_id, connection_id, status | Reporting & audit |
| SQL Knowledge Base | schema_hash, database_type | Semantic retrieval base |
| Logs | service, created_at | Filter by service/time |

Optimization: prune old messages, archive conversations, externalize large blobs (images) to ImgBB.

---

## 🧪 FUTURE EXTENSIONS

| Feature | Data Impact | Suggested Model |
|---------|-------------|-----------------|
| Agent Tool Invocations | Medium | tool_calls collection (Mongo) |
| Vector Embeddings | High | embeddings collection + external vector DB (e.g., Chroma) |
| Billing & Subscription | Medium | billing_plans (SQL) + usage_rollups (Mongo) |
| Real-time Events | Medium | websocket_events (ephemeral) |

---

## 🔚 NAVIGATION

[⬅️ ER MongoDB Only](05_er_diagram_mongodb.md) | [Database Design](04_database_design.md) | [Component Diagram](06_component_diagram.md) | [🏠 Index](README.md)

---

**✅ FULL SYSTEM ER DIAGRAM COMPLETE**  
Canonical high-level + modular branch diagrams for Word-friendly export.
