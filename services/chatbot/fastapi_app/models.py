"""
Pydantic models for request/response validation
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────

class ModelName(str, Enum):
    grok = "grok"
    openai = "openai"
    deepseek = "deepseek"
    qwen = "qwen"
    gemini = "gemini"
    local = "local"


class ContextType(str, Enum):
    casual = "casual"
    psychological = "psychological"
    lifestyle = "lifestyle"
    academic = "academic"
    creative = "creative"
    code = "code"


class VideoResolution(str, Enum):
    portrait = "720x1280"
    landscape = "1280x720"
    square = "1080x1920"


class VideoSeconds(str, Enum):
    short = "4"
    medium = "8"
    long = "12"


class VideoModel(str, Enum):
    sora_2 = "sora-2"
    sora_2_pro = "sora-2-pro"


# ── Chat ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message")
    model: str = Field("grok", description="AI model to use")
    context: str = Field("casual", description="Conversation context")
    deep_thinking: bool = Field(False, description="Enable detailed reasoning")
    thinking_mode: str = Field("instant", description="Thinking mode: instant or multi-thinking")
    language: str = Field("vi", description="Response language")
    custom_prompt: str = Field("", description="Custom system prompt")
    memory_ids: list[str] = Field(default_factory=list)
    history: list[dict[str, Any]] | None = None
    mcp_selected_files: list[str] = Field(default_factory=list)
    # Agent / tool config
    agent_config: dict[str, Any] | None = None
    tools: list[str] = Field(default_factory=list)
    # Vision (base64 data-URLs from frontend)
    images: list[str] = Field(default_factory=list, description="Base64 data-URL images for vision models")
    # ── Image generation controls ──────────────────────────────────
    enable_image_gen: bool = Field(
        True,
        description="Set False to skip image orchestration and go straight to LLM",
    )
    image_quality: str = Field(
        "auto",
        description="Image quality hint: auto | fast | quality | free | cheap",
    )
    # RAG
    rag_collection_ids: list[str] = Field(default_factory=list, description="RAG collections to search")
    rag_top_k: int = Field(5, description="Max RAG results to retrieve")
    # ── Multi-agent council (all optional, safe defaults) ─────────
    agent_mode: str = Field(
        "off",
        description="Agent orchestration mode: off | council | grok_native_research",
    )
    agent_strategy: str = Field(
        "sequential",
        description="Council execution strategy: sequential | parallel_research",
    )
    max_agent_iterations: int = Field(
        2, ge=1, le=5,
        description="Max Planner→Researcher→Critic rounds before forced synthesis",
    )
    emit_agent_events: bool = Field(
        False,
        description="When True, stream emits council_step SSE events for live progress",
    )
    preferred_planner_model: str | None = Field(
        None, description="Override model for the Planner agent",
    )
    preferred_researcher_model: str | None = Field(
        None, description="Override model for the Researcher agent",
    )
    preferred_critic_model: str | None = Field(
        None, description="Override model for the Critic agent",
    )
    preferred_synthesizer_model: str | None = Field(
        None, description="Override model for the Synthesizer agent",
    )
    # ── xAI native multi-agent (only used when agent_mode="grok_native_research") ──
    reasoning_effort: str = Field(
        "high",
        description="xAI reasoning effort: low | medium | high (controls agent count: low/medium→4, high→16)",
    )
    enable_web_search: bool = Field(
        True, description="Enable xAI server-side web search tool",
    )
    enable_x_search: bool = Field(
        False, description="Enable xAI server-side X/Twitter search tool",
    )


class ChatResponse(BaseModel):
    response: str
    model: str
    context: str
    deep_thinking: bool = False
    thinking_process: str | None = None
    citations: list[dict[str, Any]] | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    # ── Image generation result (only when image was generated) ──
    image_result: dict[str, Any] | None = Field(
        None,
        description="Set when an image was generated. Contains intent, provider, "
                    "images_url, images_b64, enhanced_prompt, cost_usd, latency_ms.",
    )
    # ── Multi-agent council (only populated when agent_mode != "off") ──
    agent_run_id: str | None = Field(
        None, description="Unique ID of the council run (None when agent_mode=off)",
    )
    agent_trace_summary: dict[str, Any] | None = Field(
        None,
        description="Condensed council trace: rounds, agents_used, total_tokens, elapsed_seconds",
    )


# ── Streaming ──────────────────────────────────────────────────────────

class StreamRequest(ChatRequest):
    """Identical to ChatRequest; kept separate for clarity"""
    pass


# ── Conversations ──────────────────────────────────────────────────────

class NewConversationRequest(BaseModel):
    model: str = "grok"
    title: str = "New Chat"


class ConversationOut(BaseModel):
    id: str = Field(..., alias="_id")
    title: str = ""
    model: str = "grok"
    created_at: str = ""
    updated_at: str = ""

    class Config:
        populate_by_name = True


# ── Memory ─────────────────────────────────────────────────────────────

class SaveMemoryRequest(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    images: list[dict[str, Any]] = Field(default_factory=list)


class UpdateMemoryRequest(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


# ── Images ─────────────────────────────────────────────────────────────

class SaveImageRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image data")
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Video Generation (Sora 2) ─────────────────────────────────────────

class VideoGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Video generation prompt")
    size: VideoResolution = Field(
        VideoResolution.landscape,
        description="Aspect ratio: 16:9 (landscape), 9:16 (portrait), or 1:1 (square)",
    )
    seconds: VideoSeconds = Field(
        VideoSeconds.medium,
        description="Duration: 4, 8, or 12 seconds",
    )
    model: VideoModel = Field(
        VideoModel.sora_2,
        description="Model: sora-2 ($0.10/s) or sora-2-pro ($0.30/s)",
    )


class VideoStatusResponse(BaseModel):
    id: str
    status: str  # queued, in_progress, completed, failed
    prompt: str | None = None
    size: str | None = None
    aspect_ratio: str | None = None
    seconds: str | None = None
    model: str | None = None
    progress: int | None = None
    error: str | None = None
    cost_estimate: str | None = None
    created_at: str | None = None
    completed_at: str | None = None
    expires_at: str | None = None
