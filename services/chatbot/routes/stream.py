"""
Streaming routes: /chat/stream - SSE endpoint for real-time chat responses
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
import sys
from flask import Blueprint, request, session, Response
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import MEMORY_DIR
from core.extensions import MONGODB_ENABLED, logger
from core.chatbot_v2 import get_chatbot
from core.streaming import StreamingChatHandler, StreamEvent

# Check MCP availability
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import inject_code_context, get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    pass

stream_bp = Blueprint('stream', __name__)


@stream_bp.route('/chat/stream', methods=['POST', 'GET'])
def chat_stream():
    """
    Streaming chat endpoint using Server-Sent Events (SSE)
    
    Supports both POST (preferred) and GET (for simple testing)
    
    Request Body (POST) or Query Params (GET):
        - message: User message (required)
        - model: AI model to use (default: 'grok')
        - context: Conversation context (default: 'casual')
        - deep_thinking: Enable detailed reasoning (default: false)
        - language: Response language (default: 'vi')
        - custom_prompt: Custom system prompt (optional)
        - memory_ids: List of memory IDs to include (optional)
    
    Returns:
        SSE stream with events:
        - metadata: Initial metadata about the request
        - chunk: Response chunks as they arrive
        - complete: Final event with full response
        - error: Error event if something fails
    """
    try:
        # Parse request
        if request.method == 'POST':
            if request.content_type and 'application/json' in request.content_type:
                data = request.json or {}
            else:
                data = request.form.to_dict()
                # Parse JSON fields
                for key in ['memory_ids', 'history', 'mcp_selected_files']:
                    if key in data:
                        try:
                            data[key] = json.loads(data[key])
                        except:
                            data[key] = []
        else:
            # GET request
            data = request.args.to_dict()
        
        message = data.get('message', '')
        model = data.get('model', 'grok')
        context = data.get('context', 'casual')
        deep_thinking = str(data.get('deep_thinking', 'false')).lower() == 'true'
        language = data.get('language', 'vi')
        custom_prompt = data.get('custom_prompt', '')
        memory_ids = data.get('memory_ids', [])
        mcp_selected_files = data.get('mcp_selected_files', [])
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
                    message = inject_code_context(message, mcp_client, mcp_selected_files)
            except Exception as e:
                logger.warning(f"[MCP] Error injecting context: {e}")
        
        session_id = session.get('session_id')
        chatbot = get_chatbot(session_id)
        
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
        
        # Create streaming generator
        def generate_stream():
            try:
                # Send metadata
                yield StreamEvent(
                    event="metadata",
                    data=json.dumps({
                        "model": model,
                        "context": context,
                        "deep_thinking": deep_thinking,
                        "streaming": True,
                        "timestamp": datetime.now().isoformat()
                    })
                ).format()
                
                full_response = ""
                chunk_count = 0
                
                # Get streaming response from chatbot
                for chunk in chatbot.chat_stream(
                    message=message,
                    model=model,
                    context=context,
                    deep_thinking=deep_thinking,
                    history=history,
                    memories=memories if memories else None,
                    language=language,
                    custom_prompt=custom_prompt
                ):
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
                
            except GeneratorExit:
                logger.info("[SSE] Client disconnected")
            except Exception as e:
                logger.error(f"[SSE] Streaming error: {e}")
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
        logger.error(f"[Stream] Error: {e}")
        return Response(
            StreamEvent(event="error", data=json.dumps({"error": str(e)})).format(),
            mimetype='text/event-stream',
            status=500
        )


@stream_bp.route('/chat/stream/models', methods=['GET'])
def list_streaming_models():
    """List models that support streaming"""
    from core.chatbot_v2 import get_model_registry
    
    registry = get_model_registry()
    models = []
    
    for name in registry.list_available():
        config = registry.get_config(name)
        if config:
            models.append({
                'name': name,
                'supports_streaming': config.supports_streaming,
                'provider': config.provider.value
            })
    
    return {
        'models': models,
        'streaming_supported': [m['name'] for m in models if m['supports_streaming']]
    }
