"""
Tests for image_pipeline.reasoning.execution.comic_assembler — Cycle 5.

Coverage:
* Layout/panel-count validation mirrors ComicSequenceSpec rules.
* SINGLE: passthrough one panel; canvas equals cell + 2*gutter.
* HORIZONTAL_STRIP: 1 row, N cols; correct W/H math with gutters.
* VERTICAL_STRIP: N rows, 1 col.
* GRID_2X2 / GRID_2X3 / GRID_3X3 fixed dims; assembler raises on wrong count.
* Heterogeneous panel sizes letterbox-fit into the common cell (max W, max H).
* Gutter math: gutter_px=0 valid; negative raises.
* CUSTOM layout raises ValueError.
* Empty input list raises.
* Empty / undecodable panel bytes raise with index in message.
* Background validation (must be 3-tuple of ints in [0, 255]).
* JPEG output drops alpha / produces JPEG bytes.
* AssembledComic.to_dict is JSON-serializable and omits image_bytes.
* Cross-layer hygiene: assembler does not call load_dotenv, import dotenv,
  or import services.chatbot / core / image_pipeline.evaluator.
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from PIL import Image

from image_pipeline.reasoning.execution import (
    assemble_comic,
)
from image_pipeline.reasoning.schemas import OutputLayout

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _png(width: int, height: int, color=(200, 50, 50)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def _decode(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    return img


# ---------------------------------------------------------------------------
# Layout validation
# ---------------------------------------------------------------------------


class TestPanelCountValidation:
    @pytest.mark.parametrize(
        "layout, count",
        [
            (OutputLayout.SINGLE, 2),
            (OutputLayout.GRID_2X2, 3),
            (OutputLayout.GRID_2X2, 5),
            (OutputLayout.GRID_2X3, 5),
            (OutputLayout.GRID_3X3, 8),
        ],
    )
    def test_wrong_count_raises(self, layout, count):
        panels = [_png(100, 100) for _ in range(count)]
        with pytest.raises(ValueError, match=re.escape(f"layout={layout.value}")):
            assemble_comic(layout, panels)

    def test_strip_accepts_any_count(self):
        result = assemble_comic(
            OutputLayout.HORIZONTAL_STRIP,
            [_png(60, 40) for _ in range(5)],
            gutter_px=0,
        )
        assert result.panel_count == 5


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


class TestSingle:
    def test_single_panel_canvas_includes_padding(self):
        result = assemble_comic(OutputLayout.SINGLE, [_png(80, 60)], gutter_px=4)
        # 1 col × 80 + 2 × 4 gutter; 1 row × 60 + 2 × 4
        assert result.cell_width == 80
        assert result.cell_height == 60
        assert result.width == 80 + 2 * 4
        assert result.height == 60 + 2 * 4
        assert _decode(result.image_bytes).size == (result.width, result.height)


class TestHorizontalStrip:
    def test_three_panel_strip(self):
        panels = [_png(50, 40) for _ in range(3)]
        result = assemble_comic(OutputLayout.HORIZONTAL_STRIP, panels, gutter_px=10)
        assert result.cell_width == 50
        assert result.cell_height == 40
        # 3 cols × 50 + 4 × 10 gutter
        assert result.width == 3 * 50 + 4 * 10
        assert result.height == 40 + 2 * 10
        assert _decode(result.image_bytes).size == (result.width, result.height)


class TestVerticalStrip:
    def test_two_panel_strip(self):
        panels = [_png(60, 30) for _ in range(2)]
        result = assemble_comic(OutputLayout.VERTICAL_STRIP, panels, gutter_px=5)
        assert result.width == 60 + 2 * 5
        assert result.height == 2 * 30 + 3 * 5


class TestGrid:
    def test_grid_2x2(self):
        panels = [_png(100, 100) for _ in range(4)]
        result = assemble_comic(OutputLayout.GRID_2X2, panels, gutter_px=8)
        assert result.width == 2 * 100 + 3 * 8
        assert result.height == 2 * 100 + 3 * 8

    def test_grid_2x3_is_two_rows_three_cols(self):
        panels = [_png(50, 70) for _ in range(6)]
        result = assemble_comic(OutputLayout.GRID_2X3, panels, gutter_px=0)
        # 2 rows × 70, 3 cols × 50, no gutter
        assert result.width == 3 * 50
        assert result.height == 2 * 70

    def test_grid_3x3(self):
        panels = [_png(40, 40) for _ in range(9)]
        result = assemble_comic(OutputLayout.GRID_3X3, panels, gutter_px=2)
        assert result.width == 3 * 40 + 4 * 2
        assert result.height == 3 * 40 + 4 * 2


# ---------------------------------------------------------------------------
# Cell normalization
# ---------------------------------------------------------------------------


class TestLetterbox:
    def test_heterogeneous_panels_use_max_cell(self):
        panels = [_png(80, 40), _png(40, 80), _png(60, 60), _png(20, 20)]
        result = assemble_comic(OutputLayout.GRID_2X2, panels, gutter_px=0)
        assert result.cell_width == 80
        assert result.cell_height == 80
        assert result.width == 2 * 80
        assert result.height == 2 * 80
        # Decoded canvas matches advertised geometry.
        assert _decode(result.image_bytes).size == (result.width, result.height)

    def test_single_panel_smaller_than_cell_is_unchanged_geometry(self):
        result = assemble_comic(OutputLayout.SINGLE, [_png(30, 30)], gutter_px=0)
        # cell = panel size, no gutter → canvas equals panel size.
        assert (result.width, result.height) == (30, 30)


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


class TestArgValidation:
    def test_custom_layout_rejected(self):
        with pytest.raises(ValueError, match="CUSTOM"):
            assemble_comic(OutputLayout.CUSTOM, [_png(10, 10)])

    def test_negative_gutter_rejected(self):
        with pytest.raises(ValueError, match="gutter_px"):
            assemble_comic(OutputLayout.SINGLE, [_png(10, 10)], gutter_px=-1)

    def test_zero_gutter_allowed(self):
        result = assemble_comic(OutputLayout.SINGLE, [_png(10, 10)], gutter_px=0)
        assert result.gutter_px == 0
        assert (result.width, result.height) == (10, 10)

    def test_empty_input_rejected(self):
        with pytest.raises(ValueError, match="at least one"):
            assemble_comic(OutputLayout.HORIZONTAL_STRIP, [])

    def test_layout_must_be_enum(self):
        with pytest.raises(ValueError, match="OutputLayout"):
            assemble_comic("grid_2x2", [_png(10, 10)] * 4)  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        "bg",
        [
            (255, 255),  # too short
            (255, 255, 255, 0),  # too long
            (-1, 0, 0),  # out of range
            (0, 0, 256),  # out of range
            "white",  # wrong type
            (1.0, 1.0, 1.0),  # floats not ints
        ],
    )
    def test_invalid_background_rejected(self, bg):
        with pytest.raises(ValueError, match="background"):
            assemble_comic(
                OutputLayout.SINGLE,
                [_png(10, 10)],
                background=bg,  # type: ignore[arg-type]
            )


class TestPanelBytesValidation:
    def test_empty_bytes_rejected(self):
        with pytest.raises(ValueError, match=r"panel\[1\] is empty"):
            assemble_comic(
                OutputLayout.HORIZONTAL_STRIP,
                [_png(10, 10), b"", _png(10, 10)],
            )

    def test_undecodable_bytes_rejected(self):
        with pytest.raises(ValueError, match=r"panel\[0\] could not be decoded"):
            assemble_comic(
                OutputLayout.SINGLE,
                [b"not an image"],
            )

    def test_non_bytes_rejected(self):
        with pytest.raises(ValueError, match=r"panel\[0\] must be bytes"):
            assemble_comic(
                OutputLayout.SINGLE,
                ["not bytes"],  # type: ignore[list-item]
            )


# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------


class TestOutputFormat:
    def test_png_default(self):
        result = assemble_comic(OutputLayout.SINGLE, [_png(20, 20)])
        assert result.image_format == "PNG"
        assert _decode(result.image_bytes).format == "PNG"

    def test_jpeg_output(self):
        result = assemble_comic(
            OutputLayout.SINGLE, [_png(20, 20)], output_format="JPEG"
        )
        assert result.image_format == "JPEG"
        decoded = _decode(result.image_bytes)
        assert decoded.format == "JPEG"
        assert decoded.mode == "RGB"

    def test_jpg_alias_normalizes_to_jpeg(self):
        result = assemble_comic(
            OutputLayout.SINGLE, [_png(20, 20)], output_format="jpg"
        )
        assert result.image_format == "JPEG"
        assert _decode(result.image_bytes).format == "JPEG"


# ---------------------------------------------------------------------------
# Result serialization
# ---------------------------------------------------------------------------


class TestResultSerialization:
    def test_to_dict_round_trips_via_json(self):
        result = assemble_comic(OutputLayout.GRID_2X2, [_png(40, 40)] * 4)
        payload = result.to_dict()
        assert "image_bytes" not in payload
        # JSON-safe.
        encoded = json.dumps(payload)
        decoded = json.loads(encoded)
        assert decoded["layout"] == "grid_2x2"
        assert decoded["panel_count"] == 4
        assert decoded["image_format"] == "PNG"
        assert decoded["image_bytes_size"] == len(result.image_bytes)


# ---------------------------------------------------------------------------
# Hygiene
# ---------------------------------------------------------------------------


_EXEC_DIR = (
    Path(__file__).resolve().parents[4]
    / "app"
    / "image_pipeline"
    / "reasoning"
    / "execution"
)
_ASSEMBLER = _EXEC_DIR / "comic_assembler.py"


class TestComicAssemblerHygiene:
    def test_no_load_dotenv(self):
        text = _ASSEMBLER.read_text(encoding="utf-8")
        assert "load_dotenv" not in text

    def test_no_dotenv_import(self):
        text = _ASSEMBLER.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                assert "dotenv" not in stripped, stripped

    def test_no_chatbot_or_evaluator_import(self):
        text = _ASSEMBLER.read_text(encoding="utf-8")
        forbidden = ("services.chatbot", "core.", "image_pipeline.evaluator")
        for line in text.splitlines():
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            for needle in forbidden:
                assert needle not in stripped, f"forbidden import: {stripped}"
