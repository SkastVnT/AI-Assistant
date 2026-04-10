"""Contract tests for stream telemetry metrics."""

from core.stream_metrics import (
    get_stream_metrics_snapshot,
    record_stream_complete,
    record_stream_error,
    record_stream_start,
)


def test_stream_metrics_snapshot_has_expected_shape():
    snap = get_stream_metrics_snapshot()

    assert "totals" in snap
    assert "rates" in snap
    assert "by_backend" in snap
    assert "recent_completions" in snap
    assert "recent_errors" in snap


def test_stream_metrics_records_lifecycle_events():
    before = get_stream_metrics_snapshot()
    req_id = "testmetrics001"

    record_stream_start(backend="flask", request_id=req_id)
    record_stream_complete(
        backend="flask",
        request_id=req_id,
        elapsed_s=1.2,
        time_to_first_chunk_s=0.3,
        chunk_count=5,
        tokens=950,
        max_tokens=1000,
        fallback_used=True,
    )
    record_stream_error(backend="flask", request_id=req_id, error="simulated")

    after = get_stream_metrics_snapshot()

    assert after["totals"]["total_requests"] >= before["totals"]["total_requests"] + 1
    assert after["totals"]["completed_requests"] >= before["totals"]["completed_requests"] + 1
    assert after["totals"]["errored_requests"] >= before["totals"]["errored_requests"] + 1
    assert after["totals"]["fallback_to_standard"] >= before["totals"]["fallback_to_standard"] + 1
    assert after["totals"]["near_token_limit"] >= before["totals"]["near_token_limit"] + 1
