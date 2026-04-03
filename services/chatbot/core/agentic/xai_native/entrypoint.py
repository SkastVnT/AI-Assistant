"""
xAI Native Multi-Agent — Router entry point
=============================================
Thin bridge between FastAPI routers and the ``XaiResponsesAdapter``.

Feature flag
~~~~~~~~~~~~
Set ``XAI_NATIVE_MULTI_AGENT_ENABLED=true`` to activate.
When disabled, returns a graceful error — existing behaviour is intact.

Usage from routers::

    from core.agentic.xai_native.entrypoint import run_xai_native
    result = await run_xai_native(message=..., ...)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, AsyncGenerator

from core.agentic.xai_native.adapter import XaiResponsesAdapter
from core.agentic.xai_native.contracts import (
    ReasoningEffort,
    XaiNativeConfig,
    XaiNativeResult,
    XaiNativeStatus,
)

logger = logging.getLogger(__name__)


# ── Feature flag ───────────────────────────────────────────────────────

XAI_NATIVE_MULTI_AGENT_ENABLED: bool = os.environ.get(
    "XAI_NATIVE_MULTI_AGENT_ENABLED", "false"
).lower() in ("1", "true", "yes")


def is_xai_native_enabled() -> bool:
    """Check if xAI native multi-agent mode is turned on."""
    return XAI_NATIVE_MULTI_AGENT_ENABLED


# ── Adapter factory ───────────────────────────────────────────────────

def _get_adapter() -> XaiResponsesAdapter | None:
    """Create an adapter using the GROK_API_KEY env var."""
    from core.config import GROK_API_KEY

    if not GROK_API_KEY:
        logger.error(
            "xAI native multi-agent is enabled, but GROK_API_KEY is missing or empty."
        )
        return None

    try:
        return XaiResponsesAdapter(api_key=GROK_API_KEY)
    except ValueError as exc:
        logger.error(
            "Failed to initialize XaiResponsesAdapter due to invalid GROK_API_KEY configuration: %s",
            exc,
        )
        return None
def _build_system_prompt(
    *,
    context_type: str,
    language: str,
    custom_prompt: str,
    mcp_context: str,
    rag_context: str,
) -> str:
    """Assemble a system prompt from the various context sources."""
    parts: list[str] = []

    if custom_prompt:
        parts.append(custom_prompt)
    else:
        parts.append(
            f"You are a helpful research assistant. "
            f"Respond in {language}. "
            f"Context type: {context_type}."
        )

    if rag_context:
        parts.append(f"\n--- RAG Context ---\n{rag_context}\n--- End RAG ---")

    if mcp_context:
        parts.append(f"\n--- Code Context ---\n{mcp_context}\n--- End Code ---")

    return "\n\n".join(parts)


def _build_config(
    *,
    reasoning_effort: str = "high",
    enable_web_search: bool = True,
    enable_x_search: bool = False,
) -> XaiNativeConfig:
    """Build config with safe defaults."""
    try:
        effort = ReasoningEffort(reasoning_effort)
    except ValueError:
        effort = ReasoningEffort.high

    return XaiNativeConfig(
        reasoning_effort=effort,
        enable_web_search=enable_web_search,
        enable_x_search=enable_x_search,
    )


# ── Non-streaming entry point ─────────────────────────────────────────


async def run_xai_native(
    *,
    original_message: str,
    augmented_message: str,
    language: str = "vi",
    context_type: str = "casual",
    custom_prompt: str = "",
    rag_context: str = "",
    rag_citations: list[dict[str, Any]] | None = None,
    mcp_context: str = "",
    reasoning_effort: str = "high",
    enable_web_search: bool = True,
    enable_x_search: bool = False,
) -> dict[str, Any]:
    """Run xAI native multi-agent research and return ChatResponse-compatible dict.

    Returns dict with keys: response, model, context, agent_run_id,
    agent_trace_summary, citations, deep_thinking, thinking_process.
    """
    if not is_xai_native_enabled():
        logger.debug("[XaiNative] Feature flag off — returning disabled response")
        return _disabled_response(context_type, rag_citations)

    config = _build_config(
        reasoning_effort=reasoning_effort,
        enable_web_search=enable_web_search,
        enable_x_search=enable_x_search,
    )
    system_prompt = _build_system_prompt(
        context_type=context_type,
        language=language,
        custom_prompt=custom_prompt,
        mcp_context=mcp_context,
        rag_context=rag_context,
    )

    logger.info(
        "[XaiNative] Starting — model=%s effort=%s web_search=%s",
        config.model, config.reasoning_effort.value, config.enable_web_search,
    )

    adapter = _get_adapter()
    if adapter is None:
        return _disabled_response(context_type, rag_citations)

    result: XaiNativeResult = await adapter.call(
        message=augmented_message,
        config=config,
        system_prompt=system_prompt,
    )

    logger.info(
        "[XaiNative] Completed — id=%s status=%s tokens=%d elapsed=%.1fs",
        result.response_id, result.status.value,
        result.usage.total_tokens, result.elapsed_seconds,
    )

    return _build_response_dict(result, config, context_type, rag_citations)


# ── Streaming entry point ─────────────────────────────────────────────

def _sse(event: str, data: dict | str) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


async def run_xai_native_stream(
    *,
    original_message: str,
    augmented_message: str,
    language: str = "vi",
    context_type: str = "casual",
    custom_prompt: str = "",
    rag_context: str = "",
    rag_citations: list[dict[str, Any]] | None = None,
    mcp_context: str = "",
    reasoning_effort: str = "high",
    enable_web_search: bool = True,
    enable_x_search: bool = False,
) -> AsyncGenerator[str, None]:
    """Stream xAI native research via SSE events.

    Events:
      - ``xai_native_event`` — progress (thinking tokens, status)
      - ``xai_native_chunk`` — content delta
      - ``xai_native_result`` — final ChatResponse-compatible dict
      - ``xai_native_error``  — on failure
    """
    if not is_xai_native_enabled():
        yield _sse("xai_native_result", _disabled_response(context_type, rag_citations))
        return

    config = _build_config(
        reasoning_effort=reasoning_effort,
        enable_web_search=enable_web_search,
        enable_x_search=enable_x_search,
    )
    system_prompt = _build_system_prompt(
        context_type=context_type,
        language=language,
        custom_prompt=custom_prompt,
        mcp_context=mcp_context,
        rag_context=rag_context,
    )

    # Emit start event
    yield _sse("xai_native_event", {
        "stage": "starting",
        "model": config.model,
        "reasoning_effort": config.reasoning_effort.value,
    })

    adapter = _get_adapter()
    if adapter is None:
        yield _sse("xai_native_error", {
            "error": "xAI adapter could not be initialized. Check GROK_API_KEY.",
        })
        return

    async for chunk in adapter.stream(
        message=augmented_message,
        config=config,
        system_prompt=system_prompt,
    ):
        chunk_type = chunk.get("type")

        if chunk_type == "thinking":
            yield _sse("xai_native_event", {
                "stage": "thinking",
                "reasoning_tokens": chunk["reasoning_tokens"],
            })

        elif chunk_type == "content":
            yield _sse("xai_native_chunk", {
                "text": chunk["text"],
            })

        elif chunk_type == "done":
            result: XaiNativeResult = chunk["result"]
            response_dict = _build_response_dict(
                result, config, context_type, rag_citations,
            )
            yield _sse("xai_native_result", response_dict)

        elif chunk_type == "error":
            yield _sse("xai_native_error", {
                "error": chunk["error"],
            })


# ── Response builders ──────────────────────────────────────────────────


def _disabled_response(
    context_type: str,
    rag_citations: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    return {
        "response": (
            "xAI native multi-agent mode is not enabled on this server. "
            "Set XAI_NATIVE_MULTI_AGENT_ENABLED=true to activate."
        ),
        "model": "grok-native",
        "context": context_type,
        "deep_thinking": False,
        "thinking_process": None,
        "citations": rag_citations,
        "agent_run_id": None,
        "agent_trace_summary": None,
    }


def _build_response_dict(
    result: XaiNativeResult,
    config: XaiNativeConfig,
    context_type: str,
    rag_citations: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Convert XaiNativeResult → ChatResponse-compatible dict."""
    # Build safe trace summary
    trace = result.to_trace_summary()
    trace["reasoning_effort"] = config.reasoning_effort.value

    # Merge citations: RAG + xAI annotations
    merged_citations = list(rag_citations) if rag_citations else []
    for ann in result.annotations:
        if ann.url:
            merged_citations.append({
                "url": ann.url,
                "title": ann.title or "",
                "source": "xai_web_search",
            })

    thinking_lines = [
        f"xAI multi-agent research completed in {result.elapsed_seconds:.1f}s.",
        f"Model: {result.model}, effort: {config.reasoning_effort.value}.",
        f"Tokens: {result.usage.total_tokens} total "
        f"({result.usage.reasoning_tokens} reasoning).",
    ]
    if result.usage.num_sources_used:
        thinking_lines.append(f"Web sources used: {result.usage.num_sources_used}.")
    if result.error:
        thinking_lines.append(f"Error: {result.error}")

    return {
        "response": result.content or result.error or "No response generated.",
        "model": "grok-native",
        "context": context_type,
        "deep_thinking": True,
        "thinking_process": "\n".join(thinking_lines),
        "citations": merged_citations or None,
        "agent_run_id": result.response_id or None,
        "agent_trace_summary": trace,
    }
