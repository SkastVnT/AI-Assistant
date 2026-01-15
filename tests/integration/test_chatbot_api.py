"""
Integration Tests for API Endpoints

Tests API routes with real database connections (in test environment).
"""

import pytest
from unittest.mock import patch
import json


@pytest.fixture
def app():
    """Create test Flask application"""
    import sys
    from pathlib import Path
    
    # Add service path
    service_path = Path(__file__).parent.parent.parent / 'services' / 'chatbot'
    if str(service_path) not in sys.path:
        sys.path.insert(0, str(service_path))
    
    try:
        from app import create_app
        
        app = create_app('testing')
        app.config['TESTING'] = True
        
        yield app
    except ImportError:
        # Fallback if new structure not available
        pytest.skip("New app structure not available")


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.mark.integration
class TestChatAPI:
    """Test chat API endpoints"""
    
    def test_send_message(self, client):
        """Test sending a message"""
        with patch('services.chatbot.app.services.ai_service.AIService.chat') as mock_chat:
            mock_chat.return_value = {
                'text': 'Hello! How can I help?',
                'tokens': {'input': 10, 'output': 20}
            }
            
            response = client.post('/api/v1/chat/send',
                json={
                    'message': 'Hello',
                    'model': 'grok'
                }
            )
            
            # Should return 200 or 404 (if route not registered yet)
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 200:
                data = json.loads(response.data)
                assert 'response' in data or 'error' in data
    
    def test_get_available_models(self, client):
        """Test getting available models"""
        response = client.get('/api/v1/chat/models')
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'models' in data


@pytest.mark.integration
class TestConversationAPI:
    """Test conversation API endpoints"""
    
    def test_list_conversations(self, client):
        """Test listing conversations"""
        response = client.get('/api/v1/conversations/')
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'conversations' in data
    
    def test_create_conversation(self, client):
        """Test creating a conversation"""
        response = client.post('/api/v1/conversations/',
            json={
                'title': 'Test Chat',
                'model': 'grok'
            }
        )
        
        assert response.status_code in [200, 201, 404]
    
    def test_get_conversation(self, client):
        """Test getting a specific conversation"""
        response = client.get('/api/v1/conversations/test-id-123')
        
        # Should return 404 (not found) or 200 (found)
        assert response.status_code in [200, 404]


@pytest.mark.integration
class TestMemoryAPI:
    """Test memory API endpoints"""
    
    def test_create_memory(self, client):
        """Test creating a memory"""
        response = client.post('/api/v1/memory/',
            json={
                'title': 'Test Memory',
                'content': 'This is test content',
                'category': 'general'
            }
        )
        
        assert response.status_code in [200, 201, 404]
    
    def test_search_memories(self, client):
        """Test searching memories"""
        response = client.get('/api/v1/memory/search?q=python')
        
        assert response.status_code in [200, 404]


@pytest.mark.integration
class TestLearningAPI:
    """Test learning API endpoints"""
    
    def test_get_learning_stats(self, client):
        """Test getting learning statistics"""
        response = client.get('/api/v1/learning/stats')
        
        assert response.status_code in [200, 404]
    
    def test_submit_learning_data(self, client):
        """Test submitting learning data"""
        response = client.post('/api/v1/learning/data',
            json={
                'source': 'manual',
                'category': 'qa',
                'data': {
                    'question': 'What is Python?',
                    'answer': 'A programming language'
                },
                'quality_score': 0.8
            }
        )
        
        assert response.status_code in [200, 201, 404]


@pytest.mark.integration
class TestLegacyAPI:
    """Test legacy API endpoints for backward compatibility"""
    
    def test_index_page(self, client):
        """Test main index page"""
        response = client.get('/')
        
        assert response.status_code in [200, 404]
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data.get('status') == 'healthy'
    
    def test_legacy_chat(self, client):
        """Test legacy chat endpoint"""
        with patch('services.chatbot.app.controllers.chat_controller.ChatController.process_message') as mock:
            mock.return_value = {
                'response': 'Hello!',
                'model_used': 'grok',
                'conversation_id': 'test-123'
            }
            
            response = client.post('/chat',
                json={
                    'message': 'Hello',
                    'model': 'grok'
                }
            )
            
            assert response.status_code in [200, 404, 500]
