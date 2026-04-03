"""
SSE Streaming route for the council pipeline — POST /chat/council/stream

Yields ``council_event`` SSE messages as the orchestrator progresses through
Planner → Researcher → Synthesizer → Critic, then a final ``council_result``
event with the complete ChatResponse-compatible payload.

The non-streaming ``/chat`` endpoint is unaffected.
"""
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from fastapi_app.dependencies import get_session_id
from fastapi_app.models import ChatRequest
from fastapi_app.rag_helpers import retrieve_rag_context
from core.agentic.entrypoint import run_council_stream, is_council_enabled
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


@router.post("/chat/council/stream")
async def council_stream(body: ChatRequest, request: Request):
    """Stream council progress events via SSE.

    Returns ``text/event-stream`` with events:

    - ``council_event``  — one per stage transition (safe operational status)
    - ``council_result`` — final ChatResponse-compatible JSON payload
    - ``council_error``  — if the pipeline fails
    """
    return StreamingResponse(
        _generate_council_events(body, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _generate_council_events(
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
            logger.warning("[MCP] Error in council stream: %s", e)

    # RAG retrieval
    rag = await retrieve_rag_context(
        message=message,
        custom_prompt=custom_prompt,
        language=body.language,
        tenant_id=get_session_id(request),
        rag_collection_ids=body.rag_collection_ids or [],
        rag_top_k=body.rag_top_k,
    )

    # Yield SSE events from the council pipeline
    async for sse_chunk in run_council_stream(
        original_message=original_message,
        augmented_message=rag.message,
        language=body.language,
        context_type=body.context,
        custom_prompt=rag.custom_prompt,
        rag_chunks=None,
        rag_citations=rag.citations,
        mcp_context=mcp_context,
        max_agent_iterations=body.max_agent_iterations,
        preferred_planner_model=body.preferred_planner_model,
        preferred_researcher_model=body.preferred_researcher_model,
        preferred_critic_model=body.preferred_critic_model,
        preferred_synthesizer_model=body.preferred_synthesizer_model,
    ):
        yield sse_chunk
