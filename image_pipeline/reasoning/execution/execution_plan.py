"""
image_pipeline.reasoning.execution.execution_plan
=================================================

Translate a :class:`SinglePanelSpec` plus a set of required stages into an
ordered list of :class:`ExecutionStep` records.

Routing is fully injected via a callable ``route_fn(task_type, quality) ->
RouteDecisionLike``. The return value is duck-typed: any object exposing
``.model`` (str), ``.provider`` (str), ``.location`` (str), and
``.cost_usd`` (float) works. The chatbot wires this to
:class:`image_pipeline.workflow.capability_router.CapabilityRouter.route`
in Cycle 6; tests inject a stub.

This module performs no I/O, reads no config, and triggers no env loading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Mapping, Optional, Protocol, Tuple

from image_pipeline.reasoning.schemas import (
    SchemaValidationError,
    SinglePanelSpec,
)


# ---------------------------------------------------------------------------
# Stage taxonomy
# ---------------------------------------------------------------------------


class StageKind(str, Enum):
    """Canonical stage names. Ordered by typical execution sequence."""

    RENDER = "render"
    """Base text-to-image or image-to-image render. Always present."""

    INPAINT = "inpaint"
    """Mask-driven inpainting on the rendered base."""

    FACE_PATCH = "face_patch"
    """Face/eyes detect + inpaint patch."""

    PROP_PATCH = "prop_patch"
    """Object/region patch (background, hands, etc.)."""

    OVERLAY = "overlay"
    """Compose text/captions/speech bubbles on top of the rendered image.

    Handled outside ComfyUI by the comic_assembler in Cycle 5; recorded
    here so the planner has a complete view.
    """

    UPSCALE = "upscale"
    """Final super-resolution pass."""


# Mapping from raw ``required_stages`` strings (as produced by Cycle-1
# ``prompt_parser``) to the canonical :class:`StageKind`.
_STAGE_ALIASES: dict[str, StageKind] = {
    "render": StageKind.RENDER,
    "t2i": StageKind.RENDER,
    "i2i": StageKind.RENDER,
    "inpaint": StageKind.INPAINT,
    "face_patch": StageKind.FACE_PATCH,
    "face": StageKind.FACE_PATCH,
    "prop_patch": StageKind.PROP_PATCH,
    "background_patch": StageKind.PROP_PATCH,
    "overlay": StageKind.OVERLAY,
    "upscale": StageKind.UPSCALE,
}

# Default ordering when stages need to be sequenced.
_STAGE_ORDER: tuple[StageKind, ...] = (
    StageKind.RENDER,
    StageKind.INPAINT,
    StageKind.PROP_PATCH,
    StageKind.FACE_PATCH,
    StageKind.UPSCALE,
    StageKind.OVERLAY,
)

# Mapping from stage to the ``task_type`` string passed to ``route_fn``.
_STAGE_TASK: dict[StageKind, str] = {
    StageKind.RENDER: "t2i",
    StageKind.INPAINT: "inpaint",
    StageKind.FACE_PATCH: "inpaint",
    StageKind.PROP_PATCH: "inpaint",
    StageKind.UPSCALE: "upscale",
    StageKind.OVERLAY: "overlay",
}


# ---------------------------------------------------------------------------
# Route decision protocol
# ---------------------------------------------------------------------------


class RouteDecisionLike(Protocol):
    """Duck-typed shape returned by an injected ``route_fn``."""

    model: str
    provider: str
    location: str
    cost_usd: float


RouteFn = Callable[[str], RouteDecisionLike]
"""A callable ``route_fn(task_type) -> RouteDecisionLike``.

The planner calls this once per stage. Quality / availability are the
caller's responsibility — wrap a real router with ``functools.partial`` if
extra kwargs are needed.
"""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExecutionStep:
    """One stage in an execution plan."""

    stage: StageKind
    task_type: str
    model: str
    provider: str
    location: str
    cost_usd: float
    params: Mapping[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage.value,
            "task_type": self.task_type,
            "model": self.model,
            "provider": self.provider,
            "location": self.location,
            "cost_usd": self.cost_usd,
            "params": dict(self.params),
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """Ordered execution plan for a single panel."""

    panel_id: str
    steps: Tuple[ExecutionStep, ...]
    aspect_ratio: str = "1:1"
    width: int = 1024
    height: int = 1024
    seed: int = 0
    estimated_cost_usd: float = 0.0
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.panel_id:
            raise SchemaValidationError("ExecutionPlan.panel_id required")
        if not self.steps:
            raise SchemaValidationError(
                "ExecutionPlan.steps must contain at least one step"
            )
        if self.width <= 0 or self.height <= 0:
            raise SchemaValidationError(
                f"ExecutionPlan dimensions must be positive (got {self.width}x{self.height})"
            )

    @property
    def render_step(self) -> ExecutionStep:
        """The first :attr:`StageKind.RENDER` step. Always present."""
        for step in self.steps:
            if step.stage is StageKind.RENDER:
                return step
        raise SchemaValidationError("ExecutionPlan missing RENDER step")

    def steps_by_kind(self, kind: StageKind) -> tuple[ExecutionStep, ...]:
        return tuple(s for s in self.steps if s.stage is kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "steps": [s.to_dict() for s in self.steps],
            "aspect_ratio": self.aspect_ratio,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "estimated_cost_usd": self.estimated_cost_usd,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Aspect ratio → resolution
# ---------------------------------------------------------------------------


def _aspect_to_dims(aspect_ratio: str, base: int = 1024) -> tuple[int, int]:
    """Map ``"w:h"`` to integer (width, height) sized close to ``base``×``base``."""
    try:
        w_str, h_str = aspect_ratio.split(":")
        w_ratio = int(w_str)
        h_ratio = int(h_str)
    except (ValueError, AttributeError):
        return (base, base)
    if w_ratio <= 0 or h_ratio <= 0:
        return (base, base)
    # Keep the longer side at ~base, round to nearest multiple of 64
    # (ComfyUI / SDXL friendly).
    if w_ratio >= h_ratio:
        width = base
        height = int(round(base * h_ratio / w_ratio / 64) * 64) or 64
    else:
        height = base
        width = int(round(base * w_ratio / h_ratio / 64) * 64) or 64
    return (width, height)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_stages(required_stages: Iterable[str]) -> tuple[StageKind, ...]:
    """Translate raw stage strings into a deduplicated, ordered tuple.

    ``StageKind.RENDER`` is always inserted first.
    """
    seen: set[StageKind] = {StageKind.RENDER}
    for raw in required_stages or ():
        kind = _STAGE_ALIASES.get(str(raw).strip().lower())
        if kind is not None:
            seen.add(kind)
    return tuple(s for s in _STAGE_ORDER if s in seen)


def plan_panel(
    spec: SinglePanelSpec,
    *,
    route_fn: RouteFn,
    required_stages: Iterable[str] = (),
    quality: str = "quality",  # noqa: ARG001 — reserved for future use
    seed: int = 0,
    base_resolution: int = 1024,
    extra_params: Optional[Mapping[StageKind, Mapping[str, Any]]] = None,
) -> ExecutionPlan:
    """Build an :class:`ExecutionPlan` for a single panel.

    Parameters
    ----------
    spec
        The panel to render.
    route_fn
        Callable returning model routing for a given ``task_type`` string.
        See :data:`RouteFn`.
    required_stages
        Free-form stage names from the parser (e.g. ``("face_patch",
        "overlay")``). Unknown values are silently ignored — the planner
        always adds a :attr:`StageKind.RENDER` step.
    quality
        Currently unused; reserved so callers can wire quality tiers
        through without changing the call site again.
    seed
        Deterministic seed (0 → caller will randomize).
    base_resolution
        Target longer-edge resolution before aspect adjustment.
    extra_params
        Optional per-stage parameter overrides merged into ``ExecutionStep.params``.
    """
    if route_fn is None:
        raise ValueError("plan_panel requires a route_fn")

    width, height = _aspect_to_dims(spec.aspect_ratio, base=base_resolution)
    extras = dict(extra_params or {})

    stages = normalize_stages(required_stages)
    steps: list[ExecutionStep] = []
    total_cost = 0.0

    for stage in stages:
        task_type = _STAGE_TASK.get(stage, stage.value)
        try:
            decision = route_fn(task_type)
        except Exception as exc:
            raise SchemaValidationError(
                f"route_fn({task_type!r}) failed for stage {stage.value}: {exc}"
            ) from exc
        params = _default_params_for(stage, spec, width, height, seed)
        if stage in extras:
            params = {**params, **dict(extras[stage])}
        steps.append(
            ExecutionStep(
                stage=stage,
                task_type=task_type,
                model=getattr(decision, "model", "") or "",
                provider=getattr(decision, "provider", "") or "",
                location=getattr(decision, "location", "") or "",
                cost_usd=float(getattr(decision, "cost_usd", 0.0) or 0.0),
                params=params,
                notes=f"{stage.value} via {getattr(decision, 'provider', '?')}",
            )
        )
        total_cost += float(getattr(decision, "cost_usd", 0.0) or 0.0)

    return ExecutionPlan(
        panel_id=spec.panel_id,
        steps=tuple(steps),
        aspect_ratio=spec.aspect_ratio,
        width=width,
        height=height,
        seed=int(seed),
        estimated_cost_usd=total_cost,
        notes=f"{len(steps)} step(s) for {spec.panel_id}",
    )


# ---------------------------------------------------------------------------
# Internals — default per-stage params
# ---------------------------------------------------------------------------


def _positive_prompt(spec: SinglePanelSpec) -> str:
    parts: list[str] = []
    if spec.action_description:
        parts.append(spec.action_description)
    if spec.scene_description:
        parts.append(spec.scene_description)
    if spec.extra_positive_tags:
        parts.extend(spec.extra_positive_tags)
    return ", ".join(p for p in parts if p)


def _negative_prompt(spec: SinglePanelSpec) -> str:
    parts: list[str] = []
    if spec.forbidden_drift:
        parts.extend(spec.forbidden_drift)
    if spec.extra_negative_tags:
        parts.extend(spec.extra_negative_tags)
    return ", ".join(p for p in parts if p)


def _default_params_for(
    stage: StageKind,
    spec: SinglePanelSpec,
    width: int,
    height: int,
    seed: int,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "width": width,
        "height": height,
        "seed": seed,
        "positive_prompt": _positive_prompt(spec),
        "negative_prompt": _negative_prompt(spec),
    }
    if stage is StageKind.RENDER:
        base.update(
            {"steps": 28, "cfg": 6.5, "sampler": "euler", "scheduler": "normal"}
        )
    elif stage is StageKind.INPAINT:
        base.update({"steps": 24, "cfg": 6.5, "denoise": 0.8})
    elif stage is StageKind.FACE_PATCH:
        base.update(
            {
                "steps": 20,
                "cfg": 6.0,
                "denoise": 0.45,
                "target_regions": ["face", "eyes"],
            }
        )
    elif stage is StageKind.PROP_PATCH:
        base.update(
            {
                "steps": 22,
                "cfg": 6.0,
                "denoise": 0.5,
                "target_regions": [req.prop_key for req in spec.prop_requirements],
            }
        )
    elif stage is StageKind.UPSCALE:
        base.update({"scale": 2.0})
    elif stage is StageKind.OVERLAY:
        base.update(
            {
                "elements": [
                    {
                        "id": el.element_id,
                        "kind": el.kind.value,
                        "text": el.text,
                        "z_order": el.z_order,
                    }
                    for el in spec.overlay_plan.elements
                ],
            }
        )
    return base


__all__ = [
    "ExecutionPlan",
    "ExecutionStep",
    "RouteDecisionLike",
    "RouteFn",
    "StageKind",
    "normalize_stages",
    "plan_panel",
]
