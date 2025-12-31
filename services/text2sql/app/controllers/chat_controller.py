"""
Chat Controller
Handle chat and SQL generation requests
"""

import logging
from typing import Dict, Any
from flask import current_app
from sklearn.metrics import accuracy_score

from ..services import SQLGeneratorService, SchemaService, MemoryService, DatabaseService

logger = logging.getLogger(__name__)


class ChatController:
    """Controller for chat and SQL generation endpoints."""
    
    def __init__(self):
        """Initialize controller with services."""
        self.sql_generator = SQLGeneratorService()
        self.schema_service = SchemaService(
            upload_folder=current_app.config.get('UPLOAD_FOLDER', 'uploads')
        )
        self.memory_service = MemoryService(
            memory_dir=str(current_app.config.get('MEMORY_DIR', 'knowledge_base/memory')),
            data_dir=str(current_app.config.get('DATA_DIR', 'data'))
        )
        self.db_service = DatabaseService(current_app.config)
    
    def find_or_ask_confirmation(self, question: str) -> Dict[str, Any]:
        """
        Find question in dataset or ask for confirmation.
        
        Args:
            question: User question
        
        Returns:
            Response with SQL or confirmation request
        """
        # Try to find in existing dataset
        sql = self.memory_service.find_in_dataset(
            question, 
            self.schema_service.active_tables
        )
        
        if sql:
            # Found in dataset - execute and return
            data, status = self.db_service.execute_sql(sql)
            
            return {
                'sql': sql,
                'source': 'dataset',
                'result': data,
                'status': status,
                'preview': self.db_service.preview_result(data)
            }
        
        # Not found - ask for confirmation
        return {
            'message': f'Không tìm thấy SQL cho câu hỏi này. Bạn muốn AI tạo SQL không? (có/không)',
            'question': question,
            'needs_confirmation': True
        }
    
    def generate_sql_with_confirmation(self, question: str, model: str = 'grok') -> Dict[str, Any]:
        """
        Generate SQL after user confirmation.
        
        Args:
            question: User question
            model: AI model to use
        
        Returns:
            Generated SQL with execution result
        """
        try:
            # Get schema
            schema_text = self.schema_service.read_all_schemas()
            
            if not schema_text:
                return {
                    'error': 'Chưa upload schema. Vui lòng upload schema trước.',
                    'needs_schema': True
                }
            
            # Generate SQL
            sql = self.sql_generator.generate_sql(schema_text, question, model)
            
            # Try to execute
            data, status = self.db_service.execute_sql(sql)
            
            return {
                'sql': sql,
                'source': 'generated',
                'model': model,
                'result': data,
                'status': status,
                'preview': self.db_service.preview_result(data),
                'needs_check': True,  # User should approve to save
                'message': 'SQL đã được tạo. Xem kết quả và gọi /check để lưu vào memory nếu đúng.'
            }
        
        except Exception as e:
            logger.error(f"SQL generation error: {e}")
            return {
                'error': f'Lỗi tạo SQL: {str(e)}',
                'question': question
            }
    
    def approve_sql(self, question: str, sql: str) -> Dict[str, Any]:
        """
        Approve and save SQL to memory.
        
        Args:
            question: User question
            sql: Generated SQL
        
        Returns:
            Save result
        """
        # Infer table from SQL
        table = self.memory_service.infer_table_from_sql(
            sql, 
            self.schema_service.known_tables
        )
        
        # Save to memory
        success, message = self.memory_service.save_to_memory(
            question, sql, table
        )
        
        if success:
            return {
                'message': message,
                'saved': True,
                'table': table
            }
        else:
            return {
                'error': message,
                'saved': False
            }
    
    def refine_sql(self, question: str, prev_sql: str, 
                   feedback: str, extra_context: str, 
                   model: str = 'gemini') -> Dict[str, Any]:
        """
        Refine an existing SQL query.
        
        Args:
            question: Original question
            prev_sql: Previous SQL
            feedback: What was wrong
            extra_context: Additional constraints
            model: AI model to use
        
        Returns:
            Refined SQL with execution result
        """
        try:
            schema_text = self.schema_service.read_all_schemas()
            
            if not schema_text:
                return {
                    'error': 'Chưa upload schema',
                    'needs_schema': True
                }
            
            # Refine SQL
            sql = self.sql_generator.refine_sql(
                schema_text, question, prev_sql, 
                feedback, extra_context, model
            )
            
            # Execute refined SQL
            data, status = self.db_service.execute_sql(sql)
            
            return {
                'sql': sql,
                'previous_sql': prev_sql,
                'model': model,
                'result': data,
                'status': status,
                'preview': self.db_service.preview_result(data),
                'needs_check': True
            }
        
        except Exception as e:
            logger.error(f"SQL refinement error: {e}")
            return {
                'error': f'Lỗi refine SQL: {str(e)}'
            }
    
    def evaluate_model(self) -> Dict[str, Any]:
        """
        Evaluate model using eval dataset.
        
        Returns:
            Evaluation results
        """
        eval_data = self.memory_service.load_evaluation_data()
        
        if not eval_data:
            return {
                'error': 'Không tìm thấy file eval.jsonl',
                'accuracy': 0
            }
        
        expected = []
        predicted = []
        results = []
        
        for item in eval_data:
            question = item.get('question', '')
            expected_sql = item.get('sql', '').strip()
            
            # Find in dataset
            found_sql = self.memory_service.find_in_dataset(question)
            
            if found_sql:
                found_sql = found_sql.strip()
            else:
                found_sql = ''
            
            # Exact match
            match = 1 if expected_sql.lower() == found_sql.lower() else 0
            expected.append(1)
            predicted.append(match)
            
            results.append({
                'question': question,
                'expected': expected_sql,
                'found': found_sql,
                'match': bool(match)
            })
        
        accuracy = accuracy_score(expected, predicted) if expected else 0
        
        return {
            'total': len(eval_data),
            'matched': sum(predicted),
            'accuracy': round(accuracy * 100, 2),
            'results': results[:20]  # First 20 for preview
        }
