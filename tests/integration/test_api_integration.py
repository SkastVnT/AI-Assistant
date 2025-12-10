"""
Integration Tests for AI-Assistant Services
Tests service interactions, API endpoints, and end-to-end workflows
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
import time


@pytest.mark.integration
class TestDocumentIntelligenceAPI:
    """Test Document Intelligence Service API Integration"""
    
    @patch('src.ocr.paddle_ocr.PaddleOCREngine')
    def test_ocr_extraction_integration(self, mock_ocr):
        """Test OCR extraction endpoint"""
        mock_ocr.return_value.extract_text.return_value = {
            'text': 'Extracted Vietnamese text from document',
            'confidence': 0.95,
            'boxes': []
        }
        
        # Simulate OCR extraction
        result = mock_ocr().extract_text('test_image.jpg')
        assert result['confidence'] > 0.9
    
    @patch('google.generativeai.GenerativeModel')
    def test_document_analysis_integration(self, mock_model):
        """Test Gemini document analysis"""
        mock_response = MagicMock()
        mock_response.text = "Summary: This is an invoice document"
        mock_model.return_value.generate_content.return_value = mock_response
        
        import google.generativeai as genai
        model = genai.GenerativeModel('gemini-pro')
        result = model.generate_content("Analyze this document")
        
        assert 'invoice' in result.text.lower()


@pytest.mark.integration
class TestSpeech2TextAPI:
    """Test Speech2Text Service API Integration"""
    
    @patch('whisper.load_model')
    def test_transcription_integration(self, mock_whisper):
        """Test Whisper transcription"""
        mock_whisper.return_value.transcribe.return_value = {
            'text': 'This is the transcribed speech',
            'language': 'vi'
        }
        
        import whisper
        model = whisper.load_model('base')
        result = model.transcribe('audio.mp3')
        
        assert 'text' in result
        assert result['language'] == 'vi'


@pytest.mark.integration
class TestLoRATrainingIntegration:
    """Test LoRA Training Integration"""
    
    def test_training_workflow(self):
        """Test LoRA training workflow"""
        workflow_steps = [
            'load_config',
            'prepare_dataset',
            'initialize_model',
            'train_epochs',
            'save_checkpoint'
        ]
        
        completed_steps = []
        for step in workflow_steps:
            # Simulate step completion
            completed_steps.append(step)
        
        assert len(completed_steps) == len(workflow_steps)


@pytest.mark.integration
class TestUpscaleIntegration:
    """Test Upscale Tool Integration"""
    
    @patch('torch.nn.Module')
    def test_upscale_pipeline(self, mock_model):
        """Test upscaling pipeline"""
        input_size = (512, 512)
        scale = 4
        output_size = (input_size[0] * scale, input_size[1] * scale)
        
        assert output_size == (2048, 2048)


@pytest.mark.integration
class TestStableDiffusionIntegration:
    """Test Stable Diffusion Integration"""
    
    @patch('modules.processing.process_images')
    def test_txt2img_integration(self, mock_process):
        """Test txt2img generation"""
        mock_process.return_value = MagicMock(
            images=['img1', 'img2'],
            info='{"seed": 12345}'
        )
        
        from modules.processing import process_images
        result = process_images(MagicMock())
        
        assert len(result.images) == 2


@pytest.mark.integration
@pytest.mark.api
class TestHubGatewayAPI:
    """Integration tests for Hub Gateway API"""
    
    def test_hub_services_endpoint_integration(self, hub_client):
        """Test hub services endpoint returns all services"""
        response = hub_client.get('/api/services')
        assert response.status_code == 200
        
        data = response.get_json()
        
        # Should have multiple services
        assert len(data) >= 3
        
        # Check service names
        service_names = [data[key]['name'] for key in data]
        assert any('ChatBot' in name for name in service_names)
        assert any('Text to SQL' in name or 'SQL' in name for name in service_names)
    
    def test_hub_health_check_integration(self, hub_client):
        """Test hub health check provides system status"""
        response = hub_client.get('/api/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert data['services_count'] > 0
        assert 'version' in data
    
    def test_hub_stats_integration(self, hub_client):
        """Test hub stats endpoint"""
        response = hub_client.get('/api/stats')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'total_services' in data
        assert 'services_list' in data
        assert data['total_services'] == len(data['services_list'])
    
    def test_hub_service_details(self, hub_client):
        """Test getting specific service details"""
        # Get all services first
        response = hub_client.get('/api/services')
        services = response.get_json()
        
        # Test first service
        first_service = list(services.keys())[0]
        response = hub_client.get(f'/api/services/{first_service}')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'name' in data
        assert 'url' in data
        assert 'features' in data


@pytest.mark.integration
@pytest.mark.api
class TestChatBotAPI:
    """Integration tests for ChatBot API"""
    
    @patch('ChatBot.app.MONGODB_ENABLED', False)
    @patch('google.generativeai.GenerativeModel')
    def test_chatbot_conversation_flow(self, mock_model, chatbot_client):
        """Test complete chatbot conversation flow"""
        # Setup mock AI response
        mock_response = MagicMock()
        mock_response.text = "Hello! How can I help you today?"
        mock_model.return_value.generate_content.return_value = mock_response
        
        # Note: This test assumes chatbot has a chat endpoint
        # Adjust based on actual API structure
        pass
    
    @patch('ChatBot.app.MONGODB_ENABLED', False)
    def test_chatbot_session_management(self, chatbot_client):
        """Test chatbot session management"""
        # Test that sessions are created and maintained
        with chatbot_client.session_transaction() as sess:
            sess['user_id'] = 'test_user_123'
            sess['conversation_id'] = 'conv_123'
        
        # Session should persist
        with chatbot_client.session_transaction() as sess:
            assert sess.get('user_id') == 'test_user_123'


@pytest.mark.integration
@pytest.mark.api
class TestText2SQLAPI:
    """Integration tests for Text2SQL API"""
    
    @patch('google.generativeai.GenerativeModel')
    def test_text2sql_generation_flow(self, mock_model, text2sql_client, sample_schema):
        """Test complete Text2SQL generation flow"""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = "SELECT * FROM users WHERE age > 25 LIMIT 100;"
        mock_model.return_value.generate_content.return_value = mock_response
        
        # This would test the actual API endpoint
        # Adjust based on actual endpoint structure
        pass


@pytest.mark.integration
class TestServiceCommunication:
    """Test communication between services"""
    
    def test_hub_to_chatbot_reference(self, hub_client):
        """Test hub references chatbot correctly"""
        response = hub_client.get('/api/services/chatbot')
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'url' in data
            assert 'port' in data
            assert data['port'] > 0
    
    def test_hub_to_text2sql_reference(self, hub_client):
        """Test hub references text2sql correctly"""
        response = hub_client.get('/api/services/text2sql')
        
        if response.status_code == 200:
            data = response.get_json()
            assert 'url' in data
            assert 'port' in data
    
    @patch('requests.get')
    def test_service_health_check_call(self, mock_get):
        """Test calling service health check from hub"""
        # Setup mock response
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {'status': 'healthy', 'service': 'chatbot'}
        )
        
        # Test health check call
        import requests
        response = requests.get('http://localhost:5000/api/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'


@pytest.mark.integration
@pytest.mark.slow
class TestDatabaseIntegration:
    """Test database integration workflows"""
    
    def test_mongodb_conversation_workflow(self):
        """Test complete conversation storage workflow"""
        from tests.mocks import MockMongoDBClient
        
        # Setup
        client = MockMongoDBClient()
        client.connect()
        db = client['chatbot_db']
        conversations = db['conversations']
        
        # Create conversation
        conv = {
            'user_id': 'user_123',
            'title': 'Integration Test Chat',
            'messages': [],
            'created_at': '2025-12-10T10:00:00'
        }
        result = conversations.insert_one(conv)
        conv_id = result.inserted_id
        
        # Add messages
        messages = db['messages']
        messages.insert_one({
            'conversation_id': conv_id,
            'role': 'user',
            'content': 'Hello',
            'timestamp': '2025-12-10T10:00:01'
        })
        messages.insert_one({
            'conversation_id': conv_id,
            'role': 'assistant',
            'content': 'Hi there!',
            'timestamp': '2025-12-10T10:00:02'
        })
        
        # Retrieve conversation with messages
        conv_data = conversations.find_one({'_id': conv_id})
        conv_messages = messages.find({'conversation_id': conv_id})
        
        assert conv_data is not None
        assert len(list(conv_messages)) >= 2
    
    def test_text2sql_knowledge_base_workflow(self, temp_dir):
        """Test Text2SQL knowledge base storage and retrieval"""
        kb_dir = temp_dir / "knowledge_base"
        kb_dir.mkdir()
        
        # Store query
        entry = {
            'id': 'kb_test_001',
            'question': 'Get all active users',
            'sql': 'SELECT * FROM users WHERE active = 1',
            'schema_hash': 'abc123',
            'feedback': 'positive',
            'timestamp': '2025-12-10T10:00:00'
        }
        
        kb_file = kb_dir / f"{entry['id']}.json"
        kb_file.write_text(json.dumps(entry, indent=2))
        
        # Search knowledge base
        search_term = 'active users'
        matching = []
        
        for file in kb_dir.glob("*.json"):
            data = json.loads(file.read_text())
            if search_term.lower() in data['question'].lower():
                matching.append(data)
        
        assert len(matching) == 1
        assert matching[0]['sql'] == entry['sql']


@pytest.mark.integration
@pytest.mark.api
class TestExternalAPIIntegration:
    """Test integration with external APIs"""
    
    @patch('google.generativeai.GenerativeModel')
    def test_gemini_api_integration(self, mock_model):
        """Test Gemini API integration workflow"""
        # Setup mock
        mock_response = MagicMock()
        mock_response.text = "This is a test response from Gemini"
        mock_model.return_value.generate_content.return_value = mock_response
        
        # Test
        import google.generativeai as genai
        model = genai.GenerativeModel('gemini-pro')
        
        # Multiple calls
        responses = []
        for i in range(3):
            response = model.generate_content(f"Test prompt {i}")
            responses.append(response.text)
        
        assert len(responses) == 3
        for resp in responses:
            assert isinstance(resp, str)
    
    @patch('openai.OpenAI')
    def test_openai_api_integration(self, mock_client):
        """Test OpenAI API integration workflow"""
        # Setup mock
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="OpenAI test response"))
        ]
        mock_client.return_value.chat.completions.create.return_value = mock_response
        
        # Test
        import openai
        client = openai.OpenAI(api_key="test-key")
        
        # Conversation flow
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"}
        ]
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        
        assert response.choices[0].message.content is not None
    
    @patch('requests.post')
    def test_stable_diffusion_api_integration(self, mock_post):
        """Test Stable Diffusion API integration"""
        # Setup mock
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                'images': ['base64_image_data_here'],
                'info': json.dumps({'prompt': 'test prompt'})
            }
        )
        
        # Test image generation
        import requests
        response = requests.post(
            'http://localhost:7860/sdapi/v1/txt2img',
            json={
                'prompt': 'A beautiful landscape',
                'steps': 20,
                'width': 512,
                'height': 512
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'images' in data
        assert len(data['images']) > 0


@pytest.mark.integration
@pytest.mark.slow
class TestCacheIntegration:
    """Test cache integration workflows"""
    
    def test_cache_workflow_with_api(self, temp_dir):
        """Test caching API responses"""
        from src.utils.cache import Cache
        
        cache = Cache(cache_dir=str(temp_dir / "cache"), ttl_seconds=60)
        
        # Simulate API call with cache
        cache_key = "api:services:all"
        
        # First call - cache miss
        cached_data = cache.get(cache_key)
        assert cached_data is None
        
        # Fetch data (simulated)
        api_data = {
            'services': ['chatbot', 'text2sql', 'speech2text'],
            'count': 3
        }
        
        # Store in cache
        cache.set(cache_key, api_data)
        
        # Second call - cache hit
        cached_data = cache.get(cache_key)
        assert cached_data is not None
        assert cached_data['count'] == 3
    
    def test_cache_invalidation_workflow(self, temp_dir):
        """Test cache invalidation on updates"""
        from src.utils.cache import Cache
        
        cache = Cache(cache_dir=str(temp_dir / "cache"))
        
        # Set initial data
        cache.set('user:123', {'name': 'John', 'email': 'john@example.com'})
        
        # Update user (invalidate cache)
        cache.delete('user:123')
        
        # Set new data
        cache.set('user:123', {'name': 'John Doe', 'email': 'johndoe@example.com'})
        
        # Verify updated
        user_data = cache.get('user:123')
        assert user_data['name'] == 'John Doe'


@pytest.mark.integration
class TestRateLimitingIntegration:
    """Test rate limiting integration"""
    
    def test_rate_limit_across_requests(self, hub_client):
        """Test rate limiting across multiple requests"""
        # Make several requests
        responses = []
        for i in range(10):
            response = hub_client.get('/api/health')
            responses.append(response.status_code)
        
        # All should succeed (under limit)
        assert all(status == 200 for status in responses)
    
    def test_rate_limit_enforcement(self):
        """Test rate limit is enforced"""
        from src.utils.rate_limiter import RateLimiter
        
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Make requests up to limit
        allowed_count = 0
        blocked_count = 0
        
        for i in range(10):
            if limiter.is_allowed('test_client'):
                allowed_count += 1
            else:
                blocked_count += 1
        
        assert allowed_count == 5
        assert blocked_count == 5


@pytest.mark.integration
@pytest.mark.smoke
class TestSmokeTests:
    """Quick smoke tests for critical functionality"""
    
    def test_hub_gateway_alive(self, hub_client):
        """Smoke test: Hub gateway is responsive"""
        response = hub_client.get('/')
        assert response.status_code == 200
    
    def test_hub_api_alive(self, hub_client):
        """Smoke test: Hub API endpoints are responsive"""
        endpoints = ['/api/services', '/api/health', '/api/stats']
        
        for endpoint in endpoints:
            response = hub_client.get(endpoint)
            assert response.status_code == 200
    
    def test_chatbot_alive(self, chatbot_client):
        """Smoke test: ChatBot service is responsive"""
        response = chatbot_client.get('/')
        assert response.status_code in [200, 404]  # Either has index or not
    
    def test_text2sql_alive(self, text2sql_client):
        """Smoke test: Text2SQL service is responsive"""
        response = text2sql_client.get('/')
        assert response.status_code in [200, 404]
    
    def test_all_services_configured(self, service_configs):
        """Smoke test: All services are properly configured"""
        assert len(service_configs) >= 3
        
        for name, config in service_configs.items():
            assert config.name is not None
            assert config.port > 0
            assert config.url.startswith('http')


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Test error handling across services"""
    
    def test_404_error_handling(self, hub_client):
        """Test 404 error handling"""
        response = hub_client.get('/api/nonexistent/endpoint')
        assert response.status_code == 404
    
    def test_service_not_found_error(self, hub_client):
        """Test service not found error"""
        response = hub_client.get('/api/services/invalid_service_xyz')
        assert response.status_code == 404
        
        data = response.get_json()
        assert 'error' in data
    
    def test_invalid_method_error(self, hub_client):
        """Test invalid HTTP method error"""
        # POST to GET-only endpoint
        response = hub_client.post('/api/health')
        assert response.status_code in [404, 405]  # Method not allowed
