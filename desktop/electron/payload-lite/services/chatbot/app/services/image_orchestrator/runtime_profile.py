"""
RuntimeProfile
==============
Determines the operating mode for the image orchestrator by reading
existing environment variables.  No new env vars are introduced.

Modes
-----
- **full**:          All services enabled including local GPU (ComfyUI / SD).
- **low_resource**:  Local heavy services disabled; orchestration + remote
                     providers still active.  Ideal for laptop / 8 GB RAM.
- **remote_only**:   Explicit subset of low_resource where *no* local image
                     service URL is configured at all.

Env vars consumed (all pre-existing):
    AUTO_START_IMAGE_SERVICES   0|1   Master toggle for local services
    AUTO_START_COMFYUI          0|1   ComfyUI autostart
    AUTO_START_STABLE_DIFFUSION 0|1   Stable Diffusion autostart
    SD_API_URL                  str   Local SD / ComfyUI URL
    COMFYUI_URL                 str   Local ComfyUI URL
    IMAGE_FIRST_MODE            0|1   Business-logic toggle
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _env_bool(key: str, default: bool = True) -> bool:
    """Read a 0/1 or true/false env var."""
    raw = os.getenv(key, "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    return default


@dataclass(frozen=True)
class RuntimeProfile:
    """Immutable snapshot of the current operating mode."""

    # ── derived booleans ─────────────────────────────────────────────
    auto_start_image_services: bool
    auto_start_comfyui: bool
    auto_start_stable_diffusion: bool
    image_first_mode: bool

    # Resolved URLs (empty string = not configured)
    comfyui_url: str
    sd_api_url: str

    @property
    def mode(self) -> str:
        """Return 'full', 'low_resource', or 'remote_only'."""
        if self.local_services_enabled:
            return "full"
        if self.comfyui_url or self.sd_api_url:
            # URLs are set but auto-start is off → low_resource
            # (user might still have a remote ComfyUI box)
            return "low_resource"
        return "remote_only"

    @property
    def local_services_enabled(self) -> bool:
        """True when at least one local image service is set to auto-start."""
        if not self.auto_start_image_services:
            return False
        return self.auto_start_comfyui or self.auto_start_stable_diffusion

    @property
    def is_low_resource(self) -> bool:
        """True when the system should avoid local GPU services."""
        return self.mode in ("low_resource", "remote_only")

    @property
    def skip_comfyui_provider(self) -> bool:
        """True when ComfyUI provider should not be registered at all."""
        # Skip when user explicitly disabled local services
        if not self.auto_start_image_services:
            return True
        if not self.auto_start_comfyui:
            return True
        return False

    @property
    def prefer_local_when_healthy(self) -> bool:
        """True when healthy local providers should be tried before remote."""
        return self.mode == "full"

    def describe(self) -> str:
        """Return a human-readable summary (for logging)."""
        lines = [
            f"RuntimeProfile: mode={self.mode}",
            f"  local_services_enabled: {self.local_services_enabled}",
            f"  AUTO_START_IMAGE_SERVICES={self.auto_start_image_services}",
            f"  AUTO_START_COMFYUI={self.auto_start_comfyui}",
            f"  AUTO_START_STABLE_DIFFUSION={self.auto_start_stable_diffusion}",
            f"  IMAGE_FIRST_MODE={self.image_first_mode}",
            f"  COMFYUI_URL={self.comfyui_url or '(not set)'}",
            f"  SD_API_URL={self.sd_api_url or '(not set)'}",
            f"  skip_comfyui_provider={self.skip_comfyui_provider}",
            f"  prefer_local_when_healthy={self.prefer_local_when_healthy}",
        ]
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# Module-level singleton
# ─────────────────────────────────────────────────────────────────────

_profile: RuntimeProfile | None = None


def get_runtime_profile() -> RuntimeProfile:
    """Return the shared RuntimeProfile, reading env vars on first call."""
    global _profile
    if _profile is None:
        _profile = RuntimeProfile(
            auto_start_image_services=_env_bool("AUTO_START_IMAGE_SERVICES", default=True),
            auto_start_comfyui=_env_bool("AUTO_START_COMFYUI", default=True),
            auto_start_stable_diffusion=_env_bool("AUTO_START_STABLE_DIFFUSION", default=True),
            image_first_mode=_env_bool("IMAGE_FIRST_MODE", default=False),
            comfyui_url=os.getenv("COMFYUI_URL", "").strip(),
            sd_api_url=os.getenv("SD_API_URL", "").strip(),
        )
        logger.info(f"[RuntimeProfile] Initialized:\n{_profile.describe()}")
    return _profile


def reset_runtime_profile() -> None:
    """Clear the cached profile (for testing)."""
    global _profile
    _profile = None


def is_low_resource_mode() -> bool:
    """Convenience: True when local heavy services are disabled."""
    return get_runtime_profile().is_low_resource
