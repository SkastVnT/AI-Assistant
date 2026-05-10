"""
ProviderRouter
==============
The bridge between the new image_orchestrator layer and the existing
core/image_gen provider infrastructure.

This module does NOT own any provider logic. It delegates entirely to:
    core.image_gen.router.ImageGenerationRouter.generate()

The only responsibility here is:
- Map ImageGenerationRequest / ImageFollowupRequest fields → generate() kwargs
- Return ImageResult as-is so the caller can inspect success/error
- Hold a lazily-initialised singleton of ImageGenerationRouter
  (same pattern used by core/image_gen/orchestrator.py: _get_router())
"""

from __future__ import annotations

import logging
from typing import Optional, Union

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Lazy singleton wrapper around the existing router
# ─────────────────────────────────────────────────────────────────────

class ProviderRouter:
    """
    Thin adapter: converts app-layer request objects into
    ImageGenerationRouter.generate() kwargs and returns the raw ImageResult.

    Usage:
        router = ProviderRouter()
        result = router.route(
            request=req,          # ImageGenerationRequest or ImageFollowupRequest
            built_prompt=prompt,  # output of PromptBuilder.build()
            negative_prompt=neg,  # output of PromptBuilder.build_negative()
        )
    """

    _shared_router = None  # type: ignore[assignment]

    @classmethod
    def _get_router(cls):
        """
        Return the shared ImageGenerationRouter instance, creating it on first
        call.  Uses the same lazy-init pattern as core/image_gen/orchestrator.py.
        """
        if cls._shared_router is None:
            try:
                # Log runtime profile so we know which mode we're in
                from .runtime_profile import get_runtime_profile
                profile = get_runtime_profile()
                logger.info(f"[ProviderRouter] {profile.describe()}")
            except Exception:
                pass

            try:
                from core.image_gen.router import ImageGenerationRouter
                cls._shared_router = ImageGenerationRouter()
                logger.info("[ProviderRouter] ImageGenerationRouter initialised")
            except Exception as exc:
                logger.error(f"[ProviderRouter] Failed to init ImageGenerationRouter: {exc}")
                raise
        return cls._shared_router

    def route(
        self,
        request:         "Union[ImageGenerationRequest, ImageFollowupRequest]",  # type: ignore
        built_prompt:    str,
        negative_prompt: str = "",
    ):
        """
        Route one request through the existing provider stack.

        Returns:
            core.image_gen.providers.base.ImageResult
        """
        # resolve fields that differ between request types
        scene           = getattr(request, "scene", None)
        source_b64      = getattr(request, "source_image_b64", None)
        source_url      = getattr(request, "source_image_url", None)
        strength        = float(getattr(request, "strength", 0.75))
        seed            = getattr(request, "seed", None)
        provider_hint   = getattr(request, "provider", None)
        model_hint      = getattr(request, "model", None)

        # SceneSpec overrides request-level fields when present
        if scene:
            seed          = scene.seed if scene.seed is not None else seed
            provider_hint = scene.provider_hint or provider_hint
            width         = scene.width
            height        = scene.height
            quality       = scene.quality_preset
            style         = scene.style
        else:
            width   = getattr(request, "width",  1024)
            height  = getattr(request, "height", 1024)
            quality = getattr(request, "quality", "auto")
            style   = getattr(request, "style",  None)

        # Determine image-to-image mode
        has_source  = bool(source_b64 or source_url)
        is_followup = type(request).__name__ == "ImageFollowupRequest"
        mode        = "i2i" if (is_followup and has_source) else "t2i"

        # Build negative prompt extra dict (passed via `extra` or ignored by
        # providers that don't support it; never breaks anything)
        extra_kwargs: dict = {}
        if negative_prompt:
            extra_kwargs["negative_prompt"] = negative_prompt

        try:
            router = self._get_router()
            result = router.generate(
                prompt           = built_prompt,
                mode             = mode,
                quality          = quality or "auto",
                style            = style,
                width            = int(width),
                height           = int(height),
                source_image_b64 = source_b64,
                strength         = strength,
                seed             = seed,
                provider_name    = provider_hint,
                model_name       = model_hint,
                enhance_prompt   = False,       # PromptBuilder already handled this
                context          = None,
                **extra_kwargs,
            )
            return result

        except Exception as exc:
            logger.error(f"[ProviderRouter] generate() raised: {exc}")
            # Return a failed ImageResult rather than propagating the exception,
            # so the caller can decide to fall back to the legacy flow.
            try:
                from core.image_gen.providers.base import ImageResult
                return ImageResult(
                    success    = False,
                    error      = str(exc),
                    prompt_used= built_prompt,
                )
            except ImportError:
                raise
