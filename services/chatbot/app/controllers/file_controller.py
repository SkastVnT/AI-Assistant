"""
File Controller

Handles file upload and management operations.
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from ..services.file_service import FileService

logger = logging.getLogger(__name__)


class FileController:
    """Controller for file operations"""
    
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'txt', 'md', 'json'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self):
        self.file_service = FileService()
    
    def list_files(self, user_id: str) -> Dict[str, Any]:
        """List all files for a user"""
        try:
            files = self.file_service.list_by_user(user_id)
            return {
                'files': files,
                'total': len(files)
            }
        except Exception as e:
            logger.error(f"❌ Error listing files: {e}")
            raise
    
    def upload_file(
        self,
        file: FileStorage,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload a new file"""
        try:
            # Validate file
            if not file or not file.filename:
                raise ValueError("No file provided")
            
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            
            if ext not in self.ALLOWED_EXTENSIONS:
                raise ValueError(f"File type not allowed: {ext}")
            
            # Check file size
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            
            if size > self.MAX_FILE_SIZE:
                raise ValueError(f"File too large: {size} bytes (max: {self.MAX_FILE_SIZE})")
            
            # Save file
            result = self.file_service.save(
                file=file,
                filename=filename,
                user_id=user_id,
                conversation_id=conversation_id,
                file_type=ext
            )
            
            logger.info(f"✅ Uploaded file: {filename}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error uploading file: {e}")
            raise
    
    def get_file_path(self, file_id: str) -> Optional[Path]:
        """Get file path by ID"""
        try:
            file_info = self.file_service.get(file_id)
            
            if not file_info:
                return None
            
            path = Path(file_info.get('path', ''))
            
            if not path.exists():
                return None
            
            return path
            
        except Exception as e:
            logger.error(f"❌ Error getting file path: {e}")
            raise
    
    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """Delete a file"""
        try:
            self.file_service.delete(file_id)
            logger.info(f"✅ Deleted file: {file_id}")
            return {'deleted': True, 'file_id': file_id}
        except Exception as e:
            logger.error(f"❌ Error deleting file: {e}")
            raise
