"""
image_pipeline.reasoning.execution.comfy_workflow_builder
=========================================================

Translate an :class:`ExecutionPlan` into a ComfyUI prompt-API JSON.

The output is a flat ``dict[node_id_str, node_def]`` matching ComfyUI's
``POST /prompt`` schema, accepted verbatim by
:class:`image_pipeline.anime_pipeline.comfy_client.ComfyClient`.

Design rules
------------
* Node graphs are minimal but valid (CheckpointLoaderSimple →
  CLIPTextEncode×2 → EmptyLatentImage → KSampler → VAEDecode → SaveImage).
* Stage augmentations append nodes, never mutate prior ones.
* No model checkpoint name is hardcoded — it comes from
  ``ExecutionStep.model``.
* The builder is pure: same plan in → same JSON out.
"""

from __future__ import annotations

from typing import Any

from .execution_plan import ExecutionPlan, ExecutionStep, StageKind


class _NodeAllocator:
    """Hands out string node IDs starting at "1" and tracks the graph."""

    def __init__(self) -> None:
        self._next = 1
        self.graph: dict[str, dict[str, Any]] = {}

    def add(self, class_type: str, inputs: dict[str, Any]) -> str:
        nid = str(self._next)
        self._next += 1
        self.graph[nid] = {"class_type": class_type, "inputs": dict(inputs)}
        return nid


def _ref(node_id: str, slot: int = 0) -> list[Any]:
    """ComfyUI uses ``[node_id, slot_index]`` for inter-node references."""
    return [node_id, slot]


def _build_render_subgraph(
    alloc: _NodeAllocator,
    step: ExecutionStep,
    plan: ExecutionPlan,
) -> dict[str, str]:
    """Build the base render subgraph and return a map of useful node IDs."""
    params = step.params
    pos = params.get("positive_prompt", "") or ""
    neg = params.get("negative_prompt", "") or ""

    ckpt_id = alloc.add(
        "CheckpointLoaderSimple",
        {"ckpt_name": step.model or "model.safetensors"},
    )
    pos_id = alloc.add(
        "CLIPTextEncode",
        {"text": pos, "clip": _ref(ckpt_id, 1)},
    )
    neg_id = alloc.add(
        "CLIPTextEncode",
        {"text": neg, "clip": _ref(ckpt_id, 1)},
    )
    latent_id = alloc.add(
        "EmptyLatentImage",
        {
            "width": int(params.get("width", plan.width)),
            "height": int(params.get("height", plan.height)),
            "batch_size": 1,
        },
    )
    sampler_id = alloc.add(
        "KSampler",
        {
            "model": _ref(ckpt_id, 0),
            "positive": _ref(pos_id, 0),
            "negative": _ref(neg_id, 0),
            "latent_image": _ref(latent_id, 0),
            "seed": int(params.get("seed", plan.seed)),
            "steps": int(params.get("steps", 28)),
            "cfg": float(params.get("cfg", 6.5)),
            "sampler_name": str(params.get("sampler", "euler")),
            "scheduler": str(params.get("scheduler", "normal")),
            "denoise": float(params.get("denoise", 1.0)),
        },
    )
    decode_id = alloc.add(
        "VAEDecode",
        {"samples": _ref(sampler_id, 0), "vae": _ref(ckpt_id, 2)},
    )
    save_id = alloc.add(
        "SaveImage",
        {
            "images": _ref(decode_id, 0),
            "filename_prefix": f"reasoning/{plan.panel_id}_render",
        },
    )
    return {
        "ckpt": ckpt_id,
        "positive": pos_id,
        "negative": neg_id,
        "latent": latent_id,
        "sampler": sampler_id,
        "decode": decode_id,
        "save": save_id,
    }


def _build_inpaint_subgraph(
    alloc: _NodeAllocator,
    step: ExecutionStep,
    plan: ExecutionPlan,
    upstream: dict[str, str],
    *,
    suffix: str,
) -> dict[str, str]:
    """Append an inpaint subgraph that consumes the previous decoded image.

    The mask source is left as a placeholder ``LoadImageMask`` node; the
    chatbot wires real masks in Cycle 4 (correction loop) — the schema
    contract here is only that the subgraph references ``upstream["decode"]``.
    """
    params = step.params
    mask_id = alloc.add(
        "LoadImageMask",
        {
            "image": params.get("mask_filename", "mask_placeholder.png"),
            "channel": "alpha",
        },
    )
    encode_id = alloc.add(
        "VAEEncodeForInpaint",
        {
            "pixels": _ref(upstream["decode"], 0),
            "vae": _ref(upstream["ckpt"], 2),
            "mask": _ref(mask_id, 0),
            "grow_mask_by": 6,
        },
    )
    pos_id = alloc.add(
        "CLIPTextEncode",
        {
            "text": params.get("positive_prompt", "") or "",
            "clip": _ref(upstream["ckpt"], 1),
        },
    )
    neg_id = alloc.add(
        "CLIPTextEncode",
        {
            "text": params.get("negative_prompt", "") or "",
            "clip": _ref(upstream["ckpt"], 1),
        },
    )
    sampler_id = alloc.add(
        "KSampler",
        {
            "model": _ref(upstream["ckpt"], 0),
            "positive": _ref(pos_id, 0),
            "negative": _ref(neg_id, 0),
            "latent_image": _ref(encode_id, 0),
            "seed": int(params.get("seed", plan.seed)),
            "steps": int(params.get("steps", 24)),
            "cfg": float(params.get("cfg", 6.5)),
            "sampler_name": str(params.get("sampler", "euler")),
            "scheduler": str(params.get("scheduler", "normal")),
            "denoise": float(params.get("denoise", 0.8)),
        },
    )
    decode_id = alloc.add(
        "VAEDecode",
        {"samples": _ref(sampler_id, 0), "vae": _ref(upstream["ckpt"], 2)},
    )
    save_id = alloc.add(
        "SaveImage",
        {
            "images": _ref(decode_id, 0),
            "filename_prefix": f"reasoning/{plan.panel_id}_{suffix}",
        },
    )
    return {
        "mask": mask_id,
        "encode": encode_id,
        "positive": pos_id,
        "negative": neg_id,
        "sampler": sampler_id,
        "decode": decode_id,
        "save": save_id,
    }


def _build_upscale_subgraph(
    alloc: _NodeAllocator,
    step: ExecutionStep,
    plan: ExecutionPlan,
    upstream: dict[str, str],
) -> dict[str, str]:
    upscale_model_id = alloc.add(
        "UpscaleModelLoader",
        {"model_name": step.model or "RealESRGAN_x4plus.pth"},
    )
    upscale_id = alloc.add(
        "ImageUpscaleWithModel",
        {
            "upscale_model": _ref(upscale_model_id, 0),
            "image": _ref(upstream["decode"], 0),
        },
    )
    save_id = alloc.add(
        "SaveImage",
        {
            "images": _ref(upscale_id, 0),
            "filename_prefix": f"reasoning/{plan.panel_id}_upscale",
        },
    )
    return {
        "upscale_model": upscale_model_id,
        "upscale": upscale_id,
        "save": save_id,
    }


def build_workflow(plan: ExecutionPlan) -> dict[str, dict[str, Any]]:
    """Compile an :class:`ExecutionPlan` into a ComfyUI prompt-API dict.

    Stages handled inside ComfyUI: RENDER, INPAINT, FACE_PATCH, PROP_PATCH,
    UPSCALE. The OVERLAY stage is recorded in the plan but assembled by
    :mod:`comic_assembler` (Cycle 5) outside ComfyUI; it is skipped here.
    """
    alloc = _NodeAllocator()
    upstream: dict[str, str] = {}

    for step in plan.steps:
        if step.stage is StageKind.RENDER:
            upstream = _build_render_subgraph(alloc, step, plan)
        elif step.stage is StageKind.INPAINT:
            if not upstream:
                raise ValueError(
                    "INPAINT stage requires a prior RENDER stage in the plan"
                )
            new = _build_inpaint_subgraph(
                alloc, step, plan, upstream, suffix="inpaint"
            )
            upstream = {**upstream, "decode": new["decode"], "save": new["save"]}
        elif step.stage is StageKind.FACE_PATCH:
            if not upstream:
                raise ValueError(
                    "FACE_PATCH requires a prior RENDER stage in the plan"
                )
            new = _build_inpaint_subgraph(
                alloc, step, plan, upstream, suffix="face_patch"
            )
            upstream = {**upstream, "decode": new["decode"], "save": new["save"]}
        elif step.stage is StageKind.PROP_PATCH:
            if not upstream:
                raise ValueError(
                    "PROP_PATCH requires a prior RENDER stage in the plan"
                )
            new = _build_inpaint_subgraph(
                alloc, step, plan, upstream, suffix="prop_patch"
            )
            upstream = {**upstream, "decode": new["decode"], "save": new["save"]}
        elif step.stage is StageKind.UPSCALE:
            if not upstream:
                raise ValueError(
                    "UPSCALE requires a prior RENDER stage in the plan"
                )
            new = _build_upscale_subgraph(alloc, step, plan, upstream)
            upstream = {**upstream, "decode": new["upscale"], "save": new["save"]}
        elif step.stage is StageKind.OVERLAY:
            # Overlay is composited outside ComfyUI by the comic_assembler.
            continue
        else:
            # Unknown stage — skip rather than fail; the planner already
            # validated the stage taxonomy.
            continue

    if not alloc.graph:
        raise ValueError("build_workflow produced an empty graph (no RENDER step)")

    return alloc.graph


__all__ = ["build_workflow"]
