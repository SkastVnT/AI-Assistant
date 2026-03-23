"""
SSE Streaming router — /chat/stream
"""
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from fastapi_app.dependencies import get_chatbot_for_session, get_session_id
from fastapi_app.models import StreamRequest
from core.config import MEMORY_DIR
from core.extensions import logger

router = APIRouter()

# MCP
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import inject_code_context, get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    pass


def _sse(event: str, data: dict | str) -> str:
    """Format a single Server-Sent Event."""
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/chat/stream")
async def chat_stream(body: StreamRequest, request: Request):
    """Streaming chat via Server-Sent Events."""
    message = body.message
    model = body.model
    context = body.context
    deep_thinking = body.deep_thinking
    language = body.language
    custom_prompt = body.custom_prompt
    memory_ids = body.memory_ids
    mcp_selected_files = body.mcp_selected_files
    history = body.history

    if not message:
        return StreamingResponse(
            iter([_sse("error", {"error": "Empty message"})]),
            media_type="text/event-stream",
            status_code=400,
        )

    # MCP integration
    if MCP_AVAILABLE:
        try:
            mcp_client = get_mcp_client()
            if mcp_client and mcp_client.enabled:
                message = inject_code_context(message, mcp_client, mcp_selected_files)
        except Exception as e:
            logger.warning(f"[MCP] Stream context error: {e}")

    chatbot = get_chatbot_for_session(request)

    # Load memories
    memories = []
    for mid in memory_ids:
        path = MEMORY_DIR / f"{mid}.json"
        if path.exists():
            try:
                memories.append(json.loads(path.read_text("utf-8")))
            except Exception:
                pass

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            yield _sse("metadata", {
                "model": model,
                "context": context,
                "deep_thinking": deep_thinking,
                "streaming": True,
                "timestamp": datetime.now().isoformat(),
            })

            full_response = ""
            chunk_count = 0

            for chunk in chatbot.chat_stream(
                message=message,
                model=model,
                context=context,
                deep_thinking=deep_thinking,
                history=history,
                memories=memories or None,
                language=language,
                custom_prompt=custom_prompt,
            ):
                if chunk:
                    full_response += chunk
                    chunk_count += 1
                    yield _sse("chunk", {"content": chunk, "chunk_index": chunk_count})

            yield _sse("complete", {
                "response": full_response,
                "model": model,
                "context": context,
                "deep_thinking": deep_thinking,
                "total_chunks": chunk_count,
                "timestamp": datetime.now().isoformat(),
            })

        except GeneratorExit:
            logger.info("[SSE] Client disconnected")
        except Exception as e:
            logger.error(f"[SSE] Streaming error: {e}")
            yield _sse("error", {"error": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/stream/models")
async def list_streaming_models():
    """List models that support streaming."""
    from core.chatbot_v2 import get_model_registry

    registry = get_model_registry()
    models = []
    for name in registry.list_available():
        config = registry.get_config(name)
        if config:
            models.append({
                "name": name,
                "supports_streaming": config.supports_streaming,
                "provider": config.provider.value,
            })
    return {
        "models": models,
        "streaming_supported": [m["name"] for m in models if m["supports_streaming"]],
    }
