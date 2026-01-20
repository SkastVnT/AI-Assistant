"""
Advanced Features for Document Intelligence Service
Provides processing history tracking and quick actions
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class ProcessingRecord:
    """Record of a document processing operation"""
    id: str
    filename: str
    operation: str
    timestamp: str
    status: str
    output_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class ProcessingHistory:
    """
    Tracks document processing history
    Persists to a JSON file for recovery across restarts
    """
    
    def __init__(self, history_file: Path):
        """
        Initialize processing history
        
        Args:
            history_file: Path to the history JSON file
        """
        self.history_file = Path(history_file)
        self.records: List[ProcessingRecord] = []
        self._load_history()
    
    def _load_history(self) -> None:
        """Load history from file if it exists"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.records = [
                        ProcessingRecord(**record) 
                        for record in data.get('records', [])
                    ]
                logger.info(f"Loaded {len(self.records)} history records")
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")
                self.records = []
        else:
            # Create parent directories if needed
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.records = []
    
    def _save_history(self) -> None:
        """Save history to file"""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'records': [asdict(r) for r in self.records],
                    'updated_at': datetime.now().isoformat()
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def add_record(
        self,
        record_id: str,
        filename: str,
        operation: str,
        status: str = 'pending',
        output_path: Optional[str] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ProcessingRecord:
        """
        Add a new processing record
        
        Args:
            record_id: Unique identifier for the record
            filename: Name of the processed file
            operation: Type of operation performed
            status: Status of the operation
            output_path: Path to the output file
            error: Error message if failed
            metadata: Additional metadata
        
        Returns:
            The created ProcessingRecord
        """
        record = ProcessingRecord(
            id=record_id,
            filename=filename,
            operation=operation,
            timestamp=datetime.now().isoformat(),
            status=status,
            output_path=output_path,
            error=error,
            metadata=metadata or {}
        )
        self.records.append(record)
        self._save_history()
        return record
    
    def update_record(
        self,
        record_id: str,
        status: Optional[str] = None,
        output_path: Optional[str] = None,
        error: Optional[str] = None
    ) -> Optional[ProcessingRecord]:
        """Update an existing record"""
        for record in self.records:
            if record.id == record_id:
                if status:
                    record.status = status
                if output_path:
                    record.output_path = output_path
                if error:
                    record.error = error
                self._save_history()
                return record
        return None
    
    def get_recent(self, limit: int = 10) -> List[ProcessingRecord]:
        """Get recent processing records"""
        return self.records[-limit:]
    
    def get_by_status(self, status: str) -> List[ProcessingRecord]:
        """Get records by status"""
        return [r for r in self.records if r.status == status]
    
    def clear_history(self) -> None:
        """Clear all history records"""
        self.records = []
        self._save_history()


class QuickActions:
    """
    Predefined quick actions for common document operations
    """
    
    def __init__(self):
        """Initialize quick actions"""
        self.actions = self._load_default_actions()
    
    def _load_default_actions(self) -> List[Dict[str, Any]]:
        """Load default quick actions"""
        return [
            {
                'id': 'ocr_basic',
                'name': 'Basic OCR',
                'description': 'Extract text from image using OCR',
                'icon': '📝',
                'params': {
                    'mode': 'text',
                    'language': 'vi'
                }
            },
            {
                'id': 'ocr_structured',
                'name': 'Structured OCR',
                'description': 'Extract text with layout preservation',
                'icon': '📋',
                'params': {
                    'mode': 'structured',
                    'language': 'vi'
                }
            },
            {
                'id': 'ocr_table',
                'name': 'Table Extraction',
                'description': 'Extract tables from document',
                'icon': '📊',
                'params': {
                    'mode': 'table',
                    'language': 'vi'
                }
            },
            {
                'id': 'pdf_to_text',
                'name': 'PDF to Text',
                'description': 'Convert PDF document to text',
                'icon': '📄',
                'params': {
                    'mode': 'pdf',
                    'output_format': 'text'
                }
            },
            {
                'id': 'ai_enhance',
                'name': 'AI Enhancement',
                'description': 'Enhance OCR results with AI',
                'icon': '🤖',
                'params': {
                    'mode': 'text',
                    'ai_enhance': True
                }
            },
            {
                'id': 'batch_process',
                'name': 'Batch Process',
                'description': 'Process multiple files at once',
                'icon': '📁',
                'params': {
                    'mode': 'batch'
                }
            }
        ]
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all available quick actions"""
        return self.actions
    
    def get_by_id(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific action by ID"""
        for action in self.actions:
            if action['id'] == action_id:
                return action
        return None
    
    def add_custom_action(
        self,
        action_id: str,
        name: str,
        description: str,
        params: Dict[str, Any],
        icon: str = '⚡'
    ) -> Dict[str, Any]:
        """Add a custom action"""
        action = {
            'id': action_id,
            'name': name,
            'description': description,
            'icon': icon,
            'params': params
        }
        self.actions.append(action)
        return action
    
    def remove_action(self, action_id: str) -> bool:
        """Remove an action by ID"""
        for i, action in enumerate(self.actions):
            if action['id'] == action_id:
                self.actions.pop(i)
                return True
        return False
