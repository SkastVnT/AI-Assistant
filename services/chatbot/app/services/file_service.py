"""
File Service

Handles file storage and management.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)


class FileService:
    """Service for file management"""
    
    def __init__(self):
        self.storage_path = Path(__file__).parent.parent.parent / 'Storage'
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory file registry fallback
        self._files: Dict[str, Dict] = {}
    
    def save(
        self,
        file: FileStorage,
        filename: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        file_type: str = ''
    ) -> Dict[str, Any]:
        """Save an uploaded file"""
        try:
            # Generate unique filename
            file_id = str(uuid.uuid4())
            safe_filename = f"{file_id}_{filename}"
            
            # Determine storage subdirectory
            if file_type in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
                subdir = 'images'
            else:
                subdir = 'documents'
            
            # Create directory
            save_dir = self.storage_path / subdir / user_id
            save_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_path = save_dir / safe_filename
            file.save(str(file_path))
            
            # Create file record
            file_record = {
                '_id': file_id,
                'user_id': user_id,
                'conversation_id': conversation_id,
                'filename': filename,
                'path': str(file_path),
                'file_type': file_type,
                'size': file_path.stat().st_size,
                'uploaded_at': datetime.now().isoformat()
            }
            
            # Save to database or memory
            self._save_record(file_record)
            
            return file_record
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            raise
    
    def get(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file info by ID"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                return db.files.find_one({'_id': file_id})
            else:
                return self._files.get(file_id)
                
        except Exception as e:
            logger.error(f"Error getting file: {e}")
            return None
    
    def list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """List files for a user"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                return list(db.files.find({'user_id': user_id}).sort('uploaded_at', -1))
            else:
                files = [f for f in self._files.values() if f['user_id'] == user_id]
                files.sort(key=lambda x: x.get('uploaded_at', ''), reverse=True)
                return files
                
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []
    
    def delete(self, file_id: str) -> bool:
        """Delete a file"""
        try:
            file_info = self.get(file_id)
            
            if not file_info:
                raise ValueError("File not found")
            
            # Delete physical file
            file_path = Path(file_info.get('path', ''))
            if file_path.exists():
                file_path.unlink()
            
            # Delete record
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                db.files.delete_one({'_id': file_id})
            else:
                if file_id in self._files:
                    del self._files[file_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            raise
    
    def _save_record(self, record: Dict[str, Any]) -> None:
        """Save file record to database or memory"""
        try:
            from ..extensions import get_mongodb
            client = get_mongodb()
            
            if client:
                db = client.get_database('ai_assistant')
                db.files.insert_one(record)
            else:
                self._files[record['_id']] = record
                
        except Exception as e:
            logger.warning(f"Could not save file record to database: {e}")
            self._files[record['_id']] = record
