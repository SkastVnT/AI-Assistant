"""
xAI Native Multi-Agent — Responses API adapter
================================================
Async HTTP client that calls ``POST /v1/responses`` with the
``grok-4.20-multi-agent`` model.

This adapter does **not** use the OpenAI SDK — the Responses API has
a different request/response shape than Chat Completions.

Streaming
~~~~~~~~~
Streaming uses ``stream: true`` which returns SSE ``data:`` lines.
The adapter yields parsed chunks as dicts.

Security notes
~~~~~~~~~~~~~~
* API key is read from ``GROK_API_KEY`` env var (same as existing grok).
* Hidden chain-of-thought / encrypted sub-agent state is never exposed.
* Only the leader agent's final text and annotations are surfaced.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncGenerator

import httpx

from core.agentic.xai_native.contracts import (
    ReasoningEffort,
    XaiAnnotation,
    XaiNativeConfig,
    XaiNativeResult,
    XaiNativeStatus,
    XaiUsage,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.x.ai/v1"


class XaiResponsesAdapter:
    """Async adapter for xAI's Responses API."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("GROK_API_KEY is required for xAI native mode")
        self._api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    # ── Request builder ────────────────────────────────────────────

    def _build_payload(
        self,
        *,
        message: str,
        config: XaiNativeConfig,
        system_prompt: str = "",
        stream: bool = False,
    ) -> dict[str, Any]:
        tools: list[dict[str, Any]] = []
        if config.enable_web_search:
            tools.append({"type": "web_search"})
        if config.enable_x_search:
            tools.append({"type": "x_search"})

        payload: dict[str, Any] = {
            "model": config.model,
            "input": message,
            "stream": stream,
            "store": False,  # don't persist on xAI side
        }

        if system_prompt:
            payload["instructions"] = system_prompt

        if tools:
            payload["tools"] = tools

        payload["reasoning"] = {"effort": config.reasoning_effort.value}

        return payload

    # ── Non-streaming call ─────────────────────────────────────────

    async def call(
        self,
        *,
        message: str,
        config: XaiNativeConfig,
        system_prompt: str = "",
    ) -> XaiNativeResult:
        """Call xAI Responses API (non-streaming) and return normalized result."""
        payload = self._build_payload(
            message=message, config=config, system_prompt=system_prompt,
        )
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(config.timeout_seconds, connect=15.0),
            ) as client:
                resp = await client.post(
                    f"{_BASE_URL}/responses",
                    headers=self._headers,
                    json=payload,
                )
            elapsed = time.monotonic() - start

            if resp.status_code != 200:
                logger.error(
                    "[XaiAdapter] HTTP %d: %s", resp.status_code, resp.text[:500],
                )
                return XaiNativeResult(
                    status=XaiNativeStatus.failed,
                    error=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    elapsed_seconds=elapsed,
                )

            data = resp.json()
            return self._parse_response(data, elapsed)

        except httpx.TimeoutException:
            elapsed = time.monotonic() - start
            logger.error("[XaiAdapter] Request timed out after %.1fs", elapsed)
            return XaiNativeResult(
                status=XaiNativeStatus.failed,
                error=f"Request timed out after {elapsed:.0f}s",
                elapsed_seconds=elapsed,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            logger.exception("[XaiAdapter] Unexpected error")
            return XaiNativeResult(
                status=XaiNativeStatus.failed,
                error=str(exc),
                elapsed_seconds=elapsed,
            )

    # ── Streaming call ─────────────────────────────────────────────

    async def stream(
        self,
        *,
        message: str,
        config: XaiNativeConfig,
        system_prompt: str = "",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream xAI Responses API and yield parsed SSE chunks.

        Yields dicts with keys:
          - ``type``: "thinking" | "content" | "done" | "error"
          - ``text``: partial text (for content chunks)
          - ``reasoning_tokens``: int (for thinking updates)
          - ``result``: XaiNativeResult (for done)
          - ``error``: str (for error)
        """
        payload = self._build_payload(
            message=message, config=config, system_prompt=system_prompt, stream=True,
        )
        start = time.monotonic()
        accumulated_text = ""
        accumulated_annotations: list[XaiAnnotation] = []
        last_usage: dict[str, Any] = {}
        response_id = ""
        model_used = config.model

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(config.timeout_seconds, connect=15.0),
            ) as client:
                async with client.stream(
                    "POST",
                    f"{_BASE_URL}/responses",
                    headers=self._headers,
                    json=payload,
                ) as resp:
                    if resp.status_code != 200:
                        body = await resp.aread()
                        yield {
                            "type": "error",
                            "error": f"HTTP {resp.status_code}: {body.decode()[:200]}",
                        }
                        return

                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:]
                        if raw.strip() == "[DONE]":
                            break

                        try:
                            chunk = json.loads(raw)
                        except json.JSONDecodeError:
                            continue

                        # Extract response ID and model
                        if chunk.get("id"):
                            response_id = chunk["id"]
                        if chunk.get("model"):
                            model_used = chunk["model"]

                        # Usage updates (reasoning progress)
                        if "usage" in chunk:
                            last_usage = chunk["usage"]
                            reasoning_tokens = (
                                last_usage
                                .get("completion_tokens_details", {})
                                .get("reasoning_tokens", 0)
                            ) or last_usage.get("output_tokens_details", {}).get(
                                "reasoning_tokens", 0
                            )
                            if reasoning_tokens:
                                yield {
                                    "type": "thinking",
                                    "reasoning_tokens": reasoning_tokens,
                                }

                        # Content deltas — Responses API format
                        content_delta = self._extract_content_delta(chunk)
                        if content_delta:
                            accumulated_text += content_delta
                            yield {
                                "type": "content",
                                "text": content_delta,
                            }

                        # Collect annotations from this chunk
                        chunk_annotations = self._extract_annotations_from_chunk(chunk)
                        if chunk_annotations:
                            accumulated_annotations.extend(chunk_annotations)

        except httpx.TimeoutException:
            elapsed = time.monotonic() - start
            yield {"type": "error", "error": f"Request timed out after {elapsed:.0f}s"}
            return
        except Exception as exc:
            yield {"type": "error", "error": str(exc)}
            return

        elapsed = time.monotonic() - start

        # Build final result
        usage = self._parse_usage(last_usage)
        result = XaiNativeResult(
            response_id=response_id,
            status=XaiNativeStatus.completed,
            content=accumulated_text,
            model=model_used,
            usage=usage,
            annotations=accumulated_annotations,
            elapsed_seconds=elapsed,
        )
        yield {"type": "done", "result": result}

    # ── Response parsing ───────────────────────────────────────────

    def _parse_response(self, data: dict[str, Any], elapsed: float) -> XaiNativeResult:
        """Parse a non-streaming Responses API response."""
        response_id = data.get("id", "")
        model_used = data.get("model", "")
        status_str = data.get("status", "completed")
        status = XaiNativeStatus.completed if status_str == "completed" else XaiNativeStatus.failed

        # Extract text from output items
        content = ""
        annotations: list[XaiAnnotation] = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        content += c.get("text", "")
                        for ann in c.get("annotations", []):
                            annotations.append(XaiAnnotation(
                                type=ann.get("type", ""),
                                url=ann.get("url"),
                                title=ann.get("title"),
                                start_index=ann.get("start_index"),
                                end_index=ann.get("end_index"),
                            ))
            # Skip "reasoning" items — do not expose hidden chain-of-thought

        # Error from API
        error_obj = data.get("error")
        error_str = None
        if error_obj:
            error_str = error_obj.get("message", str(error_obj))
            status = XaiNativeStatus.failed

        usage = self._parse_usage(data.get("usage", {}))

        return XaiNativeResult(
            response_id=response_id,
            status=status,
            content=content,
            model=model_used,
            usage=usage,
            annotations=annotations,
            elapsed_seconds=elapsed,
            error=error_str,
        )

    def _parse_usage(self, raw: dict[str, Any]) -> XaiUsage:
        """Normalize usage from either Chat Completions or Responses format."""
        reasoning_tokens = 0
        details = raw.get("completion_tokens_details") or raw.get("output_tokens_details") or {}
        reasoning_tokens = details.get("reasoning_tokens", 0)

        return XaiUsage(
            input_tokens=raw.get("input_tokens", 0) or raw.get("prompt_tokens", 0),
            output_tokens=raw.get("output_tokens", 0) or raw.get("completion_tokens", 0),
            total_tokens=raw.get("total_tokens", 0),
            reasoning_tokens=reasoning_tokens,
            num_sources_used=raw.get("num_sources_used", 0),
            num_server_side_tools_used=raw.get("num_server_side_tools_used", 0),
        )

    def _extract_annotations_from_chunk(self, chunk: dict[str, Any]) -> list[XaiAnnotation]:
        """Extract annotations from a streaming SSE chunk.

        Annotations appear in ``output`` items (output_text.annotations) and
        occasionally in ``delta`` objects for streaming annotation updates.
        """
        annotations: list[XaiAnnotation] = []

        # Responses API: annotations inside output items
        for item in chunk.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        for ann in c.get("annotations", []):
                            annotations.append(XaiAnnotation(
                                type=ann.get("type", ""),
                                url=ann.get("url"),
                                title=ann.get("title"),
                                start_index=ann.get("start_index"),
                                end_index=ann.get("end_index"),
                            ))

        # Responses API: annotations in delta (streaming annotation deltas)
        if "delta" in chunk and isinstance(chunk["delta"], dict):
            for ann in chunk["delta"].get("annotations", []):
                annotations.append(XaiAnnotation(
                    type=ann.get("type", ""),
                    url=ann.get("url"),
                    title=ann.get("title"),
                    start_index=ann.get("start_index"),
                    end_index=ann.get("end_index"),
                ))

        return annotations

    def _extract_content_delta(self, chunk: dict[str, Any]) -> str:
        """Extract content text from an SSE chunk (Responses or Chat Completions format)."""
        # Responses API streaming format
        # Look for output_text content delta
        if "delta" in chunk:
            delta = chunk["delta"]
            if isinstance(delta, str):
                return delta
            if isinstance(delta, dict):
                return delta.get("content", "") or delta.get("text", "")

        # Chat Completions streaming format (choices[].delta.content)
        for choice in chunk.get("choices", []):
            delta = choice.get("delta", {})
            content = delta.get("content")
            if content:
                return content

        # Responses API: output items in stream
        for item in chunk.get("output", []):
            if item.get("type") == "message":
                for c in item.get("content", []):
                    if c.get("type") == "output_text":
                        return c.get("text", "")

        return ""
