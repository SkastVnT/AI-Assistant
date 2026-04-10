"""Contract tests for SSE complete payload in Flask stream route."""

from routes.stream import _build_complete_event_payload


REQUIRED_COMPLETE_FIELDS = {
    "response",
    "model",
    "context",
    "deep_thinking",
    "thinking_mode",
    "total_chunks",
    "thinking_summary",
    "thinking_steps",
    "thinking_duration_ms",
    "timestamp",
    "elapsed_time",
    "tokens",
    "max_tokens",
}


def test_complete_payload_contains_required_fields():
    payload = _build_complete_event_payload(
        full_response="ok",
        model="grok",
        context="casual",
        deep_thinking=True,
        thinking_mode="multi-thinking",
        chunk_count=3,
        thinking_summary="done",
        thinking_steps_text=["a", "b"],
        thinking_duration=120,
        elapsed_time=1.2345,
        tokens=321,
        max_tokens=4096,
    )

    assert REQUIRED_COMPLETE_FIELDS.issubset(payload.keys())


def test_complete_payload_contract_types_and_values():
    payload = _build_complete_event_payload(
        full_response="hello",
        model="grok",
        context="casual",
        deep_thinking=False,
        thinking_mode="instant",
        chunk_count=1,
        thinking_summary="",
        thinking_steps_text=[],
        thinking_duration=0,
        elapsed_time=2.34567,
        tokens=100,
        max_tokens=2000,
    )

    assert isinstance(payload["response"], str)
    assert isinstance(payload["thinking_steps"], list)
    assert isinstance(payload["elapsed_time"], float)
    assert payload["elapsed_time"] == 2.346
    assert payload["tokens"] > 0
    assert payload["max_tokens"] >= payload["tokens"]
