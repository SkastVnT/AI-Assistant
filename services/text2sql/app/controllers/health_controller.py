"""
Health Controller
Handle health check and monitoring requests
"""

import logging
from typing import Dict, Any
from flask import current_app

from ..services import DatabaseService, MemoryService, SchemaService
from .schema_controller import get_schema_service

logger = logging.getLogger(__name__)


class HealthController:
    """Controller for health and monitoring endpoints."""
    
    def __init__(self):
        """Initialize controller."""
        self.db_service = DatabaseService(current_app.config)
    
    def check_database(self) -> Dict[str, Any]:
        """Check database health."""
        return self.db_service.check_health()
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get table information."""
        return self.db_service.get_table_info(table_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        schema_service = get_schema_service()
        memory_service = MemoryService(
            memory_dir=str(current_app.config.get('MEMORY_DIR', 'knowledge_base/memory')),
            data_dir=str(current_app.config.get('DATA_DIR', 'data'))
        )
        
        memory_stats = memory_service.get_memory_stats()
        
        return {
            'service': 'text2sql',
            'version': '2.0.0',
            'config': {
                'default_model': current_app.config.get('DEFAULT_SQL_MODEL', 'grok'),
                'refine_strategy': current_app.config.get('REFINE_STRATEGY', 'gemini'),
                'debug': current_app.config.get('DEBUG', False)
            },
            'schema': {
                'files': len(schema_service.schema_files),
                'tables': len(schema_service.known_tables),
                'active_tables': len(schema_service.active_tables)
            },
            'memory': memory_stats,
            'database': self.db_service.check_health()
        }
