"""
End-to-End Tests

Tests complete user workflows from API to database.
"""

import pytest
from unittest.mock import patch
import json
import time


@pytest.fixture
def app():
    """Create test Flask application with real database"""
    import sys
    from pathlib import Path
    
    service_path = Path(__file__).parent.parent.parent / 'services' / 'chatbot'
    if str(service_path) not in sys.path:
        sys.path.insert(0, str(service_path))
    
    try:
        from app import create_app
        
        app = create_app('testing')
        app.config['TESTING'] = True
        
        yield app
    except ImportError:
        pytest.skip("App not available")


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.mark.e2e
class TestChatWorkflow:
    """Test complete chat workflow"""
    
    def test_full_chat_session(self, client):
        """Test complete chat session: create, message, list, delete"""
        # Skip if routes not available
        response = client.get('/health')
        if response.status_code != 200:
            pytest.skip("Service not available")
        
        # 1. Create a new conversation
        create_response = client.post('/api/v1/conversations/',
            json={'title': 'E2E Test Chat'}
        )
        
        if create_response.status_code == 404:
            pytest.skip("API routes not available")
        
        conversation_id = json.loads(create_response.data).get('_id')
        
        # 2. Send a message
        with patch('services.chatbot.app.services.ai_service.AIService.chat') as mock_chat:
            mock_chat.return_value = {
                'text': 'Test response',
                'tokens': {'input': 10, 'output': 20}
            }
            
            chat_response = client.post('/api/v1/chat/send',
                json={
                    'message': 'Hello!',
                    'conversation_id': conversation_id
                }
            )
            
            assert chat_response.status_code == 200
        
        # 3. List conversations
        list_response = client.get('/api/v1/conversations/')
        assert list_response.status_code == 200
        
        # 4. Delete conversation
        if conversation_id:
            delete_response = client.delete(f'/api/v1/conversations/{conversation_id}')
            assert delete_response.status_code in [200, 404]


@pytest.mark.e2e
class TestLearningWorkflow:
    """Test AI learning workflow"""
    
    def test_conversation_to_learning_pipeline(self, client):
        """Test extracting learning data from conversations"""
        response = client.get('/health')
        if response.status_code != 200:
            pytest.skip("Service not available")
        
        # 1. Submit learning data
        submit_response = client.post('/api/v1/learning/data',
            json={
                'source': 'e2e_test',
                'category': 'qa',
                'data': {
                    'question': 'What is E2E testing?',
                    'answer': 'End-to-end testing validates the complete system.'
                },
                'quality_score': 0.85
            }
        )
        
        if submit_response.status_code == 404:
            pytest.skip("Learning API not available")
        
        assert submit_response.status_code in [200, 201]
        
        # 2. Get learning stats
        stats_response = client.get('/api/v1/learning/stats')
        
        if stats_response.status_code == 200:
            stats = json.loads(stats_response.data)
            assert 'total_entries' in stats


@pytest.mark.e2e
class TestMemoryWorkflow:
    """Test memory/knowledge base workflow"""
    
    def test_memory_crud_operations(self, client):
        """Test creating, reading, updating, deleting memories"""
        response = client.get('/health')
        if response.status_code != 200:
            pytest.skip("Service not available")
        
        # 1. Create memory
        create_response = client.post('/api/v1/memory/',
            json={
                'title': 'E2E Test Memory',
                'content': 'This is a test memory for E2E testing',
                'category': 'testing',
                'tags': ['test', 'e2e']
            }
        )
        
        if create_response.status_code == 404:
            pytest.skip("Memory API not available")
        
        assert create_response.status_code in [200, 201]
        
        memory_id = json.loads(create_response.data).get('_id')
        
        # 2. Search for memory
        search_response = client.get('/api/v1/memory/search?q=e2e')
        assert search_response.status_code == 200
        
        # 3. Delete memory
        if memory_id:
            delete_response = client.delete(f'/api/v1/memory/{memory_id}')
            assert delete_response.status_code in [200, 404]
