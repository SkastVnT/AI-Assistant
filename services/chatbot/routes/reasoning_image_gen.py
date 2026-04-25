"""
Reasoning Image Generation API — Flask Blueprint (Cycle 6).

This is the FIRST cycle that wires the ``image_pipeline.reasoning`` library
(Cycles 1-5) into the live chatbot. The route is registered ONLY when
``REASONING_PIPELINE=true`` (see :mod:`core.config`); when disabled the
import is never executed and the URL map is byte-identical to today.

Endpoints (URL prefix ``/api/reasoning-image-gen``):

* ``GET  /status``    → flag + dependency snapshot
* ``POST /generate``  → run the full pipeline:
        parse → (per panel) plan_panel → run_panel → maybe_correct
        → assemble_comic → return descriptor + base64 image

Module-level injectables (overridable in tests via monkeypatch):

* :func:`_default_route_fn`         — stage → (model, provider, location, cost)
* :func:`_default_comfy_client`     — ComfyClientLike adapter around
                                       :class:`ComfyUIClient`
* :func:`_default_scorer_fn`        — no-op scorer (passes everything)
* :func:`_default_inpaint_runner`   — pass-through inpaint (returns input bytes)

This file does NOT call ``load_dotenv``; environment is loaded once via
``services.shared_env`` through :mod:`core.config`.
"""

from __future__ import annotations

import base64
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from flask import Blueprint, jsonify, request

from core.config import (
    REASONING_PIPELINE_COMFY_URL,
    REASONING_PIPELINE_MAX_CORRECTION_PASSES,
    REASONING_PIPELINE_MAX_PANELS,
)

from image_pipeline.reasoning import (
    ComicSequenceSpec,
    OutputLayout,
    SchemaValidationError,
    SinglePanelSpec,
    parse,
)
from image_pipeline.reasoning.execution import (
    assemble_comic,
    maybe_correct,
    run_panel,
)
from image_pipeline.reasoning.state import default_resolver

logger = logging.getLogger(__name__)

reasoning_image_gen_bp = Blueprint(
    "reasoning_image_gen", __name__, url_prefix="/api/reasoning-image-gen"
)


# ---------------------------------------------------------------------------
# Default injected dependencies (test-overridable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _RouteDecision:
    """Concrete RouteDecisionLike used by the local pipeline."""

    model: str
    provider: str
    location: str
    cost_usd: float


def _default_route_fn(task_type: str) -> _RouteDecision:
    """Stage → route decision. All stages run on local ComfyUI."""
    return _RouteDecision(
        model="local-comfyui",
        provider="comfyui",
        location="local",
        cost_usd=0.0,
    )


@dataclass(frozen=True)
class _ComfyJobResult:
    """ComfyClientLike.submit_workflow return shape."""

    success: bool
    images_b64: tuple[str, ...]
    duration_ms: float
    error: str = ""
    cancelled: bool = False


class _ComfyClientAdapter:
    """Adapter over :class:`ComfyUIClient` matching ``ComfyClientLike``.

    The reasoning runner expects ``submit_workflow(workflow, job_id, pass_name)``
    returning an object with ``success / images_b64 / duration_ms / error /
    cancelled``. The chatbot's ``ComfyUIClient`` exposes lower-level
    ``_queue_prompt`` + ``_wait_for_prompt`` + ``_get_image``.
    """

    def __init__(self, api_url: str | None = None) -> None:
        # Lazy import — keeps the module import cheap when the flag is off
        # AND avoids hard-binding tests to the real client.
        from src.utils.comfyui_client import ComfyUIClient  # type: ignore

        self._client = ComfyUIClient(api_url or REASONING_PIPELINE_COMFY_URL)

    def submit_workflow(
        self, workflow: dict, job_id: str = "", pass_name: str = ""
    ) -> _ComfyJobResult:
        started = time.monotonic()
        try:
            prompt_id = self._client._queue_prompt(workflow)  # noqa: SLF001
        except Exception as exc:  # pragma: no cover — defensive
            return _ComfyJobResult(
                success=False,
                images_b64=(),
                duration_ms=(time.monotonic() - started) * 1000.0,
                error=f"queue_prompt raised: {exc}",
            )
        if not prompt_id:
            return _ComfyJobResult(
                success=False,
                images_b64=(),
                duration_ms=(time.monotonic() - started) * 1000.0,
                error="ComfyUI did not return a prompt_id",
            )
        outputs = self._client._wait_for_prompt(prompt_id, timeout=300)  # noqa: SLF001
        duration_ms = (time.monotonic() - started) * 1000.0
        if not outputs:
            return _ComfyJobResult(
                success=False, images_b64=(), duration_ms=duration_ms,
                error=f"timeout waiting for prompt {prompt_id}",
            )
        if isinstance(outputs, dict) and outputs.get("error"):
            return _ComfyJobResult(
                success=False, images_b64=(), duration_ms=duration_ms,
                error=str(outputs["error"]),
            )
        img_bytes = self._client._get_image(outputs)  # noqa: SLF001
        if not img_bytes:
            return _ComfyJobResult(
                success=False, images_b64=(), duration_ms=duration_ms,
                error=f"no image in outputs for prompt {prompt_id}",
            )
        return _ComfyJobResult(
            success=True,
            images_b64=(base64.b64encode(img_bytes).decode("ascii"),),
            duration_ms=duration_ms,
        )


def _default_comfy_client() -> Any:
    """Return a fresh ComfyClientLike. Override in tests via monkeypatch."""
    return _ComfyClientAdapter()


@dataclass(frozen=True)
class _NoopScore:
    score: float = 1.0
    targets: tuple = ()


def _default_scorer_fn(panel: SinglePanelSpec, image_bytes: bytes) -> _NoopScore:
    """No-op scorer. Always 1.0 / empty targets — correction loop short-circuits."""
    return _NoopScore()


def _default_inpaint_runner(
    panel: SinglePanelSpec, image_bytes: bytes, targets: Iterable[Any]
) -> bytes:
    """No-op inpaint runner — returns input unchanged."""
    return image_bytes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_layout(value: Any, default: OutputLayout) -> OutputLayout:
    if value is None:
        return default
    if isinstance(value, OutputLayout):
        return value
    try:
        return OutputLayout(str(value).lower())
    except ValueError:
        return default


def _panels_from_parse(result: Any) -> tuple[tuple[SinglePanelSpec, ...], OutputLayout]:
    if result.sequence is not None:
        seq: ComicSequenceSpec = result.sequence
        return seq.ordered_panels, seq.output_layout
    if result.single_panel is not None:
        return (result.single_panel,), OutputLayout.SINGLE
    return (), OutputLayout.SINGLE


def _decode_image_b64(data_b64: str) -> bytes:
    return base64.b64decode(data_b64.encode("ascii"))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@reasoning_image_gen_bp.get("/status")
def status() -> Any:
    """Lightweight introspection — confirms flag is on and dependencies load."""
    return jsonify({
        "enabled": True,
        "comfy_url": REASONING_PIPELINE_COMFY_URL,
        "max_panels": REASONING_PIPELINE_MAX_PANELS,
        "max_correction_passes": REASONING_PIPELINE_MAX_CORRECTION_PASSES,
    })


@reasoning_image_gen_bp.post("/generate")
def generate() -> Any:
    """Run parse → plan → run → correct → assemble for the supplied prompt.

    Request JSON
    ------------
    ``prompt`` (str, required) — natural-language request.
    ``layout`` (str, optional) — override OutputLayout (e.g. ``"grid_2x2"``).
    ``attached_images`` (int, optional) — count of attachments, forwarded to parser.
    ``character_hint`` (mapping, optional) — pin character resolution.

    Response JSON
    -------------
    ``job_id``, ``parse``, ``panels`` (per-panel diagnostic dicts),
    ``comic`` (descriptor from :meth:`AssembledComic.to_dict`),
    ``image_b64`` (final assembled comic, base64 PNG).

    Failures surface as HTTP 4xx (validation) or HTTP 200 with
    ``success=False`` + per-panel error fields when a panel's render fails.
    """
    payload = request.get_json(silent=True) or {}
    prompt_text = (payload.get("prompt") or "").strip()
    if not prompt_text:
        return jsonify({"success": False, "error": "prompt is required"}), 400

    job_id = f"reason-{uuid.uuid4().hex[:12]}"
    logger.info("[%s] reasoning pipeline start: %r", job_id, prompt_text[:160])

    # 1. Parse — wire the chatbot's CharacterRegistry via Cycle 2 resolver.
    try:
        parse_result = parse(
            prompt_text,
            attached_images=int(payload.get("attached_images") or 0),
            character_hint=payload.get("character_hint"),
            state_resolver=default_resolver(),
        )
    except SchemaValidationError as exc:
        return jsonify({"success": False, "error": f"parse failed: {exc}"}), 400
    except Exception as exc:
        logger.exception("[%s] parse raised", job_id)
        return jsonify({"success": False, "error": f"parse raised: {exc}"}), 500

    panels, parsed_layout = _panels_from_parse(parse_result)
    if not panels:
        return jsonify({
            "success": False,
            "error": "parser produced no panels",
            "parse": parse_result.to_dict(),
        }), 422
    if len(panels) > REASONING_PIPELINE_MAX_PANELS:
        return jsonify({
            "success": False,
            "error": (
                f"panel count {len(panels)} exceeds max "
                f"{REASONING_PIPELINE_MAX_PANELS}"
            ),
        }), 422

    layout = _coerce_layout(payload.get("layout"), parsed_layout)
    required_stages = tuple(parse_result.required_stages or ())

    # 2. Per-panel: plan + run + correct.
    comfy_client = _default_comfy_client()
    panel_reports: list[dict] = []
    panel_bytes: list[bytes] = []
    any_failure = False

    for panel in panels:
        panel_result = run_panel(
            panel,
            comfy_client=comfy_client,
            route_fn=_default_route_fn,
            required_stages=required_stages,
            job_id=job_id,
        )
        report: dict = {
            "panel_id": panel.panel_id,
            "success": panel_result.success,
            "duration_ms": panel_result.duration_ms,
            "error": panel_result.error,
            "cancelled": panel_result.cancelled,
        }
        if not panel_result.success or not panel_result.images_b64:
            report["correction"] = None
            panel_reports.append(report)
            any_failure = True
            continue

        raw_bytes = _decode_image_b64(panel_result.images_b64[0])
        if REASONING_PIPELINE_MAX_CORRECTION_PASSES > 0:
            correction = maybe_correct(
                panel,
                raw_bytes,
                scorer_fn=_default_scorer_fn,
                inpaint_runner_fn=_default_inpaint_runner,
                required_stages=required_stages,
                max_passes=REASONING_PIPELINE_MAX_CORRECTION_PASSES,
            )
            report["correction"] = correction.to_dict()
            panel_bytes.append(correction.image_bytes)
        else:
            report["correction"] = {"skipped": True}
            panel_bytes.append(raw_bytes)
        panel_reports.append(report)

    # 3. Assemble — bail if any panel produced no bytes.
    if any_failure or not panel_bytes:
        return jsonify({
            "success": False,
            "job_id": job_id,
            "parse": parse_result.to_dict(),
            "panels": panel_reports,
            "error": "one or more panels failed to render",
        }), 200

    try:
        # SINGLE layout supports exactly 1 panel; downgrade if mismatch.
        if layout is OutputLayout.SINGLE and len(panel_bytes) != 1:
            layout = OutputLayout.HORIZONTAL_STRIP
        comic = assemble_comic(layout, panel_bytes)
    except ValueError as exc:
        return jsonify({
            "success": False,
            "job_id": job_id,
            "parse": parse_result.to_dict(),
            "panels": panel_reports,
            "error": f"assemble_comic: {exc}",
        }), 200

    return jsonify({
        "success": True,
        "job_id": job_id,
        "parse": parse_result.to_dict(),
        "panels": panel_reports,
        "comic": comic.to_dict(),
        "image_b64": base64.b64encode(comic.image_bytes).decode("ascii"),
    })


__all__ = ["reasoning_image_gen_bp"]
