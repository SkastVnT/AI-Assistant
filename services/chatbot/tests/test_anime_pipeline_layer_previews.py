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

pytestmark = pytest.mark.image

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


def test_latest_any_intermediate_b64_returns_most_recent_nonempty():
    """Used as the placeholder image for layer stages that are about to
    start or that finish without producing a fresh intermediate."""
    from core.anime_pipeline_service import _latest_any_intermediate_b64

    # Empty job → None.
    assert _latest_any_intermediate_b64(SimpleNamespace(intermediates=[])) is None

    # Returns the most recent non-empty entry across any stage.
    fake_job = SimpleNamespace(intermediates=[
        SimpleNamespace(stage="composition_pass", image_b64="comp"),
        SimpleNamespace(stage="structure_lock",   image_b64=""),
        SimpleNamespace(stage="beauty_pass",      image_b64="beauty"),
        SimpleNamespace(stage="critique",         image_b64=None),
    ])
    assert _latest_any_intermediate_b64(fake_job) == "beauty"

    # Skips empty/None entries from the tail.
    only_empties = SimpleNamespace(intermediates=[
        SimpleNamespace(stage="composition_pass", image_b64="real"),
        SimpleNamespace(stage="structure_lock",   image_b64=None),
        SimpleNamespace(stage="beauty_pass",      image_b64=""),
    ])
    assert _latest_any_intermediate_b64(only_empties) == "real"


def test_make_thumb_b64_returns_smaller_jpeg():
    """The inline thumb b64 must decode back to a tiny JPEG so the SSE
    frame stays small even when the source PNG is multi-MB."""
    import base64 as _b64
    from io import BytesIO
    from PIL import Image
    from core.anime_pipeline_service import _make_thumb_b64

    # Build a real-ish 1024x1024 PNG so thumbnail() actually downscales.
    src = Image.new("RGB", (1024, 1024), color=(120, 80, 200))
    buf = BytesIO()
    src.save(buf, format="PNG")
    src_b64 = _b64.b64encode(buf.getvalue()).decode("ascii")

    thumb_b64 = _make_thumb_b64(src_b64, max_dim=128)
    assert thumb_b64 is not None
    # Resulting payload must be substantially smaller than the source.
    assert len(thumb_b64) < len(src_b64) // 4
    # And it must be a valid JPEG that round-trips through PIL.
    decoded = Image.open(BytesIO(_b64.b64decode(thumb_b64)))
    assert decoded.format == "JPEG"
    assert max(decoded.size) <= 128


def test_make_thumb_b64_handles_garbage_input():
    from core.anime_pipeline_service import _make_thumb_b64
    assert _make_thumb_b64("") is None
    assert _make_thumb_b64("not-base64-at-all!!") is None
