"""
Database models package

Import all models here for easy access and proper relationship setup
"""

from database.models.base import Base, BaseModel, TimestampMixin
from database.models.user import User
from database.models.chatbot import (
    Conversation,
    Message,
    MessageRole,
    ChatbotMemory,
    UploadedFile
)

__all__ = [
    # Base classes
    "Base",
    "BaseModel",
    "TimestampMixin",
    
    # User models
    "User",
    
    # ChatBot models
    "Conversation",
    "Message",
    "MessageRole",
    "ChatbotMemory",
    "UploadedFile",
]
