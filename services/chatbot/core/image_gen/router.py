"""
ImageRouter — the brain of the image generation system.
Selects the optimal provider based on: quality preference, cost budget,
speed requirements, feature needs (i2i, inpaint), and provider availability.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Optional
from dataclasses import dataclass, field

from .providers.base import (
    BaseImageProvider, ImageRequest, ImageResult,
    ImageMode, ProviderTier,
)
from .providers import (
    FalProvider, ReplicateProvider, BFLProvider,
    OpenAIImageProvider, ComfyUIProvider, TogetherProvider,
    StepFunProvider,
)
from .enhancer import PromptEnhancer, create_enhancer, STYLE_PRESETS

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
        self._total_cost: float = 0.0
        self._total_generations: int = 0
        self._init_providers()
        self._init_enhancer()

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
            self._providers["bfl"] = ProviderConfig(
                provider=BFLProvider(api_key=bfl_key),
                priority=85,
            )

        # OpenAI
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            self._providers["openai"] = ProviderConfig(
                provider=OpenAIImageProvider(api_key=openai_key),
                priority=70,
            )

        # ComfyUI (local) — always available as fallback
        comfyui_url = os.getenv("COMFYUI_URL", os.getenv("SD_API_URL", "http://127.0.0.1:8189"))
        self._providers["comfyui"] = ProviderConfig(
            provider=ComfyUIProvider(base_url=comfyui_url),
            priority=10,  # lowest priority unless explicitly requested
        )

        # Together.ai (free tier available)
        together_key = os.getenv("TOGETHER_API_KEY", "")
        if together_key:
            self._providers["together"] = ProviderConfig(
                provider=TogetherProvider(api_key=together_key),
                priority=60,
            )

        # StepFun (Step1X-Edit — best editing model)
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

    # ── Public API ──────────────────────────────────────────────────

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
        """

        # 1. Determine mode
        img_mode = self._resolve_mode(mode, source_image_b64, mask_b64)

        # 2. Enhance prompt
        enhanced_prompt = prompt
        if enhance_prompt and self._enhancer:
            try:
                enhanced_prompt = self._enhancer.enhance(prompt, style_preset=style, context=context)
                logger.info(f"[ImageRouter] Enhanced: '{prompt[:50]}...' → '{enhanced_prompt[:80]}...'")
            except Exception as e:
                logger.warning(f"[ImageRouter] Enhance failed: {e}")

        # 3. Build request
        req = ImageRequest(
            prompt=enhanced_prompt,
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
            extra={"model": model_name} if model_name else {},
        )

        # 4. Select provider(s)
        providers = self._select_providers(quality, img_mode, provider_name)

        if not providers:
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

    # ── Private helpers ─────────────────────────────────────────────

    def _resolve_mode(
        self, mode: str, source_b64: Optional[str], mask_b64: Optional[str]
    ) -> ImageMode:
        if mode == "inpaint" or (source_b64 and mask_b64):
            return ImageMode.INPAINT
        if mode == "i2i" or source_b64:
            return ImageMode.IMAGE_TO_IMAGE
        return ImageMode.TEXT_TO_IMAGE

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
            # Auto: sort by priority (configured ranking)
            candidates.sort(key=lambda c: c.priority, reverse=True)

        return candidates
