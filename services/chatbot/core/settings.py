"""
core/settings.py — Typed settings object for the chatbot service.

Provides a single ``Settings`` instance that reads environment variables in a
grouped, testable way.  Existing code that imports directly from ``core.config``
continues to work unchanged — this module adds an additional, preferred import
path for new code.

Usage:
    from core.settings import settings

    if settings.hermes.enabled:
        ...
    url = settings.stable_diffusion.api_url
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).lower() in ("1", "true", "yes", "on")


def _int(key: str, default: int = 0) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# Provider / API key groups
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProviderKeys:
    openai: str | None = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    deepseek: str | None = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY"))
    qwen: str | None = field(default_factory=lambda: os.getenv("QWEN_API_KEY"))
    huggingface: str | None = field(default_factory=lambda: os.getenv("HUGGINGFACE_API_KEY"))
    grok: str | None = field(default_factory=lambda: os.getenv("GROK_API_KEY"))
    openrouter: str | None = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY"))
    stepfun: str | None = field(default_factory=lambda: os.getenv("STEPFUN_API_KEY"))
    gemini: list[str] = field(
        default_factory=lambda: [k for k in [os.getenv("GEMINI_API_KEY_1")] if k]
    )
    serpapi: str | None = field(default_factory=lambda: os.getenv("SERPAPI_API_KEY"))
    saucenao: str | None = field(default_factory=lambda: os.getenv("SAUCENAO_API_KEY"))
    google_search_1: str | None = field(default_factory=lambda: os.getenv("GOOGLE_SEARCH_API_KEY_1"))
    google_search_2: str | None = field(default_factory=lambda: os.getenv("GOOGLE_SEARCH_API_KEY_2"))
    google_cse_id: str | None = field(default_factory=lambda: os.getenv("GOOGLE_CSE_ID"))
    github_token: str | None = field(default_factory=lambda: os.getenv("GITHUB_TOKEN"))


# ---------------------------------------------------------------------------
# Sidecar / feature settings
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HermesSettings:
    enabled: bool = field(default_factory=lambda: _bool("HERMES_ENABLED"))
    api_url: str = field(default_factory=lambda: os.getenv("HERMES_API_URL", "http://localhost:8080"))
    api_key: str = field(default_factory=lambda: os.getenv("HERMES_API_KEY", ""))
    timeout: int = field(default_factory=lambda: _int("HERMES_TIMEOUT", 120))


@dataclass(frozen=True)
class CharacterSelectSettings:
    enabled: bool = field(default_factory=lambda: _bool("CHARACTER_SELECT_ENABLED"))
    url: str = field(default_factory=lambda: os.getenv("CHARACTER_SELECT_URL", "http://localhost:51028"))
    port: int = field(default_factory=lambda: _int("CHARACTER_SELECT_PORT", 51028))
    auto_start: bool = field(default_factory=lambda: _bool("CHARACTER_SELECT_AUTO_START"))
    path: str = field(default_factory=lambda: os.getenv("CHARACTER_SELECT_PATH", "./character_select_stand_alone_app-main"))
    timeout: int = field(default_factory=lambda: _int("CHARACTER_SELECT_TIMEOUT", 5))


@dataclass(frozen=True)
class ReasoningPipelineSettings:
    enabled: bool = field(default_factory=lambda: _bool("REASONING_PIPELINE"))
    comfy_url: str = field(
        default_factory=lambda: os.getenv(
            "REASONING_PIPELINE_COMFY_URL",
            os.getenv("COMFYUI_URL", "http://localhost:8188"),
        )
    )
    max_panels: int = field(default_factory=lambda: _int("REASONING_PIPELINE_MAX_PANELS", 9))
    max_correction_passes: int = field(
        default_factory=lambda: _int("REASONING_PIPELINE_MAX_CORRECTION_PASSES", 0)
    )


@dataclass(frozen=True)
class Last30DaysSettings:
    enabled: bool = field(default_factory=lambda: _bool("LAST30DAYS_ENABLED"))
    script_path: str = field(default_factory=lambda: os.getenv("LAST30DAYS_SCRIPT_PATH", ""))
    python_path: str = field(default_factory=lambda: os.getenv("LAST30DAYS_PYTHON_PATH", ""))
    timeout: int = field(default_factory=lambda: _int("LAST30DAYS_TIMEOUT", 180))


@dataclass(frozen=True)
class StableDiffusionSettings:
    api_url: str = field(default_factory=lambda: os.getenv("SD_API_URL", "http://127.0.0.1:7861"))


# ---------------------------------------------------------------------------
# Root settings object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    """Top-level settings object.  Instantiate once; treat as immutable."""

    keys: ProviderKeys = field(default_factory=ProviderKeys)
    hermes: HermesSettings = field(default_factory=HermesSettings)
    character_select: CharacterSelectSettings = field(default_factory=CharacterSelectSettings)
    reasoning_pipeline: ReasoningPipelineSettings = field(default_factory=ReasoningPipelineSettings)
    last30days: Last30DaysSettings = field(default_factory=Last30DaysSettings)
    stable_diffusion: StableDiffusionSettings = field(default_factory=StableDiffusionSettings)

    # Paths — resolved at instantiation time
    @property
    def chatbot_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def root_dir(self) -> Path:
        return self.chatbot_dir.parent.parent

    @property
    def memory_dir(self) -> Path:
        return self.chatbot_dir / "data" / "memory"

    @property
    def image_storage_dir(self) -> Path:
        return self.chatbot_dir / "Storage" / "Image_Gen"

    @property
    def comfyui_output_dir(self) -> Path:
        default = (self.root_dir / "ComfyUI" / "output").resolve()
        return Path(os.getenv("COMFYUI_OUTPUT_DIR", str(default)))


# Module-level singleton — lazily populated so tests can set env vars first.
settings = Settings()
