"""
SSE Streaming route for xAI native multi-agent — POST /chat/xai-native/stream

Yields ``xai_native_event``, ``xai_native_chunk``, and ``xai_native_result``
SSE messages as the xAI server-side agents process the request.

Mirrors the pattern in ``council_stream.py`` — keeps RAG/MCP pre-processing
identical.
"""
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from fastapi_app.dependencies import get_session_id
from fastapi_app.models import ChatRequest
from fastapi_app.rag_helpers import retrieve_rag_context
from core.agentic.xai_native.entrypoint import run_xai_native_stream
from core.extensions import logger

# MCP availability (same pattern as chat.py)
MCP_AVAILABLE = False
try:
    from src.handlers.mcp_handler import inject_code_context, get_mcp_client
    MCP_AVAILABLE = True
except ImportError:
    pass

router = APIRouter()


def _sse(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


@router.post("/chat/xai-native/stream")
async def xai_native_stream(body: ChatRequest, request: Request):
    """Stream xAI native multi-agent research via SSE.

    Returns ``text/event-stream`` with events:

    - ``xai_native_event``  — progress / status (thinking tokens, stage)
    - ``xai_native_chunk``  — content delta text
    - ``xai_native_result`` — final ChatResponse-compatible JSON payload
    - ``xai_native_error``  — on failure
    """
    return StreamingResponse(
        _generate_xai_native_events(body, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _generate_xai_native_events(
    body: ChatRequest, request: Request
) -> AsyncGenerator[str, None]:
    """Pre-process the request (MCP, RAG) then delegate to the streaming entrypoint."""

    message = body.message

    # Agent config processing (mirrors _do_chat)
    custom_prompt = body.custom_prompt or ""
    if body.agent_config:
        ac = body.agent_config
        if not custom_prompt and ac.get("systemPrompt"):
            custom_prompt = ac["systemPrompt"]
        if ac.get("injectionPrompt"):
            message = f"{ac['injectionPrompt']}\n\n{message}"
        if ac.get("contextPrompt"):
            custom_prompt = f"{custom_prompt}\n\n--- Context ---\n{ac['contextPrompt']}"

    original_message = message
    mcp_context = ""

    # MCP injection
    if MCP_AVAILABLE:
        try:
            mcp_client = get_mcp_client()
            if mcp_client and mcp_client.enabled:
                augmented = inject_code_context(
                    message, mcp_client, body.mcp_selected_files or []
                )
                if augmented != message:
                    mcp_context = augmented[: augmented.find(message)] if message in augmented else ""
                message = augmented
        except Exception as e:
            logger.warning("[MCP] Error in xai_native stream: %s", e)

    # RAG retrieval
    rag = await retrieve_rag_context(
        message=message,
        custom_prompt=custom_prompt,
        language=body.language,
        tenant_id=get_session_id(request),
        rag_collection_ids=body.rag_collection_ids or [],
        rag_top_k=body.rag_top_k,
    )

    # Yield SSE events from the xAI native pipeline
    async for sse_chunk in run_xai_native_stream(
        original_message=original_message,
        augmented_message=rag.message,
        language=body.language,
        context_type=body.context,
        custom_prompt=rag.custom_prompt,
        rag_context="",
        rag_citations=rag.citations,
        mcp_context=mcp_context,
        reasoning_effort=body.reasoning_effort,
        enable_web_search=body.enable_web_search,
        enable_x_search=body.enable_x_search,
    ):
        yield sse_chunk
