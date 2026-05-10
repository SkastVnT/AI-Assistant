"""
layer_painter.py - Spec §8/§9/§10/§11 post-inpaint artistic layer system.

Provides four composable post-processing passes applied AFTER
``DetectionInpaintAgent`` finishes but BEFORE ``UpscaleAgent``:

  * **Layer 1 - Base**        : pass-through (identity) — the beauty + inpaint
                                output is the "base" canvas.
  * **Layer 2 - Shadow pass** : gentle darken under hair / chin / brow lines
                                using face bbox + PIL multiply blend.
  * **Layer 3 - Highlight**   : subtle screen-mode highlight on iris/skin peaks.
  * **Layer 4 - Eye FX**      : two optional sub-effects:
        - eye-rolling: rotate iris/pupil upward (sclera-first, iris-second,
          direction configurable).
        - bloodshot: vein overlay on sclera (gradient #CC2200 → #FF4444).
  * **Layer 5 - Classifier**  : vision-language check that the final eye
                                state matches the user's request. Returns a
                                ``EyeStateReport`` the orchestrator can use
                                as a re-plan trigger.

All layers are optional and degrade gracefully when PIL / httpx are missing.
The module never mutates inputs; every pass returns a new base64 PNG string.
"""

from __future__ import annotations

import base64
import io
import json
import logging
import math
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Public data contracts ────────────────────────────────────────────

@dataclass
class EyeFXSpec:
    """Spec §9 / §10 eye-effect toggles."""

    eye_rolling: bool = False
    # Direction of iris offset, in clock coordinates
    #   "up" (default lewd anime trope), "up_left", "up_right", "down"
    rolling_direction: str = "up"
    # Strength of eye roll: 0.0 (no shift) → 1.0 (iris fully out of frame).
    # Recommend 0.45–0.60 for the "fucked silly" look.
    rolling_strength: float = 0.55

    bloodshot: bool = False
    # Intensity multiplier for bloodshot red veins, 0.0–1.0.
    bloodshot_intensity: float = 0.65

    def active(self) -> bool:
        return self.eye_rolling or self.bloodshot


@dataclass
class EyeBBox:
    """Axis-aligned bbox (pixel coords) for a single eye or eye pair."""

    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def w(self) -> int:
        return max(0, self.x1 - self.x0)

    @property
    def h(self) -> int:
        return max(0, self.y1 - self.y0)

    @property
    def cx(self) -> int:
        return (self.x0 + self.x1) // 2

    @property
    def cy(self) -> int:
        return (self.y0 + self.y1) // 2


@dataclass
class EyeStateReport:
    """Spec §11 eye-state classifier output."""

    detected_state: str = "unknown"      # e.g. "open", "rolled_back", "bloodshot"
    requested_state: str = "unknown"
    matches_request: bool = True
    confidence: float = 0.0
    notes: str = ""
    # Populated when classifier couldn't run (missing API key, network).
    skipped: bool = False

    def to_dict(self) -> dict:
        return {
            "detected_state": self.detected_state,
            "requested_state": self.requested_state,
            "matches_request": self.matches_request,
            "confidence": self.confidence,
            "notes": self.notes,
            "skipped": self.skipped,
        }


# ── Utilities ────────────────────────────────────────────────────────

def _b64_to_pil(image_b64: str):
    from PIL import Image
    raw = image_b64.split(",", 1)[-1] if "," in image_b64 else image_b64
    return Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGBA")


def _pil_to_b64(img) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _safe_import_pil():
    try:
        import PIL  # noqa: F401
        return True
    except Exception:
        logger.warning("[LayerPainter] Pillow not installed — all layers become no-ops.")
        return False


# ── Layer 2: shadow pass ─────────────────────────────────────────────

def layer2_shadow(image_b64: str, face_bbox: Optional[EyeBBox], strength: float = 0.18) -> str:
    """Apply a subtle vertical shadow gradient under the hair/brow line.

    If ``face_bbox`` is ``None`` the pass is a no-op. Strength is clamped
    to ``[0.05, 0.4]`` to avoid muddy output.
    """
    if not _safe_import_pil() or face_bbox is None:
        return image_b64
    try:
        from PIL import Image, ImageDraw, ImageFilter

        s = max(0.05, min(strength, 0.4))
        base = _b64_to_pil(image_b64)
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Shadow band: top ~25% of the face bbox, fading downward.
        x0, y0, x1 = face_bbox.x0, face_bbox.y0, face_bbox.x1
        band_h = max(8, face_bbox.h // 4)
        for i in range(band_h):
            # Linear fade from s*255 at top to 0 at bottom of band.
            alpha = int(max(0, s * 255 * (1 - i / band_h)))
            draw.rectangle([x0, y0 + i, x1, y0 + i + 1], fill=(0, 0, 0, alpha))

        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=face_bbox.h * 0.03))
        merged = Image.alpha_composite(base, overlay)
        return _pil_to_b64(merged)
    except Exception as e:
        logger.warning("[LayerPainter] layer2_shadow failed: %s", e)
        return image_b64


# ── Layer 3: highlight pass ──────────────────────────────────────────

def layer3_highlight(image_b64: str, face_bbox: Optional[EyeBBox], strength: float = 0.12) -> str:
    """Add a subtle screen-blend highlight along the top-left of the face
    bbox to mimic rim lighting / catchlight reinforcement."""
    if not _safe_import_pil() or face_bbox is None:
        return image_b64
    try:
        from PIL import Image, ImageDraw, ImageFilter

        s = max(0.04, min(strength, 0.3))
        base = _b64_to_pil(image_b64)
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Diagonal highlight from top-left corner of face bbox.
        band_w = max(12, face_bbox.w // 3)
        band_h = max(12, face_bbox.h // 4)
        for i in range(band_w):
            alpha = int(max(0, s * 255 * (1 - i / band_w)))
            draw.line(
                [(face_bbox.x0 + i, face_bbox.y0),
                 (face_bbox.x0, face_bbox.y0 + i)],
                fill=(255, 248, 230, alpha),
                width=2,
            )
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=4))
        merged = Image.alpha_composite(base, overlay)
        return _pil_to_b64(merged)
    except Exception as e:
        logger.warning("[LayerPainter] layer3_highlight failed: %s", e)
        return image_b64


# ── Layer 4a: eye-rolling ────────────────────────────────────────────

def _direction_to_offset(direction: str, amount_x: int, amount_y: int) -> Tuple[int, int]:
    d = direction.lower().strip()
    if d == "up":
        return 0, -amount_y
    if d == "down":
        return 0, amount_y
    if d == "left":
        return -amount_x, 0
    if d == "right":
        return amount_x, 0
    if d == "up_left":
        return -int(amount_x * 0.7), -int(amount_y * 0.7)
    if d == "up_right":
        return int(amount_x * 0.7), -int(amount_y * 0.7)
    return 0, -amount_y


def layer4a_eye_rolling(
    image_b64: str,
    eye_boxes: list[EyeBBox],
    direction: str = "up",
    strength: float = 0.55,
) -> str:
    """Two-pass eye roll: (1) repaint sclera white over the original iris
    position, (2) composite a shifted iris crop at the new position.

    The iris is harvested by cropping the inner ellipse of ``eye_box`` and
    blending it back at a translated location. Not a perfect anatomical
    simulation — meant as a stylistic VFX pass for anime aesthetics.
    """
    if not _safe_import_pil() or not eye_boxes:
        return image_b64
    try:
        from PIL import Image, ImageDraw, ImageFilter

        base = _b64_to_pil(image_b64).convert("RGBA")
        strength = max(0.1, min(strength, 1.0))

        for bb in eye_boxes:
            if bb.w < 8 or bb.h < 6:
                continue

            # Inner iris ellipse (centered, ~65% of bbox).
            ex_pad = int(bb.w * 0.18)
            ey_pad = int(bb.h * 0.15)
            iris_box = (
                bb.x0 + ex_pad, bb.y0 + ey_pad,
                bb.x1 - ex_pad, bb.y1 - ey_pad,
            )

            # Crop iris region.
            iris = base.crop(iris_box).convert("RGBA")

            # Build elliptical mask so we don't composite square corners.
            iris_mask = Image.new("L", iris.size, 0)
            ImageDraw.Draw(iris_mask).ellipse(
                (0, 0, iris.size[0] - 1, iris.size[1] - 1), fill=255,
            )
            iris.putalpha(iris_mask)

            # --- Pass 1: paint the original iris location white (sclera). ---
            sclera_patch = Image.new("RGBA", iris.size, (250, 245, 240, 255))
            sclera_patch.putalpha(iris_mask)
            base.alpha_composite(sclera_patch, dest=(iris_box[0], iris_box[1]))

            # --- Pass 2: composite the iris shifted in the chosen direction. ---
            max_offset_x = int(bb.w * 0.45 * strength)
            max_offset_y = int(bb.h * 0.70 * strength)
            ox, oy = _direction_to_offset(direction, max_offset_x, max_offset_y)
            dst = (iris_box[0] + ox, iris_box[1] + oy)
            # Clamp to image bounds.
            dst = (max(0, min(base.size[0] - iris.size[0], dst[0])),
                   max(0, min(base.size[1] - iris.size[1], dst[1])))

            # Feather iris edge slightly to blend.
            iris = iris.filter(ImageFilter.GaussianBlur(radius=0.8))
            base.alpha_composite(iris, dest=dst)

        return _pil_to_b64(base)
    except Exception as e:
        logger.warning("[LayerPainter] layer4a_eye_rolling failed: %s", e)
        return image_b64


# ── Layer 4b: bloodshot FX ───────────────────────────────────────────

def layer4b_bloodshot(
    image_b64: str,
    eye_boxes: list[EyeBBox],
    intensity: float = 0.65,
) -> str:
    """Overlay red veins on the sclera of each eye bbox.

    Uses a gradient from #CC2200 (dark) to #FF4444 (bright) along radial
    vein lines drawn inside the eye ellipse. Intensity scales alpha + count.
    """
    if not _safe_import_pil() or not eye_boxes:
        return image_b64
    try:
        import random
        from PIL import Image, ImageDraw, ImageFilter

        intensity = max(0.1, min(intensity, 1.0))
        base = _b64_to_pil(image_b64).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        rng = random.Random(42)  # deterministic

        for bb in eye_boxes:
            if bb.w < 10 or bb.h < 8:
                continue
            cx, cy = bb.cx, bb.cy
            rx = int(bb.w * 0.50)
            ry = int(bb.h * 0.45)
            n_veins = max(3, int(8 * intensity))

            for _ in range(n_veins):
                # Start at a random edge point of the eye ellipse.
                theta = rng.uniform(0, 2 * math.pi)
                sx = int(cx + math.cos(theta) * rx)
                sy = int(cy + math.sin(theta) * ry)

                # End somewhat toward the iris center (partial inward reach).
                reach = rng.uniform(0.40, 0.85)
                ex = int(cx + math.cos(theta) * rx * (1 - reach))
                ey = int(cy + math.sin(theta) * ry * (1 - reach))

                # Gradient segments from #CC2200 to #FF4444.
                steps = 6
                for step in range(steps):
                    t = step / max(1, steps - 1)
                    r = int(0xCC + (0xFF - 0xCC) * t)
                    g = int(0x22 + (0x44 - 0x22) * t)
                    b = int(0x00 + (0x44 - 0x00) * t)
                    a = int(intensity * 180 * (1 - t * 0.3))
                    px = int(sx + (ex - sx) * (step / steps))
                    py = int(sy + (ey - sy) * (step / steps))
                    nx = int(sx + (ex - sx) * ((step + 1) / steps))
                    ny = int(sy + (ey - sy) * ((step + 1) / steps))
                    draw.line([(px, py), (nx, ny)], fill=(r, g, b, a), width=1)

        # Slight blur to make veins sit in the skin.
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=0.6))
        merged = Image.alpha_composite(base, overlay)
        return _pil_to_b64(merged)
    except Exception as e:
        logger.warning("[LayerPainter] layer4b_bloodshot failed: %s", e)
        return image_b64


# ── Layer 5: vision eye-state classifier ─────────────────────────────

_EYE_STATE_PROMPT = """\
You are an anime reference checker. Look at the image below and answer \
STRICTLY in JSON:

{{
  "detected_state": "<one of: open, half_open, closed, rolled_back, rolled_up, \
                    bloodshot, crossed, glowing, unknown>",
  "confidence": <float 0.0-1.0>,
  "notes": "<one short sentence>"
}}

The user requested this eye state: "{requested}".
"""


def classify_eye_state(
    image_b64: str,
    requested_state: str = "open",
    *,
    vision_model: str = "gemini-2.0-flash",
) -> EyeStateReport:
    """Use Gemini (or OpenAI as fallback) to classify the eye state of
    the final image. Returns an ``EyeStateReport`` — never raises.
    """
    report = EyeStateReport(requested_state=requested_state or "open")

    from ._gemini_pool import get_active_key as _gp_get, mark_exhausted as _gp_mark, is_quota_error as _gp_is_quota
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if not _gp_get() and not openai_key:
        report.skipped = True
        report.notes = "no vision API key available"
        return report

    prompt = _EYE_STATE_PROMPT.format(requested=requested_state or "open")

    # Prefer Gemini (cheaper, multimodal). Rotate on 429.
    while True:
        gemini_key = _gp_get()
        if not gemini_key:
            break
        parsed, quota_err = _classify_via_gemini(image_b64, prompt, gemini_key, vision_model)
        if parsed is not None:
            _fill_report(report, parsed, requested_state)
            return report
        if quota_err:
            _gp_mark(gemini_key, "429 in eye classifier")
            continue
        break

    if openai_key:
        parsed = _classify_via_openai(image_b64, prompt, openai_key)
        if parsed is not None:
            _fill_report(report, parsed, requested_state)
            return report

    report.skipped = True
    report.notes = "all vision providers failed"
    return report


def _fill_report(report: EyeStateReport, data: dict, requested: str) -> None:
    report.detected_state = str(data.get("detected_state", "unknown")).lower()
    try:
        report.confidence = float(data.get("confidence", 0.0))
    except Exception:
        report.confidence = 0.0
    report.notes = str(data.get("notes", ""))[:200]
    report.matches_request = _states_match(report.detected_state, requested)


def _states_match(detected: str, requested: str) -> bool:
    if not requested or requested == "unknown":
        return True
    r = requested.lower().strip()
    d = detected.lower().strip()
    if r == d:
        return True
    # Loose equivalence groups.
    synonyms = {
        "rolled_back": {"rolled_back", "rolled_up"},
        "rolled_up":   {"rolled_back", "rolled_up"},
        "open":        {"open", "half_open"},
    }
    group = synonyms.get(r, {r})
    return d in group


def _classify_via_gemini(
    image_b64: str, prompt: str, api_key: str, model: str,
) -> tuple[Optional[dict], bool]:
    """Returns (parsed_json or None, quota_error_flag)."""
    import httpx
    from ._gemini_pool import is_quota_error
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent",
            headers={"X-goog-api-key": api_key},
            json={
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/png",
                                         "data": image_b64}},
                    ],
                }],
                "generationConfig": {
                    "temperature": 0.0, "maxOutputTokens": 400,
                    "responseMimeType": "application/json",
                },
            },
            timeout=20,
        )
        resp.raise_for_status()
        text = (
            resp.json().get("candidates", [{}])[0]
            .get("content", {}).get("parts", [{}])[0].get("text", "{}")
        )
        m = re.search(r"\{.*\}", text, re.DOTALL)
        return (json.loads(m.group(0)) if m else None), False
    except Exception as e:
        if is_quota_error(e):
            return None, True
        logger.debug("[LayerPainter] Gemini eye classifier failed: %s", e)
        return None, False


def _classify_via_openai(
    image_b64: str, prompt: str, api_key: str,
) -> Optional[dict]:
    import httpx
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
                    ],
                }],
                "response_format": {"type": "json_object"},
            },
            timeout=25,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{.*\}", text, re.DOTALL)
        return json.loads(m.group(0)) if m else None
    except Exception as e:
        logger.debug("[LayerPainter] OpenAI eye classifier failed: %s", e)
        return None


# ── Orchestration helper ─────────────────────────────────────────────

@dataclass
class LayerPainterResult:
    """Returned by ``apply_artistic_layers``."""
    final_b64: str
    shadow_applied: bool = False
    highlight_applied: bool = False
    eye_rolling_applied: bool = False
    bloodshot_applied: bool = False
    eye_state: Optional[EyeStateReport] = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "shadow_applied": self.shadow_applied,
            "highlight_applied": self.highlight_applied,
            "eye_rolling_applied": self.eye_rolling_applied,
            "bloodshot_applied": self.bloodshot_applied,
            "eye_state": self.eye_state.to_dict() if self.eye_state else None,
            "notes": list(self.notes),
        }


def apply_artistic_layers(
    image_b64: str,
    *,
    face_bbox: Optional[EyeBBox] = None,
    eye_boxes: Optional[list[EyeBBox]] = None,
    eye_fx: Optional[EyeFXSpec] = None,
    requested_eye_state: str = "open",
    do_shadow: bool = True,
    do_highlight: bool = True,
    do_classify: bool = True,
) -> LayerPainterResult:
    """Run the full Layer 2 → 5 pipeline in order.

    Every step is defensive: if a layer can't run (missing input, PIL not
    installed, provider failed), it's skipped and the pass-through image
    is forwarded to the next layer.
    """
    result = LayerPainterResult(final_b64=image_b64)
    current = image_b64

    # Layer 2: shadow
    if do_shadow and face_bbox is not None:
        new_img = layer2_shadow(current, face_bbox)
        if new_img != current:
            result.shadow_applied = True
            current = new_img

    # Layer 3: highlight
    if do_highlight and face_bbox is not None:
        new_img = layer3_highlight(current, face_bbox)
        if new_img != current:
            result.highlight_applied = True
            current = new_img

    # Layer 4: eye FX
    fx = eye_fx or EyeFXSpec()
    if fx.active() and eye_boxes:
        if fx.eye_rolling:
            new_img = layer4a_eye_rolling(
                current, eye_boxes,
                direction=fx.rolling_direction,
                strength=fx.rolling_strength,
            )
            if new_img != current:
                result.eye_rolling_applied = True
                current = new_img
        if fx.bloodshot:
            new_img = layer4b_bloodshot(current, eye_boxes, fx.bloodshot_intensity)
            if new_img != current:
                result.bloodshot_applied = True
                current = new_img

    # Layer 5: classifier
    if do_classify:
        try:
            result.eye_state = classify_eye_state(current, requested_eye_state)
            if not result.eye_state.skipped and not result.eye_state.matches_request:
                result.notes.append(
                    f"eye_state mismatch: got {result.eye_state.detected_state}, "
                    f"requested {requested_eye_state}"
                )
        except Exception as e:
            logger.warning("[LayerPainter] classify_eye_state crashed: %s", e)

    result.final_b64 = current
    return result


__all__ = [
    "EyeBBox",
    "EyeFXSpec",
    "EyeStateReport",
    "LayerPainterResult",
    "apply_artistic_layers",
    "classify_eye_state",
    "layer2_shadow",
    "layer3_highlight",
    "layer4a_eye_rolling",
    "layer4b_bloodshot",
]
