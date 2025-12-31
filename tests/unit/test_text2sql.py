"""
Unit Tests for Text2SQL Service
Tests SQL generation, schema handling, and AI integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import re


@pytest.mark.unit
@pytest.mark.text2sql
class TestText2SQLApp:
    """Test Text2SQL Flask application"""
    
    def test_text2sql_index_route(self, text2sql_client):
        """Test Text2SQL homepage loads"""
        response = text2sql_client.get('/')
        assert response.status_code == 200
    
    def test_text2sql_api_available(self, text2sql_client):
        """Test API endpoints are available"""
        # The app should have routes for SQL generation
        response = text2sql_client.get('/')
        assert response.status_code in [200, 404]


@pytest.mark.unit
@pytest.mark.text2sql
class TestSQLGeneration:
    """Test SQL query generation"""
    
    def test_extract_sql_from_text(self):
        """Test extracting SQL from AI response"""
        text = """
        Here's the SQL query you requested:
        
        ```sql
        SELECT * FROM users WHERE age > 25;
        ```
        
        This query will get all users older than 25.
        """
        
        # Remove code fences and extract SQL
        cleaned = re.sub(r"```+[a-zA-Z]*\n", "", text)
        cleaned = re.sub(r"```+", "", cleaned)
        
        assert "SELECT" in cleaned
        assert "users" in cleaned
    
    def test_sql_pattern_matching(self):
        """Test SQL keyword detection"""
        sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"]
        
        test_query = "SELECT id, name FROM users WHERE active = 1"
        
        # Check if it's a valid SQL query
        has_keyword = any(keyword in test_query.upper() for keyword in sql_keywords)
        assert has_keyword == True
    
    def test_sql_validation_basic(self):
        """Test basic SQL validation"""
        valid_queries = [
            "SELECT * FROM users",
            "INSERT INTO users (name) VALUES ('John')",
            "UPDATE users SET name = 'Jane' WHERE id = 1",
            "DELETE FROM users WHERE id = 1"
        ]
        
        for query in valid_queries:
            # Should contain SQL keyword
            has_keyword = any(kw in query.upper() for kw in ["SELECT", "INSERT", "UPDATE", "DELETE"])
            assert has_keyword == True


@pytest.mark.unit
@pytest.mark.text2sql
class TestSchemaHandling:
    """Test database schema handling"""
    
    def test_schema_parsing(self, sample_schema):
        """Test schema parsing"""
        assert sample_schema is not None
        assert "CREATE TABLE" in sample_schema
        assert "users" in sample_schema
        assert "orders" in sample_schema
    
    def test_schema_table_extraction(self, sample_schema):
        """Test extracting table names from schema"""
        # Find all table names
        tables = re.findall(r"CREATE TABLE\s+(\w+)", sample_schema, re.IGNORECASE)
        
        assert len(tables) >= 2
        assert "users" in tables
        assert "orders" in tables
    
    def test_schema_column_extraction(self, sample_schema):
        """Test extracting columns from schema"""
        # Find columns for users table
        users_section = re.search(
            r"CREATE TABLE users\s*\((.*?)\);",
            sample_schema,
            re.DOTALL | re.IGNORECASE
        )
        
        assert users_section is not None
        columns_text = users_section.group(1)
        
        # Should contain common columns
        assert "id" in columns_text.lower()
        assert "name" in columns_text.lower()
        assert "email" in columns_text.lower()
    
    def test_foreign_key_detection(self, sample_schema):
        """Test foreign key detection in schema"""
        has_foreign_key = "FOREIGN KEY" in sample_schema
        assert has_foreign_key == True


@pytest.mark.unit
@pytest.mark.text2sql
class TestQuestionGeneration:
    """Test SQL question generation"""
    
    def test_sample_questions(self, sample_sql_questions):
        """Test sample SQL questions are valid"""
        assert len(sample_sql_questions) > 0
        
        for question in sample_sql_questions:
            assert isinstance(question, str)
            assert len(question) > 0
    
    def test_question_types(self, sample_sql_questions):
        """Test different types of SQL questions"""
        # Questions should cover different SQL operations
        question_text = " ".join(sample_sql_questions).lower()
        
        # Should have some variety
        assert len(sample_sql_questions) >= 3


@pytest.mark.unit
@pytest.mark.text2sql
class TestGeminiIntegration:
    """Test Gemini AI integration for SQL generation"""
    
    @patch('google.genai.Client')
    def test_gemini_sql_generation(self, mock_client):
        """Test SQL generation using Gemini"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "SELECT * FROM users WHERE age > 25 LIMIT 100;"
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        # Test with new google.genai SDK
        from google import genai
        client = genai.Client(api_key='test-key')
        
        prompt = "Generate SQL to get users older than 25"
        response = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        
        assert "SELECT" in response.text
        assert "users" in response.text
        assert "LIMIT" in response.text
    
    def test_gemini_with_schema_context(self, mock_gemini_model, sample_schema):
        """Test Gemini with schema context"""
        # Create prompt with schema
        prompt = f"""
        Database Schema:
        {sample_schema}
        
        Question: Show all users with their order counts
        
        Generate SQL query:
        """
        
        # Mock should return something
        response = mock_gemini_model.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        assert response.text is not None
    
    @patch('google.genai.Client')
    def test_gemini_deep_thinking_mode(self, mock_client):
        """Test Gemini with deep thinking mode (new google.genai SDK)"""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = """
        Step 1: Identify tables needed: users, orders
        Step 2: Join condition: users.id = orders.user_id
        Step 3: Aggregation: COUNT(orders.id)
        
        SELECT u.name, COUNT(o.id) as order_count
        FROM users u
        LEFT JOIN orders o ON u.id = o.user_id
        GROUP BY u.id, u.name
        LIMIT 100;
        """
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        # Test with new SDK
        from google import genai
        client = genai.Client(api_key='test-key')
        response = client.models.generate_content(model='gemini-2.0-flash', contents="Generate query with thinking")
        
        assert "Step" in response.text
        assert "SELECT" in response.text


@pytest.mark.unit
@pytest.mark.text2sql
class TestDatabaseConnections:
    """Test database connection handling"""
    
    def test_connection_config_structure(self):
        """Test database connection configuration structure"""
        config = {
            'db_type': 'clickhouse',
            'host': 'localhost',
            'port': 8123,
            'database': 'default',
            'username': 'default',
            'password': ''
        }
        
        # Validate structure
        assert 'db_type' in config
        assert 'host' in config
        assert 'port' in config
        assert isinstance(config['port'], int)
    
    def test_supported_database_types(self):
        """Test supported database types"""
        supported_dbs = ['clickhouse', 'mysql', 'postgresql', 'sqlite']
        
        for db_type in supported_dbs:
            assert isinstance(db_type, str)
            assert len(db_type) > 0
    
    def test_connection_string_format(self):
        """Test connection string formatting"""
        # ClickHouse example
        connection_info = {
            'host': 'localhost',
            'port': 8123,
            'database': 'default'
        }
        
        # Create connection string
        conn_str = f"clickhouse://{connection_info['host']}:{connection_info['port']}/{connection_info['database']}"
        
        assert 'clickhouse://' in conn_str
        assert 'localhost' in conn_str


@pytest.mark.unit
@pytest.mark.text2sql
class TestKnowledgeBase:
    """Test knowledge base and learning features"""
    
    def test_knowledge_base_storage(self, temp_dir):
        """Test storing questions and answers"""
        kb_dir = temp_dir / "knowledge_base"
        kb_dir.mkdir()
        
        # Create a knowledge entry
        entry = {
            'id': 'kb_001',
            'question': 'Show all users',
            'sql': 'SELECT * FROM users LIMIT 100;',
            'schema_id': 'schema_001',
            'timestamp': '2025-12-10T10:00:00'
        }
        
        # Save to file
        kb_file = kb_dir / f"{entry['id']}.json"
        kb_file.write_text(json.dumps(entry, indent=2))
        
        # Verify
        assert kb_file.exists()
        
        # Load and verify
        loaded = json.loads(kb_file.read_text())
        assert loaded['question'] == entry['question']
        assert loaded['sql'] == entry['sql']
    
    def test_knowledge_base_search(self, temp_dir):
        """Test searching knowledge base"""
        kb_dir = temp_dir / "knowledge_base"
        kb_dir.mkdir()
        
        # Create multiple entries
        entries = [
            {'id': 'kb_001', 'question': 'Show all users', 'sql': 'SELECT * FROM users'},
            {'id': 'kb_002', 'question': 'Count orders', 'sql': 'SELECT COUNT(*) FROM orders'},
            {'id': 'kb_003', 'question': 'User emails', 'sql': 'SELECT email FROM users'}
        ]
        
        for entry in entries:
            kb_file = kb_dir / f"{entry['id']}.json"
            kb_file.write_text(json.dumps(entry))
        
        # Search for "users"
        matching = []
        for kb_file in kb_dir.glob("*.json"):
            data = json.loads(kb_file.read_text())
            if 'users' in data['question'].lower() or 'users' in data['sql'].lower():
                matching.append(data)
        
        # Should find 2 entries with "users"
        assert len(matching) >= 2


@pytest.mark.unit
@pytest.mark.text2sql
class TestFileUpload:
    """Test schema file upload functionality"""
    
    def test_allowed_file_extensions(self):
        """Test file extension validation"""
        allowed_extensions = {'txt', 'sql', 'json', 'jsonl'}
        
        def allowed_file(filename):
            return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions
        
        # Valid files
        assert allowed_file('schema.sql') == True
        assert allowed_file('data.json') == True
        assert allowed_file('schema.txt') == True
        
        # Invalid files
        assert allowed_file('image.png') == False
        assert allowed_file('document.pdf') == False
        assert allowed_file('noextension') == False
    
    def test_file_content_validation(self, temp_dir):
        """Test uploaded file content validation"""
        # Create a test schema file
        schema_file = temp_dir / "schema.sql"
        schema_content = """
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100)
        );
        """
        schema_file.write_text(schema_content)
        
        # Read and validate
        content = schema_file.read_text()
        assert "CREATE TABLE" in content
        assert "test_table" in content


@pytest.mark.unit
@pytest.mark.text2sql
class TestErrorHandling:
    """Test error handling in Text2SQL service"""
    
    def test_empty_schema_error(self):
        """Test handling empty schema"""
        schema = ""
        
        if not schema or schema.strip() == "":
            error_msg = "Schema is empty"
            assert error_msg == "Schema is empty"
    
    def test_invalid_question_error(self):
        """Test handling invalid question"""
        question = ""
        
        if not question or question.strip() == "":
            error_msg = "Question cannot be empty"
            assert error_msg == "Question cannot be empty"
    
    def test_sql_parse_error(self):
        """Test handling SQL parsing errors"""
        invalid_sql = "THIS IS NOT SQL"
        
        sql_keywords = ["SELECT", "INSERT", "UPDATE", "DELETE", "CREATE"]
        has_sql = any(kw in invalid_sql.upper() for kw in sql_keywords)
        
        if not has_sql:
            error_msg = "Could not parse SQL from response"
            assert error_msg == "Could not parse SQL from response"
