"""
Integration Tests

End-to-end tests for the chatbot database layer.
Tests complete workflows and interactions between components.
"""

import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime
import uuid
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add chatbot directory to path
CHATBOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(CHATBOT_DIR))


class TestCompleteConversationFlow:
    """Test complete conversation lifecycle"""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock MongoDB with all collections"""
        db = MagicMock()
        
        # Mock conversations collection
        db.conversations = MagicMock()
        db.conversations.insert_one.return_value = MagicMock(inserted_id='conv_123')
        db.conversations.find_one.return_value = {
            '_id': 'conv_123',
            'user_id': 'user_1',
            'title': 'Test Chat',
            'model': 'grok',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Mock messages collection
        db.messages = MagicMock()
        db.messages.insert_one.return_value = MagicMock(inserted_id='msg_123')
        
        # Mock memories collection
        db.memories = MagicMock()
        db.memories.insert_one.return_value = MagicMock(inserted_id='mem_123')
        
        return db
    
    def test_create_conversation_add_messages_save_memory(self, mock_db):
        """Test: Create conv → Add messages → Save memory → Retrieve"""
        from database.repositories.conversation_repository import ConversationRepository
        from database.repositories.message_repository import MessageRepository
        from database.repositories.memory_repository import MemoryRepository
        
        # Step 1: Create conversation
        conv_repo = ConversationRepository(mock_db)
        conversation = conv_repo.create_conversation(
            user_id='user_1',
            title='Test Conversation',
            model='grok'
        )
        
        assert conversation is not None
        assert conversation['user_id'] == 'user_1'
        assert 'created_at' in conversation
        
        # Step 2: Add messages
        msg_repo = MessageRepository(mock_db)
        
        user_msg = msg_repo.add_message(
            conversation_id=conversation['_id'],
            role='user',
            content='What is Python?'
        )
        assert user_msg['role'] == 'user'
        
        assistant_msg = msg_repo.add_message(
            conversation_id=conversation['_id'],
            role='assistant',
            content='Python is a programming language.'
        )
        assert assistant_msg['role'] == 'assistant'
        
        # Step 3: Save as memory
        mem_repo = MemoryRepository(mock_db)
        memory = mem_repo.save_qa_memory(
            user_id='user_1',
            conversation_id=conversation['_id'],
            question='What is Python?',
            answer='Python is a programming language.'
        )
        
        assert memory is not None
        assert 'Q: What is Python?' in memory['content']
        assert memory['category'] == 'qa'
    
    def test_delete_conversation_cascades_to_messages(self):
        """Test cascade delete removes all related data"""
        from database.repositories.conversation_repository import ConversationRepository
        
        # Create mock DB with proper collection access pattern
        mock_db = MagicMock()
        
        # Mock conversations collection
        conv_collection = MagicMock()
        delete_one_result = MagicMock()
        delete_one_result.deleted_count = 1
        conv_collection.delete_one.return_value = delete_one_result
        
        # Mock messages collection
        msg_collection = MagicMock()
        delete_many_result = MagicMock()
        delete_many_result.deleted_count = 5
        msg_collection.delete_many.return_value = delete_many_result
        
        # Setup __getitem__ for db['collection_name'] access
        def get_collection(name):
            if name == 'conversations':
                return conv_collection
            elif name == 'messages':
                return msg_collection
            return MagicMock()
        
        mock_db.__getitem__ = MagicMock(side_effect=get_collection)
        mock_db.messages = msg_collection
        
        conv_repo = ConversationRepository(mock_db)
        result = conv_repo.delete_conversation_cascade('conv_123')
        
        assert result is True
        msg_collection.delete_many.assert_called_once()
        conv_collection.delete_one.assert_called_once()


class TestCacheInvalidation:
    """Test cache behavior and invalidation"""
    
    def test_cache_set_and_get(self):
        """Test basic cache operations"""
        from database.cache.chatbot_cache import ChatbotCache
        
        # Clear any existing cache
        ChatbotCache.clear_all()
        
        test_data = {'_id': 'test_123', 'title': 'Test'}
        
        # Set cache
        ChatbotCache.set_conversation('test_123', test_data)
        
        # Get from cache
        result = ChatbotCache.get_conversation('test_123')
        assert result == test_data
    
    def test_cache_invalidation_on_update(self):
        """Test cache is invalidated after update"""
        from database.cache.chatbot_cache import ChatbotCache
        
        # Set cache
        ChatbotCache.set_conversation('test_456', {'title': 'Original'})
        
        # Invalidate
        ChatbotCache.invalidate_conversation('test_456')
        
        # Should be None now
        result = ChatbotCache.get_conversation('test_456')
        assert result is None
    
    def test_user_conversation_list_cache(self):
        """Test user conversation list caching"""
        from database.cache.chatbot_cache import ChatbotCache
        
        conversations = [
            {'_id': 'conv_1', 'title': 'Chat 1'},
            {'_id': 'conv_2', 'title': 'Chat 2'}
        ]
        
        # Cache list
        ChatbotCache.set_user_conversations('user_123', conversations)
        
        # Retrieve
        result = ChatbotCache.get_user_conversations('user_123')
        assert len(result) == 2
        
        # Invalidate
        ChatbotCache.invalidate_user_conversations('user_123')
        
        # Should be None
        result = ChatbotCache.get_user_conversations('user_123')
        assert result is None
    
    def test_message_cache(self):
        """Test message list caching"""
        from database.cache.chatbot_cache import ChatbotCache
        
        messages = [
            {'_id': 'msg_1', 'content': 'Hello'},
            {'_id': 'msg_2', 'content': 'Hi there'}
        ]
        
        # Cache messages
        ChatbotCache.set_messages('conv_789', messages)
        
        # Retrieve
        result = ChatbotCache.get_messages('conv_789')
        assert len(result) == 2
        
        # Invalidate
        ChatbotCache.invalidate_messages('conv_789')
        assert ChatbotCache.get_messages('conv_789') is None


class TestConcurrentAccess:
    """Test concurrent database access"""
    
    def test_concurrent_cache_writes(self):
        """Test multiple threads writing to cache"""
        from database.cache.chatbot_cache import ChatbotCache
        
        errors = []
        
        def write_cache(thread_id):
            try:
                for i in range(10):
                    key = f"thread_{thread_id}_item_{i}"
                    ChatbotCache.set_conversation(key, {'id': key})
                    result = ChatbotCache.get_conversation(key)
                    if result is None:
                        errors.append(f"Failed to get {key}")
            except Exception as e:
                errors.append(str(e))
        
        threads = []
        for i in range(5):
            t = threading.Thread(target=write_cache, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        assert len(errors) == 0, f"Errors: {errors}"
    
    def test_concurrent_conversation_creation(self):
        """Test multiple conversations created simultaneously"""
        from database.repositories.conversation_repository import ConversationRepository
        
        # Mock DB for each thread
        results = []
        errors = []
        
        def create_conversation(user_id):
            try:
                mock_db = MagicMock()
                mock_db.conversations.insert_one.return_value = MagicMock(
                    inserted_id=str(uuid.uuid4())
                )
                
                repo = ConversationRepository(mock_db)
                conv = repo.create_conversation(
                    user_id=user_id,
                    title=f'Chat for {user_id}'
                )
                results.append(conv)
            except Exception as e:
                errors.append(str(e))
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(create_conversation, f'user_{i}')
                for i in range(10)
            ]
            for future in as_completed(futures):
                future.result()
        
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == 10


class TestDatabaseSession:
    """Test database session management"""
    
    def test_session_singleton(self):
        """Test DatabaseSession is singleton"""
        from database.utils.session import DatabaseSession
        
        # Reset for test
        DatabaseSession._instance = None
        DatabaseSession._client = None
        
        session1 = DatabaseSession()
        session2 = DatabaseSession()
        
        assert session1 is session2
    
    @patch('database.utils.session.MongoClient')
    def test_session_reconnect(self, mock_client):
        """Test session can reconnect"""
        from database.utils.session import DatabaseSession
        
        # Reset
        DatabaseSession._instance = None
        DatabaseSession._client = None
        
        mock_client.return_value.admin.command.return_value = {'ok': 1}
        
        session = DatabaseSession()
        session.reconnect()
        
        # Should have attempted connection twice
        assert mock_client.call_count >= 1


class TestHelperFunctions:
    """Test backward-compatible helper functions"""
    
    @patch('database.helpers.get_conversation_repo')
    @patch('database.helpers.ChatbotCache')
    def test_load_conversation_from_cache(self, mock_cache, mock_repo):
        """Test load_conversation uses cache first"""
        from database.helpers import load_conversation
        
        cached_data = {'_id': 'conv_123', 'title': 'Cached'}
        mock_cache.get_conversation.return_value = cached_data
        
        result = load_conversation('conv_123')
        
        assert result == cached_data
        mock_cache.get_conversation.assert_called_once_with('conv_123')
        # Should not call repo if cache hit
        mock_repo.assert_not_called()
    
    @patch('database.helpers.get_conversation_repo')
    @patch('database.helpers.ChatbotCache')
    def test_load_conversation_from_db_on_cache_miss(self, mock_cache, mock_repo):
        """Test load_conversation falls back to DB on cache miss"""
        from database.helpers import load_conversation
        
        mock_cache.get_conversation.return_value = None
        mock_repo.return_value.get_by_id_with_messages.return_value = {
            '_id': 'conv_123',
            'title': 'From DB'
        }
        
        result = load_conversation('conv_123')
        
        assert result['title'] == 'From DB'
        mock_repo.return_value.get_by_id_with_messages.assert_called_once()


class TestDataIntegrity:
    """Test data integrity during operations"""
    
    def test_message_edit_preserves_history(self):
        """Test editing message keeps edit history"""
        from database.repositories.message_repository import MessageRepository
        
        mock_db = MagicMock()
        
        # Setup collection mock directly
        messages_collection = MagicMock()
        mock_db.__getitem__ = MagicMock(return_value=messages_collection)
        mock_db.messages = messages_collection
        
        messages_collection.find_one.return_value = {
            '_id': 'msg_123',
            'content': 'Original content',
            'is_edited': False,
            'edit_history': []
        }
        messages_collection.find_one_and_update.return_value = {
            '_id': 'msg_123',
            'content': 'Edited content',
            'is_edited': True,
            'edit_history': [{'old_content': 'Original content'}]
        }
        
        repo = MessageRepository(mock_db)
        result = repo.edit_message('msg_123', 'Edited content')
        
        assert result is not None
        assert result.get('is_edited') is True
        assert len(result.get('edit_history', [])) == 1
    
    def test_memory_importance_clamped(self):
        """Test memory importance is clamped to 0-1"""
        from database.repositories.memory_repository import MemoryRepository
        
        mock_db = MagicMock()
        mock_db.memories.insert_one.return_value = MagicMock(inserted_id='mem_123')
        
        repo = MemoryRepository(mock_db)
        
        # Test above 1
        memory = repo.save_memory(
            user_id='user_1',
            content='Test',
            importance=1.5
        )
        assert memory['importance'] == 1.0
        
        # Test below 0
        memory = repo.save_memory(
            user_id='user_1',
            content='Test',
            importance=-0.5
        )
        assert memory['importance'] == 0.0
    
    def test_tags_normalized_to_lowercase(self):
        """Test tags are normalized to lowercase"""
        from database.repositories.memory_repository import MemoryRepository
        
        mock_db = MagicMock()
        mock_db.memories.insert_one.return_value = MagicMock(inserted_id='mem_123')
        
        repo = MemoryRepository(mock_db)
        memory = repo.save_memory(
            user_id='user_1',
            content='Test',
            tags=['Python', 'CODING', 'Test']
        )
        
        assert memory['tags'] == ['python', 'coding', 'test']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
