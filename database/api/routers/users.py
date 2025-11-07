"""
Users API Router

Endpoints for user management
"""

from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from database.api.dependencies import get_db_session
from database.api.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserSearchParams,
    SuccessResponse
)
from database.api.exceptions import NotFoundException, ConflictException
from database.repositories.user_repository import UserRepository

router = APIRouter()
repo = UserRepository()


@router.get("", response_model=List[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    session: Session = Depends(get_db_session)
):
    """
    Get all users with pagination
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: Only return active users
        session: Database session
        
    Returns:
        List of users
    """
    if active_only:
        users = repo.get_active_users(session, skip=skip, limit=limit)
    else:
        users = repo.get_all(session, skip=skip, limit=limit)
    
    return users


@router.get("/search", response_model=List[UserResponse])
def search_users(
    query: str,
    skip: int = 0,
    limit: int = 50,
    session: Session = Depends(get_db_session)
):
    """
    Search users by username, email, or full name
    
    Args:
        query: Search query string
        skip: Number of records to skip
        limit: Maximum number of records to return
        session: Database session
        
    Returns:
        List of matching users
    """
    users = repo.search_users(session, query=query, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Get user by ID
    
    Args:
        user_id: User ID
        session: Database session
        
    Returns:
        User details
        
    Raises:
        NotFoundException: If user not found
    """
    user = repo.get(session, user_id)
    if not user:
        raise NotFoundException("User", user_id)
    
    return user


@router.get("/username/{username}", response_model=UserResponse)
def get_user_by_username(
    username: str,
    session: Session = Depends(get_db_session)
):
    """
    Get user by username
    
    Args:
        username: Username
        session: Database session
        
    Returns:
        User details
        
    Raises:
        NotFoundException: If user not found
    """
    user = repo.get_by_username(session, username)
    if not user:
        raise NotFoundException("User", username)
    
    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    session: Session = Depends(get_db_session)
):
    """
    Create a new user
    
    Args:
        user_data: User data
        session: Database session
        
    Returns:
        Created user
        
    Raises:
        ConflictException: If username or email already exists
    """
    # Check for existing username
    existing = repo.get_by_username(session, user_data.username)
    if existing:
        raise ConflictException(f"Username '{user_data.username}' already exists")
    
    # Check for existing email if provided
    if user_data.email:
        existing = repo.get_by_email(session, user_data.email)
        if existing:
            raise ConflictException(f"Email '{user_data.email}' already exists")
    
    # Create user
    user = repo.create(session, **user_data.model_dump())
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: Session = Depends(get_db_session)
):
    """
    Update user
    
    Args:
        user_id: User ID
        user_data: User data to update
        session: Database session
        
    Returns:
        Updated user
        
    Raises:
        NotFoundException: If user not found
        ConflictException: If email already exists
    """
    # Check user exists
    if not repo.exists(session, user_id):
        raise NotFoundException("User", user_id)
    
    # Check email uniqueness if being updated
    if user_data.email:
        existing = repo.get_by_email(session, user_data.email)
        if existing and existing.id != user_id:
            raise ConflictException(f"Email '{user_data.email}' already exists")
    
    # Update user
    update_dict = user_data.model_dump(exclude_unset=True)
    user = repo.update(session, user_id, **update_dict)
    
    if not user:
        raise NotFoundException("User", user_id)
    
    return user


@router.delete("/{user_id}", response_model=SuccessResponse)
def delete_user(
    user_id: int,
    hard_delete: bool = False,
    session: Session = Depends(get_db_session)
):
    """
    Delete user (soft delete by default)
    
    Args:
        user_id: User ID
        hard_delete: Permanently delete user
        session: Database session
        
    Returns:
        Success response
        
    Raises:
        NotFoundException: If user not found
    """
    success = repo.delete(session, user_id, soft_delete=not hard_delete)
    
    if not success:
        raise NotFoundException("User", user_id)
    
    return SuccessResponse(
        message=f"User {user_id} deleted successfully"
    )


@router.post("/{user_id}/activate", response_model=SuccessResponse)
def activate_user(
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Activate user account
    
    Args:
        user_id: User ID
        session: Database session
        
    Returns:
        Success response
        
    Raises:
        NotFoundException: If user not found
    """
    success = repo.activate_user(session, user_id)
    
    if not success:
        raise NotFoundException("User", user_id)
    
    return SuccessResponse(
        message=f"User {user_id} activated successfully"
    )


@router.post("/{user_id}/deactivate", response_model=SuccessResponse)
def deactivate_user(
    user_id: int,
    session: Session = Depends(get_db_session)
):
    """
    Deactivate user account
    
    Args:
        user_id: User ID
        session: Database session
        
    Returns:
        Success response
        
    Raises:
        NotFoundException: If user not found
    """
    success = repo.deactivate_user(session, user_id)
    
    if not success:
        raise NotFoundException("User", user_id)
    
    return SuccessResponse(
        message=f"User {user_id} deactivated successfully"
    )


@router.get("/stats/active-count", response_model=dict)
def get_active_user_count(
    session: Session = Depends(get_db_session)
):
    """
    Get count of active users
    
    Args:
        session: Database session
        
    Returns:
        Active user count
    """
    count = repo.count_active_users(session)
    return {"active_users": count}
