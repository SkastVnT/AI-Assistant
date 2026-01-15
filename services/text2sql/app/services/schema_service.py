"""
Schema Service
Handle database schema upload and management
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import List, Set, Optional, Tuple
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


class SchemaService:
    """Service for managing database schemas."""
    
    ALLOWED_EXTENSIONS = {'txt', 'json', 'jsonl', 'csv', 'sql'}
    
    def __init__(self, upload_folder: str = 'uploads'):
        """
        Initialize Schema Service.
        
        Args:
            upload_folder: Directory for uploaded schema files
        """
        self.upload_folder = upload_folder
        self.schema_files: List[str] = []
        self.known_tables: Set[str] = set()
        self.last_table_uploaded: Optional[str] = None
        
        # Active state
        self.active_tables: Set[str] = set()
        self.active_primary_table: Optional[str] = None
        self.active_upload_order: List[str] = []
        self.active_idmap: dict = {}
        self.active_agg_file: Optional[str] = None
        
        os.makedirs(upload_folder, exist_ok=True)
    
    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def upload_schema(self, file, filename: str = None) -> Tuple[bool, str, dict]:
        """
        Upload and process a schema file.
        
        Args:
            file: File object to upload
            filename: Override filename
        
        Returns:
            Tuple of (success, message, data)
        """
        if not file:
            return False, "No file provided", {}
        
        filename = filename or file.filename
        if not filename:
            return False, "No filename provided", {}
        
        if not self.allowed_file(filename):
            return False, f"File type not allowed. Allowed: {self.ALLOWED_EXTENSIONS}", {}
        
        safe_filename = secure_filename(filename)
        filepath = os.path.join(self.upload_folder, safe_filename)
        
        try:
            file.save(filepath)
            self.schema_files.append(filepath)
            
            # Parse tables from file
            tables = self._parse_tables_from_file(filepath)
            self.known_tables.update(tables)
            
            if tables:
                self.last_table_uploaded = tables[0]
            
            return True, f"Schema uploaded: {safe_filename}", {
                'filename': safe_filename,
                'tables': list(tables),
                'total_tables': len(self.known_tables)
            }
        except Exception as e:
            logger.error(f"Error uploading schema: {e}")
            return False, f"Upload failed: {str(e)}", {}
    
    def read_all_schemas(self) -> str:
        """Read and concatenate all uploaded schemas."""
        parts = []
        for path in self.schema_files:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    parts.append(f.read().strip())
            except Exception as e:
                logger.warning(f"Error reading schema {path}: {e}")
        
        return "\n\n".join(parts)
    
    def get_schema_info(self) -> dict:
        """Get current schema information."""
        return {
            'files': [os.path.basename(f) for f in self.schema_files],
            'tables': list(self.known_tables),
            'active_tables': list(self.active_tables),
            'primary_table': self.active_primary_table,
            'schema_text': self.read_all_schemas()
        }
    
    def clear_schemas(self) -> bool:
        """Clear all uploaded schemas."""
        self.schema_files.clear()
        self.known_tables.clear()
        self.active_tables.clear()
        self.active_primary_table = None
        self.active_upload_order.clear()
        self.active_idmap.clear()
        self.active_agg_file = None
        
        # Clear upload folder
        try:
            for file in os.listdir(self.upload_folder):
                filepath = os.path.join(self.upload_folder, file)
                if os.path.isfile(filepath):
                    os.remove(filepath)
            return True
        except Exception as e:
            logger.error(f"Error clearing schemas: {e}")
            return False
    
    def _parse_tables_from_file(self, filepath: str) -> Set[str]:
        """Parse table names from schema file."""
        tables = set()
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            tables = self._parse_tables_from_text(content)
        except Exception as e:
            logger.warning(f"Error parsing tables from {filepath}: {e}")
        
        return tables
    
    def _parse_tables_from_text(self, text: str) -> Set[str]:
        """
        Parse table names from schema text.
        Supports CREATE TABLE, TABLE, and header annotations.
        """
        tables = set()
        
        # Pattern: CREATE TABLE table_name
        pattern1 = re.compile(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?', re.IGNORECASE)
        tables.update(pattern1.findall(text))
        
        # Pattern: TABLE: table_name
        pattern2 = re.compile(r'TABLE[:\s]+[`"\']?(\w+)[`"\']?', re.IGNORECASE)
        tables.update(pattern2.findall(text))
        
        # Pattern: -- Table: table_name (comment)
        pattern3 = re.compile(r'--\s*Table[:\s]+(\w+)', re.IGNORECASE)
        tables.update(pattern3.findall(text))
        
        # Normalize table names
        normalized = set()
        for table in tables:
            norm = self._normalize_table_name(table)
            if norm:
                normalized.add(norm)
        
        return normalized
    
    def _normalize_table_name(self, raw: str) -> str:
        """Normalize table name to lowercase alphanumeric with underscores."""
        if not raw:
            return ""
        # Remove backticks, quotes
        raw = raw.strip('`"\'')
        # Replace non-alphanumeric with underscore
        raw = re.sub(r'[^a-zA-Z0-9_]', '_', raw)
        return raw.lower().strip('_')
    
    def set_active_tables(self, tables: List[str]) -> None:
        """Set the active tables for current session."""
        self.active_tables = set(tables)
        if tables:
            self.active_primary_table = tables[0]
