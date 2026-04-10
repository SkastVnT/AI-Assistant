"""Shared SSE stream contract helpers for Flask and FastAPI routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any


STREAM_CONTRACT_VERSION = "v2"


def with_request_id(payload: dict[str, Any], request_id: str | None) -> dict[str, Any]:
    """Attach request_id to payload if not already present."""
    if not request_id:
        return payload
    if "request_id" in payload:
        return payload
    merged = dict(payload)
    merged["request_id"] = request_id
    return merged


def build_complete_event_payload(
    *,
    full_response: str,
    model: str,
    context: str,
    deep_thinking: bool,
    thinking_mode: str,
    chunk_count: int,
    thinking_summary: str,
    thinking_steps_text: list,
    thinking_duration: int,
    elapsed_time: float,
    tokens: int,
    max_tokens: int,
    request_id: str | None = None,
    time_to_first_chunk: float | None = None,
) -> dict[str, Any]:
    """Build the stable SSE `complete` payload consumed by frontend clients."""
    payload: dict[str, Any] = {
        "response": full_response,
        "model": model,
        "context": context,
        "deep_thinking": deep_thinking,
        "thinking_mode": thinking_mode,
        "total_chunks": chunk_count,
        "thinking_summary": thinking_summary,
        "thinking_steps": thinking_steps_text,
        "thinking_duration_ms": thinking_duration,
        "timestamp": datetime.now().isoformat(),
        "elapsed_time": round(elapsed_time, 3),
        "tokens": tokens,
        "max_tokens": max_tokens,
    }
    if time_to_first_chunk is not None:
        payload["time_to_first_chunk"] = round(time_to_first_chunk, 3)
    return with_request_id(payload, request_id)
