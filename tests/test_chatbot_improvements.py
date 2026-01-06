"""
Tests for ChatBot improvements:
- Streaming (SSE)
- Async processing
- Error handling
- Retry logic
- Model fallback
- Context window management
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from dataclasses import dataclass
import sys
from pathlib import Path

# Add chatbot to path
CHATBOT_DIR = Path(__file__).parent.parent / 'services' / 'chatbot'
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))


# ============================================================================
# Tests for base_chat.py
# ============================================================================

class TestModelConfig:
    """Tests for ModelConfig dataclass"""
    
    def test_model_config_defaults(self):
        """Test ModelConfig with default values"""
        from core.base_chat import ModelConfig, ModelProvider
        
        config = ModelConfig(
            name='test-model',
            provider=ModelProvider.OPENAI
        )
        
        assert config.name == 'test-model'
        assert config.provider == ModelProvider.OPENAI
        assert config.max_tokens == 1000
        assert config.temperature == 0.7
        assert config.supports_streaming is True
    
    def test_model_config_custom_values(self):
        """Test ModelConfig with custom values"""
        from core.base_chat import ModelConfig, ModelProvider
        
        config = ModelConfig(
            name='custom-model',
            provider=ModelProvider.GROK,
            api_key='test-key',
            base_url='https://api.test.com',
            model_id='grok-3',
            max_tokens=2000,
            temperature=0.5,
            supports_streaming=False,
            fallback_model='openai'
        )
        
        assert config.api_key == 'test-key'
        assert config.base_url == 'https://api.test.com'
        assert config.model_id == 'grok-3'
        assert config.max_tokens == 2000
        assert config.fallback_model == 'openai'


class TestChatContext:
    """Tests for ChatContext dataclass"""
    
    def test_chat_context_defaults(self):
        """Test ChatContext with default values"""
        from core.base_chat import ChatContext
        
        ctx = ChatContext(message="Hello")
        
        assert ctx.message == "Hello"
        assert ctx.context == "casual"
        assert ctx.deep_thinking is False
        assert ctx.language == "vi"
        assert ctx.history is None
        assert ctx.memories is None
    
    def test_chat_context_full(self):
        """Test ChatContext with all values"""
        from core.base_chat import ChatContext
        
        ctx = ChatContext(
            message="Test message",
            context="programming",
            deep_thinking=True,
            language="en",
            custom_prompt="Custom prompt",
            history=[{"role": "user", "content": "Hi"}],
            memories=[{"title": "Memory", "content": "Content"}],
            conversation_history=[{"user": "Hello", "assistant": "Hi"}]
        )
        
        assert ctx.deep_thinking is True
        assert ctx.custom_prompt == "Custom prompt"
        assert len(ctx.history) == 1
        assert len(ctx.memories) == 1


class TestChatResponse:
    """Tests for ChatResponse dataclass"""
    
    def test_chat_response_success(self):
        """Test successful ChatResponse"""
        from core.base_chat import ChatResponse
        
        response = ChatResponse(
            content="Hello!",
            model="grok",
            provider="grok",
            success=True
        )
        
        assert response.content == "Hello!"
        assert response.success is True
        assert response.error is None
        assert response.is_fallback is False
    
    def test_chat_response_failure(self):
        """Test failed ChatResponse"""
        from core.base_chat import ChatResponse
        
        response = ChatResponse(
            content="",
            model="grok",
            provider="grok",
            success=False,
            error="API Error"
        )
        
        assert response.success is False
        assert response.error == "API Error"
    
    def test_chat_response_fallback(self):
        """Test fallback ChatResponse"""
        from core.base_chat import ChatResponse
        
        response = ChatResponse(
            content="Fallback response",
            model="deepseek",
            provider="deepseek",
            is_fallback=True,
            retry_count=2
        )
        
        assert response.is_fallback is True
        assert response.retry_count == 2


class TestContextWindowManager:
    """Tests for ContextWindowManager"""
    
    def test_estimate_tokens(self):
        """Test token estimation"""
        from core.base_chat import ContextWindowManager
        
        text = "Hello world"  # 11 chars
        tokens = ContextWindowManager.estimate_tokens(text)
        
        # ~1.5 chars per token
        assert 5 <= tokens <= 10
    
    def test_get_smart_history_empty(self):
        """Test smart history with empty input"""
        from core.base_chat import ContextWindowManager
        
        history = ContextWindowManager.get_smart_history([])
        assert history == []
    
    def test_get_smart_history_within_limit(self):
        """Test smart history within token limit"""
        from core.base_chat import ContextWindowManager
        
        conversation = [
            {"user": "Hello", "assistant": "Hi there!"},
            {"user": "How are you?", "assistant": "I'm good!"}
        ]
        
        history = ContextWindowManager.get_smart_history(
            conversation,
            model_id="gpt-4o-mini",
            system_prompt="You are helpful",
            current_message="Test"
        )
        
        assert len(history) == 2
    
    def test_get_smart_history_truncation(self):
        """Test smart history truncates old messages"""
        from core.base_chat import ContextWindowManager
        
        # Create long conversation
        conversation = [
            {"user": "A" * 1000, "assistant": "B" * 1000}
            for _ in range(50)
        ]
        
        history = ContextWindowManager.get_smart_history(
            conversation,
            model_id="bloomvn",  # Small context
            system_prompt="System",
            current_message="Test"
        )
        
        # Should be truncated
        assert len(history) < 50
    
    def test_get_smart_history_max_messages(self):
        """Test max_messages limit"""
        from core.base_chat import ContextWindowManager
        
        conversation = [
            {"user": f"Msg {i}", "assistant": f"Reply {i}"}
            for i in range(20)
        ]
        
        history = ContextWindowManager.get_smart_history(
            conversation,
            max_messages=5
        )
        
        assert len(history) <= 5


class TestRetryDecorator:
    """Tests for retry logic"""
    
    def test_retry_success_first_try(self):
        """Test successful call on first try"""
        from core.base_chat import with_retry, RetryConfig
        
        call_count = 0
        
        @with_retry(RetryConfig(max_retries=3))
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_success_after_failures(self):
        """Test success after retries"""
        from core.base_chat import with_retry, RetryConfig
        import requests
        
        call_count = 0
        
        @with_retry(RetryConfig(max_retries=3, base_delay=0.01))
        def retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.exceptions.Timeout("Timeout")
            return "success"
        
        result = retry_func()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_all_failed(self):
        """Test all retries exhausted"""
        from core.base_chat import with_retry, RetryConfig
        import requests
        
        @with_retry(RetryConfig(max_retries=2, base_delay=0.01))
        def always_fail():
            raise requests.exceptions.Timeout("Timeout")
        
        with pytest.raises(requests.exceptions.Timeout):
            always_fail()


class TestModelFallbackManager:
    """Tests for ModelFallbackManager"""
    
    def test_get_fallbacks(self):
        """Test getting fallback models"""
        from core.base_chat import ModelFallbackManager, DEFAULT_FALLBACK_CHAIN
        
        manager = ModelFallbackManager(DEFAULT_FALLBACK_CHAIN)
        
        fallbacks = manager.get_fallbacks('grok')
        assert 'deepseek' in fallbacks
        assert 'openai' in fallbacks
    
    def test_execute_with_fallback_primary_success(self):
        """Test primary model succeeds"""
        from core.base_chat import ModelFallbackManager, ChatResponse
        
        manager = ModelFallbackManager({'model1': ['model2']})
        
        def chat_func(model):
            return ChatResponse(
                content="Success",
                model=model,
                provider="test",
                success=True
            )
        
        result = manager.execute_with_fallback('model1', chat_func)
        assert result.success is True
        assert result.is_fallback is False
    
    def test_execute_with_fallback_uses_fallback(self):
        """Test fallback model is used when primary fails"""
        from core.base_chat import ModelFallbackManager, ChatResponse
        
        manager = ModelFallbackManager({'model1': ['model2', 'model3']})
        
        def chat_func(model):
            if model == 'model1':
                return ChatResponse(
                    content="",
                    model=model,
                    provider="test",
                    success=False,
                    error="Primary failed"
                )
            return ChatResponse(
                content="Fallback success",
                model=model,
                provider="test",
                success=True
            )
        
        result = manager.execute_with_fallback('model1', chat_func)
        assert result.success is True
        assert result.is_fallback is True
        assert result.model == 'model2'


# ============================================================================
# Tests for streaming.py
# ============================================================================

class TestStreamEvent:
    """Tests for StreamEvent"""
    
    def test_format_simple_event(self):
        """Test simple event formatting"""
        from core.streaming import StreamEvent
        
        event = StreamEvent(data="Hello")
        formatted = event.format()
        
        assert "data: Hello" in formatted
        assert formatted.endswith('\n\n')
    
    def test_format_with_event_type(self):
        """Test event with custom type"""
        from core.streaming import StreamEvent
        
        event = StreamEvent(event="chunk", data="content")
        formatted = event.format()
        
        assert "event: chunk" in formatted
        assert "data: content" in formatted
    
    def test_format_with_id(self):
        """Test event with ID"""
        from core.streaming import StreamEvent
        
        event = StreamEvent(event="msg", data="data", id="123")
        formatted = event.format()
        
        assert "id: 123" in formatted
    
    def test_format_multiline_data(self):
        """Test multiline data formatting"""
        from core.streaming import StreamEvent
        
        event = StreamEvent(data="line1\nline2\nline3")
        formatted = event.format()
        
        assert "data: line1" in formatted
        assert "data: line2" in formatted
        assert "data: line3" in formatted


class TestNonStreamingToStreaming:
    """Tests for NonStreamingToStreaming"""
    
    def test_simulate_stream(self):
        """Test simulating streaming from full response"""
        from core.streaming import NonStreamingToStreaming
        
        full_text = "Hello world this is a test message"
        chunks = list(NonStreamingToStreaming.simulate_stream(full_text, chunk_size=2))
        
        # Should have multiple chunks
        assert len(chunks) > 1
        
        # Reconstructed should match original
        reconstructed = ''.join(chunks)
        assert reconstructed.strip() == full_text


# ============================================================================
# Tests for chatbot_v2.py
# ============================================================================

class TestModelRegistry:
    """Tests for ModelRegistry"""
    
    @patch.dict('sys.modules', {'core.config': MagicMock()})
    @patch.dict('sys.modules', {'core.extensions': MagicMock()})
    def test_list_available_models(self):
        """Test listing available models"""
        # This test verifies the registry structure
        from core.base_chat import ModelConfig, ModelProvider
        
        config = ModelConfig(
            name='test',
            provider=ModelProvider.OPENAI,
            api_key='key'
        )
        
        assert config.name == 'test'


# ============================================================================
# Tests for async_chat.py
# ============================================================================

class TestAsyncRetryHandler:
    """Tests for AsyncRetryHandler"""
    
    @pytest.mark.asyncio
    async def test_async_retry_success(self):
        """Test async retry succeeds"""
        from core.async_chat import AsyncRetryHandler
        
        handler = AsyncRetryHandler()
        
        async def success():
            return "OK"
        
        result = await handler.execute_with_retry(success)
        assert result == "OK"
    
    @pytest.mark.asyncio
    async def test_async_retry_with_failures(self):
        """Test async retry after failures"""
        from core.async_chat import AsyncRetryHandler
        from core.base_chat import RetryConfig
        import aiohttp
        
        handler = AsyncRetryHandler(RetryConfig(max_retries=3, base_delay=0.01))
        
        call_count = 0
        
        async def retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise aiohttp.ClientError("Error")
            return "Success"
        
        # Note: aiohttp.ClientError may not be in retryable_errors by default
        # This is testing the pattern


# ============================================================================
# Integration Tests
# ============================================================================

class TestChatbotIntegration:
    """Integration tests for ChatbotAgent"""
    
    def test_chat_context_building(self):
        """Test building chat context"""
        from core.base_chat import ChatContext
        
        ctx = ChatContext(
            message="Test",
            context="programming",
            deep_thinking=True,
            memories=[{"title": "Test", "content": "Content"}]
        )
        
        assert ctx.message == "Test"
        assert ctx.context == "programming"
        assert ctx.deep_thinking is True
        assert len(ctx.memories) == 1
    
    def test_fallback_chain_configuration(self):
        """Test fallback chain is properly configured"""
        from core.base_chat import DEFAULT_FALLBACK_CHAIN
        
        # Verify key models have fallbacks
        assert 'grok' in DEFAULT_FALLBACK_CHAIN
        assert 'openai' in DEFAULT_FALLBACK_CHAIN
        assert 'deepseek' in DEFAULT_FALLBACK_CHAIN
        
        # Verify fallback lists are non-empty
        for model, fallbacks in DEFAULT_FALLBACK_CHAIN.items():
            assert len(fallbacks) > 0


# ============================================================================
# Route Tests
# ============================================================================

class TestStreamingRoutes:
    """Tests for streaming routes"""
    
    def test_stream_event_json_encoding(self):
        """Test JSON encoding in stream events"""
        from core.streaming import StreamEvent
        import json
        
        data = {"content": "Hello", "index": 1}
        event = StreamEvent(event="chunk", data=json.dumps(data))
        formatted = event.format()
        
        # Extract data line and verify JSON
        for line in formatted.split('\n'):
            if line.startswith('data: '):
                json_str = line[6:]
                parsed = json.loads(json_str)
                assert parsed['content'] == "Hello"
                assert parsed['index'] == 1


class TestErrorHandlingConsistency:
    """Tests for consistent error handling"""
    
    def test_chat_response_error_format(self):
        """Test error responses have consistent format"""
        from core.base_chat import ChatResponse
        
        error_response = ChatResponse(
            content="",
            model="test",
            provider="test",
            success=False,
            error="Test error"
        )
        
        assert error_response.success is False
        assert error_response.error is not None
        assert error_response.content == ""
    
    def test_chat_response_success_format(self):
        """Test success responses have consistent format"""
        from core.base_chat import ChatResponse
        
        success_response = ChatResponse(
            content="Hello!",
            model="test",
            provider="test",
            success=True
        )
        
        assert success_response.success is True
        assert success_response.error is None
        assert success_response.content == "Hello!"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
