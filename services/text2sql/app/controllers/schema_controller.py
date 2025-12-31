"""
Schema Controller
Handle schema upload and management requests
"""

import logging
from typing import Dict, Any, Tuple
from flask import current_app

from ..services import SchemaService

logger = logging.getLogger(__name__)

# Global schema service instance (maintains state across requests)
_schema_service = None


def get_schema_service() -> SchemaService:
    """Get or create schema service instance."""
    global _schema_service
    if _schema_service is None:
        _schema_service = SchemaService(
            upload_folder=current_app.config.get('UPLOAD_FOLDER', 'uploads')
        )
    return _schema_service


class SchemaController:
    """Controller for schema management endpoints."""
    
    def __init__(self):
        """Initialize controller."""
        self.service = get_schema_service()
    
    def upload_schema(self, file) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Upload schema file.
        
        Args:
            file: File object from request
        
        Returns:
            Tuple of (success, message, data)
        """
        return self.service.upload_schema(file)
    
    def get_schema_info(self) -> Dict[str, Any]:
        """Get current schema information."""
        return self.service.get_schema_info()
    
    def clear_schemas(self) -> bool:
        """Clear all schemas."""
        return self.service.clear_schemas()
    
    def get_tables(self) -> Dict[str, Any]:
        """Get list of known tables."""
        return {
            'tables': list(self.service.known_tables),
            'active_tables': list(self.service.active_tables),
            'primary_table': self.service.active_primary_table,
            'last_uploaded': self.service.last_table_uploaded
        }
