"""
app.services.image_orchestrator
================================
High-level image orchestration layer that wraps the existing
core/image_gen provider stack with structured scene planning.

Public API
----------
    # Functional shortcut (most callers use this)
    from app.services.image_orchestrator import handle_image_request

    result = handle_image_request(
        message    = "vẽ cô gái anime tóc hồng dưới ánh trăng",
        session_id = "user-abc",
        language   = "vi",
        tools      = ["image-generation"],   # optional
        quality    = "quality",              # auto|fast|quality|free|cheap
        style      = "anime",               # or None for auto-detect
        provider   = None,                  # or "fal", "openai", "comfyui", …
    )

    if result.is_image:
        images = result.images_url          # list[str]
        prompt = result.enhanced_prompt     # str
    elif result.fallback_to_llm:
        pass  # message was not an image request; handle with LLM

    # Class-based (useful when you need streaming or dependency injection)
    from app.services.image_orchestrator import ImageOrchestrationService

    svc    = ImageOrchestrationService()
    result = svc.handle(message, session_id, language="vi")
    for event in svc.handle_stream(message, session_id):
        print(event)

Schema types
------------
    ImageIntent               — GENERATE | EDIT | FOLLOWUP_EDIT | NONE
    SceneSpec                 — structured visual description of the scene
    ImageGenerationRequest    — typed request for text-to-image generation
    ImageFollowupRequest      — typed request for image editing
    ImageGenerationResult     — unified result returned by handle_image_request()
"""

from .orchestrator import (
    ImageOrchestrationService,
    handle_image_request,
)

from .scene_planner import merge_scene_delta

from .schemas import (
    ImageIntent,
    SceneSpec,
    ImageGenerationRequest,
    ImageFollowupRequest,
    ImageGenerationResult,
)

from .session_memory import (
    ImageSessionMemory,
    SessionMemoryStore,
    get_session_memory_store,
)

from .runtime_profile import (
    RuntimeProfile,
    get_runtime_profile,
    is_low_resource_mode,
)

__all__ = [
    # Service
    "ImageOrchestrationService",
    "handle_image_request",
    "merge_scene_delta",
    # Schemas
    "ImageIntent",
    "SceneSpec",
    "ImageGenerationRequest",
    "ImageFollowupRequest",
    "ImageGenerationResult",
    # Session memory
    "ImageSessionMemory",
    "SessionMemoryStore",
    "get_session_memory_store",
    # Runtime profile
    "RuntimeProfile",
    "get_runtime_profile",
    "is_low_resource_mode",
]
