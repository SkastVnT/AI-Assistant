"""
Base Chat Module - Unified chat logic with streaming, retry, and fallback support
"""
import time
import logging
import functools
from typing import Optional, List, Dict, Any, Generator, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import openai
import requests

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Supported model providers"""
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GROK = "grok"
    QWEN = "qwen"
    BLOOMVN = "bloomvn"
    LOCAL = "local"


@dataclass
class ModelConfig:
    """Configuration for a model"""
    name: str
    provider: ModelProvider
    api_key: str = ""
    base_url: str = ""
    model_id: str = ""
    max_tokens: int = 1000
    max_tokens_deep: int = 2000
    temperature: float = 0.7
    temperature_deep: float = 0.5
    timeout: int = 60
    supports_streaming: bool = True
    fallback_model: Optional[str] = None


@dataclass
class ChatContext:
    """Context for a chat request"""
    message: str
    context: str = "casual"
    deep_thinking: bool = False
    language: str = "vi"
    custom_prompt: Optional[str] = None
    history: Optional[List[Dict]] = None
    memories: Optional[List[Dict]] = None
    conversation_history: List[Dict] = field(default_factory=list)


@dataclass
class ChatResponse:
    """Standardized chat response"""
    content: str
    model: str
    provider: str
    success: bool = True
    error: Optional[str] = None
    thinking_process: Optional[str] = None
    is_fallback: bool = False
    retry_count: int = 0


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    retryable_errors: tuple = field(default_factory=lambda: (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        openai.APIConnectionError,
        openai.RateLimitError,
        openai.APITimeoutError,
    ))


def with_retry(retry_config: Optional[RetryConfig] = None):
    """Decorator for retry logic with exponential backoff"""
    if retry_config is None:
        retry_config = RetryConfig()
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(retry_config.max_retries):
                try:
                    return func(*args, **kwargs)
                except retry_config.retryable_errors as e:
                    last_error = e
                    if attempt < retry_config.max_retries - 1:
                        delay = min(
                            retry_config.base_delay * (retry_config.exponential_base ** attempt),
                            retry_config.max_delay
                        )
                        logger.warning(
                            f"[Retry] Attempt {attempt + 1}/{retry_config.max_retries} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                except Exception as e:
                    # Non-retryable error
                    raise
            
            # All retries exhausted
            raise last_error
        
        return wrapper
    return decorator


class ContextWindowManager:
    """Smart context window management"""
    
    # Approximate token limits per model
    MODEL_CONTEXT_LIMITS = {
        "gpt-4o-mini": 128000,
        "grok-3": 128000,
        "deepseek-chat": 64000,
        "qwen-turbo": 8000,
        "bloomvn": 4000,
        "default": 8000
    }
    
    # Target context usage (leave room for response)
    TARGET_USAGE = 0.7
    
    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Vietnamese and mixed text: ~1.5 chars per token average
        return int(len(text) / 1.5)
    
    @classmethod
    def get_smart_history(
        cls,
        conversation_history: List[Dict],
        model_id: str = "default",
        system_prompt: str = "",
        current_message: str = "",
        max_messages: Optional[int] = None
    ) -> List[Dict]:
        """
        Get conversation history with smart truncation based on:
        1. Model context limit
        2. Message recency (recent messages prioritized)
        3. Message importance (longer messages may be summarized)
        """
        if not conversation_history:
            return []
        
        context_limit = cls.MODEL_CONTEXT_LIMITS.get(model_id, cls.MODEL_CONTEXT_LIMITS["default"])
        available_tokens = int(context_limit * cls.TARGET_USAGE)
        
        # Reserve tokens for system prompt and current message
        reserved_tokens = cls.estimate_tokens(system_prompt) + cls.estimate_tokens(current_message) + 500
        available_tokens -= reserved_tokens
        
        if available_tokens <= 0:
            return []
        
        # Apply max_messages limit if specified
        if max_messages:
            conversation_history = conversation_history[-max_messages:]
        
        # Build history from most recent
        result = []
        used_tokens = 0
        
        for msg in reversed(conversation_history):
            user_content = msg.get('user', msg.get('content', ''))
            assistant_content = msg.get('assistant', '')
            
            msg_tokens = cls.estimate_tokens(user_content) + cls.estimate_tokens(assistant_content)
            
            if used_tokens + msg_tokens > available_tokens:
                break
            
            result.insert(0, msg)
            used_tokens += msg_tokens
        
        return result


class BaseModelChat(ABC):
    """Abstract base class for model-specific chat implementations"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.retry_config = RetryConfig()
    
    @abstractmethod
    def _call_api(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        """Make the actual API call"""
        pass
    
    @abstractmethod
    def _call_api_stream(self, messages: List[Dict], temperature: float, max_tokens: int) -> Generator[str, None, None]:
        """Make streaming API call"""
        pass
    
    def build_system_prompt(self, ctx: ChatContext, prompts_getter: Callable) -> str:
        """Build system prompt with context and memories"""
        if ctx.custom_prompt and ctx.custom_prompt.strip():
            system_prompt = ctx.custom_prompt
        else:
            prompts = prompts_getter(ctx.language)
            system_prompt = prompts.get(ctx.context, prompts.get('casual', ''))
        
        if ctx.deep_thinking:
            system_prompt += "\n\nIMPORTANT: Think step-by-step with detailed reasoning."
        
        if ctx.memories:
            system_prompt += "\n\n=== KNOWLEDGE BASE ===\n"
            for mem in ctx.memories:
                system_prompt += f"\n📚 {mem.get('title', 'Memory')}:\n{mem.get('content', '')}\n"
            system_prompt += "\n=== END KNOWLEDGE BASE ===\n"
        
        return system_prompt
    
    def build_messages(self, ctx: ChatContext, system_prompt: str) -> List[Dict]:
        """Build message list for API call"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Get smart history
        history_to_use = ctx.history if ctx.history else ContextWindowManager.get_smart_history(
            ctx.conversation_history,
            model_id=self.config.model_id,
            system_prompt=system_prompt,
            current_message=ctx.message
        )
        
        for hist in history_to_use:
            if 'role' in hist and 'content' in hist:
                messages.append({"role": hist['role'], "content": hist['content']})
            elif 'user' in hist:
                messages.append({"role": "user", "content": hist['user']})
                if 'assistant' in hist:
                    messages.append({"role": "assistant", "content": hist['assistant']})
        
        messages.append({"role": "user", "content": ctx.message})
        return messages
    
    def chat(self, ctx: ChatContext, prompts_getter: Callable, stream: bool = False) -> ChatResponse:
        """Execute chat with retry logic"""
        system_prompt = self.build_system_prompt(ctx, prompts_getter)
        messages = self.build_messages(ctx, system_prompt)
        
        temperature = self.config.temperature_deep if ctx.deep_thinking else self.config.temperature
        max_tokens = self.config.max_tokens_deep if ctx.deep_thinking else self.config.max_tokens
        
        retry_count = 0
        last_error = None
        
        for attempt in range(self.retry_config.max_retries):
            try:
                if stream and self.config.supports_streaming:
                    # Return generator for streaming
                    return self._call_api_stream(messages, temperature, max_tokens)
                else:
                    content = self._call_api(messages, temperature, max_tokens)
                    return ChatResponse(
                        content=content,
                        model=self.config.name,
                        provider=self.config.provider.value,
                        retry_count=retry_count
                    )
            except self.retry_config.retryable_errors as e:
                last_error = e
                retry_count = attempt + 1
                if attempt < self.retry_config.max_retries - 1:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt),
                        self.retry_config.max_delay
                    )
                    logger.warning(f"[{self.config.name}] Retry {attempt + 1}: {e}. Waiting {delay:.1f}s...")
                    time.sleep(delay)
            except Exception as e:
                return ChatResponse(
                    content="",
                    model=self.config.name,
                    provider=self.config.provider.value,
                    success=False,
                    error=str(e),
                    retry_count=retry_count
                )
        
        return ChatResponse(
            content="",
            model=self.config.name,
            provider=self.config.provider.value,
            success=False,
            error=f"All {self.retry_config.max_retries} retries failed: {last_error}",
            retry_count=retry_count
        )


class OpenAICompatibleChat(BaseModelChat):
    """Chat implementation for OpenAI-compatible APIs (OpenAI, DeepSeek, Grok)"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.base_url if config.base_url else None
        )
    
    def _call_api(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        response = self.client.chat.completions.create(
            model=self.config.model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    
    def _call_api_stream(self, messages: List[Dict], temperature: float, max_tokens: int) -> Generator[str, None, None]:
        stream = self.client.chat.completions.create(
            model=self.config.model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class QwenChat(BaseModelChat):
    """Chat implementation for Qwen API"""
    
    def _call_api(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.config.model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=self.config.timeout
        )
        
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        raise Exception(f"Qwen API error: {response.status_code}")
    
    def _call_api_stream(self, messages: List[Dict], temperature: float, max_tokens: int) -> Generator[str, None, None]:
        response = requests.post(
            "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.config.model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            },
            timeout=self.config.timeout,
            stream=True
        )
        
        if response.status_code == 200:
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data != '[DONE]':
                            try:
                                import json
                                chunk = json.loads(data)
                                content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                if content:
                                    yield content
                            except Exception:
                                # Skip invalid JSON chunks during streaming
                                pass


class BloomVNChat(BaseModelChat):
    """Chat implementation for BloomVN via HuggingFace"""
    
    def _build_conversation(self, messages: List[Dict]) -> str:
        """Build conversation string for BloomVN"""
        conversation = ""
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                conversation = f"{content}\n\n"
            elif role == 'user':
                conversation += f"User: {content}\n"
            elif role == 'assistant':
                conversation += f"Assistant: {content}\n\n"
        conversation += "Assistant:"
        return conversation
    
    def _call_api(self, messages: List[Dict], temperature: float, max_tokens: int) -> str:
        conversation = self._build_conversation(messages)
        
        response = requests.post(
            "https://api-inference.huggingface.co/models/BlossomsAI/BloomVN-8B-chat",
            headers={"Authorization": f"Bearer {self.config.api_key}"},
            json={
                "inputs": conversation,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "do_sample": True
                }
            },
            timeout=self.config.timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', '')
            return str(result)
        elif response.status_code == 503:
            raise Exception("BloomVN is loading, try again in 20-30 seconds")
        raise Exception(f"BloomVN API error: {response.status_code}")
    
    def _call_api_stream(self, messages: List[Dict], temperature: float, max_tokens: int) -> Generator[str, None, None]:
        # BloomVN doesn't support streaming, yield full response
        content = self._call_api(messages, temperature, max_tokens)
        yield content


class ModelFallbackManager:
    """Manages model fallback chain"""
    
    def __init__(self, fallback_chain: Dict[str, List[str]]):
        """
        fallback_chain: Dict mapping model name to list of fallback models
        Example: {'grok': ['deepseek', 'openai'], 'openai': ['deepseek']}
        """
        self.fallback_chain = fallback_chain
    
    def get_fallbacks(self, model: str) -> List[str]:
        """Get fallback models for a given model"""
        return self.fallback_chain.get(model, [])
    
    def execute_with_fallback(
        self,
        primary_model: str,
        chat_func: Callable[[str], ChatResponse],
    ) -> ChatResponse:
        """Execute chat with fallback to other models"""
        # Try primary model
        response = chat_func(primary_model)
        if response.success:
            return response
        
        logger.warning(f"[Fallback] Primary model {primary_model} failed: {response.error}")
        
        # Try fallback models
        for fallback_model in self.get_fallbacks(primary_model):
            logger.info(f"[Fallback] Trying fallback model: {fallback_model}")
            response = chat_func(fallback_model)
            if response.success:
                response.is_fallback = True
                logger.info(f"[Fallback] Success with {fallback_model}")
                return response
            logger.warning(f"[Fallback] {fallback_model} also failed: {response.error}")
        
        return response


# Default fallback chain
DEFAULT_FALLBACK_CHAIN = {
    'grok': ['deepseek', 'openai'],
    'openai': ['deepseek', 'grok'],
    'deepseek': ['openai', 'grok'],
    'qwen': ['deepseek', 'openai'],
    'bloomvn': ['qwen', 'deepseek'],
}
