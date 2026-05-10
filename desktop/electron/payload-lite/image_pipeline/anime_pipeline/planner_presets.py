"""
image_pipeline.anime_pipeline.planner_presets — Style presets for the layer planner.

Each preset adjusts pass parameters (steps, denoise, CFG, prompts, control strength)
to favor a particular balance of quality, speed, reference fidelity, or background detail.

Presets are applied *after* the base plan is built, overriding specific fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PassOverride:
    """Per-pass parameter overrides applied by a preset."""
    steps: Optional[int] = None
    cfg: Optional[float] = None
    denoise: Optional[float] = None
    sampler: Optional[str] = None
    scheduler: Optional[str] = None
    prompt_prefix: str = ""             # prepended to positive prompt
    prompt_suffix: str = ""             # appended to positive prompt
    negative_extra: str = ""            # appended to negative prompt
    controlnet_strength_scale: float = 1.0  # multiplied onto control strengths


@dataclass
class PlannerPreset:
    """A named style preset that tweaks planner output."""
    name: str = ""
    description: str = ""

    # Global overrides
    quality_prefix: Optional[str] = None        # replaces config quality prefix
    negative_extra: str = ""                     # appended to all negatives
    skip_upscale: bool = False
    skip_cleanup: bool = False

    # Per-pass overrides (keyed by pass_name)
    pass_overrides: dict[str, PassOverride] = field(default_factory=dict)

    # VRAM profile adjustments
    vram_step_cap: Optional[int] = None         # clamp max steps when VRAM limited
    vram_resolution_cap: Optional[int] = None   # clamp max dimension

    # Reference preservation
    reference_weight: float = 1.0       # 1.0 = normal, >1 = stricter identity
    identity_emphasis: float = 1.0      # multiplied onto identity anchor emphasis


# ═══════════════════════════════════════════════════════════════════════
# Built-in presets
# ═══════════════════════════════════════════════════════════════════════

ANIME_QUALITY = PlannerPreset(
    name="anime_quality",
    description="High-quality anime with full pipeline. Best results, slower.",
    quality_prefix="masterpiece, best quality, very aesthetic, absurdres",
    pass_overrides={
        "composition": PassOverride(
            steps=30,
            cfg=5.0,
            denoise=1.0,
            sampler="dpmpp_2m_sde",
            scheduler="karras",
        ),
        "cleanup": PassOverride(
            steps=24,
            cfg=5.5,
            denoise=0.35,
            controlnet_strength_scale=1.0,
        ),
        "beauty": PassOverride(
            steps=28,
            cfg=4.5,
            denoise=0.45,
            prompt_prefix="highly detailed, sharp focus",
            controlnet_strength_scale=1.0,
        ),
    },
)

ANIME_SPEED = PlannerPreset(
    name="anime_speed",
    description="Fast anime generation. Fewer steps, skip cleanup, smaller resolution.",
    quality_prefix="best quality, anime",
    skip_cleanup=True,
    skip_upscale=True,
    vram_step_cap=20,
    pass_overrides={
        "composition": PassOverride(
            steps=18,
            cfg=5.0,
            denoise=1.0,
            sampler="euler_a",
            scheduler="normal",
        ),
        "beauty": PassOverride(
            steps=16,
            cfg=4.5,
            denoise=0.40,
            controlnet_strength_scale=0.9,
        ),
    },
)

ANIME_REFERENCE_STRICT = PlannerPreset(
    name="anime_reference_strict",
    description="Strict reference preservation. Higher control strength, lower denoise.",
    quality_prefix="masterpiece, best quality, very aesthetic, absurdres",
    reference_weight=1.5,
    identity_emphasis=1.5,
    pass_overrides={
        "composition": PassOverride(
            steps=30,
            cfg=5.5,
            denoise=0.85,
            prompt_suffix="consistent character design, reference match",
        ),
        "cleanup": PassOverride(
            steps=22,
            cfg=5.5,
            denoise=0.28,
            controlnet_strength_scale=1.2,
        ),
        "beauty": PassOverride(
            steps=28,
            cfg=5.0,
            denoise=0.35,
            controlnet_strength_scale=1.3,
            prompt_suffix="identity preserved, same character",
        ),
    },
)

ANIME_BACKGROUND_HEAVY = PlannerPreset(
    name="anime_background_heavy",
    description="Emphasize detailed backgrounds. More composition steps, background-focused prompts.",
    quality_prefix="masterpiece, best quality, very aesthetic, absurdres, detailed background",
    negative_extra="simple background, plain background, white background",
    pass_overrides={
        "composition": PassOverride(
            steps=35,
            cfg=5.5,
            denoise=1.0,
            prompt_prefix="detailed environment, scenic composition",
            prompt_suffix="intricate background, atmospheric lighting",
        ),
        "cleanup": PassOverride(
            steps=26,
            cfg=6.0,
            denoise=0.38,
        ),
        "beauty": PassOverride(
            steps=30,
            cfg=5.0,
            denoise=0.45,
            prompt_prefix="environment detail, atmospheric perspective",
        ),
    },
)


# ═══════════════════════════════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════════════════════════════

PRESETS: dict[str, PlannerPreset] = {
    "anime_quality": ANIME_QUALITY,
    "anime_speed": ANIME_SPEED,
    "anime_reference_strict": ANIME_REFERENCE_STRICT,
    "anime_background_heavy": ANIME_BACKGROUND_HEAVY,
}


def get_preset(name: str) -> PlannerPreset:
    """Look up a preset by name. Returns anime_quality as default."""
    return PRESETS.get(name, ANIME_QUALITY)


def list_presets() -> list[str]:
    """Return all registered preset names."""
    return list(PRESETS.keys())
