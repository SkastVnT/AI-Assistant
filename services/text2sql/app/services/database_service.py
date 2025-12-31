"""
Database Service
Handle ClickHouse database operations
"""

import os
import json
import logging
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for ClickHouse database operations."""
    
    def __init__(self, config: dict = None):
        """
        Initialize Database Service.
        
        Args:
            config: Database configuration
        """
        self.config = config or {}
        self._client = None
        self._connected = False
    
    def get_client(self):
        """Get or create ClickHouse client."""
        if self._client is not None:
            return self._client
        
        try:
            from clickhouse_connect import get_client
            
            self._client = get_client(
                host=self.config.get('CLICKHOUSE_HOST', os.getenv('CLICKHOUSE_HOST', 'localhost')),
                port=int(self.config.get('CLICKHOUSE_PORT', os.getenv('CLICKHOUSE_PORT', 8123))),
                username=self.config.get('CLICKHOUSE_USER', os.getenv('CLICKHOUSE_USER', 'default')),
                password=self.config.get('CLICKHOUSE_PASSWORD', os.getenv('CLICKHOUSE_PASSWORD', '')),
                database=self.config.get('CLICKHOUSE_DATABASE', os.getenv('CLICKHOUSE_DB', 'default'))
            )
            self._connected = True
            logger.info("ClickHouse client connected successfully")
            return self._client
        
        except ImportError:
            logger.warning("clickhouse_connect not installed")
            return None
        except Exception as e:
            logger.warning(f"ClickHouse connection failed: {e}")
            return None
    
    def execute_sql(self, sql: str) -> Tuple[Optional[List[Dict]], str]:
        """
        Execute SQL query.
        
        Args:
            sql: SQL query to execute
        
        Returns:
            Tuple of (results, status)
            Status: OK, OK_EMPTY, NO_SQL, NO_DB, ERR:<message>
        """
        if not sql:
            return None, "NO_SQL"
        
        client = self.get_client()
        if client is None:
            return None, "NO_DB"
        
        try:
            result = client.query(sql)
            rows = result.result_rows or []
            cols = result.column_names or []
            
            if not rows:
                return None, "OK_EMPTY"
            
            data = [dict(zip(cols, row)) for row in rows]
            return data, "OK"
        
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return None, f"ERR:{str(e)}"
    
    def check_health(self) -> Dict[str, Any]:
        """Check database health."""
        client = self.get_client()
        
        if client is None:
            return {
                'status': 'disconnected',
                'message': 'Cannot connect to ClickHouse'
            }
        
        try:
            result = client.query("SELECT 1")
            return {
                'status': 'healthy',
                'message': 'ClickHouse connection OK',
                'version': self._get_version()
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get information about a table."""
        client = self.get_client()
        
        if client is None:
            return {'error': 'No database connection'}
        
        try:
            # Get column info
            result = client.query(f"DESCRIBE TABLE {table_name}")
            columns = []
            for row in result.result_rows:
                columns.append({
                    'name': row[0],
                    'type': row[1],
                    'default_type': row[2] if len(row) > 2 else None
                })
            
            # Get row count
            count_result = client.query(f"SELECT count() FROM {table_name}")
            row_count = count_result.result_rows[0][0] if count_result.result_rows else 0
            
            return {
                'table': table_name,
                'columns': columns,
                'row_count': row_count
            }
        
        except Exception as e:
            return {'error': str(e)}
    
    def preview_result(self, data: Any, max_rows: int = 5) -> str:
        """
        Generate preview text for query results.
        
        Args:
            data: Query result data
            max_rows: Maximum rows to include
        
        Returns:
            JSON string preview
        """
        if data is None:
            return "null"
        
        try:
            if isinstance(data, list):
                preview_data = data[:max_rows]
            else:
                preview_data = data
            
            return json.dumps(preview_data, ensure_ascii=False, indent=2)
        except Exception:
            return "null"
    
    def _get_version(self) -> str:
        """Get ClickHouse version."""
        try:
            result = self._client.query("SELECT version()")
            return result.result_rows[0][0] if result.result_rows else "unknown"
        except Exception:
            return "unknown"
    
    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected and self._client is not None
