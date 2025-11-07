# Database Package

SQLAlchemy database models, utilities, and migration scripts for AI-Assistant.

## 📁 Directory Structure

```
database/
├── __init__.py              # Package exports
├── models/                  # SQLAlchemy ORM models
│   ├── __init__.py
│   ├── base.py             # Base model classes
│   ├── user.py             # User model
│   └── chatbot.py          # ChatBot models (Conversation, Message, Memory, UploadedFile)
├── utils/                   # Database utilities
│   ├── __init__.py
│   ├── engine.py           # Database engine & session management
│   └── test_connection.py # Connection test script
├── scripts/                 # Migration & maintenance scripts
│   ├── init.sql            # PostgreSQL initialization
│   ├── setup_database.py  # Database setup & seeding
│   ├── analyze_existing_data.py
│   ├── migrate_conversations.py
│   ├── validate_migration.py
│   └── rollback_migration.py
└── pgadmin/                 # pgAdmin configuration
    └── servers.json
```

---

## 🗄️ Database Models

### User Model (`user.py`)

```python
from database.models import User

user = User(
    username="john_doe",
    email="john@example.com",
    full_name="John Doe",
    is_active=True,
    is_admin=False
)
```

**Fields:**
- `id` (Integer, PK)
- `username` (String, unique, indexed)
- `email` (String, unique, indexed)
- `full_name` (String)
- `is_active` (Boolean)
- `is_admin` (Boolean)
- `last_login` (DateTime)
- `created_at`, `updated_at` (auto-managed)

**Relationships:**
- `conversations` → One-to-many
- `memories` → One-to-many
- `uploaded_files` → One-to-many

### Conversation Model (`chatbot.py`)

```python
from database.models import Conversation

conversation = Conversation(
    user_id=1,
    title="My Conversation",
    tags=["work", "python"],
    is_pinned=True
)
```

**Fields:**
- `id` (Integer, PK)
- `conversation_uuid` (UUID, unique)
- `user_id` (Integer, FK → users)
- `title` (String)
- `tags` (Array[String])
- `template` (String, optional)
- `is_archived` (Boolean)
- `is_pinned` (Boolean)
- `parent_conversation_id` (Integer, FK → conversations)
- `metadata` (JSON)
- `message_count` (Integer)

**Relationships:**
- `user` → Many-to-one
- `messages` → One-to-many
- `memories` → One-to-many
- `uploaded_files` → One-to-many
- `branches` → Self-referential

### Message Model (`chatbot.py`)

```python
from database.models import Message, MessageRole

message = Message(
    conversation_id=1,
    role=MessageRole.USER,
    content="Hello, AI!",
    sequence_number=1
)
```

**Fields:**
- `id` (Integer, PK)
- `conversation_id` (Integer, FK → conversations)
- `role` (Enum: USER, ASSISTANT, SYSTEM)
- `content` (Text)
- `model` (String, optional)
- `sequence_number` (Integer)
- `images` (JSON array)
- `files` (JSON array)
- `is_edited` (Boolean)
- `original_message_id` (Integer, FK → messages)
- `metadata` (JSON)

**Relationships:**
- `conversation` → Many-to-one
- `edited_versions` → Self-referential

### ChatbotMemory Model (`chatbot.py`)

```python
from database.models import ChatbotMemory

memory = ChatbotMemory(
    user_id=1,
    question="What is Python?",
    answer="Python is a programming language...",
    importance=8,
    tags=["programming", "python"]
)
```

**Fields:**
- `id` (Integer, PK)
- `user_id` (Integer, FK → users)
- `conversation_id` (Integer, FK → conversations, optional)
- `question` (Text)
- `answer` (Text)
- `importance` (Integer, 1-10)
- `tags` (Array[String])
- `metadata` (JSON)

### UploadedFile Model (`chatbot.py`)

```python
from database.models import UploadedFile

file = UploadedFile(
    user_id=1,
    conversation_id=1,
    filename="document.pdf",
    file_path="/uploads/document.pdf",
    file_type="application/pdf",
    file_size=1024000
)
```

**Fields:**
- `id` (Integer, PK)
- `user_id` (Integer, FK → users)
- `conversation_id` (Integer, FK → conversations)
- `filename` (String)
- `file_path` (String)
- `file_type` (String)
- `file_size` (Integer)
- `analysis_result` (JSON)
- `is_processed` (Boolean)

---

## 🔧 Database Utilities

### Initialize Database Engine

```python
from database.utils import init_db

# Initialize with default settings
engine = init_db()

# Initialize with custom URL
engine = init_db(
    database_url="postgresql://user:pass@localhost/db",
    echo=True,
    pool_size=10
)
```

### Session Management

**Method 1: Context Manager**
```python
from database.utils import get_session
from database.models import User

with get_session() as session:
    user = session.query(User).first()
    print(user.username)
    # Auto-commit on success
```

**Method 2: SessionManager**
```python
from database.utils import SessionManager
from database.models import User

with SessionManager(auto_commit=True) as session:
    user = User(username="test", email="test@example.com")
    session.add(user)
    # Auto-commit on exit
```

**Method 3: FastAPI Dependency**
```python
from fastapi import Depends
from database.utils import get_db

@app.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

### Test Database Connection

```powershell
# Test connection and create tables
python database/utils/test_connection.py

# This will:
# - Test PostgreSQL connection
# - Show database info
# - Create all tables
# - Verify table structure
# - Test CRUD operations
```

---

## 📜 Migration Scripts

### 1. Setup Database

```powershell
# Initialize database with tables and seed data
python database/scripts/setup_database.py

# Options:
# - Create all tables
# - Seed admin user
# - Seed demo data
# - Verify setup
```

### 2. Analyze Existing Data

```powershell
# Analyze JSON conversation files
python database/scripts/analyze_existing_data.py

# Output:
# - Total files found
# - Date range
# - Total messages
# - Message type breakdown
# - Average messages per conversation
```

### 3. Migrate Conversations

```powershell
# Dry-run (test migration without saving)
python database/scripts/migrate_conversations.py --dry-run

# Actual migration
python database/scripts/migrate_conversations.py

# Options:
# --source-dir: JSON files directory (default: ChatBot/Storage/conversations/)
# --batch-size: Batch size for processing (default: 100)
# --dry-run: Test without saving
```

### 4. Validate Migration

```powershell
# Validate migrated data
python database/scripts/validate_migration.py

# Checks:
# - Record counts match
# - No duplicate conversations
# - All messages have valid roles
# - All conversations have owners
```

### 5. Rollback Migration

```powershell
# Rollback migration (⚠️ deletes data)
python database/scripts/rollback_migration.py

# Options:
# --restore-backup: Restore JSON backup (if exists)
# --confirm: Skip confirmation prompt
```

---

## 🚀 Quick Start

### 1. Start Docker Services

```powershell
# Start PostgreSQL + Redis
docker-compose up -d postgres redis pgadmin
```

### 2. Setup Database

```powershell
# Set environment variable
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/ai_assistant"

# Run setup
python database/scripts/setup_database.py
```

### 3. Use in Your Code

```python
from database import init_db, get_session
from database.models import User, Conversation, Message

# Initialize database
init_db()

# Create user and conversation
with get_session() as session:
    # Create user
    user = User(
        username="alice",
        email="alice@example.com",
        full_name="Alice Smith"
    )
    session.add(user)
    session.flush()  # Get user.id
    
    # Create conversation
    conv = Conversation(
        user_id=user.id,
        title="My First Conversation"
    )
    session.add(conv)
    session.flush()
    
    # Add messages
    from database.models import MessageRole
    
    messages = [
        Message(
            conversation_id=conv.id,
            role=MessageRole.USER,
            content="Hello!",
            sequence_number=1
        ),
        Message(
            conversation_id=conv.id,
            role=MessageRole.ASSISTANT,
            content="Hi! How can I help?",
            sequence_number=2
        )
    ]
    session.add_all(messages)
    
    # Auto-commit on exit
```

---

## 🔍 Query Examples

### Find User by Username

```python
with get_session() as session:
    user = session.query(User).filter_by(username="alice").first()
```

### Get User's Conversations

```python
with get_session() as session:
    user = session.query(User).filter_by(username="alice").first()
    conversations = user.conversations
    
    for conv in conversations:
        print(f"{conv.title}: {conv.message_count} messages")
```

### Get Conversation with Messages

```python
with get_session() as session:
    conv = session.query(Conversation).filter_by(id=1).first()
    
    for msg in conv.messages:
        print(f"[{msg.role.value}] {msg.content}")
```

### Search Messages

```python
from database.models import Message

with get_session() as session:
    # Full-text search (requires pg_trgm extension)
    results = session.query(Message).filter(
        Message.content.ilike("%python%")
    ).limit(10).all()
```

### Get User's Memories

```python
from database.models import ChatbotMemory

with get_session() as session:
    memories = session.query(ChatbotMemory).filter_by(
        user_id=1
    ).order_by(
        ChatbotMemory.importance.desc()
    ).all()
```

---

## 🔐 Environment Variables

```env
# Required
DATABASE_URL=postgresql://user:password@host:port/database

# Optional
SQLALCHEMY_ECHO=False
SQLALCHEMY_POOL_SIZE=5
SQLALCHEMY_MAX_OVERFLOW=10
SQLALCHEMY_POOL_TIMEOUT=30
```

---

## 📊 Database Schema Diagram

```
┌─────────────┐
│    users    │
├─────────────┤
│ id (PK)     │
│ username    │
│ email       │
│ ...         │
└──────┬──────┘
       │
       │ 1:N
       │
┌──────▼──────────────┐
│   conversations     │
├─────────────────────┤
│ id (PK)             │
│ conversation_uuid   │
│ user_id (FK)        │
│ title               │
│ tags[]              │
│ ...                 │
└──────┬──────────────┘
       │
       │ 1:N
       │
┌──────▼──────────┐
│    messages     │
├─────────────────┤
│ id (PK)         │
│ conversation_id │
│ role (ENUM)     │
│ content         │
│ ...             │
└─────────────────┘
```

---

## 🛠️ Troubleshooting

### Import Error

```python
# Make sure project root is in Python path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.models import User
```

### Connection Error

```powershell
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection string
echo $env:DATABASE_URL

# Test connection
python database/utils/test_connection.py
```

### Migration Errors

```powershell
# Check table exists
docker exec -it ai-assistant-postgres psql -U postgres -d ai_assistant -c "\dt"

# Drop and recreate tables
python database/scripts/setup_database.py
# Choose "yes" to drop existing tables
```

---

## 📚 Additional Documentation

- **Docker Setup:** `docs/DOCKER_SETUP.md`
- **Migration Roadmap:** `CHATBOT_MIGRATION_ROADMAP.md`
- **API Documentation:** `docs/API_DOCUMENTATION.md`

---

**Last Updated:** November 2025  
**Version:** 1.0.0
