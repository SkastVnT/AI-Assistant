"""Phase 3 — ComfyUI /ws live-preview binary frame parser + flag gating.

The parser is a pure function over ComfyUI's binary WS wire format
(see ComfyUI/server.py send_image / protocol.py):
  bytes[0:4] = big-endian event type (1 = PREVIEW_IMAGE, 4 = with metadata)
  PREVIEW_IMAGE:               bytes[4:8] = format (1 JPEG, 2 PNG), then image
  PREVIEW_IMAGE_WITH_METADATA: bytes[4:8] = metadata length, json, then image
"""

from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.image

_CHATBOT_DIR = Path(__file__).resolve().parents[1]
if str(_CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(_CHATBOT_DIR))

from image_pipeline.anime_pipeline.comfy_client import (  # noqa: E402
    parse_ws_preview_frame,
    ws_preview_enabled,
)


def _preview_image_frame(fmt_num: int, img: bytes) -> bytes:
    return struct.pack(">I", 1) + struct.pack(">I", fmt_num) + img


def _preview_with_metadata_frame(meta: dict, img: bytes) -> bytes:
    meta_json = json.dumps(meta).encode("utf-8")
    return (
        struct.pack(">I", 4)
        + struct.pack(">I", len(meta_json))
        + meta_json
        + img
    )


class TestParseWsPreviewFrame:
    def test_jpeg_preview(self):
        out = parse_ws_preview_frame(_preview_image_frame(1, b"\xff\xd8jpegbytes"))
        assert out == ("jpeg", b"\xff\xd8jpegbytes")

    def test_png_preview(self):
        out = parse_ws_preview_frame(_preview_image_frame(2, b"\x89PNGbytes"))
        assert out == ("png", b"\x89PNGbytes")

    def test_metadata_frame_png(self):
        out = parse_ws_preview_frame(
            _preview_with_metadata_frame({"image_type": "image/png"}, b"pngdata")
        )
        assert out == ("png", b"pngdata")

    def test_metadata_frame_defaults_jpeg(self):
        out = parse_ws_preview_frame(
            _preview_with_metadata_frame({"image_type": "image/jpeg"}, b"jpgdata")
        )
        assert out == ("jpeg", b"jpgdata")

    def test_unknown_event_returns_none(self):
        # event type 99 is not a preview frame
        assert parse_ws_preview_frame(struct.pack(">I", 99) + b"whatever") is None

    def test_unknown_format_returns_none(self):
        # format 7 is neither JPEG(1) nor PNG(2)
        assert parse_ws_preview_frame(_preview_image_frame(7, b"x")) is None

    def test_truncated_returns_none(self):
        assert parse_ws_preview_frame(b"\x00\x00") is None
        assert parse_ws_preview_frame(b"") is None
        assert parse_ws_preview_frame(None) is None

    def test_metadata_truncated_returns_none(self):
        # metadata length claims more bytes than present
        bad = struct.pack(">I", 4) + struct.pack(">I", 9999) + b"short"
        assert parse_ws_preview_frame(bad) is None


class TestWsPreviewFlag:
    def test_flag_off_by_default(self, monkeypatch):
        monkeypatch.delenv("ANIME_PIPELINE_WS_PREVIEW", raising=False)
        assert ws_preview_enabled() is False

    @pytest.mark.parametrize("val", ["1", "true", "TRUE", "yes", "on"])
    def test_flag_on_values(self, monkeypatch, val):
        monkeypatch.setenv("ANIME_PIPELINE_WS_PREVIEW", val)
        assert ws_preview_enabled() is True

    @pytest.mark.parametrize("val", ["", "0", "false", "no", "off"])
    def test_flag_off_values(self, monkeypatch, val):
        monkeypatch.setenv("ANIME_PIPELINE_WS_PREVIEW", val)
        assert ws_preview_enabled() is False


class TestWsReaderGating:
    """_maybe_start_ws_reader must be a no-op unless flag on AND a callback set."""

    def _client(self):
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        return ComfyClient(base_url="http://127.0.0.1:8188")

    def test_no_reader_when_flag_off(self, monkeypatch):
        import threading

        monkeypatch.setenv("ANIME_PIPELINE_WS_PREVIEW", "false")
        c = self._client()
        c.set_preview_callbacks(on_progress=lambda p: None)
        assert c._maybe_start_ws_reader("cid", "pid", threading.Event()) is None

    def test_no_reader_when_no_callbacks(self, monkeypatch):
        import threading

        monkeypatch.setenv("ANIME_PIPELINE_WS_PREVIEW", "true")
        c = self._client()  # no callbacks registered
        assert c._maybe_start_ws_reader("cid", "pid", threading.Event()) is None
