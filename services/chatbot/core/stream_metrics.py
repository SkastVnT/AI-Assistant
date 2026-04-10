"""In-memory stream telemetry for operational monitoring and long-term convergence."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

_LOCK = Lock()
_STARTED_AT = datetime.now(timezone.utc)

_COUNTERS: dict[str, int] = {
    "total_requests": 0,
    "completed_requests": 0,
    "errored_requests": 0,
    "fallback_to_standard": 0,
    "near_token_limit": 0,
}

_BY_BACKEND: dict[str, dict[str, int]] = {
    "flask": {"requests": 0, "completed": 0, "errors": 0, "fallback": 0},
    "fastapi": {"requests": 0, "completed": 0, "errors": 0, "fallback": 0},
}

_RECENT_COMPLETIONS: deque[dict[str, Any]] = deque(maxlen=200)
_RECENT_ERRORS: deque[dict[str, Any]] = deque(maxlen=100)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_stream_start(*, backend: str, request_id: str) -> None:
    with _LOCK:
        _COUNTERS["total_requests"] += 1
        _BY_BACKEND.setdefault(backend, {"requests": 0, "completed": 0, "errors": 0, "fallback": 0})
        _BY_BACKEND[backend]["requests"] += 1


def record_stream_complete(
    *,
    backend: str,
    request_id: str,
    elapsed_s: float,
    chunk_count: int,
    tokens: int,
    max_tokens: int,
    fallback_used: bool,
    time_to_first_chunk_s: float | None = None,
) -> None:
    with _LOCK:
        _COUNTERS["completed_requests"] += 1
        _BY_BACKEND.setdefault(backend, {"requests": 0, "completed": 0, "errors": 0, "fallback": 0})
        _BY_BACKEND[backend]["completed"] += 1

        token_util = (tokens / max_tokens) if max_tokens > 0 else 0.0
        if token_util >= 0.9:
            _COUNTERS["near_token_limit"] += 1

        if fallback_used:
            _COUNTERS["fallback_to_standard"] += 1
            _BY_BACKEND[backend]["fallback"] += 1

        _RECENT_COMPLETIONS.append(
            {
                "ts": _utc_now(),
                "request_id": request_id,
                "backend": backend,
                "elapsed_s": round(float(elapsed_s), 3),
                "ttfc_s": round(float(time_to_first_chunk_s), 3) if time_to_first_chunk_s is not None else None,
                "chunk_count": int(chunk_count),
                "tokens": int(tokens),
                "max_tokens": int(max_tokens),
                "token_utilization": round(token_util, 4),
                "fallback_used": bool(fallback_used),
            }
        )


def record_stream_error(*, backend: str, request_id: str, error: str) -> None:
    with _LOCK:
        _COUNTERS["errored_requests"] += 1
        _BY_BACKEND.setdefault(backend, {"requests": 0, "completed": 0, "errors": 0, "fallback": 0})
        _BY_BACKEND[backend]["errors"] += 1
        _RECENT_ERRORS.append(
            {
                "ts": _utc_now(),
                "request_id": request_id,
                "backend": backend,
                "error": str(error)[:800],
            }
        )


def get_stream_metrics_snapshot() -> dict[str, Any]:
    with _LOCK:
        total = _COUNTERS["total_requests"]
        completed = _COUNTERS["completed_requests"]
        fallback = _COUNTERS["fallback_to_standard"]
        near_limit = _COUNTERS["near_token_limit"]

        fallback_rate = (fallback / completed) if completed > 0 else 0.0
        near_limit_rate = (near_limit / completed) if completed > 0 else 0.0

        # "Potential truncation" proxy: near token limit in completed streams
        potential_truncation_ratio = near_limit_rate

        return {
            "started_at": _STARTED_AT.isoformat(),
            "snapshot_at": _utc_now(),
            "totals": dict(_COUNTERS),
            "rates": {
                "fallback_rate": round(fallback_rate, 4),
                "near_token_limit_rate": round(near_limit_rate, 4),
                "potential_truncation_ratio": round(potential_truncation_ratio, 4),
            },
            "by_backend": {k: dict(v) for k, v in _BY_BACKEND.items()},
            "recent_completions": list(_RECENT_COMPLETIONS),
            "recent_errors": list(_RECENT_ERRORS),
        }
