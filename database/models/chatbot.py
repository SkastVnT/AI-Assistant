"""
ChatBot models for conversations, messages, memories, and files
"""

import uuid
import enum
from sqlalchemy import Column, String, Text, Integer, Boolean, ForeignKey, Enum as SQLEnum, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from database.models.base import BaseModel


# Enums
class MessageRole(enum.Enum):
    """Message role in conversation"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(BaseModel):
    """
    Conversation model - stores chat conversations
    
    Relationships:
    - user: Many-to-one with User
    - messages: One-to-many with Message
    - memories: One-to-many with ChatbotMemory
    - uploaded_files: One-to-many with UploadedFile
    """
    
    __tablename__ = "conversations"
    
    # Unique conversation ID (UUID for better distribution)
    conversation_uuid = Column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        unique=True,
        nullable=False,
        index=True,
        comment="Unique conversation identifier"
    )
    
    # Foreign key to user
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who owns this conversation"
    )
    
    # Conversation metadata
    title = Column(
        String(255),
        nullable=False,
        default="New Conversation",
        comment="Conversation title"
    )
    
    # Tags for organization (stored as PostgreSQL array)
    tags = Column(
        ARRAY(String),
        nullable=True,
        comment="Tags for categorizing conversation"
    )
    
    # Template used (if any)
    template = Column(
        String(100),
        nullable=True,
        comment="Template name if conversation was created from template"
    )
    
    # Conversation status
    is_archived = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether conversation is archived"
    )
    
    is_pinned = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether conversation is pinned to top"
    )
    
    # Branching support
    parent_conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        comment="Parent conversation if this is a branch"
    )
    
    # Additional metadata (JSON for flexibility)
    metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata in JSON format"
    )
    
    # Message count (denormalized for performance)
    message_count = Column(
        Integer,
        default=0,
        nullable=False,
        comment="Cached count of messages in conversation"
    )
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id"
    )
    memories = relationship(
        "ChatbotMemory",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    uploaded_files = relationship(
        "UploadedFile",
        back_populates="conversation",
        cascade="all, delete-orphan"
    )
    
    # Self-referential relationship for branches
    branches = relationship(
        "Conversation",
        backref="parent_conversation",
        remote_side=[id]
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_conv_user_created', 'user_id', 'created_at'),
        Index('idx_conv_archived', 'is_archived', 'user_id'),
        Index('idx_conv_tags', 'tags', postgresql_using='gin'),
    )
    
    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, uuid={self.conversation_uuid}, title='{self.title}')>"


class Message(BaseModel):
    """
    Message model - stores individual messages in conversations
    
    Relationships:
    - conversation: Many-to-one with Conversation
    """
    
    __tablename__ = "messages"
    
    # Foreign key to conversation
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Conversation this message belongs to"
    )
    
    # Message content
    role = Column(
        SQLEnum(MessageRole),
        nullable=False,
        comment="Role of message sender (user/assistant/system)"
    )
    
    content = Column(
        Text,
        nullable=False,
        comment="Message content"
    )
    
    # Model used (for assistant messages)
    model = Column(
        String(50),
        nullable=True,
        comment="AI model used to generate this message"
    )
    
    # Message order in conversation
    sequence_number = Column(
        Integer,
        nullable=False,
        comment="Order of message in conversation"
    )
    
    # Image data (JSON array of image paths/URLs)
    images = Column(
        JSON,
        nullable=True,
        comment="Array of image data/paths"
    )
    
    # File attachments (JSON array)
    files = Column(
        JSON,
        nullable=True,
        comment="Array of file attachments"
    )
    
    # Message editing support
    is_edited = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether message has been edited"
    )
    
    original_message_id = Column(
        Integer,
        ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
        comment="Original message if this is an edit"
    )
    
    # Additional metadata
    metadata = Column(
        JSON,
        nullable=True,
        comment="Additional message metadata"
    )
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    # Self-referential for edit history
    edited_versions = relationship(
        "Message",
        backref="original_message",
        remote_side=[id]
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_msg_conv_seq', 'conversation_id', 'sequence_number'),
        Index('idx_msg_role', 'role'),
        Index('idx_msg_content_search', 'content', postgresql_using='gin', postgresql_ops={'content': 'gin_trgm_ops'}),
    )
    
    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role={self.role.value}, content='{content_preview}')>"


class ChatbotMemory(BaseModel):
    """
    ChatBot memory model - stores learned information from conversations
    
    Relationships:
    - user: Many-to-one with User
    - conversation: Many-to-one with Conversation (optional)
    """
    
    __tablename__ = "chatbot_memory"
    
    # Foreign keys
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User this memory belongs to"
    )
    
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Conversation where this memory was created"
    )
    
    # Memory content
    question = Column(
        Text,
        nullable=False,
        comment="Question or topic"
    )
    
    answer = Column(
        Text,
        nullable=False,
        comment="Answer or learned information"
    )
    
    # Memory importance (1-10)
    importance = Column(
        Integer,
        default=5,
        nullable=False,
        comment="Importance score (1-10)"
    )
    
    # Memory tags
    tags = Column(
        ARRAY(String),
        nullable=True,
        comment="Tags for categorizing memory"
    )
    
    # Memory metadata
    metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata"
    )
    
    # Relationships
    user = relationship("User", back_populates="memories")
    conversation = relationship("Conversation", back_populates="memories")
    
    # Indexes
    __table_args__ = (
        Index('idx_memory_user', 'user_id'),
        Index('idx_memory_question_search', 'question', postgresql_using='gin', postgresql_ops={'question': 'gin_trgm_ops'}),
        Index('idx_memory_tags', 'tags', postgresql_using='gin'),
    )
    
    def __repr__(self) -> str:
        return f"<ChatbotMemory(id={self.id}, question='{self.question[:30]}...')>"


class UploadedFile(BaseModel):
    """
    Uploaded file model - stores information about uploaded files
    
    Relationships:
    - user: Many-to-one with User
    - conversation: Many-to-one with Conversation
    """
    
    __tablename__ = "uploaded_files"
    
    # Foreign keys
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who uploaded the file"
    )
    
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Conversation where file was uploaded"
    )
    
    # File information
    filename = Column(
        String(255),
        nullable=False,
        comment="Original filename"
    )
    
    file_path = Column(
        String(500),
        nullable=False,
        comment="Path to stored file"
    )
    
    file_type = Column(
        String(50),
        nullable=True,
        comment="MIME type of file"
    )
    
    file_size = Column(
        Integer,
        nullable=True,
        comment="File size in bytes"
    )
    
    # Analysis result (if file was analyzed)
    analysis_result = Column(
        JSON,
        nullable=True,
        comment="Result of file analysis (if applicable)"
    )
    
    # File status
    is_processed = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether file has been processed"
    )
    
    # Relationships
    user = relationship("User", back_populates="uploaded_files")
    conversation = relationship("Conversation", back_populates="uploaded_files")
    
    # Indexes
    __table_args__ = (
        Index('idx_file_user', 'user_id'),
        Index('idx_file_conv', 'conversation_id'),
        Index('idx_file_type', 'file_type'),
    )
    
    def __repr__(self) -> str:
        return f"<UploadedFile(id={self.id}, filename='{self.filename}', type='{self.file_type}')>"
