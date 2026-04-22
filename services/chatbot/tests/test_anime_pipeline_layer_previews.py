"""Tests for the ChatGPT-style live "Layer N" preview gallery.

Scope:
  * _LAYER_STAGES is exposed and covers exactly the 4 visually-meaningful
    pipeline passes the UI shows as Layer 1..4.
  * _persist_intermediate_preview writes a stable per-stage filename and
    rejects unsafe job_id / stage characters.
  * _latest_intermediate_b64 honours the detail_* prefix fallback for
    the detection_inpaint stage.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_CHATBOT_DIR = Path(__file__).resolve().parents[1]
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))


def _b64_png() -> str:
    """1x1 transparent PNG, base64-encoded."""
    raw = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00"
        b"\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc"
        b"\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return base64.b64encode(raw).decode("ascii")


def test_layer_stages_cover_expected_four_passes():
    from core.anime_pipeline_service import _LAYER_STAGES
    assert set(_LAYER_STAGES.keys()) == {
        "composition_pass", "structure_lock",
        "beauty_pass", "detection_inpaint",
    }
    # Layer numbers must be 1..4 in pipeline order.
    nums = sorted(meta[0] for meta in _LAYER_STAGES.values())
    assert nums == [1, 2, 3, 4]


def test_persist_intermediate_preview_writes_stable_filename(tmp_path, monkeypatch):
    import core.anime_pipeline_service as svc
    monkeypatch.setattr(svc, "_IMAGE_STORAGE_DIR", tmp_path)
    url = svc._persist_intermediate_preview("job_abc123", "beauty_pass", _b64_png())
    assert url is not None
    assert url.startswith("/storage/images/")
    assert url.endswith("preview_job_abc123_beauty_pass.png")
    saved = tmp_path / "preview_job_abc123_beauty_pass.png"
    assert saved.exists() and saved.stat().st_size > 0
    # Calling again overwrites in place (no _2 suffix).
    url2 = svc._persist_intermediate_preview("job_abc123", "beauty_pass", _b64_png())
    assert url2 == url
    assert len(list(tmp_path.iterdir())) == 1


def test_persist_intermediate_preview_strips_unsafe_chars(tmp_path, monkeypatch):
    import core.anime_pipeline_service as svc
    monkeypatch.setattr(svc, "_IMAGE_STORAGE_DIR", tmp_path)
    # Path-traversal style payloads must be reduced to safe characters.
    url = svc._persist_intermediate_preview(
        "../../etc/passwd", "beauty_pass; rm -rf /", _b64_png(),
    )
    assert url is not None
    # No '..' should leak into the filename.
    assert ".." not in url
    assert ";" not in url
    assert " " not in url
    saved = list(tmp_path.iterdir())
    assert len(saved) == 1
    assert saved[0].name.startswith("preview_")


def test_persist_intermediate_preview_returns_none_on_empty_input(tmp_path, monkeypatch):
    import core.anime_pipeline_service as svc
    monkeypatch.setattr(svc, "_IMAGE_STORAGE_DIR", tmp_path)
    assert svc._persist_intermediate_preview("", "beauty_pass", _b64_png()) is None
    assert svc._persist_intermediate_preview("jx", "", _b64_png()) is None
    assert svc._persist_intermediate_preview("jx", "beauty_pass", "") is None


def test_latest_intermediate_b64_matches_detail_prefix_for_detection_inpaint():
    """detection_inpaint stores per-region snapshots as detail_face /
    detail_eye etc. _latest_intermediate_b64 must accept that prefix."""
    from core.anime_pipeline_service import _latest_intermediate_b64

    fake_job = SimpleNamespace(intermediates=[
        SimpleNamespace(stage="beauty_pass",  image_b64="beauty_b64"),
        SimpleNamespace(stage="detail_face",  image_b64="face_b64"),
        SimpleNamespace(stage="detail_eye",   image_b64="eye_b64"),
    ])
    # Exact match for beauty_pass
    assert _latest_intermediate_b64(fake_job, "beauty_pass") == "beauty_b64"
    # Prefix match for detection_inpaint -> picks the most recent detail_*
    assert _latest_intermediate_b64(fake_job, "detection_inpaint") == "eye_b64"
    # Other stages without intermediates return None.
    assert _latest_intermediate_b64(fake_job, "vision_analysis") is None


def test_latest_intermediate_b64_skips_empty_b64():
    from core.anime_pipeline_service import _latest_intermediate_b64
    fake_job = SimpleNamespace(intermediates=[
        SimpleNamespace(stage="beauty_pass", image_b64=""),
        SimpleNamespace(stage="beauty_pass", image_b64=None),
        SimpleNamespace(stage="beauty_pass", image_b64="real_b64"),
    ])
    assert _latest_intermediate_b64(fake_job, "beauty_pass") == "real_b64"
