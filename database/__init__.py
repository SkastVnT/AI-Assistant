"""
Database package

SQLAlchemy models, utilities, and migration scripts
"""

from database.models import (
    Base,
    BaseModel,
    TimestampMixin,
    User,
    Conversation,
    Message,
    MessageRole,
    ChatbotMemory,
    UploadedFile
)

from database.utils import (
    DatabaseEngine,
    SessionManager,
    get_session,
    get_db,
    init_db
)

__all__ = [
    # Base classes
    "Base",
    "BaseModel",
    "TimestampMixin",
    
    # Models
    "User",
    "Conversation",
    "Message",
    "MessageRole",
    "ChatbotMemory",
    "UploadedFile",
    
    # Utilities
    "DatabaseEngine",
    "SessionManager",
    "get_session",
    "get_db",
    "init_db",
]

__version__ = "1.0.0"
