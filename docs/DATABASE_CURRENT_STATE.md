# 🗄️ DATABASE CURRENT STATE ANALYSIS

> **Phân tích chi tiết về phương thức lưu trữ dữ liệu hiện tại của hệ thống AI-Assistant**  
> Ngày phân tích: 06/11/2025

---

## 📋 TÓM TẮT TỔNG QUAN

### ❌ **HIỆN TRẠNG: KHÔNG CÓ DATABASE TỔNG HỢP**

Dự án AI-Assistant hiện **KHÔNG sử dụng database truyền thống** (PostgreSQL/MySQL/MongoDB) làm hệ thống lưu trữ chính. Toàn bộ dữ liệu được lưu trữ dưới dạng **file-based system** với các format khác nhau (JSON, JSON Lines, Text files).

### 📊 **QUICK STATS**

| Metric | Value |
|--------|-------|
| **Database Type** | None (File-based) |
| **Total Services** | 5 |
| **Storage Methods** | JSON, JSONL, TXT, Binary files |
| **Centralized Storage** | ❌ None |
| **Backup Strategy** | ❌ Not implemented |
| **Query Capability** | ❌ Limited (file system only) |

---

## 🗂️ CHI TIẾT PHƯƠNG THỨC LƯU TRỮ THEO SERVICE

### 1️⃣ **ChatBot Service**

#### **Phương thức lưu trữ:** File-based JSON
#### **Thư mục:** `ChatBot/Storage/`

```
ChatBot/Storage/
├── conversations/              # Lưu trữ conversations
│   ├── <uuid-1>.json          # Mỗi conversation = 1 file JSON
│   ├── <uuid-2>.json
│   └── <uuid-n>.json
└── images/                     # Uploaded images trong chat
    ├── <filename-1>.jpg
    └── <filename-2>.png
```

#### **Cấu trúc dữ liệu:**
```json
{
  "id": "uuid-string",
  "user_id": null,
  "model": "gemini-1.5-flash",
  "title": "Conversation Title",
  "messages": [
    {
      "role": "user",
      "content": "Hello...",
      "timestamp": "2025-11-06T10:30:00Z",
      "images": []
    },
    {
      "role": "assistant",
      "content": "Response...",
      "timestamp": "2025-11-06T10:30:05Z"
    }
  ],
  "created_at": "2025-11-06T10:30:00Z",
  "updated_at": "2025-11-06T10:35:00Z"
}
```

#### **Ưu điểm:**
- ✅ Đơn giản, dễ implement
- ✅ Không cần database server
- ✅ Dễ debug (đọc file trực tiếp)

#### **Nhược điểm:**
- ❌ Không scale tốt với nhiều users
- ❌ Không thể query across conversations
- ❌ Không có transaction support
- ❌ Khó implement full-text search
- ❌ Backup phức tạp (phải copy toàn bộ thư mục)

---

### 2️⃣ **Text2SQL Service**

#### **Phương thức lưu trữ:** JSON Lines + Text files
#### **Thư mục:** `Text2SQL Services/data/` và `knowledge_base/`

```
Text2SQL Services/
├── data/
│   ├── dataset_base.jsonl         # Base SQL examples
│   ├── eval.jsonl                 # Evaluation dataset
│   ├── dataset_clickhouse.jsonl   # ClickHouse specific
│   └── connections/               # Saved DB connections
│       ├── connection_1.json
│       └── connection_2.json
└── knowledge_base/
    └── memory/
        ├── memory_table1.txt      # Learned SQL per table
        ├── memory_table2.txt
        └── memories_01+02.txt     # Multi-table memories
```

#### **Cấu trúc Knowledge Base (JSONL):**
```jsonl
{"question": "Show monthly sales", "sql": "SELECT DATE_FORMAT(date, '%Y-%m') as month, SUM(amount) FROM sales GROUP BY month", "database_type": "clickhouse"}
{"question": "Top 10 customers", "sql": "SELECT customer_id, SUM(total) as revenue FROM orders GROUP BY customer_id ORDER BY revenue DESC LIMIT 10", "database_type": "clickhouse"}
```

#### **Cấu trúc Memory Files (TXT):**
```text
# Memory for table: users
# Last updated: 2025-11-05

Q: How many users registered today?
SQL: SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURDATE()

Q: Find active users
SQL: SELECT * FROM users WHERE is_active = 1

---
```

#### **Ưu điểm:**
- ✅ JSONL dễ append (thêm dòng mới)
- ✅ Text files dễ đọc và edit
- ✅ Git-friendly (track changes)
- ✅ Lightweight

#### **Nhược điểm:**
- ❌ Không có indexing
- ❌ Full scan khi search
- ❌ Không track usage statistics
- ❌ Không có versioning
- ❌ Duplicate detection khó khăn

---

### 3️⃣ **Speech2Text Service**

#### **Phương thức lưu trữ:** Output files only (không lưu metadata)
#### **Thư mục:** `Speech2Text Services/app/data/`

```
Speech2Text Services/app/data/
├── audio/                      # Processed audio files
│   ├── original/
│   └── processed/
└── result/
    ├── raw/                    # Raw transcripts
    │   └── audio_001.txt
    ├── dual/                   # Fusion transcripts (2 models)
    │   └── audio_001.txt
    └── gemini/                 # AI-cleaned transcripts
        └── audio_001.txt
```

#### **Cấu trúc Transcript (TXT):**
```text
[Speaker 1] Hello everyone, welcome to the meeting.
[Speaker 2] Thank you for having me.
[Speaker 1] Let's start with the agenda...

---
Metadata:
- Duration: 05:32
- Language: English
- Speakers: 2
- Model: Whisper Large V3
```

#### **Ưu điểm:**
- ✅ Simple output format
- ✅ Human-readable

#### **Nhược điểm:**
- ❌ Không lưu metadata structured
- ❌ Không track processing history
- ❌ Không link với user/conversation
- ❌ Không có speaker analytics
- ❌ Không reuse transcripts

---

### 4️⃣ **Document Intelligence Service**

#### **Phương thức lưu trữ:** File storage only (no persistent metadata)
#### **Thư mục:** `Document Intelligence Service/uploads/` và `output/`

```
Document Intelligence Service/
├── uploads/                    # Original uploaded files
│   ├── document_001.pdf
│   └── document_002.png
└── output/                     # Processed results
    ├── ocr_results/
    │   └── document_001.json   # OCR text
    └── analysis/
        └── document_001.json   # AI analysis
```

#### **Cấu trúc OCR Result (JSON):**
```json
{
  "filename": "document_001.pdf",
  "pages": 5,
  "ocr_text": "Full extracted text...",
  "document_type": "invoice",
  "confidence": 0.95,
  "extracted_fields": {
    "invoice_number": "INV-001",
    "date": "2025-11-06",
    "total": 1500.00
  },
  "processing_time_ms": 3500,
  "timestamp": "2025-11-06T10:00:00Z"
}
```

#### **Ưu điểm:**
- ✅ Flexible JSON structure
- ✅ Easy to process

#### **Nhược điểm:**
- ❌ Không track document history
- ❌ Không link với users
- ❌ Không search across documents
- ❌ Không có analytics
- ❌ Duplicate detection không có

---

### 5️⃣ **Stable Diffusion (Image Generation)**

#### **Phương thức lưu trữ:** Image files only
#### **Thư mục:** `stable-diffusion-webui/outputs/`

```
stable-diffusion-webui/outputs/
└── txt2img-images/
    └── 2025-11-06/
        ├── 00001-1234567890.png
        ├── 00002-1234567891.png
        └── ...
```

#### **Metadata trong filename:**
```
Format: {index}-{seed}.png
Example: 00001-1234567890.png
```

#### **Nhược điểm:**
- ❌ Metadata không persistent (chỉ trong EXIF)
- ❌ Không track prompt history
- ❌ Không link với conversation
- ❌ Không track LoRA usage
- ❌ Không có generation analytics

---

## 🔌 DATABASE CLIENT SUPPORT (Text2SQL)

### **Supported Target Databases:**

Text2SQL service hỗ trợ **kết nối đến** các external databases sau:

| Database | Status | Connection Method |
|----------|--------|------------------|
| **ClickHouse** | ✅ Implemented | clickhouse-driver |
| **MongoDB** | ✅ Implemented | pymongo |
| **PostgreSQL** | 🟡 Planned | psycopg2 |
| **MySQL** | 🟡 Planned | mysql-connector |
| **SQL Server** | 🟡 Planned | pyodbc |

⚠️ **LƯU Ý:** Đây chỉ là **TARGET databases** để generate SQL queries, **KHÔNG PHẢI** database lưu trữ dữ liệu của dự án.

---

## 📊 SO SÁNH: FILE-BASED vs DATABASE

### **Current State (File-based):**

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Setup Complexity** | ⭐⭐⭐⭐⭐ | Very easy |
| **Query Performance** | ⭐ | Full file scan |
| **Scalability** | ⭐ | Poor with many users |
| **Data Integrity** | ⭐⭐ | No ACID guarantees |
| **Backup** | ⭐⭐ | Manual file copy |
| **Analytics** | ⭐ | Very limited |
| **Multi-user** | ⭐ | File locking issues |
| **Search** | ⭐ | Grep-based only |

**Overall:** ⭐⭐ (2/5) - Good for prototype, not for production

---

### **Proposed State (PostgreSQL):**

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Setup Complexity** | ⭐⭐⭐ | Need DB server |
| **Query Performance** | ⭐⭐⭐⭐⭐ | Indexed queries |
| **Scalability** | ⭐⭐⭐⭐⭐ | Handles millions of rows |
| **Data Integrity** | ⭐⭐⭐⭐⭐ | ACID compliant |
| **Backup** | ⭐⭐⭐⭐⭐ | pg_dump, PITR |
| **Analytics** | ⭐⭐⭐⭐⭐ | SQL aggregations |
| **Multi-user** | ⭐⭐⭐⭐⭐ | Connection pooling |
| **Search** | ⭐⭐⭐⭐⭐ | Full-text, JSONB |

**Overall:** ⭐⭐⭐⭐⭐ (5/5) - Production ready

---

## 🚨 VẤN ĐỀ HIỆN TẠI

### **1. Data Consistency Issues**

```
❌ Không có referential integrity
   - Conversation có thể reference user không tồn tại
   - Image có thể orphaned (không link với conversation)
   
❌ Không có transaction support
   - Crash khi đang save → data corrupted
   - Partial updates → inconsistent state
```

### **2. Performance Issues**

```
❌ Search toàn bộ conversations:
   - Phải đọc TỪNG FILE JSON (O(n))
   - Slow với 1000+ conversations
   
❌ Analytics queries:
   - Không thể: "Top 10 users by message count"
   - Không thể: "Monthly conversation trends"
```

### **3. Scalability Issues**

```
❌ File system limitations:
   - Too many files trong 1 folder (>10,000) → slow
   - Concurrent access → file locking
   
❌ Memory issues:
   - Load toàn bộ conversation vào RAM
   - Không có pagination
```

### **4. Data Loss Risks**

```
❌ No backup strategy:
   - Manual copy only
   - No point-in-time recovery
   
❌ No versioning:
   - Overwrite file → lost previous version
   - No audit trail
```

### **5. Feature Limitations**

```
❌ Không thể implement:
   - Full-text search across conversations
   - User analytics dashboard
   - Conversation sharing (multi-user access)
   - Real-time collaboration
   - Advanced filtering/sorting
```

---

## 📈 DATA GROWTH ESTIMATES (Current System)

### **Assumptions:**
- 1,000 active users
- Daily usage for 1 year

### **Growth Projection:**

| Service | Files/Year | Size/Year | Issues |
|---------|-----------|-----------|--------|
| **ChatBot** | 120,000 JSON files | 2 GB | Too many files |
| **Text2SQL** | 1 JSONL file | 50 MB | File gets huge |
| **Speech2Text** | 24,000 TXT files | 3 GB | No search |
| **Documents** | 60,000 files | 800 GB | Storage expensive |
| **Images** | 120,000 PNG files | 300 GB | No metadata |

**Total:** ~1.1 TB/year

### **Problems:**
- ❌ `ChatBot/Storage/conversations/` folder: 120,000 files (very slow to list)
- ❌ `dataset_base.jsonl`: 50 MB single file (slow to parse)
- ❌ Backup time: Several hours (copy 1.1 TB)

---

## 🎯 DATABASE SCHEMA (DESIGNED - NOT IMPLEMENTED)

### **ER Diagram Overview:**

File `diagram/05_er_diagram.md` đã thiết kế sẵn database schema với **21 tables**:

#### **Core Tables:**
1. `USERS` - User accounts
2. `CONVERSATIONS` - Chat conversations
3. `MESSAGES` - Chat messages
4. `CHATBOT_MEMORY` - Saved Q&A

#### **Text2SQL Tables:**
5. `SQL_KNOWLEDGE_BASE` - Learned SQL patterns
6. `QUERY_HISTORY` - Query execution logs
7. `DATABASE_CONNECTIONS` - Saved connections
8. `DATABASE_SCHEMAS` - Cached schemas

#### **Document Tables:**
9. `PROCESSED_DOCUMENTS` - Uploaded documents
10. `DOCUMENT_ANALYSIS` - Analysis results
11. `DOCUMENT_TEMPLATES` - OCR templates

#### **Speech2Text Tables:**
12. `TRANSCRIPTIONS` - Audio transcriptions
13. `SPEAKERS` - Speaker diarization

#### **Image Generation Tables:**
14. `IMAGE_GENERATIONS` - Generated images
15. `LORA_MODELS` - Available LoRA models

#### **System Tables:**
16. `USER_API_KEYS` - API authentication
17. `UPLOADED_FILES` - File metadata
18. `SYSTEM_LOGS` - Application logs
19. `API_USAGE` - API metrics
20. `SYSTEM_METRICS` - Performance metrics

### **Total Relationships:** 23 (1:N, M:N)

⚠️ **STATUS:** Schema thiết kế hoàn chỉnh, **CHƯA IMPLEMENT**

---

## 🔄 MIGRATION STRATEGY (PROPOSED)

### **Phase 1: Database Setup (Week 1)**

```bash
# Install PostgreSQL 14+
apt-get install postgresql-14

# Create database
createdb ai_assistant_db

# Install Python packages
pip install sqlalchemy alembic psycopg2-binary
```

### **Phase 2: Data Migration (Week 2-3)**

```python
# Example: Migrate ChatBot conversations
import json
from pathlib import Path
from sqlalchemy import create_engine
from models import Conversation, Message

engine = create_engine('postgresql://user:pass@localhost/ai_assistant_db')

# Read JSON files
for json_file in Path('ChatBot/Storage/conversations/').glob('*.json'):
    with open(json_file) as f:
        data = json.load(f)
    
    # Create Conversation record
    conversation = Conversation(
        id=data['id'],
        user_id=data.get('user_id'),
        model=data['model'],
        title=data['title'],
        created_at=data['created_at']
    )
    
    # Create Message records
    for msg in data['messages']:
        message = Message(
            conversation_id=conversation.id,
            role=msg['role'],
            content=msg['content'],
            created_at=msg['timestamp']
        )
        session.add(message)
    
    session.add(conversation)

session.commit()
```

### **Phase 3: Code Refactoring (Week 3-4)**

```python
# Before (File-based):
def load_conversation(conv_id):
    with open(f'Storage/conversations/{conv_id}.json') as f:
        return json.load(f)

# After (Database):
def load_conversation(conv_id):
    return db.session.query(Conversation)\
        .filter_by(id=conv_id)\
        .options(joinedload(Conversation.messages))\
        .first()
```

### **Phase 4: Testing & Rollout (Week 4)**

- ✅ Unit tests
- ✅ Integration tests
- ✅ Load testing
- ✅ Backup testing
- ✅ Rollback plan

---

## 💰 COST-BENEFIT ANALYSIS

### **Current System (File-based):**

**Costs:**
- ✅ $0 for database
- ✅ Developer time: Low (already implemented)

**Benefits:**
- ✅ Simple
- ✅ No dependencies

**Hidden Costs:**
- ❌ Slow performance → bad UX
- ❌ Cannot implement advanced features
- ❌ Manual backup → risk of data loss
- ❌ Hard to debug issues

---

### **Proposed System (PostgreSQL):**

**Costs:**
- 💰 Database hosting: $20-50/month (managed service)
- 💰 Developer time: 4 weeks implementation
- 💰 Learning curve: SQLAlchemy, Alembic

**Benefits:**
- ✅ 100x faster queries
- ✅ ACID guarantees
- ✅ Automatic backups
- ✅ Advanced features possible:
  - Full-text search
  - Analytics dashboard
  - Real-time collaboration
  - API rate limiting
  - User management

**ROI:** Break-even after 3 months of production use

---

## 🎯 RECOMMENDED DATABASE: PostgreSQL 14+

### **Why PostgreSQL?**

| Feature | PostgreSQL | MySQL | MongoDB |
|---------|-----------|-------|---------|
| **JSONB support** | ✅ Native | ❌ Limited | ✅ Native |
| **Full-text search** | ✅ Built-in | ✅ Built-in | ⚠️ Text indexes |
| **ACID compliance** | ✅ Yes | ✅ Yes | ⚠️ Depends |
| **Array types** | ✅ Native | ❌ No | ✅ Native |
| **Window functions** | ✅ Advanced | ✅ Basic | ❌ No |
| **Partitioning** | ✅ Native | ✅ Native | ✅ Sharding |
| **Open source** | ✅ MIT-like | ⚠️ GPL/Commercial | ⚠️ SSPL |
| **Python support** | ✅ Excellent | ✅ Good | ✅ Excellent |

**Winner:** ✅ **PostgreSQL** - Best balance of features and flexibility

---

## 📚 REFERENCES

### **Design Documents:**
- [04_database_design.md](04_database_design.md) - Thiết kế database chi tiết
- [05_er_diagram.md](05_er_diagram.md) - ER Diagram với 21 tables
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Cấu trúc dự án hiện tại

### **Migration Guides:**
- [PostgreSQL Migration Best Practices](https://www.postgresql.org/docs/14/migration.html)
- [SQLAlchemy Tutorial](https://docs.sqlalchemy.org/en/14/tutorial/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

---

## ✅ NEXT STEPS (RECOMMENDED)

### **Immediate (Week 1):**
1. ✅ Review database design (`04_database_design.md`)
2. ✅ Setup local PostgreSQL instance
3. ✅ Install SQLAlchemy + Alembic
4. ✅ Create initial migration

### **Short-term (Month 1):**
1. ✅ Migrate ChatBot service first (highest impact)
2. ✅ Implement user authentication
3. ✅ Add conversation sharing
4. ✅ Implement backup strategy

### **Long-term (Quarter 1):**
1. ✅ Migrate all services to database
2. ✅ Implement analytics dashboard
3. ✅ Add full-text search
4. ✅ Setup monitoring (Grafana)

---

## 🎬 CONCLUSION

### **Current State:**
- ❌ **File-based storage** (JSON, JSONL, TXT)
- ❌ **No centralized database**
- ❌ **Limited scalability**
- ❌ **No advanced features**

### **Proposed State:**
- ✅ **PostgreSQL 14+** with 21 tables
- ✅ **SQLAlchemy ORM**
- ✅ **Alembic migrations**
- ✅ **Production-ready architecture**

### **Recommendation:**
🚀 **MIGRATE TO POSTGRESQL** trong vòng 4 tuần để cải thiện:
- Performance (100x faster)
- Reliability (ACID guarantees)
- Features (analytics, search, collaboration)
- Maintainability (easier to debug and scale)

---

<div align="center">

**📅 Document Date:** November 6, 2025  
**👤 Author:** AI-Assistant Analysis  
**🔄 Status:** Current State Analysis Complete

---

[📖 View Database Design](04_database_design.md) | [📊 View ER Diagram](05_er_diagram.md) | [🏠 Back to Docs](README.md)

</div>
