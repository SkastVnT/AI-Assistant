"""Regression tests for video aspect-ratio normalization and response consistency."""

from src.video_generation import _resolve_aspect_ratio, ensure_aspect_ratio_field


def test_resolve_aspect_ratio_square_maps_to_valid_api_size():
    api_size, label = _resolve_aspect_ratio("1080x1920")
    assert api_size == "1280x720"
    assert label == "1:1"


def test_resolve_aspect_ratio_rejects_invalid_value():
    try:
        _resolve_aspect_ratio("999x999")
        assert False, "Expected ValueError for invalid aspect ratio"
    except ValueError as e:
        assert "Unsupported video size/aspect ratio" in str(e)


def test_ensure_aspect_ratio_backfills_from_size():
    payload = {"id": "abc", "status": "queued", "size": "1280x720"}
    result = ensure_aspect_ratio_field(payload)
    assert result["aspect_ratio"] == "16:9"
