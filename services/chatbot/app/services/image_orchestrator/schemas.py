"""
Image Orchestrator Schemas
==========================
Typed data contracts for the image orchestration layer.
All fields kept consistent with the existing core/image_gen types so that
objects can be handed directly to ImageGenerationRouter.generate().
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ─────────────────────────────────────────────────────────────────────
# Intent classification
# ─────────────────────────────────────────────────────────────────────

class ImageIntent(str, Enum):
    """What the user wants to do with an image."""

    GENERATE      = "generate"    # New image from text
    EDIT          = "edit"        # Modify the last image explicitly
    FOLLOWUP_EDIT = "followup"    # Short follow-up that refines last image
    NONE          = "none"        # Not an image request → hand to LLM


class PlanClassification(str, Enum):
    """
    Fine-grained classification produced by ScenePlanner.classify().
    More granular than ImageIntent: focused on how the planner should act.
    """
    GENERATE      = "generate"      # Brand-new image from scratch
    EDIT_FOLLOWUP = "edit_followup" # Edit / refine the previous image
    UNCERTAIN     = "uncertain"     # Ambiguous – caller may ask for clarification


@dataclass
class EditOperation:
    """
    A single edit command parsed from a follow-up user message.

    Examples
    --------
    "thêm kính"                 → EditOperation("add",    "glasses")
    "bỏ cái mũ"                 → EditOperation("remove", "hat")
    "đổi tóc thành trắng"       → EditOperation("change", "hair",   new_value="white")
    "làm trời tối hơn"          → EditOperation("modify", "sky",    modifier="darker")
    "thêm chữ SALE 50%"         → EditOperation("add_text", "SALE 50%")
    "giữ nhân vật cũ"           → EditOperation("keep",   "character")
    """
    operation:  str                # "add" | "remove" | "change" | "modify" | "add_text" | "keep"
    target:     str                # target in English ("glasses", "hair", "sky")
    new_value:  Optional[str] = None   # for change/add ("white", "forest")
    modifier:   Optional[str] = None   # for modify ("darker", "bigger")
    raw_target: Optional[str] = None   # original Vietnamese word (for debugging)


# ─────────────────────────────────────────────────────────────────────
# Scene description (output of scene_planner.py)
# ─────────────────────────────────────────────────────────────────────

@dataclass
class SceneSpec:
    """
    Structured description of an image scene.
    Produced by ScenePlanner and consumed by PromptBuilder.

    Example
    -------
    User says: "vẽ một cô gái anime tóc hồng ngồi dưới ánh trăng"

    SceneSpec(
        subject        = "anime girl with pink hair",
        background     = "moonlit night, outdoors",
        lighting       = "soft moonlight, cool blue tones",
        mood           = "peaceful, ethereal",
        style          = "anime",
        quality_preset = "quality",
        aspect_ratio   = "portrait",
        width          = 768,
        height         = 1024,
        negative_hints = ["blurry", "low quality"],
        extra_tags     = ["detailed", "studio ghibli inspired"],
    )
    """

    # Core visual description
    subject:        str            = ""     # main subject of the image
    action:         str            = ""     # what the subject is doing
    background:     str            = ""     # environment / setting
    lighting:       str            = ""     # lighting conditions
    mood:           str            = ""     # emotional tone / atmosphere

    # Style & quality
    style:          Optional[str]  = None   # "anime", "photorealistic", "sketch", …
    quality_preset: str            = "auto" # "auto"|"fast"|"quality"|"free"|"cheap"
    extra_tags:     list[str]      = field(default_factory=list)  # additional prompt tags
    negative_hints: list[str]      = field(default_factory=list)  # things to avoid

    # Dimensions
    aspect_ratio:   str            = "square"  # "square"|"portrait"|"landscape"|"wide"
    width:          int            = 1024
    height:         int            = 1024

    # Execution hints (optional overrides)
    provider_hint:  Optional[str]  = None   # force a specific provider name
    seed:           Optional[int]  = None
    strength:       float          = 0.75   # i2i denoising (0–1)

    # Source image reference (populated for edit/followup intents)
    source_image_b64: Optional[str] = None
    source_image_url: Optional[str] = None

    # ── Enhanced fields (populated by the new ScenePlanner v2) ────────

    subject_attributes: list[str] = field(default_factory=list)
    # Visual attributes of the subject extracted from the prompt.
    # e.g. ["pink hair", "blue eyes", "wearing glasses", "smiling"]

    composition:        str = ""
    # Framing / camera angle.
    # e.g. "close-up portrait", "bird's eye view", "low angle shot"

    camera:             str = ""
    # Lens / technical camera description.
    # e.g. "85mm prime lens, shallow bokeh", "macro, extreme detail"

    wants_text_in_image:             bool = False
    # True when the user explicitly wants text/typography overlaid.
    # Prevents 'text' from being added to the negative prompt.

    wants_consistency_with_previous: bool = False
    # True when the user says "giữ nhân vật cũ" / "keep the character".
    # Signals that the prompt should anchor to previous subject.

    wants_real_world_accuracy:       bool = False
    # True when the user wants photographic / hyperrealistic output.
    # Overrides style selection toward photorealistic.

    edit_operations:    list["EditOperation"] = field(default_factory=list)
    # Parsed edit commands (populated for EDIT_FOLLOWUP requests only).


# ─────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ImageGenerationRequest:
    """
    A request to generate a brand-new image.
    Created by the orchestrator from user input + SceneSpec.
    """

    # User-facing fields
    original_prompt:  str            # raw user message
    language:         str    = "vi"  # "vi" | "en"
    session_id:       str    = ""

    # Resolved scene (filled by ScenePlanner)
    scene:            Optional[SceneSpec] = None

    # Provider-ready prompt (filled by PromptBuilder)
    enhanced_prompt:  str    = ""

    # Explicit overrides (from UI or API caller)
    quality:          str            = "auto"
    style:            Optional[str]  = None
    provider:         Optional[str]  = None   # force provider name
    model:            Optional[str]  = None   # force model name
    width:            Optional[int]  = None
    height:           Optional[int]  = None
    seed:             Optional[int]  = None

    # Tool context
    tools:            list[str]      = field(default_factory=list)


@dataclass
class ImageFollowupRequest:
    """
    A follow-up / edit request that operates on the last generated image.
    session_memory.py fills source_image_b64 / source_image_url from history.
    """

    original_prompt:  str
    language:         str    = "vi"
    session_id:       str    = ""

    # Edit classification
    intent:           ImageIntent = ImageIntent.FOLLOWUP_EDIT
    edit_verb:        str         = ""   # "add", "remove", "change", "make", …

    # Scene (inherits from memory, then merges user deltas)
    scene:            Optional[SceneSpec] = None
    enhanced_prompt:  str    = ""

    # Source image (populated from session memory)
    source_image_b64: Optional[str] = None
    source_image_url: Optional[str] = None

    # Pass-through overrides
    strength:         float  = 0.7   # lower = more faithful to source
    seed:             Optional[int] = None
    provider:         Optional[str] = None
    tools:            list[str]     = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────
# Result model
# ─────────────────────────────────────────────────────────────────────

@dataclass
class ImageGenerationResult:
    """
    Unified result returned by handle_image_request().
    Either is_image=True (success path) or fallback_to_llm=True (LLM path).
    """

    is_image:         bool         = False
    intent:           ImageIntent  = ImageIntent.NONE

    # Generated image data
    images_b64:       list[str]    = field(default_factory=list)
    images_url:       list[str]    = field(default_factory=list)

    # What was actually sent to the model
    enhanced_prompt:  str          = ""
    original_prompt:  str          = ""

    # Provider telemetry
    provider:         str          = ""
    model:            str          = ""
    cost_usd:         float        = 0.0
    latency_ms:       float        = 0.0
    seed:             Optional[int] = None

    # UI response (pre-rendered markdown + inline HTML)
    response_text:    str          = ""

    # Error / fallback path
    error:            str          = ""
    fallback_to_llm:  bool         = False

    # Scene spec that produced this image (useful for debugging / continuation)
    scene:            Optional[SceneSpec] = None


# ─────────────────────────────────────────────────────────────────────
# Plan result (output of ScenePlanner.classify_and_plan)
# ─────────────────────────────────────────────────────────────────────

@dataclass
class PlanResult:
    """
    Combined output of ScenePlanner.classify_and_plan().
    Bundles the classification decision, the structured SceneSpec,
    the parsed edit operations, and a debug info dict.
    """
    classification: PlanClassification
    scene:          SceneSpec
    edit_ops:       list[EditOperation]  = field(default_factory=list)
    confidence:     float                = 1.0
    debug_info:     dict                 = field(default_factory=dict)
