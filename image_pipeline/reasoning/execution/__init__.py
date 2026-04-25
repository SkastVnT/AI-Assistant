"""
image_pipeline.reasoning.execution — Cycle 3: panel → ComfyUI workflow.

Pure, route-agnostic execution layer. Three modules:

* :mod:`execution_plan` — translate a :class:`SinglePanelSpec` into a
  sequence of :class:`ExecutionStep` records via an injected ``route_fn``.
* :mod:`comfy_workflow_builder` — emit a ComfyUI prompt-API JSON from
  an :class:`ExecutionPlan`.
* :mod:`runner` — submit the workflow via an injected ``comfy_client``
  and return a :class:`PanelResult`.

No module here imports ``services/chatbot``, reads .env, or hardcodes a
checkpoint name. All variation comes from the injected route function and
the spec.
"""

from __future__ import annotations

from .comfy_workflow_builder import build_workflow
from .correction_router import (
    CorrectionResult,
    CorrectionRound,
    CorrectionScore,
    maybe_correct,
)
from .execution_plan import (
    ExecutionPlan,
    ExecutionStep,
    StageKind,
    plan_panel,
)
from .runner import PanelResult, run_panel

__all__ = [
    "ExecutionPlan",
    "ExecutionStep",
    "StageKind",
    "PanelResult",
    "CorrectionResult",
    "CorrectionRound",
    "CorrectionScore",
    "plan_panel",
    "build_workflow",
    "run_panel",
    "maybe_correct",
]
