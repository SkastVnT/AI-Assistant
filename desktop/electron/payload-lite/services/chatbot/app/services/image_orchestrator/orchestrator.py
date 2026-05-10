"""
ImageOrchestrationService
=========================
New high-level wrapper around the existing core/image_gen stack.

Pipeline (happy path):
    1. detect_intent()          — core/image_gen/intent.py (unchanged)
    2. ScenePlanner.plan()      — message → SceneSpec (structured scene)
    3. PromptBuilder.build()    — SceneSpec → provider-ready prompt string
    4. ProviderRouter.route()   — delegates to ImageGenerationRouter.generate()
    5. SessionMemoryStore.update() — persist last_scene / last_image_ref
    6. Return ImageGenerationResult

Fallback:
    On ANY unhandled exception in the new pipeline, the service falls back to
    the existing core.image_gen.orchestrator.ImageOrchestrator.handle() so the
    user always gets a response.

Public API (module-level convenience):
    result = handle_image_request(message, session_id, language, tools)
"""

from __future__ import annotations

import logging
import time
from dataclasses import replace
from typing import Optional, Generator

logger = logging.getLogger(__name__)

# ── New layer components ──────────────────────────────────────────────

from .schemas import (
    ImageIntent,
    ImageGenerationRequest,
    ImageFollowupRequest,
    ImageGenerationResult,
    SceneSpec,
)
from .scene_planner  import ScenePlanner, merge_scene_delta
from .prompt_builder import PromptBuilder
from .provider_router import ProviderRouter
from .session_memory  import SessionMemoryStore, get_session_memory_store

# ── Existing layer (imported lazily inside methods to defer heavy init) ────────

def _get_legacy_intent():
    from core.image_gen.intent import detect_intent, ImageIntent as CoreIntent, IntentResult
    return detect_intent, CoreIntent, IntentResult


def _get_legacy_orchestrator(session_id: str):
    from core.image_gen.orchestrator import ImageOrchestrator
    return ImageOrchestrator(session_id=session_id)


# ─────────────────────────────────────────────────────────────────────
# Singleton helpers
# ─────────────────────────────────────────────────────────────────────

_scene_planner:   Optional[ScenePlanner]  = None
_prompt_builder:  Optional[PromptBuilder] = None
_provider_router: Optional[ProviderRouter] = None


def _get_scene_planner() -> ScenePlanner:
    global _scene_planner
    if _scene_planner is None:
        _scene_planner = ScenePlanner()
    return _scene_planner


def _get_prompt_builder(use_llm: bool = True) -> PromptBuilder:
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = PromptBuilder(use_llm_enhancer=use_llm)
    return _prompt_builder


def _get_provider_router() -> ProviderRouter:
    global _provider_router
    if _provider_router is None:
        _provider_router = ProviderRouter()
    return _provider_router


# ─────────────────────────────────────────────────────────────────────
# ImageOrchestrationService
# ─────────────────────────────────────────────────────────────────────

class ImageOrchestrationService:
    """
    Stateless service class.  All per-session state lives in SessionMemoryStore.
    Instantiate once (or use the module-level handle_image_request() shortcut).
    """

    def __init__(
        self,
        use_llm_enhancer: bool = True,
        memory_store: Optional[SessionMemoryStore] = None,
    ):
        self._use_llm    = use_llm_enhancer
        self._mem_store  = memory_store or get_session_memory_store()

    # ── Main sync entry point ─────────────────────────────────────────

    def handle(
        self,
        message:    str,
        session_id: str,
        language:   str            = "vi",
        tools:      list[str] | None = None,
        quality:    str            = "auto",
        style:      Optional[str]  = None,
        provider:   Optional[str]  = None,
    ) -> ImageGenerationResult:
        """
        Process one user turn and return a typed result.

        Returns:
            ImageGenerationResult with .is_image=True on success
            ImageGenerationResult with .fallback_to_llm=True when the message
                is not an image request (or when the new pipeline fails and
                the legacy chain also fails)
        """
        t_start  = time.monotonic()
        tools    = tools or []
        mem      = self._mem_store.get_or_create(session_id)

        # ── Step 1: intent detection (reuse existing classifier) ──────
        try:
            detect_intent, CoreIntent, IntentResult = _get_legacy_intent()
            core_intent_result = detect_intent(
                message,
                has_previous_image=mem.has_previous_image,
            )
        except Exception as exc:
            logger.warning(f"[ImageOrchestrationService] detect_intent failed: {exc}")
            return ImageGenerationResult(
                is_image=False, fallback_to_llm=True,
                error=str(exc), response_text="",
                intent=ImageIntent.NONE, original_prompt=message,
            )

        # Map core intent → app-layer intent
        intent = _map_intent(core_intent_result.intent)

        # Not an image request and tool not explicitly requested → hand off to LLM
        explicit_tool = "image-generation" in tools
        if intent == ImageIntent.NONE and not explicit_tool:
            return ImageGenerationResult(
                is_image=False, fallback_to_llm=True,
                intent=ImageIntent.NONE, original_prompt=message,
                response_text="", error="",
            )

        if explicit_tool and intent == ImageIntent.NONE:
            intent = ImageIntent.GENERATE

        # ── Steps 2-5: new pipeline (falls back to legacy on error) ───
        try:
            result = self._run_new_pipeline(
                message=message,
                session_id=session_id,
                language=language,
                intent=intent,
                core_intent_result=core_intent_result,
                quality_override=quality,
                style_override=style,
                provider_override=provider,
                mem=mem,
                t_start=t_start,
            )
            return result

        except Exception as exc:
            logger.error(
                f"[ImageOrchestrationService] New pipeline failed, falling back: {exc}",
                exc_info=True,
            )
            return self._fallback_to_legacy(
                message=message,
                session_id=session_id,
                language=language,
                tools=tools,
                original_error=str(exc),
                t_start=t_start,
            )

    # ── Internal pipeline ─────────────────────────────────────────────

    def _run_new_pipeline(
        self,
        message:            str,
        session_id:         str,
        language:           str,
        intent:             ImageIntent,
        core_intent_result, # IntentResult from core.image_gen.intent
        quality_override:   str,
        style_override:     Optional[str],
        provider_override:  Optional[str],
        mem,                # ImageSessionMemory
        t_start:            float,
    ) -> ImageGenerationResult:
        """Run the new ScenePlanner → PromptBuilder → ProviderRouter pipeline."""

        # ── Step 2: ScenePlanner → SceneSpec ──────────────────────────
        planner = _get_scene_planner()
        scene   = planner.plan(
            message         = message,
            intent          = intent,
            language        = language,
            previous_scene  = mem.last_scene_spec,
            style_override  = style_override or core_intent_result.style_hint,
            quality_override= quality_override or core_intent_result.quality_hint,
        )

        # Apply dimension hints from intent detector if scene fell back to defaults
        if scene.width == 1024 and scene.height == 1024 and \
           (core_intent_result.width != 1024 or core_intent_result.height != 1024):
            scene = replace(
                scene,
                width  = core_intent_result.width,
                height = core_intent_result.height,
            )

        if provider_override:
            scene = replace(scene, provider_hint=provider_override)

        # Carry over source image for edits from session memory
        source_b64 = None
        is_edit    = intent in (ImageIntent.EDIT, ImageIntent.FOLLOWUP_EDIT)
        if is_edit:
            ref = mem.last_image_reference
            if ref and not ref.startswith("b64:"):
                scene = replace(scene, source_image_url=ref)
                logger.info(
                    f"[EditRouting] i2i path — source_image_url from session "
                    f"(lineage={mem.edit_lineage_count})"
                )
            elif ref and ref.startswith("b64:"):
                # Can't reconstruct full b64 from snippet — fallback to t2i
                logger.info(
                    "[EditRouting] Regenerate-from-prior-scene — "
                    "source b64 unavailable, using merged scene as t2i"
                )
            else:
                logger.info(
                    "[EditRouting] Regenerate-from-prior-scene — "
                    "no previous image reference, using merged scene as t2i"
                )

        # ── Step 3: PromptBuilder → prompt strings ────────────────────
        builder  = _get_prompt_builder(use_llm=self._use_llm)
        prompt   = builder.build(scene, language=language, original_message=message)
        negative = builder.build_negative(scene)

        # ── Step 4: build typed request ───────────────────────────────
        if intent in (ImageIntent.EDIT, ImageIntent.FOLLOWUP_EDIT):
            typed_request = ImageFollowupRequest(
                original_prompt  = message,
                language         = language,
                session_id       = session_id,
                intent           = intent,
                edit_verb        = _extract_edit_verb(message),
                scene            = scene,
                enhanced_prompt  = prompt,
                source_image_b64 = source_b64,
                source_image_url = scene.source_image_url,
                strength         = scene.strength,
                seed             = scene.seed,
                provider         = scene.provider_hint,
            )
        else:
            typed_request = ImageGenerationRequest(
                original_prompt = message,
                language        = language,
                session_id      = session_id,
                scene           = scene,
                enhanced_prompt = prompt,
                quality         = scene.quality_preset,
                style           = scene.style,
                provider        = scene.provider_hint,
                model           = None,
                width           = scene.width,
                height          = scene.height,
                seed            = scene.seed,
                tools           = [],
            )

        # ── Step 4b: ProviderRouter → ImageResult ─────────────────────
        router     = _get_provider_router()
        img_result = router.route(typed_request, prompt, negative)

        latency_ms = (time.monotonic() - t_start) * 1000

        if not img_result.success:
            # Provider failed — try legacy fallback
            raise RuntimeError(
                f"Provider returned failure: {img_result.error}"
            )

        # ── Step 5: update session memory ─────────────────────────────
        self._mem_store.update(
            session_id = session_id,
            prompt     = prompt,
            scene      = scene,
            result     = img_result,
            is_edit    = is_edit,
        )

        # ── Step 6: assemble typed result ─────────────────────────────
        response_text = _build_response_text(
            images_url=img_result.images_url or [],
            images_b64=img_result.images_b64 or [],
            prompt=prompt,
            provider=img_result.provider or "",
            latency_ms=latency_ms,
        )

        return ImageGenerationResult(
            is_image        = True,
            intent          = intent,
            images_b64      = img_result.images_b64 or [],
            images_url      = img_result.images_url  or [],
            enhanced_prompt = img_result.prompt_used or prompt,
            original_prompt = message,
            provider        = img_result.provider or "",
            model           = img_result.model    or "",
            cost_usd        = img_result.cost_usd  or 0.0,
            latency_ms      = latency_ms,
            seed            = (img_result.metadata or {}).get("seed"),
            response_text   = response_text,
            error           = "",
            fallback_to_llm = False,
            scene           = scene,
        )

    # ── Legacy fallback ───────────────────────────────────────────────

    def _fallback_to_legacy(
        self,
        message:        str,
        session_id:     str,
        language:       str,
        tools:          list[str],
        original_error: str,
        t_start:        float,
    ) -> ImageGenerationResult:
        """
        Delegate directly to the existing ImageOrchestrator.handle() so the
        user always receives an image (or a graceful fallback) even when the
        new pipeline fails.
        """
        logger.info("[ImageOrchestrationService] Running legacy fallback pipeline")
        try:
            legacy    = _get_legacy_orchestrator(session_id)
            orch_res  = legacy.handle(message=message, language=language, tools=tools)
            lat        = (time.monotonic() - t_start) * 1000

            if orch_res.fallback_to_llm or not orch_res.is_image:
                return ImageGenerationResult(
                    is_image        = False,
                    fallback_to_llm = True,
                    intent          = ImageIntent.NONE,
                    original_prompt = message,
                    response_text   = "",
                    error           = original_error,
                )

            return ImageGenerationResult(
                is_image        = True,
                intent          = _map_intent(orch_res.intent),
                images_b64      = orch_res.images_b64 or [],
                images_url      = orch_res.images_url  or [],
                enhanced_prompt = orch_res.enhanced_prompt or message,
                original_prompt = message,
                provider        = orch_res.provider or "",
                model           = orch_res.model    or "",
                cost_usd        = orch_res.cost_usd  or 0.0,
                latency_ms      = lat,
                seed            = None,
                response_text   = orch_res.response_text or "",
                error           = "",
                fallback_to_llm = False,
                scene           = None,
            )
        except Exception as leg_exc:
            logger.error(f"[ImageOrchestrationService] Legacy fallback also failed: {leg_exc}")
            return ImageGenerationResult(
                is_image        = False,
                fallback_to_llm = True,
                intent          = ImageIntent.NONE,
                original_prompt = message,
                response_text   = "",
                error           = f"new={original_error}; legacy={leg_exc}",
            )

    # ── Streaming version ─────────────────────────────────────────────

    def handle_stream(
        self,
        message:    str,
        session_id: str,
        language:   str              = "vi",
        tools:      list[str] | None = None,
        quality:    str              = "auto",
        style:      Optional[str]    = None,
        provider:   Optional[str]    = None,
    ) -> Generator[dict, None, None]:
        """
        SSE-compatible streaming wrapper.

        Yields:
          {"event": "image_gen_start",  "data": {...}}
          {"event": "image_gen_status", "data": {...}}
          {"event": "image_gen_result", "data": {...}}
          {"event": "image_gen_error",  "data": {...}}

        Yields nothing when the message is not an image request.
        """
        # Run sync handle() and wrap its result into SSE events
        result = self.handle(
            message=message, session_id=session_id, language=language,
            tools=tools, quality=quality, style=style, provider=provider,
        )

        if result.fallback_to_llm and not result.is_image:
            return  # not an image request

        if result.intent != ImageIntent.NONE:
            yield {
                "event": "image_gen_start",
                "data": {
                    "intent":   result.intent.value,
                    "provider": result.provider,
                    "is_edit":  result.intent in (ImageIntent.EDIT, ImageIntent.FOLLOWUP_EDIT),
                },
            }

        if result.is_image:
            yield {
                "event": "image_gen_result",
                "data": {
                    "images_b64":      result.images_b64,
                    "images_url":      result.images_url,
                    "enhanced_prompt": result.enhanced_prompt,
                    "provider":        result.provider,
                    "model":           result.model,
                    "cost_usd":        result.cost_usd,
                    "latency_ms":      result.latency_ms,
                    "response_text":   result.response_text,
                    "intent":          result.intent.value,
                },
            }
        else:
            yield {
                "event": "image_gen_error",
                "data": {
                    "error":           result.error,
                    "fallback_to_llm": result.fallback_to_llm,
                },
            }


# ─────────────────────────────────────────────────────────────────────
# Module-level convenience functions
# ─────────────────────────────────────────────────────────────────────

_service_instance: Optional[ImageOrchestrationService] = None


def _get_service() -> ImageOrchestrationService:
    global _service_instance
    if _service_instance is None:
        _service_instance = ImageOrchestrationService()
    return _service_instance


def handle_image_request(
    message:    str,
    session_id: str,
    language:   str              = "vi",
    tools:      list[str] | None = None,
    quality:    str              = "auto",
    style:      Optional[str]    = None,
    provider:   Optional[str]    = None,
) -> ImageGenerationResult:
    """
    Module-level convenience function.  Instantiates a shared
    ImageOrchestrationService on first call.

    Usage:
        from app.services.image_orchestrator import handle_image_request
        result = handle_image_request(message, session_id, language="vi")
    """
    return _get_service().handle(
        message=message, session_id=session_id, language=language,
        tools=tools, quality=quality, style=style, provider=provider,
    )


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _map_intent(core_intent) -> ImageIntent:
    """
    Convert a core.image_gen.intent.ImageIntent value to the app-layer enum.
    Both enums share the same string values so string comparison works even
    when the types differ (avoids hard import cycle).
    """
    val = getattr(core_intent, "value", str(core_intent))
    try:
        return ImageIntent(val)
    except ValueError:
        return ImageIntent.GENERATE


_EDIT_VERBS = {
    "thêm": "add", "thay": "replace", "xóa": "remove", "bỏ": "remove",
    "đổi": "change", "chỉnh": "adjust", "sửa": "fix",
    "add": "add", "remove": "remove", "replace": "replace",
    "change": "change", "adjust": "adjust", "make": "change",
}


def _extract_edit_verb(message: str) -> str:
    lower = message.lower()
    for kw, verb in _EDIT_VERBS.items():
        if kw in lower:
            return verb
    return "edit"


def _build_response_text(
    images_url: list[str],
    images_b64: list[str],
    prompt:     str,
    provider:   str,
    latency_ms: float,
) -> str:
    count = len(images_url) or len(images_b64)
    s     = "s" if count > 1 else ""
    lat   = f"{latency_ms / 1000:.1f}s"
    prov  = f" via {provider}" if provider else ""
    return (
        f"Generated {count} image{s}{prov} in {lat}.\n"
        f"Prompt used: {prompt[:120]}{'…' if len(prompt) > 120 else ''}"
    )
