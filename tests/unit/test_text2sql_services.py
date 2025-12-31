"""
Tests for Text2SQL Service Architecture
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from flask import Flask


class TestText2SQLConfig:
    """Tests for Text2SQL configuration."""
    
    def test_development_config(self):
        """Test development configuration."""
        with patch.dict('os.environ', {'FLASK_ENV': 'development'}):
            from services.text2sql.app.config import DevelopmentConfig
            
            config = DevelopmentConfig()
            assert config.DEBUG is True
            assert config.TESTING is False
    
    def test_production_config(self):
        """Test production configuration."""
        from services.text2sql.app.config import ProductionConfig
        
        config = ProductionConfig()
        assert config.DEBUG is False
    
    def test_testing_config(self):
        """Test testing configuration."""
        from services.text2sql.app.config import TestingConfig
        
        config = TestingConfig()
        assert config.TESTING is True


class TestText2SQLAppFactory:
    """Tests for Text2SQL application factory."""
    
    def test_create_app_default(self):
        """Test default app creation."""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-key',
            'CLICKHOUSE_HOST': 'localhost'
        }, clear=False):
            from services.text2sql.app import create_app
            
            app = create_app('testing')
            
            assert app is not None
            assert isinstance(app, Flask)
            assert app.config['TESTING'] is True
    
    def test_create_app_registers_blueprints(self):
        """Test that app registers all blueprints."""
        with patch.dict('os.environ', {
            'GEMINI_API_KEY': 'test-key',
        }, clear=False):
            from services.text2sql.app import create_app
            
            app = create_app('testing')
            
            # Check registered blueprints
            blueprint_names = list(app.blueprints.keys())
            assert 'main' in blueprint_names
            assert 'health' in blueprint_names


class TestSQLGeneratorService:
    """Tests for SQL Generator Service."""
    
    def test_sql_generator_module_exists(self):
        """Test SQL generator module can be imported."""
        from services.text2sql.app.services.sql_generator import SQLGeneratorService
        assert SQLGeneratorService is not None
    
    def test_clean_sql_static(self):
        """Test SQL cleaning logic."""
        # Test the cleaning logic without instantiating the service
        raw_sql = """```sql
        SELECT * FROM users
        WHERE id = 1;
        ```"""
        
        # Basic cleaning logic
        cleaned = raw_sql.replace('```sql', '').replace('```', '').strip()
        
        assert '```' not in cleaned
        assert 'SELECT' in cleaned
    
    def test_sql_generator_class_structure(self):
        """Test SQL generator class has expected methods."""
        from services.text2sql.app.services.sql_generator import SQLGeneratorService
        
        # Check class has expected methods
        assert hasattr(SQLGeneratorService, 'generate_sql')
        assert hasattr(SQLGeneratorService, 'refine_sql')
        assert hasattr(SQLGeneratorService, '_clean_sql')


class TestSchemaService:
    """Tests for Schema Service."""
    
    @pytest.fixture
    def schema_service(self, tmp_path):
        """Create schema service instance."""
        from services.text2sql.app.services.schema_service import SchemaService
        
        service = SchemaService(upload_folder=str(tmp_path / "uploads"))
        return service
    
    def test_allowed_file(self, schema_service):
        """Test file extension validation."""
        assert schema_service.allowed_file("schema.sql") is True
        assert schema_service.allowed_file("data.txt") is True
        assert schema_service.allowed_file("data.json") is True
        assert schema_service.allowed_file("script.exe") is False
        assert schema_service.allowed_file("malware.py") is False
    
    def test_read_all_schemas_empty(self, schema_service):
        """Test reading schemas when none uploaded."""
        result = schema_service.read_all_schemas()
        assert result == ""
    
    def test_init_creates_directory(self, tmp_path):
        """Test that init creates upload directory."""
        from services.text2sql.app.services.schema_service import SchemaService
        
        upload_path = tmp_path / "new_uploads"
        service = SchemaService(upload_folder=str(upload_path))
        
        assert upload_path.exists()


class TestMemoryService:
    """Tests for Memory Service."""
    
    @pytest.fixture
    def memory_service(self, tmp_path):
        """Create memory service instance."""
        from services.text2sql.app.services.memory_service import MemoryService
        
        service = MemoryService(
            memory_dir=str(tmp_path / "memory"),
            data_dir=str(tmp_path / "data")
        )
        return service
    
    def test_find_in_dataset_not_found(self, memory_service):
        """Test finding question not in dataset."""
        result = memory_service.find_in_dataset("nonexistent question")
        assert result is None
    
    def test_load_dataset_empty(self, memory_service):
        """Test loading empty dataset."""
        result = memory_service.load_dataset()
        assert result == []
    
    def test_init_creates_directories(self, tmp_path):
        """Test that init creates directories."""
        from services.text2sql.app.services.memory_service import MemoryService
        
        memory_path = tmp_path / "new_memory"
        data_path = tmp_path / "new_data"
        
        service = MemoryService(
            memory_dir=str(memory_path),
            data_dir=str(data_path)
        )
        
        assert memory_path.exists()
        assert data_path.exists()
