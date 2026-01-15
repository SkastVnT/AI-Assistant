"""
Memory Service
Handle Q&A memory storage and retrieval
"""

import os
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set

logger = logging.getLogger(__name__)


class MemoryService:
    """Service for managing Q&A memory and datasets."""
    
    def __init__(self, memory_dir: str = 'knowledge_base/memory',
                 data_dir: str = 'data'):
        """
        Initialize Memory Service.
        
        Args:
            memory_dir: Directory for memory files
            data_dir: Directory for dataset files
        """
        self.memory_dir = memory_dir
        self.data_dir = data_dir
        
        os.makedirs(memory_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)
    
    def find_in_dataset(self, question: str, 
                       active_tables: Set[str] = None) -> Optional[str]:
        """
        Find matching SQL in dataset.
        
        Args:
            question: User question
            active_tables: Filter by active tables
        
        Returns:
            Matching SQL or None
        """
        q = (question or "").strip().lower()
        
        dataset = self.load_dataset(active_tables)
        for item in dataset:
            item_q = (item.get("question") or "").strip().lower()
            if item_q == q:
                sql = (item.get("sql") or "").strip()
                if sql:
                    return sql
        
        return None
    
    def load_dataset(self, active_tables: Set[str] = None) -> List[Dict]:
        """
        Load dataset from files.
        
        Args:
            active_tables: Filter by active tables
        
        Returns:
            List of Q&A items
        """
        items = []
        
        # Load base dataset
        base_file = os.path.join(self.data_dir, 'dataset_base.jsonl')
        if os.path.exists(base_file):
            items.extend(self._load_jsonl(base_file))
        
        # Load memory files
        if os.path.isdir(self.memory_dir):
            for filename in os.listdir(self.memory_dir):
                if filename.endswith('.txt') or filename.endswith('.jsonl'):
                    filepath = os.path.join(self.memory_dir, filename)
                    items.extend(self._load_jsonl(filepath))
        
        # Filter by active tables if specified
        if active_tables:
            filtered = []
            for item in items:
                item_table = item.get('table', '')
                if not item_table or item_table in active_tables:
                    filtered.append(item)
            items = filtered
        
        return items
    
    def save_to_memory(self, question: str, sql: str, 
                      table: str = None,
                      agg_file: str = None) -> Tuple[bool, str]:
        """
        Save Q&A pair to memory.
        
        Args:
            question: User question
            sql: Generated SQL
            table: Table name for the query
            agg_file: Aggregated file path for multi-schema mode
        
        Returns:
            Tuple of (success, message)
        """
        try:
            if agg_file:
                # Multi-schema mode
                filepath = agg_file
            elif table:
                # Per-table memory file
                filepath = os.path.join(self.memory_dir, f'memory_{table}.txt')
            else:
                # Default memory file
                filepath = os.path.join(self.memory_dir, 'memory_default.txt')
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            entry = {
                'question': question,
                'sql': sql
            }
            if table:
                entry['table'] = table
            
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            return True, f"Saved to {filepath}"
        
        except Exception as e:
            logger.error(f"Error saving to memory: {e}")
            return False, f"Error: {str(e)}"
    
    def infer_table_from_sql(self, sql: str, 
                            known_tables: Set[str]) -> Optional[str]:
        """
        Infer table name from SQL query.
        
        Args:
            sql: SQL query
            known_tables: Set of known table names
        
        Returns:
            Table name or None
        """
        if not sql or not known_tables:
            return None
        
        # Sort by length (prefer longer names to avoid prefix matches)
        for table in sorted(known_tables, key=len, reverse=True):
            pattern = rf"(?<!\w)`?{re.escape(table)}`?(?!\w)"
            if re.search(pattern, sql, flags=re.IGNORECASE):
                return table
        
        return None
    
    def load_evaluation_data(self) -> List[Dict]:
        """Load evaluation dataset."""
        eval_file = os.path.join(self.data_dir, 'eval.jsonl')
        if os.path.exists(eval_file):
            return self._load_jsonl(eval_file)
        return []
    
    def _load_jsonl(self, filepath: str) -> List[Dict]:
        """Load JSONL file."""
        items = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            items.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"Error loading {filepath}: {e}")
        
        return items
    
    def get_memory_stats(self) -> Dict:
        """Get memory statistics."""
        stats = {
            'total_items': 0,
            'memory_files': [],
            'tables': set()
        }
        
        if os.path.isdir(self.memory_dir):
            for filename in os.listdir(self.memory_dir):
                if filename.endswith('.txt') or filename.endswith('.jsonl'):
                    filepath = os.path.join(self.memory_dir, filename)
                    items = self._load_jsonl(filepath)
                    stats['total_items'] += len(items)
                    stats['memory_files'].append({
                        'name': filename,
                        'count': len(items)
                    })
                    
                    for item in items:
                        if 'table' in item:
                            stats['tables'].add(item['table'])
        
        stats['tables'] = list(stats['tables'])
        return stats
