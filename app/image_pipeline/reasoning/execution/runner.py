"""
image_pipeline.reasoning.execution.runner
=========================================

Tie :func:`plan_panel` + :func:`build_workflow` + an injected ComfyUI
client into a single entry point.

The client is duck-typed; it must expose
``submit_workflow(workflow, job_id="", pass_name="") -> result`` where
``result`` carries ``success``, ``images_b64``, ``error``, ``duration_ms``
(matching :class:`image_pipeline.anime_pipeline.comfy_client.ComfyJobResult`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Protocol

from image_pipeline.reasoning.schemas import SinglePanelSpec

from .comfy_workflow_builder import build_workflow
from .execution_plan import ExecutionPlan, RouteFn, StageKind, plan_panel


class ComfyClientLike(Protocol):
    """Minimum interface :func:`run_panel` needs from a ComfyUI client."""

    def submit_workflow(
        self,
        workflow: dict,
        job_id: str = "",
        pass_name: str = "",
    ) -> Any: ...


@dataclass(frozen=True, slots=True)
class PanelResult:
    """Result of executing a single panel plan against ComfyUI."""

    panel_id: str
    success: bool
    plan: ExecutionPlan
    workflow: dict
    images_b64: tuple[str, ...] = ()
    duration_ms: float = 0.0
    error: str = ""
    cancelled: bool = False
    raw: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "success": self.success,
            "plan": self.plan.to_dict(),
            "workflow": self.workflow,
            "images_b64": list(self.images_b64),
            "duration_ms": self.duration_ms,
            "error": self.error,
            "cancelled": self.cancelled,
        }


def run_panel(
    spec: SinglePanelSpec,
    *,
    comfy_client: ComfyClientLike,
    route_fn: RouteFn,
    required_stages: Iterable[str] = (),
    quality: str = "quality",
    seed: int = 0,
    base_resolution: int = 1024,
    extra_params: Optional[Mapping[StageKind, Mapping[str, Any]]] = None,
    job_id: str = "",
) -> PanelResult:
    """Plan, build, and submit a single panel.

    Returns a :class:`PanelResult`. Submission errors are surfaced via the
    ``success`` / ``error`` fields rather than raised, mirroring the
    semantics of :class:`ComfyJobResult`.
    """
    plan = plan_panel(
        spec,
        route_fn=route_fn,
        required_stages=required_stages,
        quality=quality,
        seed=seed,
        base_resolution=base_resolution,
        extra_params=extra_params,
    )
    workflow = build_workflow(plan)

    try:
        result = comfy_client.submit_workflow(
            workflow,
            job_id=job_id or spec.panel_id,
            pass_name="reasoning_render",
        )
    except Exception as exc:
        return PanelResult(
            panel_id=spec.panel_id,
            success=False,
            plan=plan,
            workflow=workflow,
            error=f"comfy_client.submit_workflow raised: {exc}",
        )

    success = bool(getattr(result, "success", False))
    images = tuple(getattr(result, "images_b64", ()) or ())
    duration_ms = float(getattr(result, "duration_ms", 0.0) or 0.0)
    error = str(getattr(result, "error", "") or "")
    cancelled = bool(getattr(result, "cancelled", False))

    return PanelResult(
        panel_id=spec.panel_id,
        success=success,
        plan=plan,
        workflow=workflow,
        images_b64=images,
        duration_ms=duration_ms,
        error=error,
        cancelled=cancelled,
        raw={"result": result},
    )


__all__ = ["ComfyClientLike", "PanelResult", "run_panel"]
