"""
Uploaded File Repository

Provides data access layer for UploadedFile model
"""

import logging
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database.models.chatbot import UploadedFile
from database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UploadedFileRepository(BaseRepository[UploadedFile]):
    """
    Repository for UploadedFile model
    
    Provides specialized methods:
    - get_by_user_id: Get all files uploaded by a user
    - get_by_conversation_id: Get files in a conversation
    - get_unprocessed_files: Get files that haven't been processed
    - mark_processed: Mark file as processed
    - get_by_file_type: Get files by MIME type
    - clean_old_files: Get files older than specified days
    - get_user_storage_size: Calculate total storage used by user
    """
    
    def __init__(self):
        """Initialize UploadedFile repository"""
        super().__init__(UploadedFile)
    
    def get_by_user_id(
        self,
        session: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[UploadedFile]:
        """
        Get all files uploaded by a user
        
        Args:
            session: Database session
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of uploaded files
        """
        try:
            stmt = select(UploadedFile).where(
                UploadedFile.user_id == user_id
            ).order_by(desc(UploadedFile.created_at)).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting files for user {user_id}: {e}")
            return []
    
    def get_by_conversation_id(
        self,
        session: Session,
        conversation_id: int
    ) -> List[UploadedFile]:
        """
        Get all files in a conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            
        Returns:
            List of uploaded files
        """
        try:
            stmt = select(UploadedFile).where(
                UploadedFile.conversation_id == conversation_id
            ).order_by(UploadedFile.created_at)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting files for conversation {conversation_id}: {e}")
            return []
    
    def get_unprocessed_files(
        self,
        session: Session,
        limit: int = 100
    ) -> List[UploadedFile]:
        """
        Get files that haven't been processed yet
        
        Args:
            session: Database session
            limit: Maximum number of records to return
            
        Returns:
            List of unprocessed files
        """
        try:
            stmt = select(UploadedFile).where(
                UploadedFile.is_processed == False
            ).order_by(UploadedFile.created_at).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting unprocessed files: {e}")
            return []
    
    def mark_processed(
        self,
        session: Session,
        file_id: int,
        analysis_result: Optional[dict] = None
    ) -> bool:
        """
        Mark file as processed
        
        Args:
            session: Database session
            file_id: File ID
            analysis_result: Optional analysis result to store
            
        Returns:
            True if updated, False otherwise
        """
        try:
            file = self.get(session, file_id)
            if not file:
                return False
            
            file.is_processed = True
            if analysis_result:
                file.analysis_result = analysis_result
            
            session.flush()
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error marking file {file_id} as processed: {e}")
            session.rollback()
            return False
    
    def get_by_file_type(
        self,
        session: Session,
        file_type: str,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[UploadedFile]:
        """
        Get files by MIME type
        
        Args:
            session: Database session
            file_type: MIME type (e.g., 'image/png', 'application/pdf')
            user_id: Optional user ID filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of files
        """
        try:
            stmt = select(UploadedFile).where(
                UploadedFile.file_type == file_type
            )
            
            if user_id:
                stmt = stmt.where(UploadedFile.user_id == user_id)
            
            stmt = stmt.order_by(desc(UploadedFile.created_at)).offset(skip).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting files by type '{file_type}': {e}")
            return []
    
    def clean_old_files(
        self,
        session: Session,
        days_old: int = 30,
        limit: int = 1000
    ) -> List[UploadedFile]:
        """
        Get files older than specified days for cleanup
        
        Args:
            session: Database session
            days_old: Age threshold in days
            limit: Maximum number of records to return
            
        Returns:
            List of old files
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            stmt = select(UploadedFile).where(
                UploadedFile.created_at < cutoff_date
            ).order_by(UploadedFile.created_at).limit(limit)
            
            result = session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting old files: {e}")
            return []
    
    def get_user_storage_size(
        self,
        session: Session,
        user_id: int
    ) -> int:
        """
        Calculate total storage used by user (in bytes)
        
        Args:
            session: Database session
            user_id: User ID
            
        Returns:
            Total file size in bytes
        """
        try:
            stmt = select(func.sum(UploadedFile.file_size)).where(
                UploadedFile.user_id == user_id
            )
            result = session.execute(stmt).scalar()
            return result or 0
        except SQLAlchemyError as e:
            logger.error(f"Error calculating storage for user {user_id}: {e}")
            return 0
    
    def get_conversation_files_size(
        self,
        session: Session,
        conversation_id: int
    ) -> int:
        """
        Calculate total size of files in a conversation
        
        Args:
            session: Database session
            conversation_id: Conversation ID
            
        Returns:
            Total file size in bytes
        """
        try:
            stmt = select(func.sum(UploadedFile.file_size)).where(
                UploadedFile.conversation_id == conversation_id
            )
            result = session.execute(stmt).scalar()
            return result or 0
        except SQLAlchemyError as e:
            logger.error(f"Error calculating storage for conversation {conversation_id}: {e}")
            return 0
    
    def count_user_files(
        self,
        session: Session,
        user_id: int,
        file_type: Optional[str] = None
    ) -> int:
        """
        Count files uploaded by user
        
        Args:
            session: Database session
            user_id: User ID
            file_type: Optional file type filter
            
        Returns:
            File count
        """
        try:
            stmt = select(func.count()).select_from(UploadedFile).where(
                UploadedFile.user_id == user_id
            )
            
            if file_type:
                stmt = stmt.where(UploadedFile.file_type == file_type)
            
            result = session.execute(stmt)
            return result.scalar() or 0
        except SQLAlchemyError as e:
            logger.error(f"Error counting files for user {user_id}: {e}")
            return 0
