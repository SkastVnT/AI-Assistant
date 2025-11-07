"""
Messages API Router

Endpoints for message management
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database.api.dependencies import get_db_session
from database.api.schemas import (
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageBulkCreate,
    SuccessResponse
)
from database.api.exceptions import NotFoundException
from database.repositories.message_repository import MessageRepository
from database.repositories.conversation_repository import ConversationRepository
from database.models.chatbot import MessageRole

router = APIRouter()
repo = MessageRepository()
conv_repo = ConversationRepository()


@router.get("", response_model=List[MessageResponse])
def get_messages(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db_session)
):
    """
    Get all messages with pagination
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        session: Database session
        
    Returns:
        List of messages
    """
    messages = repo.get_all(session, skip=skip, limit=limit)
    return messages


@router.get("/conversation/{conversation_id}", response_model=List[MessageResponse])
def get_conversation_messages(
    conversation_id: int,
    skip: int = 0,
    limit: Optional[int] = None,
    order_desc: bool = False,
    session: Session = Depends(get_db_session)
):
    """
    Get all messages in a conversation
    
    Args:
        conversation_id: Conversation ID
        skip: Number of records to skip
        limit: Maximum number of records to return (None for all)
        order_desc: Order by sequence number descending
        session: Database session
        
    Returns:
        List of messages
    """
    messages = repo.get_by_conversation_id(
        session,
        conversation_id=conversation_id,
        skip=skip,
        limit=limit,
        order_desc=order_desc
    )
    return messages


@router.get("/conversation/{conversation_id}/recent", response_model=List[MessageResponse])
def get_recent_messages(
    conversation_id: int,
    limit: int = 50,
    session: Session = Depends(get_db_session)
):
    """
    Get most recent messages in a conversation
    
    Args:
        conversation_id: Conversation ID
        limit: Maximum number of messages to return
        session: Database session
        
    Returns:
        List of recent messages (ordered oldest to newest)
    """
    messages = repo.get_recent_messages(
        session,
        conversation_id=conversation_id,
        limit=limit
    )
    return messages


@router.get("/search", response_model=List[MessageResponse])
def search_messages(
    query: str,
    conversation_id: Optional[int] = None,
    role: Optional[MessageRole] = None,
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_db_session)
):
    """
    Search messages by content
    
    Args:
        query: Search query string
        conversation_id: Optional conversation ID filter
        role: Optional role filter
        skip: Number of records to skip
        limit: Maximum number of records to return
        session: Database session
        
    Returns:
        List of matching messages
    """
    messages = repo.search_by_content(
        session,
        query=query,
        conversation_id=conversation_id,
        role=role,
        skip=skip,
        limit=limit
    )
    return messages


@router.get("/{message_id}", response_model=MessageResponse)
def get_message(
    message_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Get message by ID
    
    Args:
        message_id: Message ID
        session: Database session
        
    Returns:
        Message details
        
    Raises:
        NotFoundException: If message not found
    """
    message = repo.get(session, message_id)
    if not message:
        raise NotFoundException("Message", message_id)
    
    return message


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    message_data: MessageCreate,
    session: Session = Depends(get_db_session)
):
    """
    Create a new message
    
    Args:
        message_data: Message data
        session: Database session
        
    Returns:
        Created message
        
    Raises:
        NotFoundException: If conversation not found
    """
    # Verify conversation exists
    conversation = conv_repo.get(session, message_data.conversation_id)
    if not conversation:
        raise NotFoundException("Conversation", message_data.conversation_id)
    
    # Get next sequence number if not provided
    message_dict = message_data.model_dump()
    if message_dict.get("sequence_number") is None:
        message_dict["sequence_number"] = repo.get_next_sequence_number(
            session,
            message_data.conversation_id
        )
    
    # Create message
    message = repo.create(session, **message_dict)
    
    # Update conversation message count
    conv_repo.update_message_count(session, message_data.conversation_id)
    
    return message


@router.post("/bulk", response_model=List[MessageResponse], status_code=status.HTTP_201_CREATED)
def bulk_create_messages(
    bulk_data: MessageBulkCreate,
    session: Session = Depends(get_db_session)
):
    """
    Create multiple messages at once
    
    Args:
        bulk_data: Bulk message data
        session: Database session
        
    Returns:
        List of created messages
        
    Raises:
        NotFoundException: If conversation not found
    """
    # Verify conversation exists
    conversation = conv_repo.get(session, bulk_data.conversation_id)
    if not conversation:
        raise NotFoundException("Conversation", bulk_data.conversation_id)
    
    # Get starting sequence number
    next_seq = repo.get_next_sequence_number(session, bulk_data.conversation_id)
    
    # Prepare message data with sequence numbers
    messages_data = []
    for i, msg in enumerate(bulk_data.messages):
        msg_dict = msg.model_dump()
        if msg_dict.get("sequence_number") is None:
            msg_dict["sequence_number"] = next_seq + i
        msg_dict["conversation_id"] = bulk_data.conversation_id
        messages_data.append(msg_dict)
    
    # Bulk create
    messages = repo.bulk_create(session, messages_data)
    
    # Update conversation message count
    conv_repo.update_message_count(session, bulk_data.conversation_id)
    
    return messages


@router.put("/{message_id}", response_model=MessageResponse)
def update_message(
    message_id: int,
    message_data: MessageUpdate,
    session: Session = Depends(get_db_session)
):
    """
    Update message
    
    Args:
        message_id: Message ID
        message_data: Message data to update
        session: Database session
        
    Returns:
        Updated message
        
    Raises:
        NotFoundException: If message not found
    """
    if not repo.exists(session, message_id):
        raise NotFoundException("Message", message_id)
    
    update_dict = message_data.model_dump(exclude_unset=True)
    message = repo.update(session, message_id, **update_dict)
    
    if not message:
        raise NotFoundException("Message", message_id)
    
    return message


@router.delete("/{message_id}", response_model=SuccessResponse)
def delete_message(
    message_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Delete message
    
    Args:
        message_id: Message ID
        session: Database session
        
    Returns:
        Success response
        
    Raises:
        NotFoundException: If message not found
    """
    # Get message to find conversation ID
    message = repo.get(session, message_id)
    if not message:
        raise NotFoundException("Message", message_id)
    
    conversation_id = message.conversation_id
    
    # Delete message
    success = repo.delete(session, message_id, soft_delete=False)
    
    if not success:
        raise NotFoundException("Message", message_id)
    
    # Update conversation message count
    conv_repo.update_message_count(session, conversation_id)
    
    return SuccessResponse(
        message=f"Message {message_id} deleted successfully"
    )


@router.get("/conversation/{conversation_id}/count", response_model=dict)
def count_conversation_messages(
    conversation_id: int,
    role: Optional[MessageRole] = None,
    session: Session = Depends(get_db_session)
):
    """
    Count messages in conversation
    
    Args:
        conversation_id: Conversation ID
        role: Optional role filter
        session: Database session
        
    Returns:
        Message count
    """
    count = repo.get_message_count(
        session,
        conversation_id=conversation_id,
        role=role
    )
    return {"count": count}


@router.get("/conversation/{conversation_id}/edited", response_model=List[MessageResponse])
def get_edited_messages(
    conversation_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Get all edited messages in a conversation
    
    Args:
        conversation_id: Conversation ID
        session: Database session
        
    Returns:
        List of edited messages
    """
    messages = repo.get_edited_messages(session, conversation_id)
    return messages
