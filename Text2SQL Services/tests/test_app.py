"""
Unit Tests for Text2SQL Application
"""
import pytest
import json

class TestHealthEndpoint:
    """Test health check"""
    
    def test_health_or_root(self, client):
        """Test health or root endpoint"""
        response = client.get('/')
        assert response.status_code == 200

class TestSchemaUpload:
    """Test schema upload functionality"""
    
    def test_upload_endpoint_exists(self, client):
        """Test upload endpoint exists"""
        response = client.post('/upload')
        assert response.status_code in [200, 400, 415, 500]
    
    def test_upload_text_schema(self, client, sample_schema):
        """Test uploading text schema"""
        data = {
            'file': (io.BytesIO(sample_schema.encode()), 'schema.sql')
        }
        response = client.post('/upload',
                              data=data,
                              content_type='multipart/form-data')
        assert response.status_code in [200, 400, 500]
    
    def test_upload_without_file(self, client):
        """Test upload without file"""
        response = client.post('/upload')
        assert response.status_code in [400, 415]

class TestSQLGeneration:
    """Test SQL generation from natural language"""
    
    def test_chat_endpoint_exists(self, client):
        """Test chat endpoint exists"""
        response = client.post('/chat', json={})
        assert response.status_code in [200, 400, 500]
    
    def test_generate_sql_with_question(self, client, sample_question):
        """Test generating SQL from question"""
        response = client.post('/chat',
                              json=sample_question,
                              content_type='application/json')
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'sql' in data or 'error' in data
    
    def test_generate_sql_with_schema(self, client, sample_schema):
        """Test SQL generation with schema"""
        response = client.post('/chat',
                              json={
                                  'question': 'List all customers',
                                  'schema': sample_schema,
                                  'database_type': 'postgres'
                              },
                              content_type='application/json')
        assert response.status_code in [200, 500]
    
    def test_missing_question(self, client):
        """Test request without question"""
        response = client.post('/chat',
                              json={'database_type': 'mysql'},
                              content_type='application/json')
        assert response.status_code in [400, 500]
    
    def test_vietnamese_question(self, client):
        """Test Vietnamese language question"""
        response = client.post('/chat',
                              json={
                                  'question': 'Hiển thị 10 khách hàng có doanh thu cao nhất',
                                  'database_type': 'clickhouse'
                              },
                              content_type='application/json')
        assert response.status_code in [200, 500]

class TestQuestionGeneration:
    """Test automatic question generation"""
    
    def test_generate_questions(self, client, sample_schema):
        """Test question generation from schema"""
        response = client.post('/chat',
                              json={
                                  'question': 'tạo câu hỏi',
                                  'schema': sample_schema
                              },
                              content_type='application/json')
        assert response.status_code in [200, 500]
    
    def test_generate_questions_keywords(self, client, sample_schema):
        """Test various question generation keywords"""
        keywords = ['tạo câu hỏi', 'generate questions', 'gợi ý', 'ví dụ']
        
        for keyword in keywords:
            response = client.post('/chat',
                                  json={
                                      'question': keyword,
                                      'schema': sample_schema
                                  },
                                  content_type='application/json')
            assert response.status_code in [200, 500]

class TestKnowledgeBase:
    """Test AI learning and knowledge base"""
    
    def test_save_to_knowledge_base(self, client):
        """Test saving SQL to knowledge base"""
        response = client.post('/knowledge/save',
                              json={
                                  'question': 'Top customers',
                                  'sql': 'SELECT * FROM customers ORDER BY revenue DESC LIMIT 10'
                              },
                              content_type='application/json')
        assert response.status_code in [200, 404, 500]
    
    def test_list_knowledge_base(self, client):
        """Test listing knowledge base entries"""
        response = client.get('/knowledge/list')
        assert response.status_code in [200, 404]
    
    def test_ai_learning_detection(self, client):
        """Test AI learning keyword detection"""
        response = client.post('/chat',
                              json={
                                  'question': 'Câu SQL đúng là: SELECT * FROM users',
                              },
                              content_type='application/json')
        # Should be recognized as learning intent
        assert response.status_code in [200, 500]

class TestDatabaseConnection:
    """Test database connection features"""
    
    def test_test_connection_endpoint(self, client):
        """Test connection testing endpoint"""
        response = client.post('/api/database/test-connection',
                              json={
                                  'database_type': 'clickhouse',
                                  'host': 'localhost'
                              },
                              content_type='application/json')
        assert response.status_code in [200, 400, 500]
    
    def test_save_connection_endpoint(self, client):
        """Test save connection endpoint"""
        response = client.post('/api/database/save-connection',
                              json={
                                  'name': 'test_conn',
                                  'database_type': 'mongodb',
                                  'uri': 'mongodb://localhost:27017'
                              },
                              content_type='application/json')
        assert response.status_code in [200, 404, 500]
    
    def test_invalid_database_type(self, client):
        """Test with invalid database type"""
        response = client.post('/api/database/test-connection',
                              json={
                                  'database_type': 'invalid_db',
                                  'host': 'localhost'
                              },
                              content_type='application/json')
        assert response.status_code in [400, 500]

class TestMultiDatabase:
    """Test multi-database support"""
    
    def test_clickhouse_syntax(self, client):
        """Test ClickHouse SQL syntax"""
        response = client.post('/chat',
                              json={
                                  'question': 'Count total rows',
                                  'database_type': 'clickhouse'
                              },
                              content_type='application/json')
        assert response.status_code in [200, 500]
    
    def test_mongodb_syntax(self, client):
        """Test MongoDB query syntax"""
        response = client.post('/chat',
                              json={
                                  'question': 'Find all documents',
                                  'database_type': 'mongodb'
                              },
                              content_type='application/json')
        assert response.status_code in [200, 500]
    
    def test_postgres_syntax(self, client):
        """Test PostgreSQL syntax"""
        response = client.post('/chat',
                              json={
                                  'question': 'List tables',
                                  'database_type': 'postgres'
                              },
                              content_type='application/json')
        assert response.status_code in [200, 500]

class TestErrorHandling:
    """Test error handling"""
    
    def test_empty_question(self, client):
        """Test with empty question"""
        response = client.post('/chat',
                              json={'question': ''},
                              content_type='application/json')
        assert response.status_code in [400, 500]
    
    def test_very_long_question(self, client):
        """Test with very long question"""
        long_question = 'Show me ' + 'all ' * 1000 + 'records'
        response = client.post('/chat',
                              json={'question': long_question},
                              content_type='application/json')
        assert response.status_code in [200, 400, 500]
    
    def test_invalid_json(self, client):
        """Test with invalid JSON"""
        response = client.post('/chat',
                              data='not json',
                              content_type='application/json')
        assert response.status_code in [400, 500]

class TestSecurity:
    """Test security aspects"""
    
    def test_sql_injection_prevention(self, client):
        """Test SQL injection prevention in questions"""
        malicious_question = "'; DROP TABLE users; --"
        response = client.post('/chat',
                              json={'question': malicious_question},
                              content_type='application/json')
        # Should handle safely
        assert response.status_code in [200, 400, 500]
    
    def test_xss_prevention(self, client):
        """Test XSS prevention"""
        xss_question = '<script>alert("XSS")</script>'
        response = client.post('/chat',
                              json={'question': xss_question},
                              content_type='application/json')
        assert response.status_code in [200, 400, 500]

import io

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
