"""
Repository Unit Tests

Tests for the repository pattern implementation.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import uuid


class TestBaseRepository:
    """Test BaseRepository functionality"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock MongoDB database"""
        db = MagicMock()
        db.__getitem__ = Mock(return_value=MagicMock())
        return db
    
    @pytest.fixture
    def mock_collection(self, mock_db):
        """Create a mock collection"""
        collection = MagicMock()
        mock_db.__getitem__.return_value = collection
        return collection
    
    def test_create_adds_timestamps(self, mock_db, mock_collection):
        """Test that create() adds timestamps"""
        from database.repositories.base_repository import BaseRepository
        
        # Create concrete implementation
        class TestRepo(BaseRepository):
            @property
            def collection_name(self):
                return 'test'
        
        repo = TestRepo(mock_db)
        mock_collection.insert_one.return_value = MagicMock(inserted_id='123')
        
        data = {'name': 'test'}
        result = repo.create(data)
        
        assert 'created_at' in result
        assert 'updated_at' in result
        mock_collection.insert_one.assert_called_once()
    
    def test_get_by_id_returns_document(self, mock_db, mock_collection):
        """Test get_by_id returns document"""
        from database.repositories.base_repository import BaseRepository
        
        class TestRepo(BaseRepository):
            @property
            def collection_name(self):
                return 'test'
        
        repo = TestRepo(mock_db)
        expected = {'_id': '123', 'name': 'test'}
        mock_collection.find_one.return_value = expected
        
        result = repo.get_by_id('123')
        
        assert result == expected
    
    def test_update_adds_updated_at(self, mock_db, mock_collection):
        """Test that update() adds updated_at"""
        from database.repositories.base_repository import BaseRepository
        
        class TestRepo(BaseRepository):
            @property
            def collection_name(self):
                return 'test'
        
        repo = TestRepo(mock_db)
        mock_collection.find_one_and_update.return_value = {'_id': '123', 'name': 'updated'}
        
        result = repo.update('123', {'name': 'updated'})
        
        assert result is not None
        call_args = mock_collection.find_one_and_update.call_args
        assert 'updated_at' in call_args[0][1]['$set']
    
    def test_delete_returns_true_when_deleted(self, mock_db, mock_collection):
        """Test delete returns True when document deleted"""
        from database.repositories.base_repository import BaseRepository
        
        class TestRepo(BaseRepository):
            @property
            def collection_name(self):
                return 'test'
        
        repo = TestRepo(mock_db)
        mock_collection.delete_one.return_value = MagicMock(deleted_count=1)
        
        result = repo.delete('123')
        
        assert result is True
    
    def test_paginate_returns_correct_structure(self, mock_db, mock_collection):
        """Test paginate returns correct structure"""
        from database.repositories.base_repository import BaseRepository
        
        class TestRepo(BaseRepository):
            @property
            def collection_name(self):
                return 'test'
        
        repo = TestRepo(mock_db)
        mock_cursor = MagicMock()
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__ = Mock(return_value=iter([{'_id': '1'}, {'_id': '2'}]))
        mock_collection.find.return_value = mock_cursor
        mock_collection.count_documents.return_value = 10
        
        result = repo.paginate({}, page=1, per_page=5)
        
        assert 'items' in result
        assert 'total' in result
        assert result['total'] == 10
        assert result['pages'] == 2
        assert result['current_page'] == 1


class TestConversationRepository:
    """Test ConversationRepository functionality"""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        return db
    
    def test_create_conversation_generates_id(self, mock_db):
        """Test create_conversation generates UUID"""
        from database.repositories.conversation_repository import ConversationRepository
        
        repo = ConversationRepository(mock_db)
        mock_db['conversations'].insert_one.return_value = MagicMock()
        
        result = repo.create_conversation(
            user_id='user123',
            title='Test Chat'
        )
        
        assert '_id' in result
        assert result['user_id'] == 'user123'
        assert result['title'] == 'Test Chat'
    
    def test_get_user_conversations_excludes_deleted(self, mock_db):
        """Test get_user_conversations excludes deleted"""
        from database.repositories.conversation_repository import ConversationRepository
        
        repo = ConversationRepository(mock_db)
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__ = Mock(return_value=iter([]))
        mock_db['conversations'].find.return_value = mock_cursor
        
        repo.get_user_conversations('user123')
        
        call_args = mock_db['conversations'].find.call_args
        query = call_args[0][0]
        assert query['is_deleted'] == {'$ne': True}


class TestMessageRepository:
    """Test MessageRepository functionality"""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        return db
    
    def test_add_message_creates_with_id(self, mock_db):
        """Test add_message creates message with ID"""
        from database.repositories.message_repository import MessageRepository
        
        repo = MessageRepository(mock_db)
        mock_db['messages'].insert_one.return_value = MagicMock()
        
        result = repo.add_message(
            conversation_id='conv123',
            role='user',
            content='Hello!'
        )
        
        assert '_id' in result
        assert result['conversation_id'] == 'conv123'
        assert result['role'] == 'user'
        assert result['content'] == 'Hello!'
    
    def test_get_recent_messages_returns_in_order(self, mock_db):
        """Test get_recent_messages returns chronological order"""
        from database.repositories.message_repository import MessageRepository
        
        repo = MessageRepository(mock_db)
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__ = Mock(return_value=iter([
            {'_id': '3', 'content': 'Third'},
            {'_id': '2', 'content': 'Second'},
            {'_id': '1', 'content': 'First'}
        ]))
        mock_db['messages'].find.return_value = mock_cursor
        
        result = repo.get_recent_messages('conv123', limit=3)
        
        # Should be reversed to chronological order
        assert result[0]['content'] == 'First'
        assert result[2]['content'] == 'Third'


class TestMemoryRepository:
    """Test MemoryRepository functionality"""
    
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        return db
    
    def test_save_memory_normalizes_tags(self, mock_db):
        """Test save_memory lowercases tags"""
        from database.repositories.memory_repository import MemoryRepository
        
        repo = MemoryRepository(mock_db)
        mock_db['memories'].insert_one.return_value = MagicMock()
        
        result = repo.save_memory(
            user_id='user123',
            content='Test memory',
            tags=['Python', 'CODING', 'Test']
        )
        
        assert result['tags'] == ['python', 'coding', 'test']
    
    def test_save_memory_clamps_importance(self, mock_db):
        """Test save_memory clamps importance to 0-1"""
        from database.repositories.memory_repository import MemoryRepository
        
        repo = MemoryRepository(mock_db)
        mock_db['memories'].insert_one.return_value = MagicMock()
        
        result = repo.save_memory(
            user_id='user123',
            content='Test',
            importance=1.5  # Should be clamped to 1.0
        )
        
        assert result['importance'] == 1.0
    
    def test_save_qa_memory_formats_content(self, mock_db):
        """Test save_qa_memory formats Q&A content"""
        from database.repositories.memory_repository import MemoryRepository
        
        repo = MemoryRepository(mock_db)
        mock_db['memories'].insert_one.return_value = MagicMock()
        
        result = repo.save_qa_memory(
            user_id='user123',
            conversation_id='conv123',
            question='What is Python?',
            answer='A programming language'
        )
        
        assert 'Q: What is Python?' in result['content']
        assert 'A: A programming language' in result['content']
        assert result['category'] == 'qa'


class TestChatbotCache:
    """Test ChatbotCache functionality"""
    
    def test_singleton_pattern(self):
        """Test ChatbotCache is singleton"""
        from database.cache.chatbot_cache import ChatbotCache
        
        cache1 = ChatbotCache()
        cache2 = ChatbotCache()
        
        assert cache1 is cache2
    
    def test_set_and_get_conversation(self):
        """Test set and get conversation"""
        from database.cache.chatbot_cache import ChatbotCache
        
        conv_data = {'_id': 'conv123', 'title': 'Test'}
        
        ChatbotCache.set_conversation('conv123', conv_data)
        result = ChatbotCache.get_conversation('conv123')
        
        assert result == conv_data
    
    def test_invalidate_conversation(self):
        """Test invalidate conversation"""
        from database.cache.chatbot_cache import ChatbotCache
        
        conv_data = {'_id': 'conv456', 'title': 'Test'}
        
        ChatbotCache.set_conversation('conv456', conv_data)
        ChatbotCache.invalidate_conversation('conv456')
        result = ChatbotCache.get_conversation('conv456')
        
        assert result is None
    
    def test_make_query_hash_consistent(self):
        """Test query hash is consistent"""
        from database.cache.chatbot_cache import ChatbotCache
        
        hash1 = ChatbotCache.make_query_hash('arg1', 'arg2', key='value')
        hash2 = ChatbotCache.make_query_hash('arg1', 'arg2', key='value')
        hash3 = ChatbotCache.make_query_hash('different')
        
        assert hash1 == hash2
        assert hash1 != hash3


class TestDatabaseSession:
    """Test DatabaseSession functionality"""
    
    def test_singleton_pattern(self):
        """Test DatabaseSession is singleton"""
        from database.utils.session import DatabaseSession
        
        # Reset singleton for test
        DatabaseSession._instance = None
        DatabaseSession._client = None
        
        session1 = DatabaseSession()
        session2 = DatabaseSession()
        
        assert session1 is session2
    
    @patch('database.utils.session.MongoClient')
    def test_connection_failure_handled(self, mock_client):
        """Test connection failure is handled gracefully"""
        from database.utils.session import DatabaseSession
        from pymongo.errors import ConnectionFailure
        
        # Reset singleton
        DatabaseSession._instance = None
        DatabaseSession._client = None
        
        mock_client.side_effect = ConnectionFailure("Test error")
        
        session = DatabaseSession()
        
        assert session.client is None
        assert session.is_connected is False


class TestHelpers:
    """Test helper functions"""
    
    @patch('database.helpers.get_conversation_repo')
    @patch('database.helpers.ChatbotCache')
    def test_load_conversation_uses_cache(self, mock_cache, mock_repo):
        """Test load_conversation tries cache first"""
        from database.helpers import load_conversation
        
        mock_cache.get_conversation.return_value = {'_id': 'cached'}
        
        result = load_conversation('conv123')
        
        mock_cache.get_conversation.assert_called_once_with('conv123')
        mock_repo.assert_not_called()
        assert result == {'_id': 'cached'}
    
    @patch('database.helpers.get_message_repo')
    @patch('database.helpers.ChatbotCache')
    def test_add_message_invalidates_cache(self, mock_cache, mock_repo):
        """Test add_message invalidates cache"""
        from database.helpers import add_message
        
        mock_repo.return_value.add_message.return_value = {'_id': 'msg123'}
        
        with patch('database.helpers.get_conversation_repo'):
            add_message('conv123', 'user', 'Hello')
        
        mock_cache.invalidate_messages.assert_called_with('conv123')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
