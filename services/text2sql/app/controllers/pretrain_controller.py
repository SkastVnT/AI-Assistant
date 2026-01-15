"""
Pretrain Controller
Handle pre-training and configuration requests
"""

import os
import json
import logging
from typing import Dict, Any
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)


class PretrainController:
    """Controller for pre-training endpoints."""
    
    def __init__(self):
        """Initialize controller."""
        self.pretrain_dir = current_app.config.get('PRETRAIN_DIR', 'pretrain')
        os.makedirs(self.pretrain_dir, exist_ok=True)
    
    def run_pretrain(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run pre-training process.
        
        Args:
            data: Pre-training configuration
        
        Returns:
            Pre-training result
        """
        # Placeholder for pre-training logic
        # This would integrate with the existing pretrain functionality
        
        return {
            'status': 'started',
            'message': 'Pre-training process initiated',
            'config': data
        }
    
    def get_pretrain_files(self) -> Dict[str, Any]:
        """Get list of pretrain files."""
        files = []
        
        if os.path.isdir(self.pretrain_dir):
            for filename in os.listdir(self.pretrain_dir):
                filepath = os.path.join(self.pretrain_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    files.append({
                        'name': filename,
                        'size': stat.st_size,
                        'modified': stat.st_mtime
                    })
        
        return {
            'files': files,
            'count': len(files),
            'directory': self.pretrain_dir
        }
    
    def get_config(self) -> Dict[str, Any]:
        """Get pretrain configuration."""
        return {
            'pretrain_dir': str(self.pretrain_dir),
            'sqlcoder_backend': current_app.config.get('SQLCODER_BACKEND', 'hf'),
            'sqlcoder_model': current_app.config.get('SQLCODER_MODEL', 'defog/sqlcoder-7b-2'),
            'default_model': current_app.config.get('DEFAULT_SQL_MODEL', 'grok'),
            'refine_strategy': current_app.config.get('REFINE_STRATEGY', 'gemini')
        }
    
    def get_report(self) -> Dict[str, Any]:
        """Get pre-training report."""
        report_file = os.path.join(self.pretrain_dir, 'report.json')
        
        if os.path.exists(report_file):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading report: {e}")
        
        return {
            'status': 'no_report',
            'message': 'No pre-training report available'
        }
