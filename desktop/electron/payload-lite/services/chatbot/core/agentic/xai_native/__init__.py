"""
xAI Native Multi-Agent Research — package
==========================================
Separate execution path that calls xAI's Responses API with the
``grok-4.20-multi-agent`` model.  This does **not** reuse the
internal council orchestrator — the multi-agent coordination happens
server-side inside xAI's infrastructure.

Public surface:
  • :func:`run_xai_native`        — non-streaming entry point
  • :func:`run_xai_native_stream` — SSE streaming entry point
  • :func:`is_xai_native_enabled` — feature flag check
"""
from core.agentic.xai_native.entrypoint import (
    is_xai_native_enabled,
    run_xai_native,
    run_xai_native_stream,
)

__all__ = [
    "is_xai_native_enabled",
    "run_xai_native",
    "run_xai_native_stream",
]
