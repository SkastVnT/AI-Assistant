"""
User model for authentication and user management
"""

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from database.models.base import BaseModel


class User(BaseModel):
    """
    User model for storing user information
    
    Relationships:
    - conversations: One-to-many with Conversation
    - memories: One-to-many with ChatbotMemory
    - uploaded_files: One-to-many with UploadedFile
    """
    
    __tablename__ = "users"
    
    # User identification
    username = Column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique username"
    )
    
    email = Column(
        String(120),
        unique=True,
        nullable=True,
        index=True,
        comment="User email address"
    )
    
    # User profile
    full_name = Column(
        String(100),
        nullable=True,
        comment="User's full name"
    )
    
    # User status
    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        comment="Whether user account is active"
    )
    
    is_admin = Column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether user has admin privileges"
    )
    
    # Last activity
    last_login = Column(
        DateTime,
        nullable=True,
        comment="Timestamp of last login"
    )
    
    # Relationships (will be defined after other models are created)
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("ChatbotMemory", back_populates="user", cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def is_authenticated(self) -> bool:
        """Check if user is authenticated (for Flask-Login compatibility)"""
        return True
    
    @property
    def is_anonymous(self) -> bool:
        """Check if user is anonymous"""
        return False
    
    def get_id(self) -> str:
        """Get user ID as string (for Flask-Login)"""
        return str(self.id)
