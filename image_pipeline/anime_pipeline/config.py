"""
image_pipeline.anime_pipeline.config — Pipeline-specific configuration.

Reads configs/anime_pipeline.yaml at import time.
Falls back to sensible defaults if the YAML is missing.
"""

from __future__ import annotations

import enum
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_THIS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _THIS_DIR.parent.parent
_CONFIG_PATH = _REPO_ROOT / "configs" / "anime_pipeline.yaml"


@dataclass
class ModelConfig:
    checkpoint: str = ""
    model_type: str = "sdxl"
    sampler: str = "dpmpp_2m_sde"
    scheduler: str = "karras"
    steps: int = 30
    cfg: float = 5.0
    clip_skip: int = 1
    vae: str = ""
    denoise_strength: float = 1.0


class VRAMProfile(str, enum.Enum):
    """VRAM management profile — controls resolution caps, model loading, and VAE offload."""
    AUTO = "auto"              # detect from system info or default to normalvram
    NORMALVRAM = "normalvram"  # 12 GB — SDXL-class, sequential model loading
    LOWVRAM = "lowvram"        # 8 GB — aggressive caps, CPU VAE, fewer steps


@dataclass
class VRAMProfileConfig:
    """Resolved VRAM limits for a given profile."""
    profile: VRAMProfile = VRAMProfile.NORMALVRAM
    max_resolution: int = 1216
    step_cap: int = 35
    max_controlnet_layers: int = 2
    cpu_vae_offload: bool = False
    disable_previews: bool = False
    unload_models_between_passes: bool = True
    upscale_tile_size: int = 512
    max_upscale_factor: float = 2.0
    oom_retry_enabled: bool = True
    oom_resolution_step_down: int = 128
    oom_max_retries: int = 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile.value,
            "max_resolution": self.max_resolution,
            "step_cap": self.step_cap,
            "max_controlnet_layers": self.max_controlnet_layers,
            "cpu_vae_offload": self.cpu_vae_offload,
            "disable_previews": self.disable_previews,
            "unload_models_between_passes": self.unload_models_between_passes,
            "upscale_tile_size": self.upscale_tile_size,
            "max_upscale_factor": self.max_upscale_factor,
            "oom_retry_enabled": self.oom_retry_enabled,
            "oom_resolution_step_down": self.oom_resolution_step_down,
            "oom_max_retries": self.oom_max_retries,
        }


_VRAM_PROFILE_DEFAULTS: dict[VRAMProfile, dict[str, Any]] = {
    VRAMProfile.NORMALVRAM: {
        "max_resolution": 1216,
        "step_cap": 35,
        "max_controlnet_layers": 2,
        "cpu_vae_offload": False,
        "disable_previews": False,
        "unload_models_between_passes": True,
        "upscale_tile_size": 512,
        "max_upscale_factor": 2.0,
        "oom_retry_enabled": True,
        "oom_resolution_step_down": 128,
        "oom_max_retries": 2,
    },
    VRAMProfile.LOWVRAM: {
        "max_resolution": 1024,
        "step_cap": 25,
        "max_controlnet_layers": 1,
        "cpu_vae_offload": True,
        "disable_previews": True,
        "unload_models_between_passes": True,
        "upscale_tile_size": 384,
        "max_upscale_factor": 1.5,
        "oom_retry_enabled": True,
        "oom_resolution_step_down": 128,
        "oom_max_retries": 3,
    },
}


def resolve_vram_profile(profile: VRAMProfile | str = VRAMProfile.AUTO) -> VRAMProfileConfig:
    """Resolve a VRAMProfile enum (or string) to concrete limits.

    For ``auto``, reads ``ANIME_PIPELINE_VRAM_PROFILE`` env var, then
    falls back to ``normalvram``.
    """
    if isinstance(profile, str):
        try:
            profile = VRAMProfile(profile.lower())
        except ValueError:
            logger.warning("[VRAMProfile] Unknown profile '%s', using normalvram", profile)
            profile = VRAMProfile.NORMALVRAM

    if profile == VRAMProfile.AUTO:
        env_val = os.getenv("ANIME_PIPELINE_VRAM_PROFILE", "normalvram").lower()
        try:
            profile = VRAMProfile(env_val)
        except ValueError:
            profile = VRAMProfile.NORMALVRAM
        # auto can't remain auto after resolution
        if profile == VRAMProfile.AUTO:
            profile = VRAMProfile.NORMALVRAM

    defaults = _VRAM_PROFILE_DEFAULTS.get(
        profile, _VRAM_PROFILE_DEFAULTS[VRAMProfile.NORMALVRAM],
    )
    return VRAMProfileConfig(profile=profile, **defaults)


class BeautyStrength(str, enum.Enum):
    """Preset intensity for the beauty pass."""
    SUBTLE = "subtle"          # denoise 0.15–0.20, minimal redraw
    BALANCED = "balanced"      # denoise 0.25–0.35, default
    AGGRESSIVE = "aggressive"  # denoise 0.40–0.55, heavy detail add


_BEAUTY_PRESETS: dict[BeautyStrength, dict] = {
    BeautyStrength.SUBTLE:     {"denoise": 0.18, "cfg": 5.0, "steps": 25},
    BeautyStrength.BALANCED:   {"denoise": 0.30, "cfg": 5.5, "steps": 28},
    BeautyStrength.AGGRESSIVE: {"denoise": 0.48, "cfg": 6.0, "steps": 30},
}


def get_beauty_preset(strength: BeautyStrength | str) -> dict:
    """Return denoise/cfg/steps for a beauty strength preset."""
    if isinstance(strength, str):
        strength = BeautyStrength(strength)
    return dict(_BEAUTY_PRESETS[strength])


@dataclass
class StructureLayerConfig:
    layer_type: str = "lineart_anime"
    preprocessor: str = "AnimeLineArtPreprocessor"
    controlnet_model: str = ""
    strength: float = 0.8
    start_percent: float = 0.0
    end_percent: float = 0.8
    priority: int = 1
    optional: bool = True  # skip gracefully if preprocessor node not installed
    enabled: bool = True


@dataclass
class AnimePipelineConfig:
    """Parsed config from anime_pipeline.yaml with env-var overrides."""

    # VRAM profile
    vram_profile: VRAMProfile = VRAMProfile.AUTO
    vram: VRAMProfileConfig = field(default_factory=VRAMProfileConfig)

    # Models
    composition_model: ModelConfig = field(default_factory=ModelConfig)
    beauty_model: ModelConfig = field(default_factory=ModelConfig)
    final_model: ModelConfig = field(default_factory=ModelConfig)
    beauty_strength: BeautyStrength = BeautyStrength.BALANCED
    default_loras: list[dict[str, Any]] = field(default_factory=list)
    upscale_model: str = "RealESRGAN_x4plus_anime_6B"
    upscale_fallback_model: str = "RealESRGAN_x4plus"
    upscale_factor: int = 2
    upscale_tile_size: int = 512
    upscale_denoise: float = 0.2

    # Resolutions
    portrait_res: tuple[int, int] = (832, 1216)
    landscape_res: tuple[int, int] = (1216, 832)
    square_res: tuple[int, int] = (1024, 1024)

    # Structure lock
    structure_layers: list[StructureLayerConfig] = field(default_factory=list)
    max_simultaneous_layers: int = 2

    # Detection inpaint (ADetailer-style)
    detection_inpaint_enabled: bool = True
    detection_inpaint_layers: list[dict[str, Any]] = field(default_factory=list)

    # Vision
    vision_model_priority: list[str] = field(
        default_factory=lambda: ["gemini-2.0-flash", "gpt-4o-mini", "gpt-4o"]
    )
    vision_max_tokens: int = 500
    vision_temperature: float = 0.2

    # Critique
    quality_threshold: float = 0.80
    max_refine_rounds: int = 4
    critique_dimensions: list[str] = field(
        default_factory=lambda: [
            "instruction_adherence", "detail_handling", "identity_consistency"
        ]
    )
    return_best_on_fail: bool = True

    # Refine loop
    refine_score_threshold: float = 8.0
    refine_denoise_step_up: float = 0.05
    refine_denoise_step_down: float = 0.03
    refine_denoise_floor: float = 0.12
    refine_denoise_ceiling: float = 0.55
    refine_control_boost: float = 0.10
    refine_control_reduce: float = 0.05
    refine_dimension_thresholds: dict[str, int] = field(
        default_factory=lambda: {
            "anatomy": 6, "face_symmetry": 7, "eye_consistency": 7,
            "hand_quality": 5, "clothing_consistency": 6,
            "style_drift": 6, "color_drift": 6, "background_clutter": 5,
            "missing_accessories": 5, "pose_drift": 6,
        }
    )
    refine_artifact_accumulation_limit: int = 8

    # Eye-refine micro workflow
    eye_refine_enabled: bool = True
    eye_refine_trigger_score: int = 8
    eye_refine_max_steps: int = 3

    # Pipeline behavior
    timeouts: dict[str, int] = field(default_factory=dict)
    save_intermediates: bool = True
    intermediate_dir: str = "storage/intermediate"
    stream_events: bool = True
    unload_between_passes: bool = True

    # Prompts
    quality_prefix: str = "masterpiece, best quality, very aesthetic, absurdres, highly detailed, vivid colors"
    negative_base: str = (
        "lowres, bad anatomy, bad hands, text, error, missing fingers, "
        "extra digit, fewer digits, cropped, worst quality, low quality, "
        "normal quality, jpeg artifacts, signature, watermark, username, blurry, "
        "artist name, bad proportions, deformed, disfigured, ugly, "
        "monochrome, greyscale, grayscale, sketch, lineart, black_and_white, "
        "logo, copyright, credit, stamp, title_text, author_name, english_text, "
        "twitter_username, instagram_username, url, website"
    )
    style_negatives: dict[str, str] = field(default_factory=dict)

    # ComfyUI
    comfyui_url: str = ""


def load_config() -> AnimePipelineConfig:
    """Load config from YAML + env overrides."""
    cfg = AnimePipelineConfig()

    # Load YAML
    raw = _read_yaml()
    if raw:
        _apply_yaml(cfg, raw)

    # Env overrides (highest priority)
    _apply_env(cfg)

    # Resolve VRAM profile to concrete limits
    cfg.vram = resolve_vram_profile(cfg.vram_profile)

    logger.info(
        "[AnimePipeline] Config loaded: composition=%s, beauty=%s, threshold=%.2f, "
        "vram_profile=%s (max_res=%d, step_cap=%d, cpu_vae=%s)",
        cfg.composition_model.checkpoint,
        cfg.beauty_model.checkpoint,
        cfg.quality_threshold,
        cfg.vram.profile.value,
        cfg.vram.max_resolution,
        cfg.vram.step_cap,
        cfg.vram.cpu_vae_offload,
    )
    return cfg


def _read_yaml() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        logger.warning("[AnimePipeline] Config not found: %s", _CONFIG_PATH)
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("[AnimePipeline] Failed to parse config: %s", e)
        return {}


def _apply_yaml(cfg: AnimePipelineConfig, raw: dict) -> None:
    """Apply YAML values to config."""

    # VRAM profile
    vram_raw = raw.get("vram", {})
    if vram_raw:
        profile_str = vram_raw.get("profile", "auto")
        try:
            cfg.vram_profile = VRAMProfile(profile_str.lower())
        except ValueError:
            cfg.vram_profile = VRAMProfile.AUTO

    models = raw.get("models", {})

    # Composition model
    comp = models.get("composition", {})
    cfg.composition_model = ModelConfig(
        checkpoint=comp.get("checkpoint", "animagine-xl-4.0-opt.safetensors"),
        model_type=comp.get("type", "sdxl"),
        sampler=comp.get("sampler", "dpmpp_2m_sde"),
        scheduler=comp.get("scheduler", "karras"),
        steps=int(comp.get("steps", 30)),
        cfg=float(comp.get("cfg", 5.0)),
        clip_skip=int(comp.get("clip_skip", 1)),
        vae=comp.get("vae", "") or "",
    )

    # Beauty model
    beauty = models.get("beauty", {})
    cfg.beauty_model = ModelConfig(
        checkpoint=beauty.get("checkpoint", "animagine-xl-4.0-opt.safetensors"),
        model_type=beauty.get("type", "sdxl"),
        sampler=beauty.get("sampler", "dpmpp_2m_sde"),
        scheduler=beauty.get("scheduler", "karras"),
        steps=int(beauty.get("steps", 25)),
        cfg=float(beauty.get("cfg", 4.5)),
        clip_skip=int(beauty.get("clip_skip", 1)),
        vae=beauty.get("vae", "") or "",
        denoise_strength=float(beauty.get("denoise_strength", 0.45)),
    )

    # Final model (defaults to beauty model when absent)
    final_raw = models.get("final", {})
    if final_raw:
        cfg.final_model = ModelConfig(
            checkpoint=final_raw.get("checkpoint", cfg.beauty_model.checkpoint),
            model_type=final_raw.get("type", "sdxl"),
            sampler=final_raw.get("sampler", cfg.beauty_model.sampler),
            scheduler=final_raw.get("scheduler", cfg.beauty_model.scheduler),
            steps=int(final_raw.get("steps", cfg.beauty_model.steps)),
            cfg=float(final_raw.get("cfg", cfg.beauty_model.cfg)),
            clip_skip=int(final_raw.get("clip_skip", cfg.beauty_model.clip_skip)),
            vae=final_raw.get("vae", "") or "",
            denoise_strength=float(final_raw.get("denoise_strength", cfg.beauty_model.denoise_strength)),
        )
    else:
        # Fall back to beauty_model when no dedicated final slot
        cfg.final_model = ModelConfig(
            checkpoint=cfg.beauty_model.checkpoint,
            model_type=cfg.beauty_model.model_type,
            sampler=cfg.beauty_model.sampler,
            scheduler=cfg.beauty_model.scheduler,
            steps=cfg.beauty_model.steps,
            cfg=cfg.beauty_model.cfg,
            clip_skip=cfg.beauty_model.clip_skip,
            vae=cfg.beauty_model.vae,
            denoise_strength=cfg.beauty_model.denoise_strength,
        )

    # Beauty strength preset
    strength_str = raw.get("beauty_pass", {}).get("strength", "balanced")
    try:
        cfg.beauty_strength = BeautyStrength(strength_str)
    except ValueError:
        cfg.beauty_strength = BeautyStrength.BALANCED

    # Upscale
    upscale = models.get("upscale", {})
    cfg.upscale_model = upscale.get("model", cfg.upscale_model)
    cfg.upscale_fallback_model = upscale.get("fallback_model", cfg.upscale_fallback_model)
    cfg.upscale_factor = int(upscale.get("scale_factor", cfg.upscale_factor))

    # Optional LoRA stack (applied on composition/cleanup/beauty passes)
    loras = models.get("loras", {})
    defaults = loras.get("defaults", [])
    if isinstance(defaults, list):
        cfg.default_loras = [x for x in defaults if isinstance(x, dict)]

    # Resolutions
    res = raw.get("resolutions", {})
    p = res.get("portrait", {})
    if p:
        cfg.portrait_res = (int(p.get("width", 832)), int(p.get("height", 1216)))
    l_ = res.get("landscape", {})
    if l_:
        cfg.landscape_res = (int(l_.get("width", 1216)), int(l_.get("height", 832)))
    s = res.get("square", {})
    if s:
        cfg.square_res = (int(s.get("width", 1024)), int(s.get("height", 1024)))

    # Structure lock
    sl = raw.get("structure_lock", {})
    layers_raw = sl.get("layers", [])
    cfg.structure_layers = []
    for layer in layers_raw:
        cfg.structure_layers.append(StructureLayerConfig(
            layer_type=layer.get("type", "lineart_anime"),
            preprocessor=layer.get("preprocessor", ""),
            controlnet_model=layer.get("controlnet_model", ""),
            strength=float(layer.get("strength", 0.8)),
            start_percent=float(layer.get("start_percent", 0.0)),
            end_percent=float(layer.get("end_percent", 0.8)),
            priority=int(layer.get("priority", 1)),
            optional=bool(layer.get("optional", False)),
            enabled=bool(layer.get("enabled", True)),
        ))
    cfg.max_simultaneous_layers = int(sl.get("max_simultaneous", 2))

    # Detection inpaint (ADetailer-style)
    det = raw.get("detection_inpaint", {})
    cfg.detection_inpaint_enabled = bool(det.get("enabled", True))
    det_layers = det.get("layers", [])
    if isinstance(det_layers, list):
        cfg.detection_inpaint_layers = [
            x for x in det_layers if isinstance(x, dict)
        ]

    # Vision
    vision = raw.get("vision", {})
    cfg.vision_model_priority = vision.get("model_priority", cfg.vision_model_priority)
    cfg.vision_max_tokens = int(vision.get("max_tokens", 500))
    cfg.vision_temperature = float(vision.get("temperature", 0.2))

    # Critique
    critique = raw.get("critique", {})
    cfg.quality_threshold = float(critique.get("quality_threshold", 0.70))
    cfg.max_refine_rounds = int(critique.get("max_refine_rounds", 2))
    cfg.critique_dimensions = critique.get("dimensions", cfg.critique_dimensions)
    cfg.return_best_on_fail = bool(critique.get("return_best_on_fail", True))

    # Refine loop
    refine = raw.get("refine", {})
    cfg.refine_score_threshold = float(refine.get("score_threshold", 7.0))
    cfg.refine_denoise_step_up = float(refine.get("denoise_step_up", 0.05))
    cfg.refine_denoise_step_down = float(refine.get("denoise_step_down", 0.03))
    cfg.refine_denoise_floor = float(refine.get("denoise_floor", 0.12))
    cfg.refine_denoise_ceiling = float(refine.get("denoise_ceiling", 0.55))
    cfg.refine_control_boost = float(refine.get("control_boost", 0.10))
    cfg.refine_control_reduce = float(refine.get("control_reduce", 0.05))
    dim_thresh = refine.get("dimension_thresholds", {})
    if dim_thresh:
        cfg.refine_dimension_thresholds.update(
            {k: int(v) for k, v in dim_thresh.items()}
        )
    acc_limit = refine.get("artifact_accumulation_limit")
    if acc_limit is not None:
        cfg.refine_artifact_accumulation_limit = int(acc_limit)
    max_r = refine.get("max_rounds")
    if max_r is not None:
        cfg.max_refine_rounds = int(max_r)

    # Eye-refine micro workflow
    eye_refine = raw.get("eye_refine", {})
    cfg.eye_refine_enabled = bool(
        eye_refine.get("enabled", cfg.eye_refine_enabled)
    )
    cfg.eye_refine_trigger_score = int(
        eye_refine.get("trigger_score", cfg.eye_refine_trigger_score)
    )
    cfg.eye_refine_max_steps = max(
        1,
        min(
            3,
            int(eye_refine.get("max_steps", cfg.eye_refine_max_steps)),
        ),
    )

    # Pipeline
    pipeline = raw.get("pipeline", {})
    cfg.timeouts = pipeline.get("timeouts", {})
    cfg.save_intermediates = bool(pipeline.get("save_intermediates", True))
    cfg.intermediate_dir = pipeline.get("intermediate_dir", cfg.intermediate_dir)
    cfg.stream_events = bool(pipeline.get("stream_events", True))
    cfg.unload_between_passes = bool(pipeline.get("unload_between_passes", True))

    # Prompts
    prompts = raw.get("prompts", {})
    cfg.quality_prefix = prompts.get("quality_prefix", cfg.quality_prefix)
    cfg.negative_base = prompts.get("negative_base", cfg.negative_base)
    cfg.style_negatives = prompts.get("style_negatives", {})


def _apply_env(cfg: AnimePipelineConfig) -> None:
    """Apply environment variable overrides."""
    # VRAM profile override (highest priority)
    vram_env = os.getenv("ANIME_PIPELINE_VRAM_PROFILE")
    if vram_env:
        try:
            cfg.vram_profile = VRAMProfile(vram_env.lower())
        except ValueError:
            pass

    comp = os.getenv("ANIME_PIPELINE_COMPOSITION_MODEL")
    if comp:
        cfg.composition_model.checkpoint = comp

    beauty = os.getenv("ANIME_PIPELINE_BEAUTY_MODEL")
    if beauty:
        cfg.beauty_model.checkpoint = beauty

    final = os.getenv("ANIME_PIPELINE_FINAL_MODEL")
    if final:
        cfg.final_model.checkpoint = final

    strength_env = os.getenv("ANIME_PIPELINE_BEAUTY_STRENGTH")
    if strength_env:
        try:
            cfg.beauty_strength = BeautyStrength(strength_env.lower())
        except ValueError:
            pass

    threshold = os.getenv("ANIME_PIPELINE_QUALITY_THRESHOLD")
    if threshold:
        cfg.quality_threshold = float(threshold)

    max_rounds = os.getenv("ANIME_PIPELINE_MAX_REFINE_ROUNDS")
    if max_rounds:
        cfg.max_refine_rounds = int(max_rounds)

    url = os.getenv("ANIME_PIPELINE_COMFYUI_URL") or os.getenv("COMFYUI_URL")
    if url:
        cfg.comfyui_url = url

    # Per-layer control overrides: ANIME_PIPELINE_CONTROL_{TYPE}_ENABLED / _STRENGTH
    for lc in cfg.structure_layers:
        tag = lc.layer_type.upper()
        env_enabled = os.getenv(f"ANIME_PIPELINE_CONTROL_{tag}_ENABLED")
        if env_enabled is not None:
            lc.enabled = env_enabled.lower() in ("true", "1", "yes")
        env_strength = os.getenv(f"ANIME_PIPELINE_CONTROL_{tag}_STRENGTH")
        if env_strength is not None:
            lc.strength = float(env_strength)
