"""
ImageOrchestrator — unified entry point for image generation inside the chat flow.

What it does:
  1. Detects image intent (generate / edit / followup) via intent.py
  2. Plans generation parameters (quality, size, style, provider)
  3. Executes via the existing ImageGenerationRouter
  4. Maintains per-session ImageSession (multi-turn memory)
  5. Returns a structured result that chat.py / stream.py can consume
  6. Falls back silently to LLM if disabled or on any unhandled exception

Usage in chat.py / stream.py:
    orchestrator = get_image_orchestrator_for_session(request)
    orch_result  = orchestrator.handle(message, language=language, tools=tools)
    if orch_result.is_image:
        return ChatResponse(response=orch_result.response_text, ...)
    # else: fall through to normal chatbot.chat()
"""

from __future__ import annotations

import base64
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Generator, Optional

from .intent import ImageIntent, IntentResult, detect_intent
from .providers.base import ImageMode, ImageResult
from .router import ImageGenerationRouter, QualityMode
from .session import ImageSession
from .storage import ImageStorage

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────

@dataclass
class OrchestratorResult:
    """Returned by ImageOrchestrator.handle()."""
    is_image:       bool            = False   # True → image was generated
    intent:         ImageIntent     = ImageIntent.NONE
    intent_result:  Optional[IntentResult] = None
    images_b64:     list[str]       = field(default_factory=list)
    images_url:     list[str]       = field(default_factory=list)
    enhanced_prompt: str            = ""
    original_prompt: str            = ""
    provider:       str             = ""
    model:          str             = ""
    cost_usd:       float           = 0.0
    latency_ms:     float           = 0.0
    response_text:  str             = ""      # Formatted markdown for the chat UI
    error:          str             = ""
    fallback_to_llm: bool           = False   # True → caller should use LLM instead


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _orchestrator_enabled() -> bool:
    """
    Globally enable/disable via IMAGE_ORCHESTRATOR_ENABLED env var.

    Defaults to True when at least one image provider key is present.
    Set IMAGE_ORCHESTRATOR_ENABLED=0 to hard-disable.
    """
    flag = os.getenv("IMAGE_ORCHESTRATOR_ENABLED", "").lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return any([
        os.getenv("FAL_API_KEY"),
        os.getenv("REPLICATE_API_TOKEN"),
        os.getenv("BFL_API_KEY"),
        os.getenv("TOGETHER_API_KEY"),
        os.getenv("OPENAI_API_KEY"),
        os.getenv("COMFYUI_URL"),
    ])


def _fetch_url_as_b64(url: str) -> Optional[str]:
    """Download an image URL and return base64-encoded bytes (best-effort)."""
    try:
        import httpx
        with httpx.Client(timeout=20) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return base64.b64encode(resp.content).decode("utf-8")
    except Exception as exc:
        logger.warning(f"[Orchestrator] URL fetch failed: {exc}")
    return None


def _build_response_text(
    message:    str,
    img_result: ImageResult,
    stored_urls: list[str],
    intent:     ImageIntent,
    is_edit:    bool,
    language:   str,
    latency_ms: float,
) -> str:
    """Build a formatted markdown + inline-HTML response for the chat UI."""
    vi = language.startswith("vi")

    action_label = {
        ImageIntent.GENERATE:      "🎨 Ảnh đã được tạo!" if vi else "🎨 Image Generated!",
        ImageIntent.EDIT:          "✏️ Ảnh đã được chỉnh sửa!" if vi else "✏️ Image Edited!",
        ImageIntent.FOLLOWUP_EDIT: "✏️ Đã cập nhật ảnh!" if vi else "✏️ Image Updated!",
    }.get(intent, "🎨 Image Generated!")

    lines: list[str] = [f"## {action_label}", ""]

    if vi:
        lines.append(f"**Mô tả gốc:** {message}")
    else:
        lines.append(f"**Your request:** {message}")

    enhanced = img_result.prompt_used or message
    if enhanced and enhanced != message:
        label = "**Prompt được tối ưu:**" if vi else "**Enhanced prompt:**"
        lines.append(f"\n{label}\n```\n{enhanced}\n```")

    lines.append("\n**Generated Image:**")

    for b64 in img_result.images_b64:
        lines.append(
            f'<img src="data:image/png;base64,{b64}" '
            f'alt="Generated Image" '
            f'style="max-width:100%;border-radius:8px;margin:10px 0;cursor:pointer;" '
            f'class="generated-preview">'
        )

    for url in stored_urls:
        if not url.startswith("data:"):
            lines.append(
                f'<img src="{url}" alt="Generated Image" '
                f'style="max-width:100%;border-radius:8px;margin:10px 0;cursor:pointer;" '
                f'class="generated-preview">'
            )

    cloud = " | ".join(f"[Open]({u})" for u in stored_urls[:3] if not u.startswith("data:"))
    if cloud:
        lines.append(f"\n☁️ **URLs:** {cloud}")

    model_label = f" ({img_result.model})" if img_result.model else ""
    lines.extend([
        "\n---",
        f"🎯 **Info:** Provider: `{img_result.provider}`{model_label}"
        f" · Size: {img_result.metadata.get('width', '?')}×{img_result.metadata.get('height', '?')}"
        f" · Cost: ${img_result.cost_usd:.4f}"
        f" · {latency_ms / 1000:.1f}s",
    ])

    if is_edit:
        hint = (
            "\n💡 *Bạn có thể tiếp tục chỉnh sửa bằng cách mô tả thay đổi muốn thực hiện.*"
            if vi else
            "\n💡 *Keep editing by describing the next change you want.*"
        )
    else:
        hint = (
            '\n💡 *Để chỉnh sửa ảnh, mô tả thay đổi bạn muốn (vd: "thêm cầu vồng", "đổi nền trắng").*'
            if vi else
            '\n💡 *To edit this image, describe the change you want (e.g. "add a rainbow", "white background").*'
        )
    lines.append(hint)

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────

class ImageOrchestrator:
    """
    Per-session image orchestration pipeline.

    Created once per session via get_image_orchestrator_for_session() in
    fastapi_app/dependencies.py — same lifetime as the ChatbotAgent cache.

    The ImageGenerationRouter and ImageStorage are class-level singletons
    (expensive to init due to provider key scanning) shared across sessions.
    """

    # Class-level singletons shared by all sessions
    _shared_router:  Optional[ImageGenerationRouter] = None
    _shared_storage: Optional[ImageStorage]          = None

    def __init__(self, session_id: str):
        self.session_id    = session_id
        self._img_session  = ImageSession(conversation_id=session_id)
        self._enabled      = _orchestrator_enabled()

    # ── Shared singletons ─────────────────────────────────────────────

    @classmethod
    def _get_router(cls) -> ImageGenerationRouter:
        if cls._shared_router is None:
            cls._shared_router = ImageGenerationRouter()
        return cls._shared_router

    @classmethod
    def _get_storage(cls) -> ImageStorage:
        if cls._shared_storage is None:
            cls._shared_storage = ImageStorage()
        return cls._shared_storage

    # ── Session state accessors ───────────────────────────────────────

    @property
    def has_previous_image(self) -> bool:
        return bool(self._img_session.last_image)

    @property
    def last_image_b64(self) -> Optional[str]:
        return self._img_session.last_image_b64

    @property
    def last_image_url(self) -> Optional[str]:
        return self._img_session.last_image_url

    # ── Public sync API ───────────────────────────────────────────────

    def handle(
        self,
        message: str,
        language: str  = "vi",
        tools:    list[str] | None = None,
    ) -> OrchestratorResult:
        """
        Main entry point (sync).

        Returns:
          - OrchestratorResult(is_image=True, ...) if image was generated
          - OrchestratorResult(fallback_to_llm=True) if message is not for images
          - OrchestratorResult(is_image=False, error=..., fallback_to_llm=True)
            if generation was attempted but failed → caller should use LLM fallback
        """
        tools = tools or []

        if not self._enabled:
            return OrchestratorResult(fallback_to_llm=True)

        explicit_tool = "image-generation" in tools
        intent_result = detect_intent(message, has_previous_image=self.has_previous_image)

        # Not an image request and tool not forced → pass to LLM
        if intent_result.intent == ImageIntent.NONE and not explicit_tool:
            return OrchestratorResult(fallback_to_llm=True)

        # Explicit tool but intent detector found nothing → force GENERATE
        if explicit_tool and intent_result.intent == ImageIntent.NONE:
            intent_result = IntentResult(
                intent     = ImageIntent.GENERATE,
                confidence = 0.9,
                debug      = {"reason": "explicit_tool"},
            )

        return self._execute(message, intent_result, language)

    # ── Streaming public API ──────────────────────────────────────────

    def handle_stream(
        self,
        message:  str,
        language: str              = "vi",
        tools:    list[str] | None = None,
    ) -> Generator[dict, None, None]:
        """
        Streaming version — yields SSE-ready dicts.

        Events emitted:
          {"event": "image_gen_start",  "data": {intent, quality, …}}
          {"event": "image_gen_status", "data": {step, phase}}
          {"event": "image_gen_result", "data": {images_b64, images_url, …}}
          {"event": "image_gen_error",  "data": {error, fallback_to_llm}}

        If the message is not an image request, yields nothing — the caller
        should proceed with normal LLM streaming.
        """
        tools = tools or []

        if not self._enabled:
            return

        explicit_tool = "image-generation" in tools
        intent_result = detect_intent(message, has_previous_image=self.has_previous_image)

        if intent_result.intent == ImageIntent.NONE and not explicit_tool:
            return  # not an image request

        if explicit_tool and intent_result.intent == ImageIntent.NONE:
            intent_result = IntentResult(
                intent     = ImageIntent.GENERATE,
                confidence = 0.9,
                debug      = {"reason": "explicit_tool"},
            )

        intent = intent_result.intent

        yield {
            "event": "image_gen_start",
            "data": {
                "intent":      intent.value,
                "quality":     intent_result.quality_hint,
                "style":       intent_result.style_hint,
                "dimensions":  f"{intent_result.width}×{intent_result.height}",
                "is_edit":     intent in (ImageIntent.EDIT, ImageIntent.FOLLOWUP_EDIT),
                "has_previous": self.has_previous_image,
                "confidence":  round(intent_result.confidence, 2),
            },
        }

        yield {
            "event": "image_gen_status",
            "data": {"step": "Selecting best provider…", "phase": "select"},
        }

        orch_result = self._execute(message, intent_result, language)

        if not orch_result.is_image:
            yield {
                "event": "image_gen_error",
                "data": {
                    "error":           orch_result.error or "Generation failed",
                    "fallback_to_llm": orch_result.fallback_to_llm,
                },
            }
            return

        yield {
            "event": "image_gen_result",
            "data": {
                "images_b64":      orch_result.images_b64,
                "images_url":      orch_result.images_url,
                "enhanced_prompt": orch_result.enhanced_prompt,
                "provider":        orch_result.provider,
                "model":           orch_result.model,
                "cost_usd":        orch_result.cost_usd,
                "latency_ms":      orch_result.latency_ms,
                "response_text":   orch_result.response_text,
                "intent":          intent.value,
            },
        }

    # ── Internal pipeline ─────────────────────────────────────────────

    def _execute(
        self,
        message:       str,
        intent_result: IntentResult,
        language:      str,
    ) -> OrchestratorResult:
        """Run the full generation pipeline (synchronous)."""
        t_start = time.monotonic()

        try:
            router  = self._get_router()
            storage = self._get_storage()
            intent  = intent_result.intent

            # ── Mode + source image (i2i for edits) ──────────────────
            source_b64: Optional[str] = None
            is_edit = intent in (ImageIntent.EDIT, ImageIntent.FOLLOWUP_EDIT)

            if is_edit:
                source_b64 = self.last_image_b64
                if not source_b64 and self.last_image_url:
                    source_b64 = _fetch_url_as_b64(self.last_image_url)

            mode = "i2i" if (is_edit and source_b64) else "t2i"

            # ── Grounding hook: inject session image history ──────────
            session_context = self._img_session.get_context_for_enhancement()

            # ── Consistency hook: preserve active style across edits ──
            style = intent_result.style_hint
            if not style and self._img_session.active_style:
                style = self._img_session.active_style

            # ── Generate ─────────────────────────────────────────────
            logger.info(
                f"[Orchestrator:{self.session_id[:8]}] "
                f"intent={intent.value} mode={mode} quality={intent_result.quality_hint} "
                f"style={style} {intent_result.width}×{intent_result.height}"
            )

            img_result: ImageResult = router.generate(
                prompt           = message,
                mode             = mode,
                quality          = intent_result.quality_hint,
                style            = style,
                width            = intent_result.width,
                height           = intent_result.height,
                source_image_b64 = source_b64,
                enhance_prompt   = True,
                context          = session_context or None,
            )

            latency_ms = (time.monotonic() - t_start) * 1000

            if not img_result.success:
                logger.warning(f"[Orchestrator] Generation failed: {img_result.error}")
                return OrchestratorResult(
                    intent          = intent,
                    intent_result   = intent_result,
                    error           = img_result.error or "Generation failed",
                    fallback_to_llm = True,
                )

            # ── Update persistent session ─────────────────────────────
            self._img_session.add_generation(
                user_prompt     = message,
                enhanced_prompt = img_result.prompt_used or message,
                result          = img_result,
                is_edit         = is_edit,
            )
            if intent_result.style_hint:
                self._img_session.active_style = intent_result.style_hint

            # ── Store image ───────────────────────────────────────────
            stored_urls: list[str] = list(img_result.images_url)
            for b64 in img_result.images_b64:
                try:
                    store_result = storage.save(
                        image_b64 = b64,
                        prompt    = img_result.prompt_used or message,
                        provider  = img_result.provider,
                        metadata  = {
                            "original_message": message,
                            "model":            img_result.model,
                            "session_id":       self.session_id,
                        },
                    )
                    url = store_result.get("url")
                    if url:
                        stored_urls.append(url)
                except Exception as store_err:
                    logger.warning(f"[Orchestrator] Storage failed: {store_err}")

            # ── Build chat response text ──────────────────────────────
            response_text = _build_response_text(
                message     = message,
                img_result  = img_result,
                stored_urls = stored_urls,
                intent      = intent,
                is_edit     = is_edit,
                language    = language,
                latency_ms  = latency_ms,
            )

            return OrchestratorResult(
                is_image        = True,
                intent          = intent,
                intent_result   = intent_result,
                images_b64      = img_result.images_b64,
                images_url      = stored_urls,
                enhanced_prompt = img_result.prompt_used or message,
                original_prompt = message,
                provider        = img_result.provider,
                model           = img_result.model,
                cost_usd        = img_result.cost_usd,
                latency_ms      = latency_ms,
                response_text   = response_text,
            )

        except Exception as exc:
            logger.error(f"[Orchestrator] Unexpected error: {exc}", exc_info=True)
            return OrchestratorResult(
                error           = str(exc),
                fallback_to_llm = True,
            )
