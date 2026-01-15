"""
Tests for Database Optimization Module
"""

import sys
from pathlib import Path
import importlib
import pytest
from unittest.mock import Mock, MagicMock, patch

# Ensure project root is in path BEFORE any service paths
# This is needed because services/chatbot has its own src/ folder
project_root = Path(__file__).parent.parent.parent.resolve()
project_root_str = str(project_root)

# Force project root to be first
while project_root_str in sys.path:
    sys.path.remove(project_root_str)
sys.path.insert(0, project_root_str)

# Clean up any wrong src module that might be cached
for key in list(sys.modules.keys()):
    if key == 'src' or key.startswith('src.'):
        del sys.modules[key]

# Now import fresh
import src.database
importlib.reload(src.database)


class TestMongoDBIndexes:
    """Test MongoDB index definitions."""
    
    def test_indexes_defined(self):
        """Test that indexes are defined for main collections."""
        from src.database import MONGODB_INDEXES
        
        assert "conversations" in MONGODB_INDEXES
        assert "messages" in MONGODB_INDEXES
        assert "memories" in MONGODB_INDEXES
        assert "api_keys" in MONGODB_INDEXES
    
    def test_conversations_indexes(self):
        """Test conversations collection indexes."""
        from src.database import MONGODB_INDEXES
        
        conv_indexes = MONGODB_INDEXES["conversations"]
        
        # Should have user_id + created_at compound index
        index_names = [idx.get("name") for idx in conv_indexes]
        assert "idx_user_created" in index_names
    
    def test_messages_compound_index(self):
        """Test messages has compound index."""
        from src.database import MONGODB_INDEXES
        
        msg_indexes = MONGODB_INDEXES["messages"]
        
        # Should have conversation_id + created_at compound index
        index_names = [idx.get("name") for idx in msg_indexes]
        assert "idx_conv_created" in index_names


class TestDatabaseOptimizer:
    """Test DatabaseOptimizer class."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock MongoDB database."""
        mock_client = MagicMock()
        mock_database = MagicMock()
        mock_collection = MagicMock()
        
        mock_collection.index_information.return_value = {}
        mock_collection.create_index.return_value = "index_name"
        
        mock_database.__getitem__ = MagicMock(return_value=mock_collection)
        mock_database.list_collection_names.return_value = ["conversations", "messages"]
        mock_client.__getitem__ = MagicMock(return_value=mock_database)
        
        return mock_client, mock_database
    
    def test_optimizer_initialization(self, mock_db):
        """Test optimizer initialization."""
        from src.database import DatabaseOptimizer
        
        mock_client, mock_database = mock_db
        optimizer = DatabaseOptimizer(mock_client, "test_db")
        
        assert optimizer.client is mock_client
        assert optimizer.db is not None
    
    def test_create_indexes(self, mock_db):
        """Test creating indexes."""
        from src.database import DatabaseOptimizer
        
        mock_client, mock_database = mock_db
        optimizer = DatabaseOptimizer(mock_client, "test_db")
        
        # The create_indexes will use MONGODB_INDEXES
        # Just verify it returns a dict
        result = optimizer.create_indexes(["conversations"])
        assert isinstance(result, dict)
    
    def test_analyze_indexes(self, mock_db):
        """Test analyzing indexes."""
        from src.database import DatabaseOptimizer
        
        mock_client, mock_database = mock_db
        mock_collection = MagicMock()
        mock_collection.index_information.return_value = {
            "_id_": {"key": [("_id", 1)]},
            "user_id_1": {"key": [("user_id", 1)]}
        }
        mock_database.__getitem__ = MagicMock(return_value=mock_collection)
        
        optimizer = DatabaseOptimizer(mock_client, "test_db")
        result = optimizer.analyze_indexes("conversations")
        
        # Check result has expected structure
        assert "collection" in result
        assert result["collection"] == "conversations"
    
    def test_get_collection_stats(self, mock_db):
        """Test getting collection stats."""
        from src.database import DatabaseOptimizer
        
        mock_client, mock_database = mock_db
        mock_database.command.return_value = {
            "count": 1000,
            "size": 50000,
            "avgObjSize": 50,
            "totalIndexSize": 10000
        }
        
        optimizer = DatabaseOptimizer(mock_client, "test_db")
        stats = optimizer.get_collection_stats("conversations")
        
        mock_database.command.assert_called_with("collStats", "conversations")


class TestQueryBuilder:
    """Test QueryBuilder class."""
    
    def test_paginate(self):
        """Test pagination helper."""
        from src.database import QueryBuilder
        
        result = QueryBuilder.paginate(
            {"status": "active"},
            page=2,
            per_page=20
        )
        
        assert result["filter"] == {"status": "active"}
        assert result["skip"] == 20
        assert result["limit"] == 20
    
    def test_project(self):
        """Test projection helper."""
        from src.database import QueryBuilder
        
        result = QueryBuilder.project(["name", "email"])
        
        assert result["name"] == 1
        assert result["email"] == 1
    
    def test_project_exclude_id(self):
        """Test projection with excluded id."""
        from src.database import QueryBuilder
        
        result = QueryBuilder.project(["name"], exclude_id=True)
        
        assert result["name"] == 1
        assert result.get("_id") == 0
    
    def test_text_search(self):
        """Test text search query."""
        from src.database import QueryBuilder
        
        result = QueryBuilder.text_search("hello world")
        
        assert "query" in result
        assert "$text" in result["query"]
        assert result["query"]["$text"]["$search"] == "hello world"
    
    def test_date_range(self):
        """Test date range filter."""
        from src.database import QueryBuilder
        from datetime import datetime
        
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        
        result = QueryBuilder.date_range("created_at", start, end)
        
        assert "created_at" in result
        assert "$gte" in result["created_at"]
        assert "$lt" in result["created_at"]  # end_date is exclusive


class TestMongoDBConnectionManager:
    """Test MongoDBConnectionManager class."""
    
    def test_singleton_instance(self):
        """Test connection manager is singleton."""
        from src.database import MongoDBConnectionManager
        
        manager1 = MongoDBConnectionManager()
        manager2 = MongoDBConnectionManager()
        
        # Singleton - same instance
        assert manager1 is manager2
        
        # Reset for other tests
        MongoDBConnectionManager._instance = None
        MongoDBConnectionManager._client = None
    
    def test_connect_with_config(self):
        """Test connection configuration."""
        from src.database.optimization import MongoDBConnectionManager
        
        with patch('src.database.optimization.MongoClient') as mock_client:
            mock_mongo = Mock()
            mock_client.return_value = mock_mongo
            
            MongoDBConnectionManager._instance = None
            MongoDBConnectionManager._client = None
            
            manager = MongoDBConnectionManager()
            client = manager.connect(
                uri="mongodb://localhost:27017",
                max_pool_size=50
            )
            
            # Verify MongoClient was called
            assert mock_client.called
            
            MongoDBConnectionManager._instance = None
            MongoDBConnectionManager._client = None
    
    def test_get_client(self):
        """Test getting client."""
        from src.database.optimization import MongoDBConnectionManager
        
        with patch('src.database.optimization.MongoClient') as mock_client:
            mock_mongo = MagicMock()
            mock_client.return_value = mock_mongo
            
            MongoDBConnectionManager._instance = None
            MongoDBConnectionManager._client = None
            
            manager = MongoDBConnectionManager()
            manager.connect("mongodb://localhost:27017")
            
            client = manager.get_client()
            
            assert client is not None
            
            MongoDBConnectionManager._instance = None
            MongoDBConnectionManager._client = None
    
    def test_health_check(self):
        """Test health check returns dict."""
        from src.database.optimization import MongoDBConnectionManager
        
        with patch('src.database.optimization.MongoClient') as mock_client:
            mock_mongo = MagicMock()
            mock_mongo.admin.command.return_value = {"ok": 1}
            mock_mongo.server_info.return_value = {"version": "4.4.0", "uptime": 12345}
            mock_client.return_value = mock_mongo
            
            MongoDBConnectionManager._instance = None
            MongoDBConnectionManager._client = None
            
            manager = MongoDBConnectionManager()
            manager.connect("mongodb://localhost:27017")
            
            result = manager.health_check()
            
            assert result["status"] == "connected"
            
            MongoDBConnectionManager._instance = None
            MongoDBConnectionManager._client = None
    
    def test_health_check_failure(self):
        """Test health check failure returns error dict."""
        from src.database.optimization import MongoDBConnectionManager
        
        with patch('src.database.optimization.MongoClient') as mock_client:
            mock_mongo = MagicMock()
            mock_mongo.admin.command.side_effect = Exception("Connection failed")
            mock_client.return_value = mock_mongo
            
            MongoDBConnectionManager._instance = None
            MongoDBConnectionManager._client = None
            
            manager = MongoDBConnectionManager()
            manager.connect("mongodb://localhost:27017")
            
            result = manager.health_check()
            
            assert result["status"] == "error"
            assert "error" in result
            
            MongoDBConnectionManager._instance = None
            MongoDBConnectionManager._client = None
