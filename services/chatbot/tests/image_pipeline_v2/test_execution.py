"""
Tests for image_pipeline.reasoning.execution — Cycle 3.

Coverage:
* execution_plan: stage normalization, plan_panel happy path, route_fn
  is called per stage, aspect → dimensions, missing route_fn rejected,
  ExecutionPlan validation invariants.
* comfy_workflow_builder: minimal RENDER graph shape (sampler /
  checkpoint / clip / vae / save), augmentation when face_patch
  present, refusal when only inpaint without render, OVERLAY skipped.
* runner: mocked client receives the built workflow; success and error
  branches produce well-formed PanelResult.
* shared-env / cross-layer hygiene: execution package never calls
  load_dotenv and never imports services.chatbot.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dataclasses import dataclass

import pytest
from image_pipeline.reasoning.execution import (
    ExecutionPlan,
    ExecutionStep,
    PanelResult,
    StageKind,
    build_workflow,
    plan_panel,
    run_panel,
)
from image_pipeline.reasoning.execution.execution_plan import (
    _aspect_to_dims,
    normalize_stages,
)
from image_pipeline.reasoning.schemas import (
    OverlayElement,
    OverlayKind,
    OverlayPlan,
    PropRequirement,
    SchemaValidationError,
    ShotType,
    SinglePanelSpec,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclass
class _StubRoute:
    model: str = "test_ckpt.safetensors"
    provider: str = "comfyui"
    location: str = "local"
    cost_usd: float = 0.0


def _route_fn_factory(model: str = "sdxl_base.safetensors", cost: float = 0.0):
    def route_fn(task_type: str) -> _StubRoute:
        return _StubRoute(
            model=f"{model}",
            provider="comfyui",
            location="local",
            cost_usd=cost,
        )

    return route_fn


@pytest.fixture
def simple_panel() -> SinglePanelSpec:
    return SinglePanelSpec(
        panel_id="p1_abc",
        shot_type=ShotType.MEDIUM,
        scene_description="bedroom, night",
        action_description="a girl reading a book",
        aspect_ratio="1:1",
        extra_positive_tags=("masterpiece", "best quality"),
    )


@pytest.fixture
def panel_with_overlay_and_props() -> SinglePanelSpec:
    return SinglePanelSpec(
        panel_id="p2_def",
        shot_type=ShotType.CLOSE_UP,
        scene_description="cafe",
        action_description="she holds a red phone",
        aspect_ratio="3:4",
        prop_requirements=(PropRequirement(prop_key="red_phone", must_appear=True),),
        overlay_plan=OverlayPlan(
            elements=(
                OverlayElement(
                    element_id="cap_1",
                    kind=OverlayKind.CAPTION,
                    text="Hello",
                    z_order=0,
                ),
            ),
        ),
    )


# ---------------------------------------------------------------------------
# normalize_stages + aspect helper
# ---------------------------------------------------------------------------


class TestStageNormalization:
    def test_render_always_present(self):
        assert normalize_stages([]) == (StageKind.RENDER,)
        assert normalize_stages(["overlay"])[0] is StageKind.RENDER

    def test_aliases_resolve(self):
        result = normalize_stages(["face", "background_patch", "overlay"])
        assert StageKind.FACE_PATCH in result
        assert StageKind.PROP_PATCH in result
        assert StageKind.OVERLAY in result

    def test_unknown_stages_silently_dropped(self):
        result = normalize_stages(["nonsense", "overlay"])
        assert StageKind.OVERLAY in result
        assert len(result) == 2  # render + overlay

    def test_canonical_ordering(self):
        result = normalize_stages(["overlay", "upscale", "face_patch", "inpaint"])
        # Must follow _STAGE_ORDER, not input order.
        idx = {s: i for i, s in enumerate(result)}
        assert idx[StageKind.RENDER] < idx[StageKind.INPAINT]
        assert idx[StageKind.INPAINT] < idx[StageKind.FACE_PATCH]
        assert idx[StageKind.FACE_PATCH] < idx[StageKind.UPSCALE]
        assert idx[StageKind.UPSCALE] < idx[StageKind.OVERLAY]


class TestAspectDims:
    def test_square(self):
        assert _aspect_to_dims("1:1") == (1024, 1024)

    def test_portrait(self):
        w, h = _aspect_to_dims("3:4")
        assert h == 1024
        assert 700 < w < 800

    def test_landscape(self):
        w, h = _aspect_to_dims("16:9")
        assert w == 1024
        assert 500 < h < 600

    def test_invalid_falls_back_to_square(self):
        assert _aspect_to_dims("garbage") == (1024, 1024)
        assert _aspect_to_dims("0:0") == (1024, 1024)


# ---------------------------------------------------------------------------
# plan_panel
# ---------------------------------------------------------------------------


class TestPlanPanel:
    def test_render_only_default(self, simple_panel):
        plan = plan_panel(simple_panel, route_fn=_route_fn_factory())
        assert isinstance(plan, ExecutionPlan)
        assert plan.panel_id == "p1_abc"
        assert len(plan.steps) == 1
        assert plan.steps[0].stage is StageKind.RENDER
        assert plan.render_step.model == "sdxl_base.safetensors"
        assert plan.width == 1024 and plan.height == 1024

    def test_face_patch_adds_step(self, simple_panel):
        plan = plan_panel(
            simple_panel,
            route_fn=_route_fn_factory(),
            required_stages=("face_patch",),
        )
        kinds = [s.stage for s in plan.steps]
        assert StageKind.RENDER in kinds
        assert StageKind.FACE_PATCH in kinds

    def test_route_fn_called_per_stage(self, simple_panel):
        called: list[str] = []

        def rf(task_type: str) -> _StubRoute:
            called.append(task_type)
            return _StubRoute(model=f"m_{task_type}")

        plan_panel(
            simple_panel,
            route_fn=rf,
            required_stages=("face_patch", "overlay"),
        )
        assert "t2i" in called
        assert "inpaint" in called  # face_patch maps to inpaint task
        assert "overlay" in called

    def test_cost_aggregated(self, simple_panel):
        plan = plan_panel(
            simple_panel,
            route_fn=_route_fn_factory(cost=0.05),
            required_stages=("face_patch",),
        )
        assert plan.estimated_cost_usd == pytest.approx(0.10)

    def test_route_fn_required(self, simple_panel):
        with pytest.raises(ValueError):
            plan_panel(simple_panel, route_fn=None)  # type: ignore[arg-type]

    def test_route_fn_failure_wrapped(self, simple_panel):
        def bad_route(task_type: str):
            raise RuntimeError("router down")

        with pytest.raises(SchemaValidationError):
            plan_panel(simple_panel, route_fn=bad_route)

    def test_extra_params_override(self, simple_panel):
        plan = plan_panel(
            simple_panel,
            route_fn=_route_fn_factory(),
            extra_params={StageKind.RENDER: {"steps": 50, "cfg": 4.0}},
        )
        assert plan.render_step.params["steps"] == 50
        assert plan.render_step.params["cfg"] == 4.0

    def test_aspect_propagates(self, panel_with_overlay_and_props):
        plan = plan_panel(panel_with_overlay_and_props, route_fn=_route_fn_factory())
        assert plan.aspect_ratio == "3:4"
        assert plan.height == 1024
        assert plan.width < 1024


# ---------------------------------------------------------------------------
# ExecutionPlan invariants
# ---------------------------------------------------------------------------


class TestExecutionPlanInvariants:
    def test_empty_steps_rejected(self):
        with pytest.raises(SchemaValidationError):
            ExecutionPlan(panel_id="p1", steps=())

    def test_missing_panel_id_rejected(self):
        step = ExecutionStep(
            stage=StageKind.RENDER,
            task_type="t2i",
            model="m",
            provider="p",
            location="local",
            cost_usd=0.0,
        )
        with pytest.raises(SchemaValidationError):
            ExecutionPlan(panel_id="", steps=(step,))

    def test_negative_dims_rejected(self):
        step = ExecutionStep(
            stage=StageKind.RENDER,
            task_type="t2i",
            model="m",
            provider="p",
            location="local",
            cost_usd=0.0,
        )
        with pytest.raises(SchemaValidationError):
            ExecutionPlan(panel_id="p1", steps=(step,), width=-1, height=512)

    def test_to_dict_round_trip_safe(self, simple_panel):
        plan = plan_panel(simple_panel, route_fn=_route_fn_factory())
        as_dict = plan.to_dict()
        # Must be JSON-friendly.
        import json

        json.dumps(as_dict)


# ---------------------------------------------------------------------------
# build_workflow
# ---------------------------------------------------------------------------


class TestBuildWorkflow:
    def test_render_only_graph_shape(self, simple_panel):
        plan = plan_panel(simple_panel, route_fn=_route_fn_factory())
        wf = build_workflow(plan)
        classes = {n["class_type"] for n in wf.values()}
        # Minimum required nodes for SDXL-style render.
        for required in (
            "CheckpointLoaderSimple",
            "CLIPTextEncode",
            "EmptyLatentImage",
            "KSampler",
            "VAEDecode",
            "SaveImage",
        ):
            assert required in classes, f"missing {required} in {classes}"

    def test_checkpoint_name_from_route(self, simple_panel):
        plan = plan_panel(
            simple_panel, route_fn=_route_fn_factory(model="my_custom.safetensors")
        )
        wf = build_workflow(plan)
        ckpts = [n for n in wf.values() if n["class_type"] == "CheckpointLoaderSimple"]
        assert ckpts[0]["inputs"]["ckpt_name"] == "my_custom.safetensors"

    def test_face_patch_appends_inpaint_subgraph(self, simple_panel):
        plan = plan_panel(
            simple_panel,
            route_fn=_route_fn_factory(),
            required_stages=("face_patch",),
        )
        wf = build_workflow(plan)
        classes = [n["class_type"] for n in wf.values()]
        # Should contain inpaint-specific nodes.
        assert "VAEEncodeForInpaint" in classes
        assert "LoadImageMask" in classes
        # And exactly two SaveImage nodes (render + face_patch).
        assert classes.count("SaveImage") == 2

    def test_upscale_adds_upscale_nodes(self, simple_panel):
        plan = plan_panel(
            simple_panel,
            route_fn=_route_fn_factory(),
            required_stages=("upscale",),
        )
        wf = build_workflow(plan)
        classes = {n["class_type"] for n in wf.values()}
        assert "UpscaleModelLoader" in classes
        assert "ImageUpscaleWithModel" in classes

    def test_overlay_skipped_in_workflow(self, panel_with_overlay_and_props):
        plan = plan_panel(
            panel_with_overlay_and_props,
            route_fn=_route_fn_factory(),
            required_stages=("overlay",),
        )
        wf = build_workflow(plan)
        # Overlay is composited outside ComfyUI — no overlay-specific nodes.
        for node in wf.values():
            assert "overlay" not in node["class_type"].lower()
        # But the step is recorded in the plan.
        assert any(s.stage is StageKind.OVERLAY for s in plan.steps)

    def test_node_ids_are_strings_and_unique(self, simple_panel):
        plan = plan_panel(simple_panel, route_fn=_route_fn_factory())
        wf = build_workflow(plan)
        assert all(isinstance(k, str) for k in wf)
        assert len(wf) == len(set(wf.keys()))

    def test_workflow_is_json_serializable(self, simple_panel):
        plan = plan_panel(
            simple_panel,
            route_fn=_route_fn_factory(),
            required_stages=("face_patch", "upscale"),
        )
        import json

        json.dumps(build_workflow(plan))


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------


class _StubResult:
    def __init__(self, success=True, images=None, error="", cancelled=False):
        self.success = success
        self.images_b64 = images or ["AAAA"]
        self.error = error
        self.duration_ms = 123.0
        self.cancelled = cancelled


class _StubClient:
    def __init__(self, result=None, raise_exc=None):
        self.result = result or _StubResult()
        self.raise_exc = raise_exc
        self.last_workflow = None
        self.last_job_id = None

    def submit_workflow(self, workflow, job_id="", pass_name=""):
        if self.raise_exc:
            raise self.raise_exc
        self.last_workflow = workflow
        self.last_job_id = job_id
        return self.result


class TestRunner:
    def test_success_path(self, simple_panel):
        client = _StubClient(_StubResult(success=True, images=["IMGB64"]))
        result = run_panel(
            simple_panel, comfy_client=client, route_fn=_route_fn_factory()
        )
        assert isinstance(result, PanelResult)
        assert result.success is True
        assert result.images_b64 == ("IMGB64",)
        assert result.duration_ms == 123.0
        assert result.workflow == client.last_workflow

    def test_error_propagated_in_result(self, simple_panel):
        client = _StubClient(
            _StubResult(success=False, images=[], error="bad workflow")
        )
        result = run_panel(
            simple_panel, comfy_client=client, route_fn=_route_fn_factory()
        )
        assert result.success is False
        assert result.error == "bad workflow"
        # Plan and workflow are still attached for debugging.
        assert result.plan.panel_id == simple_panel.panel_id
        assert result.workflow

    def test_client_exception_caught(self, simple_panel):
        client = _StubClient(raise_exc=RuntimeError("connection refused"))
        result = run_panel(
            simple_panel, comfy_client=client, route_fn=_route_fn_factory()
        )
        assert result.success is False
        assert "connection refused" in result.error

    def test_job_id_defaults_to_panel_id(self, simple_panel):
        client = _StubClient()
        run_panel(simple_panel, comfy_client=client, route_fn=_route_fn_factory())
        assert client.last_job_id == simple_panel.panel_id

    def test_job_id_explicit(self, simple_panel):
        client = _StubClient()
        run_panel(
            simple_panel,
            comfy_client=client,
            route_fn=_route_fn_factory(),
            job_id="custom_job_42",
        )
        assert client.last_job_id == "custom_job_42"


# ---------------------------------------------------------------------------
# Cross-layer + shared-env hygiene
# ---------------------------------------------------------------------------


class TestExecutionHygiene:
    EXECUTION_DIR = _ROOT / "app" / "image_pipeline" / "reasoning" / "execution"

    def test_no_load_dotenv(self):
        offenders = [
            p.name
            for p in self.EXECUTION_DIR.glob("*.py")
            if "load_dotenv" in p.read_text(encoding="utf-8")
        ]
        assert offenders == [], f"load_dotenv leaked into: {offenders}"

    def test_no_dotenv_import(self):
        offenders = [
            p.name
            for p in self.EXECUTION_DIR.glob("*.py")
            if "from dotenv" in p.read_text(encoding="utf-8")
            or "import dotenv" in p.read_text(encoding="utf-8")
        ]
        assert offenders == [], f"dotenv imported in: {offenders}"

    def test_no_services_chatbot_import(self):
        """The reasoning/execution layer must not depend on the chatbot package.

        Cross-layer imports break reusability and pull chatbot env contracts
        into image_pipeline. The runner accepts an injected client instead.
        """
        offenders = []
        for p in self.EXECUTION_DIR.glob("*.py"):
            text = p.read_text(encoding="utf-8")
            if "services.chatbot" in text or "from core." in text:
                offenders.append(p.name)
        assert offenders == [], f"chatbot import leaked into: {offenders}"
