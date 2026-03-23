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
    portrait_wide = "1024x1792"
    landscape_wide = "1792x1024"


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
    language: str = Field("vi", description="Response language")
    custom_prompt: str = Field("", description="Custom system prompt")
    memory_ids: list[str] = Field(default_factory=list)
    history: list[dict[str, Any]] | None = None
    mcp_selected_files: list[str] = Field(default_factory=list)
    # Agent / tool config
    agent_config: dict[str, Any] | None = None
    tools: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    model: str
    context: str
    deep_thinking: bool = False
    thinking_process: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


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
        description="Video size: 720x1280 | 1280x720 | 1024x1792 | 1792x1024",
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
    seconds: str | None = None
    model: str | None = None
    progress: int | None = None
    error: str | None = None
    cost_estimate: str | None = None
    created_at: str | None = None
    completed_at: str | None = None
    expires_at: str | None = None
