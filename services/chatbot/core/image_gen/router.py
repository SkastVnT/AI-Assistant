"""
ImageRouter â€” the brain of the image generation system.
Selects the optimal provider based on: quality preference, cost budget,
speed requirements, feature needs (i2i, inpaint), and provider availability.
"""

from __future__ import annotations

import os
import time
import random
import logging
from typing import Optional, Generator
from dataclasses import dataclass, field

from .providers.base import (
    BaseImageProvider, ImageRequest, ImageResult,
    ImageMode, ProviderTier, LoraSpec,
)
from .providers import (
    FalProvider, ReplicateProvider, BFLProvider,
    OpenAIImageProvider, ComfyUIProvider, TogetherProvider,
    StepFunProvider,
)
from .providers.fal_provider import FAL_COST
from .providers.replicate_provider import REPLICATE_COST
from .enhancer import PromptEnhancer, create_enhancer, STYLE_PRESETS
from .character_detector import CharacterDetector

logger = logging.getLogger(__name__)


class QualityMode:
    """User-facing quality selection."""
    AUTO    = "auto"       # Router decides optimal provider
    FAST    = "fast"       # Speed priority (klein-4b, schnell)
    QUALITY = "quality"    # Best quality (flux2-pro, grok-imagine)
    FREE    = "free"       # Local only (ComfyUI)
    CHEAP   = "cheap"      # Lowest cost cloud ($0.003/img)


@dataclass 
class ProviderConfig:
    """Holds initialized providers and their priority."""
    provider: BaseImageProvider
    priority: int = 0       # higher = preferred
    enabled: bool = True


class ImageGenerationRouter:
    """
    Central orchestrator for image generation.
    
    Features:
    - Auto-selects best provider based on request
    - Prompt enhancement via LLM
    - Fallback chain if primary fails
    - Cost tracking
    - Style presets
    """

    def __init__(self):
        self._providers: dict[str, ProviderConfig] = {}
        self._enhancer: Optional[PromptEnhancer] = None
        self._character_detector: Optional[CharacterDetector] = None
        self._total_cost: float = 0.0
        self._total_generations: int = 0
        self._init_providers()
        self._init_enhancer()
        self._init_character_detector()

    def _init_providers(self):
        """Initialize all available providers from environment."""
        
        # fal.ai
        fal_key = os.getenv("FAL_API_KEY", "")
        if fal_key:
            self._providers["fal"] = ProviderConfig(
                provider=FalProvider(api_key=fal_key),
                priority=90,
            )

        # Replicate
        rep_key = os.getenv("REPLICATE_API_TOKEN", "")
        if rep_key:
            self._providers["replicate"] = ProviderConfig(
                provider=ReplicateProvider(api_key=rep_key),
                priority=80,
            )

        # Black Forest Labs
        bfl_key = os.getenv("BFL_API_KEY", "")
        if bfl_key:
            bfl_base = os.getenv("BFL_BASE_URL", "https://api.bfl.ai/v1")
            self._providers["bfl"] = ProviderConfig(
                provider=BFLProvider(api_key=bfl_key, base_url=bfl_base),
                priority=85,
            )

        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            self._providers["openai"] = ProviderConfig(
                provider=OpenAIImageProvider(api_key=openai_key),
                priority=70,
            )

        # ComfyUI (local) — register when local GPU services are available
        comfyui_url = os.getenv("COMFYUI_URL", os.getenv("SD_API_URL", "http://127.0.0.1:8188"))
        self._providers["comfyui"] = ProviderConfig(
            provider=ComfyUIProvider(base_url=comfyui_url),
            priority=10,  # lowest priority unless explicitly requested or FREE mode
        )

        # Together.ai (free tier available)
        together_key = os.getenv("TOGETHER_API_KEY", "")
        if together_key:
            self._providers["together"] = ProviderConfig(
                provider=TogetherProvider(api_key=together_key),
                priority=60,
            )

        # StepFun (Step1X-Edit â€” best editing model)
        stepfun_key = os.getenv("STEPFUN_API_KEY", "")
        if stepfun_key:
            self._providers["stepfun"] = ProviderConfig(
                provider=StepFunProvider(api_key=stepfun_key),
                priority=75,  # high for editing tasks
            )

        available = [name for name, cfg in self._providers.items() if cfg.provider.is_available]
        logger.info(f"[ImageRouter] Initialized providers: {available}")

    def _init_enhancer(self):
        """Initialize prompt enhancer."""
        try:
            self._enhancer = create_enhancer()
            logger.info("[ImageRouter] Prompt enhancer initialized")
        except Exception as e:
            logger.warning(f"[ImageRouter] Enhancer init failed: {e}")

    def _init_character_detector(self):
        """Initialize character detector from LoRA catalog."""
        try:
            from config.model_presets import LORA_CATALOG
            self._character_detector = CharacterDetector(LORA_CATALOG)
            logger.info("[ImageRouter] Character detector initialized")
        except Exception as e:
            logger.warning(f"[ImageRouter] Character detector init failed: {e}")

    # â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def generate(
        self,
        prompt: str,
        mode: str = "auto",
        quality: str = QualityMode.AUTO,
        style: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        source_image_b64: Optional[str] = None,
        mask_b64: Optional[str] = None,
        strength: float = 0.75,
        steps: int = 28,
        guidance: float = 3.5,
        seed: Optional[int] = None,
        num_images: int = 1,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        enhance_prompt: bool = True,
        context: Optional[str] = None,
        lora_models: Optional[list[dict]] = None,
        vae_name: Optional[str] = None,
        checkpoint: Optional[str] = None,
        preset_id: Optional[str] = None,
        hires_fix: bool = False,
        hires_scale: float = 1.5,
        hires_denoise: float = 0.45,
        hires_steps: int = 15,
    ) -> ImageResult:
        """
        Generate image(s) with automatic provider selection.
        
        Args:
            prompt: User's image description
            mode: "t2i", "i2i", "inpaint" or "auto"
            quality: "auto", "fast", "quality", "free", "cheap"
            style: Style preset name (e.g., "photorealistic", "anime")
            width/height: Output dimensions 
            source_image_b64: Base64 source image for img2img/inpaint
            mask_b64: Base64 mask for inpainting
            strength: Denoising strength for img2img (0-1)
            provider_name: Force specific provider
            model_name: Force specific model
            enhance_prompt: Whether to use LLM prompt enhancement
            context: Additional context for prompt enhancement
            lora_models: List of LoRA dicts [{"name": "file.safetensors", "weight": 0.8}]
            vae_name: Explicit VAE override filename
            checkpoint: Explicit checkpoint override
            preset_id: Workflow preset ID (resolves checkpoint + LoRAs + settings)
            hires_fix: Enable two-pass hi-res fix
            hires_scale: Upscale factor for hi-res fix
            hires_denoise: Denoise strength for hi-res fix pass 2
            hires_steps: Steps for hi-res fix pass 2
        """

        # 0. Resolve workflow preset (applies defaults that can be overridden)
        resolved_loras: list[LoraSpec] = []
        resolved_checkpoint = checkpoint
        resolved_neg = ""
        if preset_id:
            resolved_checkpoint, resolved_loras, preset_settings = self._resolve_preset(
                preset_id, checkpoint, lora_models,
            )
            if preset_settings:
                steps = preset_settings.get("steps", steps)
                guidance = preset_settings.get("cfg_scale", guidance)
                width = preset_settings.get("width", width)
                height = preset_settings.get("height", height)
                resolved_neg = preset_settings.get("negative_prompt", "")
                if preset_settings.get("hires_fix"):
                    hires_fix = True
                    hires_scale = preset_settings.get("hires_scale", hires_scale)
                    hires_denoise = preset_settings.get("hires_denoise", hires_denoise)
                    hires_steps = preset_settings.get("hires_steps", hires_steps)
        elif lora_models:
            resolved_loras = [
                LoraSpec(
                    name=l.get("name", ""),
                    weight=float(l.get("weight", 0.8)),
                    clip_weight=float(l.get("clip_weight", l.get("weight", 0.8))),
                    trigger_words=l.get("trigger_words", []),
                )
                for l in lora_models if l.get("name")
            ]

        # 0b. Auto-detect characters → pick ComfyUI with character LoRA only
        #     (no extra quality LoRA stacking — checkpoint handles that)
        auto_detected = False
        if not resolved_loras and not preset_id and self._character_detector:
            detection = self._character_detector.detect(prompt)
            if detection.has_characters:
                auto_detected = True
                # Only add LoRA specs for characters that have a LoRA file
                resolved_loras = [
                    LoraSpec(
                        name=c.lora_file,
                        weight=c.weight,
                        clip_weight=c.weight,
                        trigger_words=c.trigger_words,
                    )
                    for c in detection.characters
                    if c.lora_file  # skip trait-only characters
                ]
                if not resolved_checkpoint and detection.suggested_checkpoint:
                    resolved_checkpoint = detection.suggested_checkpoint
                logger.info(
                    f"[ImageRouter] Auto-detected characters: "
                    f"{[c.display_name for c in detection.characters]} → "
                    f"LoRAs: {[l.name for l in resolved_loras]}, "
                    f"traits: {detection.trait_tags}"
                )
                # Inject canonical trait tags as enhancer context so appearance
                # is based on the character database, not LLM knowledge
                if detection.trait_tags and not context:
                    context = (
                        f"Mandatory appearance tags — include these verbatim for the character: "
                        f"{', '.join(detection.trait_tags)}"
                    )

        # When LoRAs are specified, force ComfyUI (cloud providers don't support LoRAs)
        if resolved_loras and not provider_name:
            provider_name = "comfyui"
            quality = QualityMode.FREE

        # 1. Determine mode
        img_mode = self._resolve_mode(mode, source_image_b64, mask_b64)

        # 2. Enhance prompt
        enhanced_prompt = prompt
        if enhance_prompt and self._enhancer:
            try:
                enhanced_prompt = self._enhancer.enhance(
                    prompt, style_preset=style, context=context,
                    provider_hint=provider_name or "",
                )
                logger.info(f"[ImageRouter] Enhanced: '{prompt[:50]}...' → '{enhanced_prompt[:80]}...'")
            except Exception as e:
                logger.warning(f"[ImageRouter] Enhance failed: {e}")

        # 3. Build request
        resolved_model = self._resolve_requested_model(model_name)
        req = ImageRequest(
            prompt=enhanced_prompt,
            negative_prompt=resolved_neg,
            mode=img_mode,
            source_image_b64=source_image_b64,
            mask_b64=mask_b64,
            strength=strength,
            width=width,
            height=height,
            steps=steps,
            guidance=guidance,
            seed=seed,
            style_preset=style,
            num_images=num_images,
            lora_models=resolved_loras,
            vae_name=vae_name,
            checkpoint=resolved_checkpoint,
            preset_id=preset_id,
            extra={
                "model": resolved_model,
                "hires_fix": hires_fix,
                "hires_scale": hires_scale,
                "hires_denoise": hires_denoise,
                "hires_steps": hires_steps,
            } if resolved_model or hires_fix else (
                {"hires_fix": True, "hires_scale": hires_scale,
                 "hires_denoise": hires_denoise, "hires_steps": hires_steps}
                if hires_fix else {}
            ),
        )

        # 4. Select provider(s)
        providers = self._select_providers(quality, img_mode, provider_name)

        if resolved_model and resolved_model.startswith("nano-banana"):
            providers = [cfg for cfg in providers if cfg.provider.name in {"fal", "replicate"}]

        if not providers:
            if resolved_model and resolved_model.startswith("nano-banana"):
                return ImageResult(
                    success=False,
                    error="Nano Banana requires fal.ai or Replicate API key.",
                    prompt_used=enhanced_prompt,
                )
            return ImageResult(
                success=False,
                error="No image providers available. Add API keys for fal.ai, Replicate, or BFL.",
                prompt_used=enhanced_prompt,
            )

        # 5. Try providers with fallback
        last_error = ""
        for prov_config in providers:
            prov = prov_config.provider
            try:
                logger.info(f"[ImageRouter] Trying {prov.name} (tier={prov.tier})")
                result = prov.generate(req)
                if result.success:
                    result.prompt_used = enhanced_prompt
                    self._total_cost += result.cost_usd
                    self._total_generations += 1
                    result.metadata["original_prompt"] = prompt
                    result.metadata["enhanced"] = enhance_prompt
                    result.metadata["style"] = style
                    if auto_detected:
                        result.metadata["auto_detected_characters"] = [
                            c.display_name for c in detection.characters
                        ]
                        result.metadata["auto_loras"] = [l.name for l in resolved_loras]
                    if resolved_model:
                        result.metadata["requested_model"] = resolved_model
                    return result
                else:
                    last_error = result.error or "Unknown error"
                    logger.warning(f"[ImageRouter] {prov.name} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.error(f"[ImageRouter] {prov.name} exception: {e}")

        return ImageResult(
            success=False,
            error=f"All providers failed. Last error: {last_error}",
            prompt_used=enhanced_prompt,
        )

    def generate_stream(
        self,
        prompt: str,
        mode: str = "auto",
        quality: str = QualityMode.AUTO,
        style: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        source_image_b64: Optional[str] = None,
        mask_b64: Optional[str] = None,
        strength: float = 0.75,
        steps: int = 28,
        guidance: float = 3.5,
        seed: Optional[int] = None,
        num_images: int = 1,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        enhance_prompt: bool = True,
        context: Optional[str] = None,
        negative_prompt: str = "",
        lora_models: Optional[list[dict]] = None,
        vae_name: Optional[str] = None,
        checkpoint: Optional[str] = None,
        preset_id: Optional[str] = None,
        hires_fix: bool = False,
        hires_scale: float = 1.5,
        hires_denoise: float = 0.45,
        hires_steps: int = 15,
    ) -> Generator[dict, None, None]:
        """
        Generate image(s) with streaming status updates.
        
        Yields dicts with 'event' and 'data' keys:
          - {"event": "status", "data": {"step": "...", "phase": "...", ...}}
          - {"event": "provider_try", "data": {"provider": "...", "priority": N, ...}}
          - {"event": "provider_fail", "data": {"provider": "...", "error": "..."}}
          - {"event": "provider_success", "data": {"provider": "...", "model": "..."}}
          - {"event": "result", "data": {<ImageResult fields>}}
          - {"event": "error", "data": {"error": "..."}}
        """
        start_time = time.time()

        # 1. Resolve mode
        yield {"event": "status", "data": {"step": "Analyzing request...", "phase": "init"}}
        img_mode = self._resolve_mode(mode, source_image_b64, mask_b64)
        mode_labels = {
            ImageMode.TEXT_TO_IMAGE: "Text → Image",
            ImageMode.IMAGE_TO_IMAGE: "Image → Image",
            ImageMode.INPAINT: "Inpainting",
        }
        yield {"event": "status", "data": {
            "step": f"Mode: {mode_labels.get(img_mode, str(img_mode))}",
            "phase": "init",
        }}

        # 2. Enhance prompt
        enhanced_prompt = prompt
        if enhance_prompt and self._enhancer:
            yield {"event": "status", "data": {
                "step": "Enhancing prompt with AI...",
                "phase": "enhance",
            }}
            try:
                enhanced_prompt = self._enhancer.enhance(
                    prompt, style_preset=style, context=context,
                    provider_hint=provider_name or "",
                )
                logger.info(f"[ImageRouter] Enhanced: '{prompt[:50]}...' → '{enhanced_prompt[:80]}...'")
                yield {"event": "status", "data": {
                    "step": f"Prompt enhanced",
                    "phase": "enhance",
                    "enhanced_prompt": enhanced_prompt,
                }}
            except Exception as e:
                logger.warning(f"[ImageRouter] Enhance failed: {e}")
                yield {"event": "status", "data": {
                    "step": "Prompt enhancement skipped",
                    "phase": "enhance",
                }}

        # 3. Resolve workflow preset / loras for streaming flow
        resolved_loras: list[LoraSpec] = []
        resolved_checkpoint = checkpoint
        resolved_neg = negative_prompt or ""
        if preset_id:
            resolved_checkpoint, resolved_loras, preset_settings = self._resolve_preset(
                preset_id, checkpoint, lora_models,
            )
            if preset_settings:
                steps = preset_settings.get("steps", steps)
                guidance = preset_settings.get("cfg_scale", guidance)
                width = preset_settings.get("width", width)
                height = preset_settings.get("height", height)
                if not resolved_neg:
                    resolved_neg = preset_settings.get("negative_prompt", "")
                if preset_settings.get("hires_fix"):
                    hires_fix = True
                    hires_scale = preset_settings.get("hires_scale", hires_scale)
                    hires_denoise = preset_settings.get("hires_denoise", hires_denoise)
                    hires_steps = preset_settings.get("hires_steps", hires_steps)
        elif lora_models:
            resolved_loras = [
                LoraSpec(
                    name=l.get("name", ""),
                    weight=float(l.get("weight", 0.8)),
                    clip_weight=float(l.get("clip_weight", l.get("weight", 0.8))),
                    trigger_words=l.get("trigger_words", []),
                )
                for l in lora_models if l.get("name")
            ]

        if resolved_loras and not provider_name:
            provider_name = "comfyui"
            quality = QualityMode.FREE

        # 4. Build request
        resolved_model = self._resolve_requested_model(model_name)
        req = ImageRequest(
            prompt=enhanced_prompt,
            negative_prompt=resolved_neg,
            mode=img_mode,
            source_image_b64=source_image_b64,
            mask_b64=mask_b64,
            strength=strength,
            width=width,
            height=height,
            steps=steps,
            guidance=guidance,
            seed=seed,
            style_preset=style,
            num_images=num_images,
            lora_models=resolved_loras,
            vae_name=vae_name,
            checkpoint=resolved_checkpoint,
            preset_id=preset_id,
            extra={
                **({"model": resolved_model} if resolved_model else {}),
                "hires_fix": hires_fix,
                "hires_scale": hires_scale,
                "hires_denoise": hires_denoise,
                "hires_steps": hires_steps,
            },
        )

        # 5. Select providers
        yield {"event": "status", "data": {
            "step": "Selecting providers...",
            "phase": "select",
        }}
        providers = self._select_providers(quality, img_mode, provider_name)

        if resolved_model and resolved_model.startswith("nano-banana"):
            providers = [cfg for cfg in providers if cfg.provider.name in {"fal", "replicate"}]

        if not providers:
            error_msg = ("Nano Banana requires fal.ai or Replicate API key."
                         if resolved_model and resolved_model.startswith("nano-banana")
                         else "No image providers available. Add API keys for fal.ai, Replicate, or BFL.")
            yield {"event": "error", "data": {"error": error_msg, "prompt_used": enhanced_prompt}}
            return

        provider_names = [cfg.provider.name for cfg in providers]
        yield {"event": "status", "data": {
            "step": f"Available providers: {', '.join(provider_names)}",
            "phase": "select",
            "providers": provider_names,
        }}

        # 6. Try providers with fallback (streaming status)
        last_error = ""
        attempt = 0
        for prov_config in providers:
            prov = prov_config.provider
            attempt += 1
            yield {"event": "provider_try", "data": {
                "provider": prov.name,
                "priority": prov_config.priority,
                "attempt": attempt,
                "total_providers": len(providers),
            }}

            try:
                result = prov.generate(req)
                if result.success:
                    result.prompt_used = enhanced_prompt
                    self._total_cost += result.cost_usd
                    self._total_generations += 1
                    result.metadata["original_prompt"] = prompt
                    result.metadata["enhanced"] = enhance_prompt
                    result.metadata["style"] = style
                    if resolved_model:
                        result.metadata["requested_model"] = resolved_model

                    latency = round((time.time() - start_time) * 1000, 1)
                    yield {"event": "provider_success", "data": {
                        "provider": result.provider,
                        "model": result.model,
                        "latency_ms": latency,
                    }}
                    yield {"event": "result", "data": {
                        "success": True,
                        "provider": result.provider,
                        "model": result.model,
                        "images_b64": result.images_b64,
                        "images_url": result.images_url,
                        "prompt_used": enhanced_prompt,
                        "original_prompt": prompt,
                        "latency_ms": latency,
                        "cost_usd": result.cost_usd,
                        "metadata": result.metadata,
                    }}
                    return
                else:
                    last_error = result.error or "Unknown error"
                    logger.warning(f"[ImageRouter] {prov.name} failed: {last_error}")
                    yield {"event": "provider_fail", "data": {
                        "provider": prov.name,
                        "error": last_error,
                        "attempt": attempt,
                    }}
            except Exception as e:
                last_error = str(e)
                logger.error(f"[ImageRouter] {prov.name} exception: {e}")
                yield {"event": "provider_fail", "data": {
                    "provider": prov.name,
                    "error": last_error,
                    "attempt": attempt,
                }}

        yield {"event": "error", "data": {
            "error": f"All providers failed. Last error: {last_error}",
            "prompt_used": enhanced_prompt,
        }}

    def get_available_providers(self) -> list[dict]:
        """Return info about all configured providers."""
        result = []
        for name, cfg in self._providers.items():
            prov = cfg.provider
            result.append({
                "name": name,
                "tier": prov.tier.value if hasattr(prov.tier, 'value') else str(prov.tier),
                "available": prov.is_available,
                "supports_i2i": prov.supports_i2i,
                "supports_inpaint": prov.supports_inpaint,
                "cost_per_image": prov.cost_per_image,
                "priority": cfg.priority,
                "enabled": cfg.enabled,
            })
        return sorted(result, key=lambda x: x["priority"], reverse=True)

    def get_style_presets(self) -> dict[str, str]:
        """Return all available style presets."""
        return dict(STYLE_PRESETS)

    def get_stats(self) -> dict:
        """Return usage statistics."""
        return {
            "total_generations": self._total_generations,
            "total_cost_usd": round(self._total_cost, 4),
            "providers": self.get_available_providers(),
        }

    def health_check(self) -> dict:
        """Check health of all providers."""
        results = {}
        for name, cfg in self._providers.items():
            try:
                results[name] = cfg.provider.health_check()
            except Exception:
                results[name] = False
        return results

    # â”€â”€ Private helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _resolve_mode(
        self, mode: str, source_b64: Optional[str], mask_b64: Optional[str]
    ) -> ImageMode:
        if mode == "inpaint" or (source_b64 and mask_b64):
            return ImageMode.INPAINT
        if mode == "i2i" or source_b64:
            return ImageMode.IMAGE_TO_IMAGE
        return ImageMode.TEXT_TO_IMAGE

    def _resolve_requested_model(self, model_name: Optional[str]) -> Optional[str]:
        """Resolve model alias/defaults, including nano-banana auto cost selection."""
        raw = (model_name or os.getenv("IMAGE_GEN_DEFAULT_MODEL", "")).strip().lower()
        if not raw:
            return None

        aliases = {
            "nano": "nano-banana-auto",
            "nano-banana": "nano-banana-pro",
            "nano-pro": "nano-banana-pro",
            "nano2": "nano-banana-2",
            "nano-2": "nano-banana-2",
            "nb-pro": "nano-banana-pro",
            "nb2": "nano-banana-2",
            "auto": "nano-banana-auto",
        }
        resolved = aliases.get(raw, raw)

        if resolved == "nano-banana-auto":
            return self._pick_cheaper_nano_model()
        return resolved

    def _pick_cheaper_nano_model(self) -> str:
        """Pick the cheaper model between nano-banana-pro and nano-banana-2."""
        pro_cost = self._estimate_model_cost("nano-banana-pro")
        v2_cost = self._estimate_model_cost("nano-banana-2")

        if pro_cost is None and v2_cost is None:
            return "nano-banana-pro"
        if pro_cost is None:
            return "nano-banana-2"
        if v2_cost is None:
            return "nano-banana-pro"
        return "nano-banana-pro" if pro_cost <= v2_cost else "nano-banana-2"

    def _estimate_model_cost(self, model_key: str) -> Optional[float]:
        """Estimate lowest available cost for a model across configured providers."""
        costs: list[float] = []
        if "fal" in self._providers and self._providers["fal"].provider.is_available:
            if model_key in FAL_COST:
                costs.append(FAL_COST[model_key])
        if "replicate" in self._providers and self._providers["replicate"].provider.is_available:
            if model_key in REPLICATE_COST:
                costs.append(REPLICATE_COST[model_key])
        if not costs:
            return None
        return min(costs)

    def _select_providers(
        self,
        quality: str,
        mode: ImageMode,
        force_provider: Optional[str] = None,
    ) -> list[ProviderConfig]:
        """Select and order providers based on quality preference."""

        # Force specific provider
        if force_provider and force_provider in self._providers:
            cfg = self._providers[force_provider]
            if cfg.enabled:
                return [cfg]

        candidates = []
        for name, cfg in self._providers.items():
            if not cfg.enabled:
                continue
            prov = cfg.provider
            if not prov.is_available:
                continue
            # Filter by mode capability
            if mode == ImageMode.IMAGE_TO_IMAGE and not prov.supports_i2i:
                continue
            if mode == ImageMode.INPAINT and not prov.supports_inpaint:
                continue
            candidates.append(cfg)

        if not candidates:
            return []

        # Sort by quality preference
        if quality == QualityMode.FAST:
            # Prefer fast/cheap providers
            candidates.sort(key=lambda c: (
                0 if c.provider.tier == ProviderTier.FAST else
                1 if c.provider.tier == ProviderTier.LOCAL else
                2
            ))
        elif quality == QualityMode.QUALITY:
            # Prefer ultra/high tier
            candidates.sort(key=lambda c: (
                0 if c.provider.tier == ProviderTier.ULTRA else
                1 if c.provider.tier == ProviderTier.HIGH else
                2
            ))
        elif quality == QualityMode.FREE:
            # Only local providers
            candidates = [c for c in candidates if c.provider.tier == ProviderTier.LOCAL]
        elif quality == QualityMode.CHEAP:
            # Sort by cost
            candidates.sort(key=lambda c: c.provider.cost_per_image)
        else:
            # Auto: randomize among top-tier providers to distribute cost
            # Group by priority tier (within 15 points = same tier)
            if candidates:
                max_pri = max(c.priority for c in candidates)
                top_tier = [c for c in candidates if c.priority >= max_pri - 15]
                rest = [c for c in candidates if c.priority < max_pri - 15]
                random.shuffle(top_tier)
                rest.sort(key=lambda c: c.priority, reverse=True)
                candidates = top_tier + rest

        # ── Hybrid mode: promote healthy local providers when profile is "full" ──
        try:
            from app.services.image_orchestrator.runtime_profile import get_runtime_profile
            profile = get_runtime_profile()
            if profile.prefer_local_when_healthy and quality in (
                QualityMode.AUTO, QualityMode.FREE, QualityMode.CHEAP,
            ):
                local = [c for c in candidates if c.provider.tier == ProviderTier.LOCAL]
                remote = [c for c in candidates if c.provider.tier != ProviderTier.LOCAL]
                if local:
                    local_names = [c.provider.name for c in local]
                    remote_names = [c.provider.name for c in remote]
                    logger.info(
                        f"[ImageRouter] HYBRID decision: local {local_names} healthy "
                        f"→ promoted first (free, 0 latency). "
                        f"Fallback chain: {remote_names}"
                    )
                    candidates = local + remote
                else:
                    remote_names = [c.provider.name for c in remote]
                    logger.info(
                        f"[ImageRouter] HYBRID decision: no healthy local provider "
                        f"→ using remote providers {remote_names}"
                    )
            else:
                names = [c.provider.name for c in candidates]
                logger.info(
                    f"[ImageRouter] Provider order (quality={quality}): {names}"
                )
        except Exception:
            pass

        return candidates

    def _resolve_preset(
        self,
        preset_id: str,
        checkpoint_override: Optional[str],
        lora_override: Optional[list[dict]],
    ) -> tuple[Optional[str], list[LoraSpec], dict]:
        """
        Resolve a workflow preset into checkpoint, LoRA specs, and settings.
        User-supplied overrides take priority over preset defaults.
        """
        try:
            from config.model_presets import (
                get_workflow_preset, resolve_loras_for_preset, get_lora_by_key,
            )
        except ImportError:
            logger.warning("[ImageRouter] model_presets import failed — preset ignored")
            return checkpoint_override, [], {}

        preset = get_workflow_preset(preset_id)
        if not preset:
            safe_preset_id = str(preset_id).replace("\r", "").replace("\n", "")
            logger.warning("[ImageRouter] Unknown preset: %s", safe_preset_id)
            return checkpoint_override, [], {}

        # Checkpoint: override > preset
        ckpt = checkpoint_override or preset.get("checkpoint")

        # LoRAs: override > preset defaults
        lora_specs: list[LoraSpec] = []
        if lora_override:
            for l in lora_override:
                lora_specs.append(LoraSpec(
                    name=l.get("name", ""),
                    weight=float(l.get("weight", 0.8)),
                    clip_weight=float(l.get("clip_weight", l.get("weight", 0.8))),
                    trigger_words=l.get("trigger_words", []),
                ))
        else:
            if preset.get("use_live_loras"):
                live_weight = float(preset.get("live_lora_weight", 0.55))
                live_limit = int(preset.get("live_lora_limit", 8))
                all_live_loras = self.get_available_loras()
                preferred = [
                    n for n in all_live_loras
                    if str(n).startswith("imported_lora_chatbot/")
                ]
                include_keywords = [
                    str(k).lower() for k in preset.get("live_lora_include_keywords", [])
                ]
                exclude_keywords = [
                    str(k).lower() for k in preset.get("live_lora_exclude_keywords", [])
                ]

                candidate_pool = preferred or all_live_loras
                filtered: list[str] = []
                for n in candidate_pool:
                    name_lower = str(n).lower()
                    if include_keywords and not any(k in name_lower for k in include_keywords):
                        continue
                    if exclude_keywords and any(k in name_lower for k in exclude_keywords):
                        continue
                    filtered.append(n)

                live_loras = (filtered or candidate_pool)[:max(0, live_limit)]
                for name in live_loras:
                    lora_specs.append(LoraSpec(
                        name=name,
                        weight=live_weight,
                        clip_weight=live_weight,
                        trigger_words=[],
                    ))
            else:
                resolved = resolve_loras_for_preset(preset_id)
                for r in resolved:
                    lora_specs.append(LoraSpec(
                        name=r["file"],
                        weight=r["weight"],
                        clip_weight=r["weight"],
                        trigger_words=r.get("trigger", []),
                    ))

        # Gather other settings
        settings = {
            k: preset[k] for k in (
                "steps", "cfg_scale", "width", "height",
                "negative_prompt", "sampler",
                "hires_fix", "hires_scale", "hires_denoise", "hires_steps",
            ) if k in preset
        }

        safe_preset_id = str(preset_id).replace("\r", "").replace("\n", "")
        safe_ckpt = (
            str(ckpt).replace("\r", "").replace("\n", "")
            if ckpt is not None else None
        )
        logger.info(
            "[ImageRouter] Preset '%s': ckpt=%s, loras=%s, settings=%s",
            safe_preset_id,
            safe_ckpt,
            [l.name for l in lora_specs],
            list(settings.keys()),
        )
        return ckpt, lora_specs, settings

    def get_available_loras(self) -> list[str]:
        """Query ComfyUI for available LoRA files."""
        comfyui = self._providers.get("comfyui")
        if comfyui and hasattr(comfyui.provider, "get_loras"):
            return comfyui.provider.get_loras()
        return []

    def detect_characters(self, prompt: str) -> dict:
        """
        Public API: detect characters in a prompt.
        Returns dict with detected characters and suggested LoRAs.
        """
        if not self._character_detector:
            return {"characters": [], "detected": False}
        result = self._character_detector.detect(prompt)
        return {
            "detected": result.has_characters,
            "characters": [
                {
                    "key": c.key,
                    "name": c.display_name,
                    "lora_file": c.lora_file,
                    "weight": c.weight,
                    "trigger_words": c.trigger_words,
                    "franchise": c.franchise,
                    "base": c.base,
                }
                for c in result.characters
            ],
            "suggested_checkpoint": result.suggested_checkpoint,
            "suggested_preset_id": result.suggested_preset_id,
        }

    def get_detectable_characters(self) -> list[dict]:
        """List all characters the detector can recognize."""
        if not self._character_detector:
            return []
        return self._character_detector.get_all_characters()
