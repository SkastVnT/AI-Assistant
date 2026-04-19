"""
Feature flags loader — reads config/features.json
Usage in any module:
    from core.feature_flags import features
    if features.quota_enabled:
        ...
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "features.json"


class FeatureFlags:
    def __init__(self):
        self._data = {}
        self.reload()

    def reload(self):
        try:
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                self._data = json.load(f)
            logger.debug("[Features] Loaded feature flags")
        except Exception as e:
            logger.warning(f"[Features] Could not load features.json: {e}")
            self._data = {}

    def _get(self, *keys, default=True):
        d = self._data
        for k in keys:
            if not isinstance(d, dict):
                return default
            d = d.get(k, default)
        return d

    # ─── Auth ─────────────────────────────────────────────────────────────────
    @property
    def auth_enabled(self) -> bool:
        return self._get("auth", "enabled", default=True)

    @property
    def allow_registration(self) -> bool:
        return self._get("auth", "allow_registration", default=True)

    @property
    def require_login(self) -> bool:
        return self._get("auth", "require_login", default=True)

    # ─── Quota ────────────────────────────────────────────────────────────────
    @property
    def quota_enabled(self) -> bool:
        return self._get("quota", "enabled", default=True)

    @property
    def image_gen_limit(self) -> int:
        return int(self._get("quota", "image_gen_limit", default=5))

    @property
    def image_quota_exempts_admins(self) -> bool:
        return self._get("quota", "image_gen_exempt_admins", default=True)

    # ─── Video ────────────────────────────────────────────────────────────────
    @property
    def video_enabled(self) -> bool:
        return self._get("video", "enabled", default=True)

    @property
    def video_requires_payment(self) -> bool:
        return self._get("video", "require_payment_unlock", default=True)

    # ─── Payment ──────────────────────────────────────────────────────────────
    @property
    def payment_enabled(self) -> bool:
        return self._get("payment", "enabled", default=True)

    @property
    def qr_enabled(self) -> bool:
        return self._get("payment", "qr_generation", default=True)

    # ─── Image Pipeline V2 ────────────────────────────────────────────────────
    @property
    def image_pipeline_v2(self) -> bool:
        """Enable anime multi-pass pipeline (IMAGE_PIPELINE_V2 env or features.json)."""
        import os
        env_flag = os.getenv("IMAGE_PIPELINE_V2", "").lower()
        if env_flag in ("1", "true", "yes", "on"):
            return True
        if env_flag in ("0", "false", "no", "off"):
            return False
        # Default True — pipeline is built-in; set IMAGE_PIPELINE_V2=false to disable.
        return self._get("image_pipeline", "v2_enabled", default=True)


# Singleton
features = FeatureFlags()
