"""
Pydantic Schemas for API Request/Response Models

Provides validation and serialization for all database models
"""

from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, validator, EmailStr
from database.models.chatbot import MessageRole


# ============================================================================
# Base Schemas
# ============================================================================

class TimestampSchema(BaseModel):
    """Base schema with timestamps"""
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    """Schema for creating a user"""
    is_admin: bool = False


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = Field(None, max_length=100)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserResponse(UserBase, TimestampSchema):
    """Schema for user response"""
    id: int
    is_active: bool
    is_admin: bool
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserSearchParams(BaseModel):
    """Schema for user search parameters"""
    query: str = Field(..., min_length=1)
    skip: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=100)


# ============================================================================
# Conversation Schemas
# ============================================================================

class ConversationBase(BaseModel):
    """Base conversation schema"""
    title: str = Field("New Conversation", max_length=255)
    tags: Optional[List[str]] = None
    template: Optional[str] = Field(None, max_length=100)


class ConversationCreate(ConversationBase):
    """Schema for creating a conversation"""
    user_id: int
    parent_conversation_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation"""
    title: Optional[str] = Field(None, max_length=255)
    tags: Optional[List[str]] = None
    is_archived: Optional[bool] = None
    is_pinned: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(ConversationBase, TimestampSchema):
    """Schema for conversation response"""
    id: int
    conversation_uuid: UUID
    user_id: int
    is_archived: bool
    is_pinned: bool
    parent_conversation_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    message_count: int
    
    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    """Schema for conversation with messages"""
    messages: List['MessageResponse'] = []


# ============================================================================
# Message Schemas
# ============================================================================

class MessageBase(BaseModel):
    """Base message schema"""
    role: MessageRole
    content: str = Field(..., min_length=1)
    model: Optional[str] = Field(None, max_length=50)
    images: Optional[List[Any]] = None
    files: Optional[List[Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageCreate(MessageBase):
    """Schema for creating a message"""
    conversation_id: int
    sequence_number: Optional[int] = None  # Auto-calculated if not provided


class MessageUpdate(BaseModel):
    """Schema for updating a message"""
    content: Optional[str] = Field(None, min_length=1)
    is_edited: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None


class MessageResponse(MessageBase, TimestampSchema):
    """Schema for message response"""
    id: int
    conversation_id: int
    sequence_number: int
    is_edited: bool
    original_message_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class MessageBulkCreate(BaseModel):
    """Schema for bulk creating messages"""
    conversation_id: int
    messages: List[MessageCreate]


# ============================================================================
# ChatBot Memory Schemas
# ============================================================================

class ChatbotMemoryBase(BaseModel):
    """Base memory schema"""
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    importance: int = Field(5, ge=1, le=10)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatbotMemoryCreate(ChatbotMemoryBase):
    """Schema for creating a memory"""
    user_id: int
    conversation_id: Optional[int] = None


class ChatbotMemoryUpdate(BaseModel):
    """Schema for updating a memory"""
    answer: Optional[str] = Field(None, min_length=1)
    importance: Optional[int] = Field(None, ge=1, le=10)
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class ChatbotMemoryResponse(ChatbotMemoryBase, TimestampSchema):
    """Schema for memory response"""
    id: int
    user_id: int
    conversation_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# Uploaded File Schemas
# ============================================================================

class UploadedFileBase(BaseModel):
    """Base uploaded file schema"""
    filename: str = Field(..., max_length=255)
    file_path: str = Field(..., max_length=500)
    file_type: Optional[str] = Field(None, max_length=50)
    file_size: Optional[int] = Field(None, ge=0)


class UploadedFileCreate(UploadedFileBase):
    """Schema for creating an uploaded file record"""
    user_id: int
    conversation_id: int


class UploadedFileUpdate(BaseModel):
    """Schema for updating an uploaded file record"""
    is_processed: Optional[bool] = None
    analysis_result: Optional[Dict[str, Any]] = None


class UploadedFileResponse(UploadedFileBase, TimestampSchema):
    """Schema for uploaded file response"""
    id: int
    user_id: int
    conversation_id: int
    is_processed: bool
    analysis_result: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# ============================================================================
# Pagination Schemas
# ============================================================================

class PaginationParams(BaseModel):
    """Schema for pagination parameters"""
    skip: int = Field(0, ge=0)
    limit: int = Field(100, ge=1, le=1000)


class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    items: List[Any]
    total: int
    skip: int
    limit: int
    
    @property
    def has_more(self) -> bool:
        """Check if there are more items"""
        return (self.skip + self.limit) < self.total


# ============================================================================
# Status Schemas
# ============================================================================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Generic error response"""
    error: str
    detail: str
    path: Optional[str] = None


# Update forward refs for nested schemas
ConversationWithMessages.model_rebuild()
