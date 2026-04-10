"""
PromptBuilder
=============
Takes a SceneSpec and assembles the final provider-ready prompt string.

Responsibilities:
- Translate Vietnamese visual descriptions to English (rule-based, no LLM cost)
- Merge subject + background + lighting + mood + style + quality tags
- Append style preset strings from core/image_gen/enhancer.py STYLE_PRESETS
- Optionally call the existing PromptEnhancer (LLM) for fine-tuning
- Keep prompt under 220 tokens (models degrade beyond that)

The output of build() is the string that goes directly into
ImageGenerationRouter.generate(prompt=...).
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Import style presets from the existing enhancer module
# ─────────────────────────────────────────────────────────────────────

try:
    from core.image_gen.enhancer import STYLE_PRESETS
except ImportError:
    # Fallback: minimal inline copy so the module is self-contained
    STYLE_PRESETS: dict[str, str] = {
        "photorealistic": "photorealistic, DSLR quality, natural lighting, 8K resolution",
        "anime":          "anime art style, vibrant colors, clean linework, studio Ghibli inspired",
        "cinematic":      "cinematic composition, dramatic lighting, film grain, movie still",
        "watercolor":     "watercolor painting, soft washes, paper texture",
        "digital_art":    "digital art, artstation trending, concept art, highly detailed",
        "oil_painting":   "oil painting on canvas, rich impasto texture, classical composition",
        "pixel_art":      "pixel art, retro 16-bit style, limited color palette",
        "3d_render":      "3D render, octane render, ray tracing, physically based materials",
        "sketch":         "pencil sketch, detailed cross-hatching, graphite on paper",
        "minimalist":     "minimalist design, clean lines, simple shapes, modern aesthetic",
        "fantasy":        "fantasy art, magical atmosphere, ethereal glow, mythical",
        "noir":           "film noir style, high contrast, dramatic shadows, moody",
        "vaporwave":      "vaporwave aesthetic, pink and blue neon, retro 80s, glitch art",
        "studio_photo":   "professional studio photography, softbox lighting, clean background",
    }


# ─────────────────────────────────────────────────────────────────────
# Quality suffix table  (appended after the main prompt)
# ─────────────────────────────────────────────────────────────────────

_QUALITY_SUFFIX: dict[str, str] = {
    "quality": "highly detailed, sharp focus, 4K, masterpiece, award-winning",
    "fast":    "simple composition, clean, well-lit",
    "free":    "clean composition, good quality",
    "cheap":   "clean composition",
    "auto":    "highly detailed, sharp focus",
}

# Common low-quality negative terms always appended to negative prompt
_UNIVERSAL_NEGATIVE = (
    "blurry, low quality, pixelated, distorted, deformed, "
    "ugly, bad anatomy, watermark, signature, text"
)

# ─────────────────────────────────────────────────────────────────────
# Very basic VI→EN visual vocabulary (covers the most common subjects)
# No external dependency — intentionally simple and fast.
# ─────────────────────────────────────────────────────────────────────

_VI_TO_EN: list[tuple[str, str]] = [
    # Colors
    (r"\btóc hồng\b",        "pink hair"),
    (r"\btóc vàng\b",        "blonde hair"),
    (r"\btóc đen\b",         "black hair"),
    (r"\btóc trắng\b",       "white hair"),
    (r"\btóc xanh\b",        "blue hair"),
    (r"\btóc đỏ\b",          "red hair"),
    # Subjects
    (r"\bcô gái\b",          "girl"),
    (r"\bcậu bé\b|\bchàng trai\b", "young man"),
    (r"\bcon mèo\b",         "cat"),
    (r"\bcon chó\b",         "dog"),
    (r"\bcon rồng\b",        "dragon"),
    (r"\bcon ngựa\b",        "horse"),
    (r"\bcon thỏ\b",         "rabbit"),
    (r"\bcây\b",             "tree"),
    (r"\bhoa\b",             "flowers"),
    # Settings
    (r"\bthành phố\b",       "city"),
    (r"\bbiển\b|\bbãi biển\b", "beach"),
    (r"\bnúi\b",             "mountains"),
    (r"\brừng\b",            "forest"),
    (r"\bvũ trụ\b",          "outer space"),
    # Actions
    (r"\bngồi\b",            "sitting"),
    (r"\bđứng\b",            "standing"),
    (r"\bchạy\b",            "running"),
    (r"\bbay\b",             "flying"),
    (r"\bchiến đấu\b",       "fighting"),
    # Time / lighting words
    (r"\bánh trăng\b",       "moonlight"),
    (r"\bhoàng hôn\b",       "sunset"),
    (r"\bbình minh\b",       "sunrise"),
    (r"\bban đêm\b|\bđêm khuya\b", "late night"),
    (r"\bgiữa trưa\b",       "midday"),
    # Misc
    (r"\bkiếm\b",            "sword"),
    (r"\báo giáp\b",         "armor"),
    (r"\bcánh\b",            "wings"),
    (r"\blâu đài\b",         "castle"),
]


def _partial_translate_vi(text: str) -> str:
    """Apply rule-based VI→EN substitutions for common visual words."""
    for pattern, replacement in _VI_TO_EN:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


# ─────────────────────────────────────────────────────────────────────
# PromptBuilder
# ─────────────────────────────────────────────────────────────────────

class PromptBuilder:
    """
    Assembles a provider-ready prompt string from a SceneSpec.

    Optional LLM enhancement is wired through the existing PromptEnhancer
    so no new API integration is needed.
    """

    def __init__(self, use_llm_enhancer: bool = True):
        self._enhancer = None
        if use_llm_enhancer:
            self._enhancer = self._load_enhancer()

    def _load_enhancer(self):
        """Load the existing PromptEnhancer (best-effort)."""
        try:
            from core.image_gen.enhancer import create_enhancer
            return create_enhancer()
        except Exception as exc:
            logger.warning(f"[PromptBuilder] Enhancer unavailable: {exc}")
            return None

    def build(
        self,
        scene:            "SceneSpec",  # type: ignore[name-defined]
        language:         str  = "vi",
        original_message: str  = "",
        session_context:  str  = "",
    ) -> str:
        """
        Assemble the final positive prompt string from a SceneSpec.

        Order:
            subject → subject_attributes → action → background → lighting → mood
            → composition → camera → style preset → quality suffix
            → consistency anchor → extra_tags
            → (optional LLM polish)
        """
        parts: list[str] = []

        # ── 1. Subject ────────────────────────────────────────────────
        subject = scene.subject or original_message
        if language.startswith("vi"):
            subject = _partial_translate_vi(subject)
        if subject:
            parts.append(subject.strip())

        # ── 2. Subject attributes (pink hair, blue eyes, etc.) ────────
        if scene.subject_attributes:
            parts.extend(scene.subject_attributes)

        # ── 3. Action ─────────────────────────────────────────────────
        if scene.action:
            action = _partial_translate_vi(scene.action) if language.startswith("vi") else scene.action
            parts.append(action.strip())

        # ── 4. Background / environment ───────────────────────────────
        if scene.background:
            parts.append(scene.background)

        # ── 5. Lighting ───────────────────────────────────────────────
        if scene.lighting:
            parts.append(scene.lighting)

        # ── 6. Mood ───────────────────────────────────────────────────
        if scene.mood:
            parts.append(scene.mood)

        # ── 7. Composition (framing) ──────────────────────────────────
        if scene.composition:
            parts.append(scene.composition)

        # ── 8. Camera / lens ──────────────────────────────────────────
        if scene.camera:
            parts.append(scene.camera)

        # ── 9. Style preset string ────────────────────────────────────
        # Photorealistic override when wants_real_world_accuracy is set
        effective_style = scene.style
        if scene.wants_real_world_accuracy and not effective_style:
            effective_style = "photorealistic"
        if effective_style and effective_style in STYLE_PRESETS:
            parts.append(STYLE_PRESETS[effective_style])

        # ── 10. Quality suffix ────────────────────────────────────────
        quality_sfx = _QUALITY_SUFFIX.get(scene.quality_preset, _QUALITY_SUFFIX["auto"])
        parts.append(quality_sfx)

        # ── 11. Consistency anchor (for EDIT_FOLLOWUP) ────────────────
        if scene.wants_consistency_with_previous:
            parts.append(
                "maintain consistent character design, same character appearance as before"
            )

        # ── 12. Extra tags from SceneSpec ─────────────────────────────
        if scene.extra_tags:
            parts.extend(scene.extra_tags)

        # ── 13. Text overlay hint ─────────────────────────────────────
        if scene.wants_text_in_image:
            parts.append("crisp readable text, sharp typography")

        # ── 14. Assemble raw prompt ───────────────────────────────────
        raw_prompt = ", ".join(p.strip(", ") for p in parts if p.strip())
        raw_prompt = self._trim_to_budget(raw_prompt, max_words=220)

        # ── 15. Optional LLM polish ───────────────────────────────────
        if self._enhancer:
            try:
                enhanced = self._enhancer.enhance(
                    raw_prompt,
                    style_preset=effective_style,
                    context=session_context or None,
                )
                logger.debug(f"[PromptBuilder] LLM enhanced: {len(raw_prompt)} → {len(enhanced)} chars")
                return enhanced
            except Exception as exc:
                logger.warning(f"[PromptBuilder] LLM enhance failed, using rule-based: {exc}")

        return raw_prompt

    def build_for_edit(
        self,
        scene:           "SceneSpec",
        edit_ops:        list,       # list[EditOperation]
        previous_prompt: str  = "",
        language:        str  = "vi",
    ) -> str:
        """
        Build a short prompt optimised for img2img editing.

        Strategy: anchor → describe changes → lighting/background updates.
        Falls back to build() when there are no edit_ops.
        """
        if not edit_ops:
            return self.build(scene, language=language)

        change_parts: list[str] = []
        for op in edit_ops:
            t   = op.target or ""
            v   = op.new_value or ""
            mod = op.modifier or ""

            if op.operation == "add_text":
                change_parts.append(f"add text '{t}' overlaid on image")
            elif op.operation == "add":
                change_parts.append(f"add {t}")
            elif op.operation == "remove":
                change_parts.append(f"remove {t}")
            elif op.operation in ("change", "replace"):
                change_parts.append(f"change {t} to {v}" if v else f"change {t}")
            elif op.operation in ("modify", "modify_general"):
                change_parts.append(
                    f"make {t} {mod}" if t and t != "lighting/atmosphere" else f"overall {mod}"
                )
            elif op.operation == "keep":
                change_parts.append(f"keep {t} the same")

        anchor = ("maintain consistent character design, keep same character"
                  if scene.wants_consistency_with_previous
                  else "keep overall composition and character")

        parts = [anchor, ", ".join(change_parts)]
        if scene.lighting:
            parts.append(scene.lighting)
        if scene.background:
            parts.append(scene.background)
        if scene.extra_tags:
            parts.extend(scene.extra_tags)
        if scene.wants_text_in_image:
            parts.append("crisp readable text")

        return ", ".join(p.strip() for p in parts if p.strip())

    def build_negative(self, scene: "SceneSpec") -> str:  # type: ignore[name-defined]
        """
        Build the negative prompt string.

        Rules:
        - Always include universal low-quality negatives
        - Include style-conflict negatives from scene.negative_hints
        - Skip 'text, signature, watermark' when wants_text_in_image=True
          (adding those to the negative would prevent the desired text overlay)
        - Skip 'text' from universal when wants_text_in_image is set
        """
        parts = list(scene.negative_hints)

        if scene.wants_text_in_image:
            # Remove negative terms that would prevent text rendering
            universal = _UNIVERSAL_NEGATIVE
            for blocked in ("watermark,", "signature,", "text,"):
                universal = universal.replace(blocked, "").replace("  ", " ")
            parts.append(universal.strip(", ").strip())
        else:
            parts.append(_UNIVERSAL_NEGATIVE)

        # Style-specific negatives
        style = scene.style or ""
        if style == "anime":
            parts.append("realistic, photorealistic, photograph, 3d render")
        elif style == "photorealistic":
            parts.append("cartoon, anime style, illustration, painting, sketch")
        elif style == "sketch":
            parts.append("color, painted, photo, photorealistic")
        elif style == "pixel_art":
            parts.append("smooth gradients, photorealistic, blurry")
        elif style == "3d_render":
            parts.append("flat 2d, cartoon, anime, sketch")

        return ", ".join(p.strip().strip(",") for p in parts if p.strip())

    @staticmethod
    def _trim_to_budget(text: str, max_words: int) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        trimmed = " ".join(words[:max_words])
        # Don't cut in the middle of a tag — trim back to last comma
        last_comma = trimmed.rfind(",")
        if last_comma > len(trimmed) * 0.7:
            trimmed = trimmed[:last_comma]
        return trimmed.strip(", ")
