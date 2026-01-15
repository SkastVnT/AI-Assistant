"""
Async Streaming routes: /chat/async - Async SSE endpoint for high-performance chat
Requires Flask with async support or use with Quart/FastAPI
"""
import json
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
import sys
from flask import Blueprint, request, session, Response
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import MEMORY_DIR, OPENAI_API_KEY, DEEPSEEK_API_KEY, GROK_API_KEY, QWEN_API_KEY, HUGGINGFACE_API_KEY, get_system_prompts
from core.extensions import logger
from core.streaming import StreamEvent
from core.base_chat import ModelConfig, ModelProvider, ChatContext
from core.async_chat import AsyncChatbotAgent

# Check MCP availability
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import inject_code_context, get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    pass

async_bp = Blueprint('async', __name__)

# Initialize async agent with available models
_async_agent = None

def get_async_agent() -> AsyncChatbotAgent:
    """Get or create async chatbot agent"""
    global _async_agent
    if _async_agent is None:
        config_map = {}
        
        if OPENAI_API_KEY:
            config_map['openai'] = ModelConfig(
                name='openai',
                provider=ModelProvider.OPENAI,
                api_key=OPENAI_API_KEY,
                model_id='gpt-4o-mini',
                supports_streaming=True
            )
        
        if DEEPSEEK_API_KEY:
            config_map['deepseek'] = ModelConfig(
                name='deepseek',
                provider=ModelProvider.DEEPSEEK,
                api_key=DEEPSEEK_API_KEY,
                base_url='https://api.deepseek.com/v1',
                model_id='deepseek-chat',
                supports_streaming=True
            )
        
        if GROK_API_KEY:
            config_map['grok'] = ModelConfig(
                name='grok',
                provider=ModelProvider.GROK,
                api_key=GROK_API_KEY,
                base_url='https://api.x.ai/v1',
                model_id='grok-3',
                supports_streaming=True
            )
        
        if QWEN_API_KEY:
            config_map['qwen'] = ModelConfig(
                name='qwen',
                provider=ModelProvider.QWEN,
                api_key=QWEN_API_KEY,
                model_id='qwen-turbo',
                supports_streaming=True
            )
        
        if HUGGINGFACE_API_KEY:
            config_map['bloomvn'] = ModelConfig(
                name='bloomvn',
                provider=ModelProvider.BLOOMVN,
                api_key=HUGGINGFACE_API_KEY,
                model_id='BlossomsAI/BloomVN-8B-chat',
                timeout=60,
                supports_streaming=False
            )
        
        _async_agent = AsyncChatbotAgent(config_map)
    
    return _async_agent


def run_async(coro):
    """Run async coroutine in sync context"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # If loop is already running (e.g., in Jupyter), create new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return loop.run_until_complete(coro)


@async_bp.route('/chat/async', methods=['POST'])
def chat_async():
    """
    Async chat endpoint - non-streaming but concurrent
    
    Request Body:
        - message: User message (required)
        - model: AI model to use (default: 'grok')
        - context: Conversation context (default: 'casual')
        - deep_thinking: Enable detailed reasoning (default: false)
        - language: Response language (default: 'vi')
        - custom_prompt: Custom system prompt (optional)
        - memory_ids: List of memory IDs to include (optional)
    
    Returns:
        JSON response with chat result
    """
    try:
        data = request.json or {}
        
        message = data.get('message', '')
        model = data.get('model', 'grok')
        context = data.get('context', 'casual')
        deep_thinking = data.get('deep_thinking', False)
        language = data.get('language', 'vi')
        custom_prompt = data.get('custom_prompt', '')
        memory_ids = data.get('memory_ids', [])
        history = data.get('history')
        
        if not message:
            return {'error': 'Empty message'}, 400
        
        # Ensure session
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        # MCP Integration
        if MCP_AVAILABLE:
            try:
                mcp_client = get_mcp_client()
                if mcp_client and mcp_client.enabled:
                    mcp_selected_files = data.get('mcp_selected_files', [])
                    message = inject_code_context(message, mcp_client, mcp_selected_files)
            except Exception as e:
                logger.warning(f"[MCP] Error injecting context: {e}")
        
        # Load memories
        memories = []
        if memory_ids:
            for mem_id in memory_ids:
                memory_file = MEMORY_DIR / f"{mem_id}.json"
                if memory_file.exists():
                    try:
                        with open(memory_file, 'r', encoding='utf-8') as f:
                            memories.append(json.load(f))
                    except Exception as e:
                        logger.error(f"Error loading memory {mem_id}: {e}")
        
        # Build context
        ctx = ChatContext(
            message=message,
            context=context,
            deep_thinking=deep_thinking,
            language=language,
            custom_prompt=custom_prompt,
            history=history,
            memories=memories if memories else None,
            conversation_history=[]
        )
        
        # Get async agent and execute
        agent = get_async_agent()
        
        async def do_chat():
            return await agent.chat(model, ctx, get_system_prompts)
        
        response = run_async(do_chat())
        
        return {
            'response': response.content,
            'model': response.model,
            'success': response.success,
            'error': response.error,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[Async] Error: {e}")
        return {'error': str(e)}, 500


@async_bp.route('/chat/async/stream', methods=['POST'])
def chat_async_stream():
    """
    Async streaming chat endpoint using SSE
    
    Uses async generators for better I/O performance
    """
    try:
        data = request.json or {}
        
        message = data.get('message', '')
        model = data.get('model', 'grok')
        context = data.get('context', 'casual')
        deep_thinking = data.get('deep_thinking', False)
        language = data.get('language', 'vi')
        custom_prompt = data.get('custom_prompt', '')
        memory_ids = data.get('memory_ids', [])
        history = data.get('history')
        
        if not message:
            return Response(
                StreamEvent(event="error", data=json.dumps({"error": "Empty message"})).format(),
                mimetype='text/event-stream',
                status=400
            )
        
        # Ensure session
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        
        # MCP Integration
        if MCP_AVAILABLE:
            try:
                mcp_client = get_mcp_client()
                if mcp_client and mcp_client.enabled:
                    mcp_selected_files = data.get('mcp_selected_files', [])
                    message = inject_code_context(message, mcp_client, mcp_selected_files)
            except Exception as e:
                logger.warning(f"[MCP] Error injecting context: {e}")
        
        # Load memories
        memories = []
        if memory_ids:
            for mem_id in memory_ids:
                memory_file = MEMORY_DIR / f"{mem_id}.json"
                if memory_file.exists():
                    try:
                        with open(memory_file, 'r', encoding='utf-8') as f:
                            memories.append(json.load(f))
                    except Exception as e:
                        logger.error(f"Error loading memory {mem_id}: {e}")
        
        # Build context
        ctx = ChatContext(
            message=message,
            context=context,
            deep_thinking=deep_thinking,
            language=language,
            custom_prompt=custom_prompt,
            history=history,
            memories=memories if memories else None,
            conversation_history=[]
        )
        
        agent = get_async_agent()
        
        def generate_stream():
            try:
                # Send metadata
                yield StreamEvent(
                    event="metadata",
                    data=json.dumps({
                        "model": model,
                        "context": context,
                        "deep_thinking": deep_thinking,
                        "async": True,
                        "timestamp": datetime.now().isoformat()
                    })
                ).format()
                
                full_response = ""
                chunk_count = 0
                
                # Run async generator in sync context
                async def get_chunks():
                    chunks = []
                    async for chunk in agent.chat_stream(model, ctx, get_system_prompts):
                        chunks.append(chunk)
                    return chunks
                
                chunks = run_async(get_chunks())
                
                for chunk in chunks:
                    if chunk:
                        full_response += chunk
                        chunk_count += 1
                        yield StreamEvent(
                            event="chunk",
                            data=json.dumps({
                                "content": chunk,
                                "chunk_index": chunk_count
                            })
                        ).format()
                
                # Send complete event
                yield StreamEvent(
                    event="complete",
                    data=json.dumps({
                        "response": full_response,
                        "model": model,
                        "context": context,
                        "deep_thinking": deep_thinking,
                        "total_chunks": chunk_count,
                        "timestamp": datetime.now().isoformat()
                    })
                ).format()
                
            except Exception as e:
                logger.error(f"[Async SSE] Error: {e}")
                yield StreamEvent(
                    event="error",
                    data=json.dumps({"error": str(e)})
                ).format()
        
        return Response(
            generate_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*',
            }
        )
        
    except Exception as e:
        logger.error(f"[Async Stream] Error: {e}")
        return Response(
            StreamEvent(event="error", data=json.dumps({"error": str(e)})).format(),
            mimetype='text/event-stream',
            status=500
        )


@async_bp.route('/chat/async/batch', methods=['POST'])
def chat_batch():
    """
    Batch chat endpoint - process multiple messages concurrently
    
    Request Body:
        - requests: List of chat requests, each with:
            - message: User message (required)
            - model: AI model to use (default: 'grok')
            - context: Conversation context (default: 'casual')
    
    Returns:
        JSON response with list of chat results
    """
    try:
        data = request.json or {}
        requests_list = data.get('requests', [])
        
        if not requests_list:
            return {'error': 'No requests provided'}, 400
        
        agent = get_async_agent()
        
        async def process_batch():
            tasks = []
            for req in requests_list:
                ctx = ChatContext(
                    message=req.get('message', ''),
                    context=req.get('context', 'casual'),
                    deep_thinking=req.get('deep_thinking', False),
                    language=req.get('language', 'vi'),
                    custom_prompt=req.get('custom_prompt', ''),
                    conversation_history=[]
                )
                tasks.append({
                    'model': req.get('model', 'grok'),
                    'ctx': ctx
                })
            
            from core.async_chat import run_multiple_chats
            return await run_multiple_chats(tasks, agent, get_system_prompts)
        
        responses = run_async(process_batch())
        
        results = []
        for i, resp in enumerate(responses):
            results.append({
                'index': i,
                'response': resp.content,
                'model': resp.model,
                'success': resp.success,
                'error': resp.error
            })
        
        return {
            'results': results,
            'total': len(results),
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"[Batch] Error: {e}")
        return {'error': str(e)}, 500
