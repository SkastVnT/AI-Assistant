"""
Unit Tests for Chatbot Controllers

Tests business logic in controllers without external dependencies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.fixture
def mock_services():
    """Mock all service dependencies"""
    with patch('services.chatbot.app.controllers.chat_controller.AIService') as ai_mock, \
         patch('services.chatbot.app.controllers.chat_controller.ConversationService') as conv_mock, \
         patch('services.chatbot.app.controllers.chat_controller.CacheService') as cache_mock, \
         patch('services.chatbot.app.controllers.chat_controller.LearningService') as learn_mock:
        
        yield {
            'ai': ai_mock.return_value,
            'conversation': conv_mock.return_value,
            'cache': cache_mock.return_value,
            'learning': learn_mock.return_value
        }


@pytest.mark.unit
class TestChatController:
    """Test ChatController functionality"""
    
    def test_process_message_creates_conversation_when_none(self, mock_services):
        """Test that a new conversation is created when none exists"""
        from services.chatbot.app.controllers.chat_controller import ChatController
        
        # Setup mocks
        mock_services['conversation'].create.return_value = {
            '_id': 'test-conv-123',
            'user_id': 'test-user',
            'title': 'Test Message...'
        }
        mock_services['conversation'].get_history.return_value = []
        mock_services['ai'].chat.return_value = {
            'text': 'Hello! How can I help?',
            'tokens': {'input': 10, 'output': 20}
        }
        mock_services['cache'].get.return_value = None
        
        controller = ChatController()
        controller.ai_service = mock_services['ai']
        controller.conversation_service = mock_services['conversation']
        controller.cache_service = mock_services['cache']
        controller.learning_service = mock_services['learning']
        
        result = controller.process_message(
            message="Test message",
            user_id="test-user"
        )
        
        assert result['conversation_id'] == 'test-conv-123'
        assert 'response' in result
        mock_services['conversation'].create.assert_called_once()
    
    def test_process_message_uses_cache(self, mock_services):
        """Test that cached responses are returned when available"""
        from services.chatbot.app.controllers.chat_controller import ChatController
        
        mock_services['cache'].get.return_value = "Cached response"
        
        controller = ChatController()
        controller.cache_service = mock_services['cache']
        controller.conversation_service = mock_services['conversation']
        mock_services['conversation'].create.return_value = {'_id': 'test-123'}
        
        result = controller.process_message(
            message="Test message",
            user_id="test-user",
            deep_thinking=False
        )
        
        assert result['cached'] == True
        assert result['response'] == "Cached response"
    
    def test_get_available_models(self, mock_services):
        """Test getting available AI models"""
        from services.chatbot.app.controllers.chat_controller import ChatController
        
        mock_services['ai'].get_available_models.return_value = [
            {'id': 'grok', 'name': 'Grok', 'available': True},
            {'id': 'openai', 'name': 'OpenAI', 'available': True}
        ]
        
        controller = ChatController()
        controller.ai_service = mock_services['ai']
        
        models = controller.get_available_models()
        
        assert len(models) == 2
        assert models[0]['id'] == 'grok'


@pytest.mark.unit
class TestConversationController:
    """Test ConversationController functionality"""
    
    def test_list_conversations(self):
        """Test listing user conversations"""
        with patch('services.chatbot.app.controllers.conversation_controller.ConversationService') as mock:
            from services.chatbot.app.controllers.conversation_controller import ConversationController
            
            mock.return_value.list_by_user.return_value = [
                {'_id': '1', 'title': 'Chat 1'},
                {'_id': '2', 'title': 'Chat 2'}
            ]
            mock.return_value.count_by_user.return_value = 2
            
            controller = ConversationController()
            result = controller.list_conversations(user_id='test-user')
            
            assert result['total'] == 2
            assert len(result['conversations']) == 2
    
    def test_delete_conversation_archives_for_learning(self):
        """Test that deleted conversations are archived for learning"""
        with patch('services.chatbot.app.controllers.conversation_controller.ConversationService') as conv_mock, \
             patch('services.chatbot.app.controllers.conversation_controller.LearningService') as learn_mock:
            
            from services.chatbot.app.controllers.conversation_controller import ConversationController
            
            conv_mock.return_value.get.return_value = {
                '_id': 'test-123',
                'messages': [
                    {'role': 'user', 'content': 'Hello'},
                    {'role': 'assistant', 'content': 'Hi there!'},
                    {'role': 'user', 'content': 'Question'},
                    {'role': 'assistant', 'content': 'Answer'}
                ]
            }
            conv_mock.return_value.get_messages.return_value = conv_mock.return_value.get.return_value['messages']
            
            controller = ConversationController()
            result = controller.delete_conversation(
                conversation_id='test-123',
                save_for_learning=True
            )
            
            assert result['deleted'] == True
            assert result['archived_for_learning'] == True


@pytest.mark.unit
class TestMemoryController:
    """Test MemoryController functionality"""
    
    def test_create_memory(self):
        """Test creating a memory entry"""
        with patch('services.chatbot.app.controllers.memory_controller.MemoryService') as mock:
            from services.chatbot.app.controllers.memory_controller import MemoryController
            
            mock.return_value.create.return_value = {
                '_id': 'mem-123',
                'title': 'Test Memory',
                'content': 'Test content'
            }
            
            controller = MemoryController()
            result = controller.create_memory(
                user_id='test-user',
                title='Test Memory',
                content='Test content'
            )
            
            assert result['_id'] == 'mem-123'
            assert result['title'] == 'Test Memory'
    
    def test_search_memories(self):
        """Test searching memories"""
        with patch('services.chatbot.app.controllers.memory_controller.MemoryService') as mock:
            from services.chatbot.app.controllers.memory_controller import MemoryController
            
            mock.return_value.search.return_value = [
                {'_id': '1', 'title': 'Python Tips', 'content': 'Use list comprehensions'}
            ]
            
            controller = MemoryController()
            result = controller.search_memories(
                user_id='test-user',
                query='python'
            )
            
            assert result['total'] == 1
            assert 'python' in result['query'].lower()


@pytest.mark.unit
class TestLearningController:
    """Test LearningController functionality"""
    
    def test_submit_learning_data(self):
        """Test submitting learning data"""
        with patch('services.chatbot.app.controllers.learning_controller.LearningService') as mock:
            from services.chatbot.app.controllers.learning_controller import LearningController
            
            mock.return_value.submit.return_value = {
                '_id': 'learn-123',
                'source': 'manual',
                'category': 'qa',
                'quality_score': 0.8
            }
            
            controller = LearningController()
            result = controller.submit_learning_data(
                source='manual',
                category='qa',
                data={'question': 'What is Python?', 'answer': 'A programming language'},
                quality_score=0.8
            )
            
            assert result['_id'] == 'learn-123'
            assert result['quality_score'] == 0.8
    
    def test_get_learning_stats(self):
        """Test getting learning statistics"""
        with patch('services.chatbot.app.controllers.learning_controller.LearningService') as mock:
            from services.chatbot.app.controllers.learning_controller import LearningController
            
            mock.return_value.get_stats.return_value = {
                'total_entries': 100,
                'approved': 50,
                'pending': 40,
                'rejected': 10,
                'average_quality': 0.75
            }
            
            controller = LearningController()
            result = controller.get_stats()
            
            assert result['total_entries'] == 100
            assert result['approved'] == 50
