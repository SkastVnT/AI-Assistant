"""
Async Chat Module - Asynchronous chat implementations for better I/O performance
"""
import asyncio
import logging
from typing import Optional, List, Dict, Any, AsyncGenerator
from dataclasses import dataclass
import aiohttp
import openai
from openai import AsyncOpenAI

from core.base_chat import (
    ModelConfig, ModelProvider, ChatContext, ChatResponse,
    ContextWindowManager, RetryConfig
)

logger = logging.getLogger(__name__)


class AsyncRetryHandler:
    """Async retry handler with exponential backoff"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    async def execute_with_retry(self, coro_func, *args, **kwargs):
        """Execute async function with retry logic"""
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await coro_func(*args, **kwargs)
            except self.config.retryable_errors as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    delay = min(
                        self.config.base_delay * (self.config.exponential_base ** attempt),
                        self.config.max_delay
                    )
                    logger.warning(f"[Retry] Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
            except Exception as e:
                raise
        
        raise last_error


class AsyncOpenAICompatibleChat:
    """Async chat implementation for OpenAI-compatible APIs"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url if config.base_url else None
        )
        self.retry_handler = AsyncRetryHandler()
    
    async def chat(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Execute async chat"""
        async def _call():
            response = await self.client.chat.completions.create(
                model=self.config.model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        
        return await self.retry_handler.execute_with_retry(_call)
    
    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Execute async streaming chat"""
        try:
            stream = await self.client.chat.completions.create(
                model=self.config.model_id,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"[{self.config.name}] Streaming error: {e}")
            raise


class AsyncQwenChat:
    """Async chat implementation for Qwen API"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.retry_handler = AsyncRetryHandler()
    
    async def chat(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Execute async chat"""
        async def _call():
            async with aiohttp.ClientSession() as session:
                async with session.post(
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
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['choices'][0]['message']['content']
                    raise Exception(f"Qwen API error: {response.status}")
        
        return await self.retry_handler.execute_with_retry(_call)
    
    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """Execute async streaming chat"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
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
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = line[6:]
                            if data != '[DONE]':
                                try:
                                    import json
                                    chunk = json.loads(data)
                                    content = chunk.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                    if content:
                                        yield content
                                except:
                                    pass


class AsyncBloomVNChat:
    """Async chat implementation for BloomVN via HuggingFace"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.retry_handler = AsyncRetryHandler()
    
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
    
    async def chat(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Execute async chat"""
        async def _call():
            conversation = self._build_conversation(messages)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
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
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if isinstance(result, list) and len(result) > 0:
                            return result[0].get('generated_text', '')
                        return str(result)
                    elif response.status == 503:
                        raise Exception("BloomVN is loading, try again in 20-30 seconds")
                    raise Exception(f"BloomVN API error: {response.status}")
        
        return await self.retry_handler.execute_with_retry(_call)
    
    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float,
        max_tokens: int
    ) -> AsyncGenerator[str, None]:
        """BloomVN doesn't support streaming, yield full response"""
        content = await self.chat(messages, temperature, max_tokens)
        yield content


class AsyncChatbotAgent:
    """Async multi-model chatbot agent"""
    
    def __init__(self, config_map: Dict[str, ModelConfig]):
        self.config_map = config_map
        self._handlers: Dict[str, Any] = {}
        self._initialize_handlers()
    
    def _initialize_handlers(self):
        """Initialize async handlers for each model"""
        for name, config in self.config_map.items():
            if config.provider in [ModelProvider.OPENAI, ModelProvider.DEEPSEEK, ModelProvider.GROK]:
                self._handlers[name] = AsyncOpenAICompatibleChat(config)
            elif config.provider == ModelProvider.QWEN:
                self._handlers[name] = AsyncQwenChat(config)
            elif config.provider == ModelProvider.BLOOMVN:
                self._handlers[name] = AsyncBloomVNChat(config)
    
    def _build_messages(
        self,
        ctx: ChatContext,
        system_prompt: str
    ) -> List[Dict]:
        """Build message list for API call"""
        messages = [{"role": "system", "content": system_prompt}]
        
        # Get smart history
        history_to_use = ctx.history if ctx.history else ContextWindowManager.get_smart_history(
            ctx.conversation_history,
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
    
    async def chat(
        self,
        model: str,
        ctx: ChatContext,
        prompts_getter
    ) -> ChatResponse:
        """Execute async chat"""
        handler = self._handlers.get(model)
        config = self.config_map.get(model)
        
        if not handler or not config:
            return ChatResponse(
                content=f"❌ Model '{model}' not available",
                model=model,
                provider="unknown",
                success=False,
                error=f"Model '{model}' not available"
            )
        
        try:
            # Build system prompt
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
            
            messages = self._build_messages(ctx, system_prompt)
            
            temperature = config.temperature_deep if ctx.deep_thinking else config.temperature
            max_tokens = config.max_tokens_deep if ctx.deep_thinking else config.max_tokens
            
            content = await handler.chat(messages, temperature, max_tokens)
            
            return ChatResponse(
                content=content,
                model=model,
                provider=config.provider.value,
                success=True
            )
            
        except Exception as e:
            return ChatResponse(
                content="",
                model=model,
                provider=config.provider.value if config else "unknown",
                success=False,
                error=str(e)
            )
    
    async def chat_stream(
        self,
        model: str,
        ctx: ChatContext,
        prompts_getter
    ) -> AsyncGenerator[str, None]:
        """Execute async streaming chat"""
        handler = self._handlers.get(model)
        config = self.config_map.get(model)
        
        if not handler or not config:
            yield f"❌ Model '{model}' not available"
            return
        
        try:
            # Build system prompt
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
            
            messages = self._build_messages(ctx, system_prompt)
            
            temperature = config.temperature_deep if ctx.deep_thinking else config.temperature
            max_tokens = config.max_tokens_deep if ctx.deep_thinking else config.max_tokens
            
            async for chunk in handler.chat_stream(messages, temperature, max_tokens):
                yield chunk
                
        except Exception as e:
            logger.error(f"[{model}] Async streaming error: {e}")
            yield f"❌ Error: {str(e)}"


async def run_multiple_chats(
    tasks: List[Dict[str, Any]],
    agent: AsyncChatbotAgent,
    prompts_getter
) -> List[ChatResponse]:
    """
    Run multiple chat requests concurrently
    
    Args:
        tasks: List of dicts with 'model' and 'ctx' keys
        agent: AsyncChatbotAgent instance
        prompts_getter: Function to get system prompts
    
    Returns:
        List of ChatResponse objects
    """
    coroutines = [
        agent.chat(task['model'], task['ctx'], prompts_getter)
        for task in tasks
    ]
    return await asyncio.gather(*coroutines)
