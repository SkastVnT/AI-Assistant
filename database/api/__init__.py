"""
Database API Package

FastAPI routers for database operations
"""

from fastapi import APIRouter
from database.api.routers import users, conversations, messages

# Create main API router
api_router = APIRouter(prefix="/api/v1/database", tags=["database"])

# Include sub-routers
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])

__all__ = ["api_router"]
