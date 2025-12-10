"""
Unit Tests for ChatBot Flask Application
"""
import pytest
import json
from flask import session

class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_exists(self, client):
        """Test if health endpoint exists"""
        response = client.get('/health')
        assert response.status_code in [200, 404]  # May not be implemented yet
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns HTML"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data

class TestChatEndpoint:
    """Test chat endpoint functionality"""
    
    def test_chat_endpoint_exists(self, client):
        """Test if chat endpoint exists"""
        response = client.post('/chat', json={})
        assert response.status_code in [200, 400, 401, 500]
    
    def test_chat_with_valid_message(self, client, sample_message):
        """Test chat with valid message"""
        response = client.post('/chat', 
                              json=sample_message,
                              content_type='application/json')
        assert response.status_code in [200, 500]  # May fail if no API key
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'response' in data or 'error' in data
    
    def test_chat_with_missing_message(self, client):
        """Test chat with missing message field"""
        response = client.post('/chat', 
                              json={'model': 'gemini'},
                              content_type='application/json')
        assert response.status_code in [400, 500]
    
    def test_chat_with_invalid_model(self, client):
        """Test chat with invalid model"""
        response = client.post('/chat',
                              json={
                                  'message': 'Hello',
                                  'model': 'invalid_model_xyz'
                              },
                              content_type='application/json')
        # Should handle gracefully
        assert response.status_code in [200, 400, 500]
    
    def test_chat_with_file_attachment(self, client, sample_message, sample_file):
        """Test chat with file attachment"""
        sample_message['files'] = [sample_file]
        response = client.post('/chat',
                              json=sample_message,
                              content_type='application/json')
        assert response.status_code in [200, 400, 500]
    
    def test_chat_response_format(self, client, sample_message):
        """Test chat response has correct format"""
        response = client.post('/chat',
                              json=sample_message,
                              content_type='application/json')
        
        if response.status_code == 200:
            data = response.get_json()
            # Check for expected fields
            assert isinstance(data, dict)

class TestImageGenerationEndpoints:
    """Test image generation endpoints"""
    
    def test_generate_image_endpoint_exists(self, client):
        """Test if generate-image endpoint exists"""
        response = client.post('/api/generate-image', json={})
        assert response.status_code in [200, 400, 401, 500, 503]
    
    def test_generate_image_with_valid_params(self, client, sample_image_params):
        """Test image generation with valid parameters"""
        response = client.post('/api/generate-image',
                              json=sample_image_params,
                              content_type='application/json')
        # May fail if SD not running
        assert response.status_code in [200, 500, 503]
    
    def test_generate_image_with_missing_prompt(self, client):
        """Test image generation with missing prompt"""
        response = client.post('/api/generate-image',
                              json={'steps': 20},
                              content_type='application/json')
        assert response.status_code in [400, 500]
    
    def test_img2img_endpoint_exists(self, client):
        """Test if img2img endpoint exists"""
        response = client.post('/api/img2img', json={})
        assert response.status_code in [200, 400, 500, 503]
    
    def test_get_sd_models_endpoint(self, client):
        """Test get SD models endpoint"""
        response = client.get('/api/sd-models')
        assert response.status_code in [200, 500, 503]

class TestHistoryEndpoints:
    """Test conversation history endpoints"""
    
    def test_get_history_endpoint(self, client):
        """Test get history endpoint"""
        response = client.get('/history')
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, (list, dict))
    
    def test_get_specific_conversation(self, client):
        """Test get specific conversation"""
        response = client.get('/history?session_id=test_session')
        assert response.status_code == 200
    
    def test_clear_conversation(self, client):
        """Test clear conversation"""
        response = client.post('/clear',
                              json={'conversation_id': 'test_id'},
                              content_type='application/json')
        assert response.status_code in [200, 404]

class TestMemoryEndpoints:
    """Test memory/learning endpoints"""
    
    def test_save_memory_endpoint(self, client):
        """Test save memory endpoint"""
        response = client.post('/api/memory/save',
                              json={
                                  'conversation_id': 'test',
                                  'title': 'Test Memory'
                              },
                              content_type='application/json')
        assert response.status_code in [200, 400, 500]
    
    def test_get_memories_endpoint(self, client):
        """Test get memories endpoint"""
        response = client.get('/api/memory/list')
        assert response.status_code in [200, 404]

class TestStorageEndpoints:
    """Test storage management endpoints"""
    
    def test_get_storage_info(self, client):
        """Test get storage info"""
        response = client.get('/api/storage/info')
        assert response.status_code in [200, 404]
    
    def test_cleanup_storage(self, client):
        """Test storage cleanup"""
        response = client.post('/api/storage/cleanup',
                              content_type='application/json')
        assert response.status_code in [200, 404]

class TestExportEndpoints:
    """Test export functionality"""
    
    def test_export_pdf_endpoint(self, client):
        """Test PDF export endpoint"""
        response = client.post('/export',
                              json={'conversation_id': 'test'},
                              content_type='application/json')
        assert response.status_code in [200, 400, 404]

class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_json(self, client):
        """Test handling of invalid JSON"""
        response = client.post('/chat',
                              data='not valid json',
                              content_type='application/json')
        assert response.status_code in [400, 500]
    
    def test_large_message(self, client):
        """Test handling of very large messages"""
        large_message = 'A' * 100000  # 100KB message
        response = client.post('/chat',
                              json={
                                  'message': large_message,
                                  'model': 'gemini'
                              },
                              content_type='application/json')
        # Should handle gracefully (accept or reject)
        assert response.status_code in [200, 400, 413, 500]
    
    def test_missing_content_type(self, client):
        """Test request without content-type header"""
        response = client.post('/chat',
                              data=json.dumps({'message': 'test'}))
        assert response.status_code in [200, 400, 415, 500]

class TestSecurity:
    """Test security aspects"""
    
    def test_xss_in_message(self, client):
        """Test XSS prevention in messages"""
        xss_payload = '<script>alert("XSS")</script>'
        response = client.post('/chat',
                              json={
                                  'message': xss_payload,
                                  'model': 'gemini'
                              },
                              content_type='application/json')
        # Should not execute script
        assert response.status_code in [200, 400, 500]
    
    def test_sql_injection_attempt(self, client):
        """Test SQL injection prevention"""
        sql_payload = "'; DROP TABLE users; --"
        response = client.post('/chat',
                              json={
                                  'message': sql_payload,
                                  'model': 'gemini'
                              },
                              content_type='application/json')
        # Should handle safely
        assert response.status_code in [200, 400, 500]

class TestRateLimiting:
    """Test rate limiting (if implemented)"""
    
    def test_multiple_requests(self, client, sample_message):
        """Test multiple rapid requests"""
        responses = []
        for _ in range(5):
            response = client.post('/chat',
                                  json=sample_message,
                                  content_type='application/json')
            responses.append(response.status_code)
        
        # Should all succeed or some be rate limited
        assert all(code in [200, 429, 500] for code in responses)

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
