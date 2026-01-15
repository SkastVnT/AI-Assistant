"""
ChatbotAgent class - Multi-model AI chatbot with streaming, retry, and fallback support
Refactored to eliminate code duplication and add enterprise features
"""
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Generator, Union
import openai
import requests

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import (
    OPENAI_API_KEY, DEEPSEEK_API_KEY, GROK_API_KEY,
    QWEN_API_KEY, HUGGINGFACE_API_KEY,
    SYSTEM_PROMPTS, get_system_prompts
)
from core.extensions import (
    MONGODB_ENABLED, LOCALMODELS_AVAILABLE, model_loader,
    get_cached_response, cache_response, wait_for_openai_rate_limit,
    ConversationDB, logger
)
from core.db_helpers import (
    load_conversation_history, save_message_to_db,
    get_user_id_from_session, set_active_conversation
)
from core.base_chat import (
    ModelConfig, ModelProvider, ChatContext, ChatResponse,
    OpenAICompatibleChat, QwenChat, BloomVNChat,
    ModelFallbackManager, DEFAULT_FALLBACK_CHAIN,
    ContextWindowManager
)


class ChatError(Exception):
    """Custom exception for chat errors"""
    def __init__(self, message: str, model: str, recoverable: bool = True):
        super().__init__(message)
        self.model = model
        self.recoverable = recoverable


class ModelRegistry:
    """Registry for model configurations and handlers"""
    
    def __init__(self):
        self._configs: Dict[str, ModelConfig] = {}
        self._handlers: Dict[str, Any] = {}
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize all supported models"""
        # OpenAI
        if OPENAI_API_KEY:
            self._configs['openai'] = ModelConfig(
                name='openai',
                provider=ModelProvider.OPENAI,
                api_key=OPENAI_API_KEY,
                model_id='gpt-4o-mini',
                supports_streaming=True,
                fallback_model='deepseek'
            )
        
        # DeepSeek
        if DEEPSEEK_API_KEY:
            self._configs['deepseek'] = ModelConfig(
                name='deepseek',
                provider=ModelProvider.DEEPSEEK,
                api_key=DEEPSEEK_API_KEY,
                base_url='https://api.deepseek.com/v1',
                model_id='deepseek-chat',
                supports_streaming=True,
                fallback_model='openai'
            )
        
        # Grok
        if GROK_API_KEY:
            self._configs['grok'] = ModelConfig(
                name='grok',
                provider=ModelProvider.GROK,
                api_key=GROK_API_KEY,
                base_url='https://api.x.ai/v1',
                model_id='grok-3',
                supports_streaming=True,
                fallback_model='deepseek'
            )
        
        # Qwen
        if QWEN_API_KEY:
            self._configs['qwen'] = ModelConfig(
                name='qwen',
                provider=ModelProvider.QWEN,
                api_key=QWEN_API_KEY,
                model_id='qwen-turbo',
                supports_streaming=True,
                fallback_model='deepseek'
            )
        
        # BloomVN
        if HUGGINGFACE_API_KEY:
            self._configs['bloomvn'] = ModelConfig(
                name='bloomvn',
                provider=ModelProvider.BLOOMVN,
                api_key=HUGGINGFACE_API_KEY,
                model_id='BlossomsAI/BloomVN-8B-chat',
                timeout=60,
                supports_streaming=False,
                fallback_model='qwen'
            )
        
        # Create handlers
        for name, config in self._configs.items():
            self._handlers[name] = self._create_handler(config)
    
    def _create_handler(self, config: ModelConfig):
        """Create appropriate handler for model"""
        if config.provider in [ModelProvider.OPENAI, ModelProvider.DEEPSEEK, ModelProvider.GROK]:
            return OpenAICompatibleChat(config)
        elif config.provider == ModelProvider.QWEN:
            return QwenChat(config)
        elif config.provider == ModelProvider.BLOOMVN:
            return BloomVNChat(config)
        return None
    
    def get_handler(self, model: str):
        """Get handler for a model"""
        return self._handlers.get(model)
    
    def get_config(self, model: str) -> Optional[ModelConfig]:
        """Get config for a model"""
        return self._configs.get(model)
    
    def is_available(self, model: str) -> bool:
        """Check if model is available"""
        return model in self._handlers
    
    def list_available(self) -> List[str]:
        """List all available models"""
        return list(self._handlers.keys())


# Global model registry
_model_registry = None

def get_model_registry() -> ModelRegistry:
    """Get or create model registry"""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry


class ChatbotAgent:
    """Multi-model chatbot agent with streaming, retry, and fallback support"""
    
    def __init__(self, conversation_id=None):
        self.conversation_history: List[Dict] = []
        self.current_model = 'grok'
        self.conversation_id = conversation_id
        self.registry = get_model_registry()
        self.fallback_manager = ModelFallbackManager(DEFAULT_FALLBACK_CHAIN)
        
        if MONGODB_ENABLED and conversation_id:
            self.conversation_history = load_conversation_history(conversation_id)
    
    def _build_context(
        self,
        message: str,
        context: str = 'casual',
        deep_thinking: bool = False,
        history: Optional[List[Dict]] = None,
        memories: Optional[List[Dict]] = None,
        language: str = 'vi',
        custom_prompt: Optional[str] = None
    ) -> ChatContext:
        """Build chat context"""
        return ChatContext(
            message=message,
            context=context,
            deep_thinking=deep_thinking,
            language=language,
            custom_prompt=custom_prompt,
            history=history,
            memories=memories,
            conversation_history=self.conversation_history
        )
    
    def _chat_with_model(
        self,
        model: str,
        ctx: ChatContext,
        stream: bool = False
    ) -> Union[ChatResponse, Generator[str, None, None]]:
        """Execute chat with a specific model"""
        handler = self.registry.get_handler(model)
        
        if handler is None:
            return ChatResponse(
                content=f"❌ Model '{model}' not available or API key not configured",
                model=model,
                provider="unknown",
                success=False,
                error=f"Model '{model}' not available"
            )
        
        # Check cache for non-streaming requests
        if not stream:
            config = self.registry.get_config(model)
            if config:
                cache_key_params = {
                    'context': ctx.context,
                    'deep_thinking': ctx.deep_thinking,
                    'language': ctx.language,
                    'custom_prompt': ctx.custom_prompt[:50] if ctx.custom_prompt else None
                }
                cached = get_cached_response(ctx.message, config.model_id, provider=model, **cache_key_params)
                if cached:
                    return ChatResponse(
                        content=cached,
                        model=model,
                        provider=config.provider.value,
                        success=True
                    )
        
        # Rate limiting for OpenAI
        if model == 'openai':
            wait_for_openai_rate_limit()
        
        # Execute chat
        result = handler.chat(ctx, get_system_prompts, stream=stream)
        
        # Cache successful non-streaming responses
        if not stream and isinstance(result, ChatResponse) and result.success:
            config = self.registry.get_config(model)
            if config:
                cache_key_params = {
                    'context': ctx.context,
                    'deep_thinking': ctx.deep_thinking,
                    'language': ctx.language,
                    'custom_prompt': ctx.custom_prompt[:50] if ctx.custom_prompt else None
                }
                cache_response(ctx.message, config.model_id, result.content, provider=model, **cache_key_params)
        
        return result
    
    def chat_stream(
        self,
        message: str,
        model: str = 'grok',
        context: str = 'casual',
        deep_thinking: bool = False,
        history: Optional[List[Dict]] = None,
        memories: Optional[List[Dict]] = None,
        language: str = 'vi',
        custom_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Stream chat response in real-time
        
        Yields:
            str: Response chunks as they arrive
        """
        ctx = self._build_context(message, context, deep_thinking, history, memories, language, custom_prompt)
        
        # Save user message if using MongoDB
        if MONGODB_ENABLED and self.conversation_id and history is None:
            save_message_to_db(
                conversation_id=self.conversation_id,
                role='user',
                content=message,
                metadata={'model': model, 'context': context, 'deep_thinking': deep_thinking}
            )
        
        # Try to get streaming response
        handler = self.registry.get_handler(model)
        config = self.registry.get_config(model)
        
        if handler is None:
            yield f"❌ Model '{model}' not available"
            return
        
        if not config or not config.supports_streaming:
            # Fallback to non-streaming and simulate
            response = self._chat_with_model(model, ctx, stream=False)
            if isinstance(response, ChatResponse):
                from core.streaming import NonStreamingToStreaming
                for chunk in NonStreamingToStreaming.simulate_stream(response.content):
                    yield chunk
                
                # Save to history
                self._save_to_history(message, response.content, model, history)
            return
        
        # Stream the response
        try:
            full_response = ""
            for chunk in handler.chat(ctx, get_system_prompts, stream=True):
                full_response += chunk
                yield chunk
            
            # Save to history after streaming completes
            self._save_to_history(message, full_response, model, history)
            
        except Exception as e:
            logger.error(f"[{model}] Streaming error: {e}")
            yield f"❌ Error: {str(e)}"
    
    def _save_to_history(
        self,
        message: str,
        response: str,
        model: str,
        history: Optional[List[Dict]] = None,
        thinking_process: Optional[str] = None
    ):
        """Save message and response to history"""
        if history is None:
            self.conversation_history.append({
                'user': message,
                'assistant': response,
                'timestamp': datetime.now().isoformat(),
                'model': model
            })
            
            if MONGODB_ENABLED and self.conversation_id:
                save_message_to_db(
                    conversation_id=self.conversation_id,
                    role='assistant',
                    content=response,
                    metadata={'model': model, 'thinking_process': thinking_process}
                )
    
    def chat(
        self,
        message: str,
        model: str = 'grok',
        context: str = 'casual',
        deep_thinking: bool = False,
        history: Optional[List[Dict]] = None,
        memories: Optional[List[Dict]] = None,
        language: str = 'vi',
        custom_prompt: Optional[str] = None,
        enable_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Main chat method with fallback support
        
        Args:
            message: User message
            model: Model to use
            context: Conversation context type
            deep_thinking: Enable detailed reasoning
            history: Custom history (overrides internal history)
            memories: Knowledge base memories to include
            language: Response language
            custom_prompt: Custom system prompt
            enable_fallback: Enable automatic fallback on failure
        
        Returns:
            Dict with 'response' and optional 'thinking_process'
        """
        # Handle local models separately
        if model in ['bloomvn-local', 'qwen1.5-local', 'qwen2.5-local']:
            return self._chat_with_local_model(message, model, context, deep_thinking, language)
        
        ctx = self._build_context(message, context, deep_thinking, history, memories, language, custom_prompt)
        
        # Save user message
        if MONGODB_ENABLED and self.conversation_id and history is None:
            save_message_to_db(
                conversation_id=self.conversation_id,
                role='user',
                content=message,
                metadata={'model': model, 'context': context, 'deep_thinking': deep_thinking}
            )
        
        # Execute with or without fallback
        if enable_fallback:
            response = self.fallback_manager.execute_with_fallback(
                model,
                lambda m: self._chat_with_model(m, ctx)
            )
        else:
            response = self._chat_with_model(model, ctx)
        
        # Handle response
        if isinstance(response, ChatResponse):
            if response.success:
                result_text = response.content
                if response.is_fallback:
                    result_text = f"⚠️ [Fallback to {response.model}]\n\n{result_text}"
            else:
                result_text = f"❌ Error: {response.error}"
            
            # Save to history
            self._save_to_history(message, result_text, response.model, history, response.thinking_process)
            
            return {
                'response': result_text,
                'thinking_process': response.thinking_process,
                'model': response.model,
                'is_fallback': response.is_fallback,
                'retry_count': response.retry_count
            }
        
        # Fallback for unexpected response type
        return {'response': str(response), 'thinking_process': None}
    
    def _chat_with_local_model(
        self,
        message: str,
        model: str,
        context: str = 'casual',
        deep_thinking: bool = False,
        language: str = 'vi'
    ) -> Dict[str, Any]:
        """Chat with local models"""
        if not LOCALMODELS_AVAILABLE:
            return {'response': "❌ Local models not available", 'thinking_process': None}
        
        try:
            model_map = {
                'bloomvn-local': 'bloomvn',
                'qwen1.5-local': 'qwen1.5',
                'qwen2.5-local': 'qwen2.5'
            }
            model_key = model_map.get(model)
            if not model_key:
                return {'response': f"Model not supported: {model}", 'thinking_process': None}
            
            system_prompt = SYSTEM_PROMPTS.get(context, SYSTEM_PROMPTS['casual'])
            
            # Use smart context window
            history = ContextWindowManager.get_smart_history(
                self.conversation_history,
                model_id='local',
                system_prompt=system_prompt,
                current_message=message,
                max_messages=5
            )
            
            messages = []
            for hist in history:
                messages.append({'role': 'user', 'content': hist.get('user', hist.get('content', ''))})
                if 'assistant' in hist:
                    messages.append({'role': 'assistant', 'content': hist['assistant']})
            messages.append({'role': 'user', 'content': message})
            
            response = model_loader.generate(
                model_key=model_key,
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=2000 if deep_thinking else 1000,
                temperature=0.5 if deep_thinking else 0.7
            )
            
            self._save_to_history(message, response, model, None)
            return {'response': response, 'thinking_process': None}
            
        except Exception as e:
            error_msg = f"❌ Local model error: {str(e)}"
            return {'response': error_msg, 'thinking_process': None}
    
    # Legacy methods for backwards compatibility
    def chat_with_openai(self, message, context='casual', deep_thinking=False,
                         history=None, memories=None, language='vi', custom_prompt=None):
        """Legacy: Chat using OpenAI"""
        result = self.chat(message, 'openai', context, deep_thinking, history, memories, language, custom_prompt, enable_fallback=False)
        return result.get('response', '')
    
    def chat_with_deepseek(self, message, context='casual', deep_thinking=False,
                           history=None, memories=None, language='vi', custom_prompt=None):
        """Legacy: Chat using DeepSeek"""
        result = self.chat(message, 'deepseek', context, deep_thinking, history, memories, language, custom_prompt, enable_fallback=False)
        return result.get('response', '')
    
    def chat_with_grok(self, message, context='casual', deep_thinking=False,
                       history=None, memories=None, language='vi', custom_prompt=None):
        """Legacy: Chat using GROK"""
        result = self.chat(message, 'grok', context, deep_thinking, history, memories, language, custom_prompt, enable_fallback=False)
        return result.get('response', '')
    
    def chat_with_qwen(self, message, context='casual', deep_thinking=False, language='vi'):
        """Legacy: Chat using Qwen"""
        result = self.chat(message, 'qwen', context, deep_thinking, None, None, language, None, enable_fallback=False)
        return result.get('response', '')
    
    def chat_with_bloomvn(self, message, context='casual', deep_thinking=False, language='vi'):
        """Legacy: Chat using BloomVN"""
        result = self.chat(message, 'bloomvn', context, deep_thinking, None, None, language, None, enable_fallback=False)
        return result.get('response', '')
    
    def chat_with_local_model(self, message, model, context='casual', deep_thinking=False, language='vi'):
        """Legacy: Chat with local models"""
        result = self._chat_with_local_model(message, model, context, deep_thinking, language)
        return result.get('response', '')
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        
        if MONGODB_ENABLED and self.conversation_id:
            try:
                ConversationDB.archive_conversation(str(self.conversation_id))
                user_id = get_user_id_from_session()
                conv = ConversationDB.create_conversation(user_id=user_id, model=self.current_model, title="New Chat")
                self.conversation_id = conv['_id']
                set_active_conversation(self.conversation_id)
            except Exception as e:
                logging.error(f"Error clearing history: {e}")


# Store chatbot instances per session
chatbots: Dict[str, ChatbotAgent] = {}


def get_chatbot(session_id: str) -> ChatbotAgent:
    """Get or create chatbot for session"""
    from core.db_helpers import get_or_create_conversation, get_user_id_from_session, set_active_conversation
    
    if session_id not in chatbots:
        conversation_id = None
        if MONGODB_ENABLED:
            user_id = get_user_id_from_session()
            conv = get_or_create_conversation(user_id)
            if conv:
                conversation_id = conv['_id']
                set_active_conversation(conversation_id)
        
        chatbots[session_id] = ChatbotAgent(conversation_id=conversation_id)
    return chatbots[session_id]
