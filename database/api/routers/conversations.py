"""
Conversations API Router

Endpoints for conversation management
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database.api.dependencies import get_db_session
from database.api.schemas import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationWithMessages,
    SuccessResponse
)
from database.api.exceptions import NotFoundException
from database.repositories.conversation_repository import ConversationRepository

router = APIRouter()
repo = ConversationRepository()


@router.get("", response_model=List[ConversationResponse])
def get_conversations(
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_db_session)
):
    """
    Get all conversations with pagination
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        session: Database session
        
    Returns:
        List of conversations
    """
    conversations = repo.get_all(session, skip=skip, limit=limit)
    return conversations


@router.get("/user/{user_id}", response_model=List[ConversationResponse])
def get_user_conversations(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
    session: Session = Depends(get_db_session)
):
    """
    Get all conversations for a user
    
    Args:
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        include_archived: Include archived conversations
        session: Database session
        
    Returns:
        List of user's conversations
    """
    conversations = repo.get_by_user_id(
        session,
        user_id=user_id,
        skip=skip,
        limit=limit,
        include_archived=include_archived
    )
    return conversations


@router.get("/user/{user_id}/active", response_model=List[ConversationResponse])
def get_user_active_conversations(
    user_id: int,
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_db_session)
):
    """
    Get active (non-archived) conversations for a user
    
    Args:
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        session: Database session
        
    Returns:
        List of active conversations
    """
    conversations = repo.get_active_conversations(
        session,
        user_id=user_id,
        skip=skip,
        limit=limit
    )
    return conversations


@router.get("/user/{user_id}/pinned", response_model=List[ConversationResponse])
def get_user_pinned_conversations(
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Get pinned conversations for a user
    
    Args:
        user_id: User ID
        session: Database session
        
    Returns:
        List of pinned conversations
    """
    conversations = repo.get_pinned_conversations(session, user_id=user_id)
    return conversations


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Get conversation by ID
    
    Args:
        conversation_id: Conversation ID
        session: Database session
        
    Returns:
        Conversation details
        
    Raises:
        NotFoundException: If conversation not found
    """
    conversation = repo.get(session, conversation_id)
    if not conversation:
        raise NotFoundException("Conversation", conversation_id)
    
    return conversation


@router.get("/uuid/{conversation_uuid}", response_model=ConversationResponse)
def get_conversation_by_uuid(
    conversation_uuid: UUID,
    session: Session = Depends(get_db_session)
):
    """
    Get conversation by UUID
    
    Args:
        conversation_uuid: Conversation UUID
        session: Database session
        
    Returns:
        Conversation details
        
    Raises:
        NotFoundException: If conversation not found
    """
    conversation = repo.get_by_uuid(session, conversation_uuid)
    if not conversation:
        raise NotFoundException("Conversation", conversation_uuid)
    
    return conversation


@router.get("/{conversation_id}/with-messages", response_model=ConversationWithMessages)
def get_conversation_with_messages(
    conversation_id: int,
    message_limit: Optional[int] = None,
    session: Session = Depends(get_db_session)
):
    """
    Get conversation with all messages
    
    Args:
        conversation_id: Conversation ID
        message_limit: Optional limit on number of messages
        session: Database session
        
    Returns:
        Conversation with messages
        
    Raises:
        NotFoundException: If conversation not found
    """
    conversation = repo.get_with_messages(
        session,
        conversation_id=conversation_id,
        message_limit=message_limit
    )
    
    if not conversation:
        raise NotFoundException("Conversation", conversation_id)
    
    return conversation


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conversation_data: ConversationCreate,
    session: Session = Depends(get_db_session)
):
    """
    Create a new conversation
    
    Args:
        conversation_data: Conversation data
        session: Database session
        
    Returns:
        Created conversation
    """
    conversation = repo.create(session, **conversation_data.model_dump())
    return conversation


@router.put("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    conversation_data: ConversationUpdate,
    session: Session = Depends(get_db_session)
):
    """
    Update conversation
    
    Args:
        conversation_id: Conversation ID
        conversation_data: Conversation data to update
        session: Database session
        
    Returns:
        Updated conversation
        
    Raises:
        NotFoundException: If conversation not found
    """
    if not repo.exists(session, conversation_id):
        raise NotFoundException("Conversation", conversation_id)
    
    update_dict = conversation_data.model_dump(exclude_unset=True)
    conversation = repo.update(session, conversation_id, **update_dict)
    
    if not conversation:
        raise NotFoundException("Conversation", conversation_id)
    
    return conversation


@router.delete("/{conversation_id}", response_model=SuccessResponse)
def delete_conversation(
    conversation_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Delete conversation
    
    Args:
        conversation_id: Conversation ID
        session: Database session
        
    Returns:
        Success response
        
    Raises:
        NotFoundException: If conversation not found
    """
    success = repo.delete(session, conversation_id, soft_delete=False)
    
    if not success:
        raise NotFoundException("Conversation", conversation_id)
    
    return SuccessResponse(
        message=f"Conversation {conversation_id} deleted successfully"
    )


@router.post("/{conversation_id}/archive", response_model=SuccessResponse)
def archive_conversation(
    conversation_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Archive conversation
    
    Args:
        conversation_id: Conversation ID
        session: Database session
        
    Returns:
        Success response
        
    Raises:
        NotFoundException: If conversation not found
    """
    success = repo.archive_conversation(session, conversation_id, archive=True)
    
    if not success:
        raise NotFoundException("Conversation", conversation_id)
    
    return SuccessResponse(
        message=f"Conversation {conversation_id} archived successfully"
    )


@router.post("/{conversation_id}/unarchive", response_model=SuccessResponse)
def unarchive_conversation(
    conversation_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Unarchive conversation
    
    Args:
        conversation_id: Conversation ID
        session: Database session
        
    Returns:
        Success response
        
    Raises:
        NotFoundException: If conversation not found
    """
    success = repo.archive_conversation(session, conversation_id, archive=False)
    
    if not success:
        raise NotFoundException("Conversation", conversation_id)
    
    return SuccessResponse(
        message=f"Conversation {conversation_id} unarchived successfully"
    )


@router.post("/{conversation_id}/pin", response_model=SuccessResponse)
def pin_conversation(
    conversation_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Pin conversation
    
    Args:
        conversation_id: Conversation ID
        session: Database session
        
    Returns:
        Success response
        
    Raises:
        NotFoundException: If conversation not found
    """
    success = repo.pin_conversation(session, conversation_id, pin=True)
    
    if not success:
        raise NotFoundException("Conversation", conversation_id)
    
    return SuccessResponse(
        message=f"Conversation {conversation_id} pinned successfully"
    )


@router.post("/{conversation_id}/unpin", response_model=SuccessResponse)
def unpin_conversation(
    conversation_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Unpin conversation
    
    Args:
        conversation_id: Conversation ID
        session: Database session
        
    Returns:
        Success response
        
    Raises:
        NotFoundException: If conversation not found
    """
    success = repo.pin_conversation(session, conversation_id, pin=False)
    
    if not success:
        raise NotFoundException("Conversation", conversation_id)
    
    return SuccessResponse(
        message=f"Conversation {conversation_id} unpinned successfully"
    )


@router.get("/user/{user_id}/count", response_model=dict)
def count_user_conversations(
    user_id: int,
    include_archived: bool = False,
    session: Session = Depends(get_db_session)
):
    """
    Count conversations for a user
    
    Args:
        user_id: User ID
        include_archived: Include archived conversations
        session: Database session
        
    Returns:
        Conversation count
    """
    count = repo.count_user_conversations(
        session,
        user_id=user_id,
        include_archived=include_archived
    )
    return {"count": count}
