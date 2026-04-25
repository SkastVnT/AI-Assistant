"""
image_pipeline.reasoning.execution.comic_assembler — Cycle 5.

Compose N rendered panel images into a single final image according to a
:class:`~image_pipeline.reasoning.schemas.OutputLayout`.

Design constraints (locked by the cycle plan):

* Pure synchronous Pillow-only assembler. No network, no .env, no chatbot
  imports, no evaluator imports.
* Inputs are raw image bytes (the same shape produced by the Cycle 3
  runner / Cycle 4 correction router). Outputs are raw image bytes plus a
  small JSON-safe descriptor.
* Layout count rules mirror :class:`OutputLayout` validation in
  :mod:`image_pipeline.reasoning.schemas` to fail fast and uniformly.
* Heterogeneous panel sizes are normalized by letterbox-fitting each panel
  into a common cell (max width, max height across the input set), padded
  with the requested background color. This preserves aspect ratio and
  produces deterministic geometry independent of upstream renderer drift.
* Overlay rendering (caption / speech-bubble text) is **out of scope** for
  Cycle 5 — the assembler exposes only layout composition; overlay text
  rendering can be layered on top in a later cycle without changing this
  contract.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Mapping, Sequence, Tuple

from PIL import Image

from image_pipeline.reasoning.schemas import OutputLayout

__all__ = [
    "AssembledComic",
    "assemble_comic",
]


# Layout -> (rows, cols) when fixed; None means "derive from panel count".
_GRID_DIMS: Mapping[OutputLayout, Tuple[int, int] | None] = {
    OutputLayout.SINGLE: (1, 1),
    OutputLayout.HORIZONTAL_STRIP: None,  # 1 row, N cols
    OutputLayout.VERTICAL_STRIP: None,    # N rows, 1 col
    OutputLayout.GRID_2X2: (2, 2),
    OutputLayout.GRID_2X3: (2, 3),
    OutputLayout.GRID_3X3: (3, 3),
}

# Mirror of ComicSequenceSpec._check_layout_compat for assembler inputs.
_PANEL_COUNT_RULES: Mapping[OutputLayout, Tuple[int, ...] | None] = {
    OutputLayout.SINGLE: (1,),
    OutputLayout.HORIZONTAL_STRIP: None,
    OutputLayout.VERTICAL_STRIP: None,
    OutputLayout.GRID_2X2: (4,),
    OutputLayout.GRID_2X3: (6,),
    OutputLayout.GRID_3X3: (9,),
}


@dataclass(frozen=True, slots=True)
class AssembledComic:
    """Result of :func:`assemble_comic`.

    ``image_bytes`` is excluded from :meth:`to_dict` so the descriptor is
    JSON-serializable for logging and SSE event payloads.
    """

    layout: OutputLayout
    panel_count: int
    width: int
    height: int
    image_format: str
    gutter_px: int
    cell_width: int
    cell_height: int
    image_bytes: bytes = field(repr=False)

    def to_dict(self) -> dict:
        return {
            "layout": self.layout.value,
            "panel_count": self.panel_count,
            "width": self.width,
            "height": self.height,
            "image_format": self.image_format,
            "gutter_px": self.gutter_px,
            "cell_width": self.cell_width,
            "cell_height": self.cell_height,
            "image_bytes_size": len(self.image_bytes),
        }


def assemble_comic(
    layout: OutputLayout,
    panel_images: Sequence[bytes],
    *,
    gutter_px: int = 12,
    background: Tuple[int, int, int] = (255, 255, 255),
    output_format: str = "PNG",
) -> AssembledComic:
    """Compose ``panel_images`` into a single image according to ``layout``.

    Parameters
    ----------
    layout
        Target :class:`OutputLayout`. ``CUSTOM`` is not supported by this
        assembler — caller must perform bespoke composition.
    panel_images
        Ordered sequence of PNG/JPEG bytes, one per panel. Must match the
        layout's required panel count (see :class:`OutputLayout`).
    gutter_px
        Pixel gap between adjacent cells. Must be ``>= 0``. Background
        color fills the gutter.
    background
        RGB tuple (0-255 each) used for letterbox padding and gutters.
    output_format
        Pillow format identifier for the output bytes (``"PNG"``,
        ``"JPEG"``, ``"WEBP"``).

    Raises
    ------
    ValueError
        On invalid arguments (wrong panel count for layout, ``CUSTOM``
        layout, non-positive gutter, empty / undecodable panel bytes,
        empty input set).
    """
    if not isinstance(layout, OutputLayout):
        raise ValueError(f"layout must be OutputLayout, got {type(layout).__name__}")
    if layout is OutputLayout.CUSTOM:
        raise ValueError("layout=CUSTOM is not supported by assemble_comic")
    if gutter_px < 0:
        raise ValueError(f"gutter_px must be >= 0, got {gutter_px}")
    if not panel_images:
        raise ValueError("panel_images must contain at least one image")
    _validate_background(background)
    fmt = output_format.upper()

    panel_count = len(panel_images)
    allowed = _PANEL_COUNT_RULES.get(layout)
    if allowed is not None and panel_count not in allowed:
        raise ValueError(
            f"layout={layout.value} requires {allowed} panels, got {panel_count}"
        )

    rows, cols = _resolve_grid(layout, panel_count)

    # Decode panels eagerly so caller errors surface up-front.
    decoded = [_decode_panel(idx, raw) for idx, raw in enumerate(panel_images)]

    cell_w = max(img.width for img in decoded)
    cell_h = max(img.height for img in decoded)

    canvas_w = cols * cell_w + (cols + 1) * gutter_px
    canvas_h = rows * cell_h + (rows + 1) * gutter_px

    # JPEG cannot store alpha — use RGB; otherwise preserve RGBA capability.
    canvas_mode = "RGB" if fmt in {"JPEG", "JPG"} else "RGBA"
    canvas_bg = background if canvas_mode == "RGB" else (*background, 255)
    canvas = Image.new(canvas_mode, (canvas_w, canvas_h), canvas_bg)

    for idx, panel in enumerate(decoded):
        row = idx // cols
        col = idx % cols
        cell_x = gutter_px + col * (cell_w + gutter_px)
        cell_y = gutter_px + row * (cell_h + gutter_px)
        fitted = _letterbox(panel, cell_w, cell_h, background, canvas_mode)
        canvas.paste(fitted, (cell_x, cell_y))

    out_buf = io.BytesIO()
    save_kwargs: dict = {}
    if fmt in {"JPEG", "JPG"}:
        save_kwargs["quality"] = 92
    canvas.save(out_buf, format="JPEG" if fmt == "JPG" else fmt, **save_kwargs)
    out_bytes = out_buf.getvalue()

    return AssembledComic(
        layout=layout,
        panel_count=panel_count,
        width=canvas_w,
        height=canvas_h,
        image_format="JPEG" if fmt == "JPG" else fmt,
        gutter_px=gutter_px,
        cell_width=cell_w,
        cell_height=cell_h,
        image_bytes=out_bytes,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_grid(layout: OutputLayout, panel_count: int) -> Tuple[int, int]:
    fixed = _GRID_DIMS.get(layout)
    if fixed is not None:
        return fixed
    if layout is OutputLayout.HORIZONTAL_STRIP:
        return (1, panel_count)
    if layout is OutputLayout.VERTICAL_STRIP:
        return (panel_count, 1)
    # Defensive — _PANEL_COUNT_RULES already gated CUSTOM out.
    raise ValueError(f"unsupported layout for grid resolution: {layout.value}")


def _decode_panel(idx: int, raw: bytes) -> Image.Image:
    if not isinstance(raw, (bytes, bytearray)):
        raise ValueError(f"panel[{idx}] must be bytes, got {type(raw).__name__}")
    if not raw:
        raise ValueError(f"panel[{idx}] is empty bytes")
    try:
        img = Image.open(io.BytesIO(bytes(raw)))
        img.load()
    except Exception as exc:  # noqa: BLE001 — surface decode failures uniformly
        raise ValueError(f"panel[{idx}] could not be decoded: {exc}") from exc
    return img


def _letterbox(
    img: Image.Image,
    target_w: int,
    target_h: int,
    background: Tuple[int, int, int],
    canvas_mode: str,
) -> Image.Image:
    if img.width == target_w and img.height == target_h and img.mode == canvas_mode:
        return img

    src = img.convert(canvas_mode) if img.mode != canvas_mode else img
    scale = min(target_w / src.width, target_h / src.height)
    new_w = max(1, int(round(src.width * scale)))
    new_h = max(1, int(round(src.height * scale)))
    resized = src.resize((new_w, new_h), Image.LANCZOS)

    bg = background if canvas_mode == "RGB" else (*background, 255)
    cell = Image.new(canvas_mode, (target_w, target_h), bg)
    off_x = (target_w - new_w) // 2
    off_y = (target_h - new_h) // 2
    cell.paste(resized, (off_x, off_y))
    return cell


def _validate_background(bg: Tuple[int, int, int]) -> None:
    if (
        not isinstance(bg, tuple)
        or len(bg) != 3
        or not all(isinstance(c, int) and 0 <= c <= 255 for c in bg)
    ):
        raise ValueError(
            f"background must be a 3-tuple of ints in [0, 255], got {bg!r}"
        )
