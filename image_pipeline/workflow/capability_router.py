"""
image_pipeline.workflow.capability_router
==========================================

Runtime router that maps (task_type, quality_tier, availability) → (model, provider, location).

Reads three YAML configs at startup:
    configs/models.yaml     — model registry (capabilities, costs, VRAM)
    configs/pipeline.yaml   — stage timeouts, eval thresholds, deployment topology
    configs/routing.yaml    — task-type → model chain mapping + quality overrides

Usage:
    router = CapabilityRouter()                # auto-discovers configs
    route  = router.route("semantic_edit", quality="quality")
    # route => RouteDecision(model="qwen-image-edit", provider="vps_vllm",
    #                        location="vps", cost_usd=0.0, fallbacks=[...])

    # With health-check awareness:
    route  = router.route("semantic_edit", unavailable={"vps"})
    # route => RouteDecision(model="flux1-kontext", provider="fal", location="api", ...)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

# ─── Locate configs ────────────────────────────────────────────────

_THIS_DIR = Path(__file__).resolve().parent             # image_pipeline/workflow/
_REPO_ROOT = _THIS_DIR.parent.parent                    # AI-Assistant/
_CONFIGS_DIR = _REPO_ROOT / "configs"

_MODELS_YAML   = _CONFIGS_DIR / "models.yaml"
_PIPELINE_YAML = _CONFIGS_DIR / "pipeline.yaml"
_ROUTING_YAML  = _CONFIGS_DIR / "routing.yaml"


# ─── Data classes ──────────────────────────────────────────────────

@dataclass(frozen=True)
class RouteDecision:
    """The output of a routing decision."""
    task_type: str
    model: str
    provider: str
    location: str                       # local | vps | api
    cost_usd: float                     # estimated per-image cost
    fallbacks: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ModelInfo:
    """Parsed model entry from models.yaml."""
    name: str
    provider: str
    endpoint: str
    location: str
    vram_gb: float
    cost_usd: float
    tier: str
    capabilities: list[str]
    max_refs: int = 0
    notes: str = ""


# ─── Router ────────────────────────────────────────────────────────

class CapabilityRouter:
    """
    Reads YAML configs and resolves (task_type, quality, availability) → RouteDecision.
    """

    def __init__(
        self,
        models_path: str | Path | None = None,
        pipeline_path: str | Path | None = None,
        routing_path: str | Path | None = None,
    ):
        self._models_path   = Path(models_path   or _MODELS_YAML)
        self._pipeline_path = Path(pipeline_path  or _PIPELINE_YAML)
        self._routing_path  = Path(routing_path   or _ROUTING_YAML)

        self._models: dict[str, ModelInfo] = {}
        self._task_routes: dict[str, dict[str, Any]] = {}
        self._quality_overrides: dict[str, dict[str, str]] = {}
        self._location_rules: dict[str, Any] = {}
        self._max_cost: float = 0.50

        self._load()

    # ───────────────────────────────────────────────────────────────
    # Loading
    # ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load and validate all three config files."""
        self._load_models()
        self._load_routing()
        self._load_pipeline()
        logger.info(
            "CapabilityRouter loaded: %d models, %d task routes, %d quality tiers",
            len(self._models),
            len(self._task_routes),
            len(self._quality_overrides),
        )

    def _load_models(self) -> None:
        raw = self._read_yaml(self._models_path)
        if not raw:
            return
        models_section = raw.get("models", {})
        # models.yaml stores models as a dict keyed by model name
        for name, entry in models_section.items():
            if not isinstance(entry, dict):
                continue
            self._models[name] = ModelInfo(
                name=name,
                provider=entry.get("provider", "unknown"),
                endpoint=entry.get("endpoint", ""),
                location=entry.get("location", "api"),
                vram_gb=float(entry.get("vram_gb") or 0),
                cost_usd=float(entry.get("cost_usd") or 0),
                tier=entry.get("tier", "standard"),
                capabilities=entry.get("capabilities", []),
                max_refs=int(entry.get("max_refs") or 0),
                notes=entry.get("notes", ""),
            )

    def _load_routing(self) -> None:
        raw = self._read_yaml(self._routing_path)
        if not raw:
            return
        self._task_routes = raw.get("task_routes", {})
        self._quality_overrides = raw.get("quality_overrides", {})
        self._location_rules = raw.get("location_rules", {})
        self._max_cost = float(
            self._location_rules.get("max_cost_per_job", 0.50)
        )

    def _load_pipeline(self) -> None:
        # Pipeline config is loaded for future use (timeouts, thresholds).
        # The router itself only needs routing.yaml + models.yaml.
        raw = self._read_yaml(self._pipeline_path)
        if not raw:
            return
        self._pipeline_cfg = raw

    @staticmethod
    def _read_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            logger.warning("Config not found: %s", path)
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # ───────────────────────────────────────────────────────────────
    # Public API
    # ───────────────────────────────────────────────────────────────

    def route(
        self,
        task_type: str,
        *,
        quality: str = "quality",
        unavailable: set[str] | None = None,
    ) -> RouteDecision:
        """
        Resolve the best model for a given task type.

        Args:
            task_type:   One of the keys in routing.yaml task_routes
            quality:     "fast" | "quality" | "free" | "cheap"
            unavailable: Set of unavailable locations {"vps", "local", "api"}

        Returns:
            RouteDecision with model, provider, location, cost, fallbacks.

        Raises:
            ValueError if no route can be resolved.
        """
        unavailable = unavailable or set()

        route_cfg = self._task_routes.get(task_type)
        if not route_cfg:
            raise ValueError(
                f"Unknown task type: {task_type!r}. "
                f"Available: {sorted(self._task_routes.keys())}"
            )

        # 1. Determine primary model — quality override takes precedence
        primary_model = self._resolve_primary(task_type, quality, route_cfg)

        # 2. Build full candidate list: primary + fallbacks
        fallback_names: list[str] = route_cfg.get("fallbacks", [])
        candidates = [primary_model] + [
            fb for fb in fallback_names if fb != primary_model
        ]

        # 3. Apply rerouting for unavailable locations
        candidates = self._apply_reroutes(
            task_type, candidates, unavailable
        )

        # 4. Pick the first candidate whose location is available
        for model_name in candidates:
            info = self._models.get(model_name)
            if info is None:
                logger.debug("Model %r not in registry, skipping", model_name)
                continue
            if info.location in unavailable:
                logger.debug(
                    "Model %r location %r unavailable, skipping",
                    model_name, info.location,
                )
                continue

            remaining = [m for m in candidates if m != model_name]
            return RouteDecision(
                task_type=task_type,
                model=model_name,
                provider=info.provider,
                location=info.location,
                cost_usd=info.cost_usd,
                fallbacks=remaining,
                notes=route_cfg.get("notes", ""),
            )

        raise ValueError(
            f"No available model for task {task_type!r} "
            f"(quality={quality!r}, unavailable={unavailable})"
        )

    def get_model(self, name: str) -> ModelInfo | None:
        """Look up a model by name."""
        return self._models.get(name)

    def list_task_types(self) -> list[str]:
        """Return all known task types."""
        return sorted(self._task_routes.keys())

    def list_models(self, *, location: str | None = None) -> list[ModelInfo]:
        """Return all registered models, optionally filtered by location."""
        models = list(self._models.values())
        if location:
            models = [m for m in models if m.location == location]
        return models

    @property
    def max_cost_per_job(self) -> float:
        return self._max_cost

    # ───────────────────────────────────────────────────────────────
    # Internal helpers
    # ───────────────────────────────────────────────────────────────

    def _resolve_primary(
        self,
        task_type: str,
        quality: str,
        route_cfg: dict[str, Any],
    ) -> str:
        """Pick the primary model: quality override → route default."""
        tier = self._quality_overrides.get(quality, {})
        override = tier.get(task_type)
        if override and override in self._models:
            return override
        return route_cfg["primary"]

    def _apply_reroutes(
        self,
        task_type: str,
        candidates: list[str],
        unavailable: set[str],
    ) -> list[str]:
        """Prepend reroute models when a whole location is down."""
        reroutes: list[str] = []

        if "vps" in unavailable:
            remap = self._location_rules.get("vps_unavailable_reroute", {})
            alt = remap.get(task_type)
            if alt:
                reroutes.append(alt)

        if "local" in unavailable:
            remap = self._location_rules.get("local_unavailable_reroute", {})
            alt = remap.get(task_type)
            if alt:
                reroutes.append(alt)

        if reroutes:
            # Prepend reroutes, then keep original order (deduplicated)
            seen: set[str] = set()
            merged: list[str] = []
            for m in reroutes + candidates:
                if m not in seen:
                    seen.add(m)
                    merged.append(m)
            return merged

        return candidates
