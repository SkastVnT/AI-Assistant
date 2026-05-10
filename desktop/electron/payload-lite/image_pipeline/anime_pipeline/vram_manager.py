"""
image_pipeline.anime_pipeline.vram_manager — VRAM-aware execution helpers.

Provides:
  - Model unloading between passes (POST /free to ComfyUI)
  - Preview suppression (strip PreviewImage nodes from workflows)
  - CPU VAE offload node injection
  - OOM-aware retry strategy (lower resolution / switch profile)
  - Logging for memory mode, retry cause, and fallback used
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

from .config import VRAMProfile, VRAMProfileConfig

logger = logging.getLogger(__name__)

# ── OOM detection ─────────────────────────────────────────────────

_OOM_MARKERS = (
    "out of memory",
    "oom",
    "cuda out of memory",
    "torch.cuda.outofmemoryerror",
    "allocator",
    "not enough memory",
)


def is_oom_error(error_text: str) -> bool:
    """Return True if the error string indicates a GPU OOM condition."""
    lower = error_text.lower()
    return any(marker in lower for marker in _OOM_MARKERS)


# ── Retry strategy ────────────────────────────────────────────────

@dataclass
class RetryContext:
    """Tracks OOM retry state for a single pipeline pass."""
    original_width: int = 0
    original_height: int = 0
    current_width: int = 0
    current_height: int = 0
    attempts: int = 0
    max_retries: int = 2
    resolution_step_down: int = 128
    profile_escalated: bool = False
    last_error: str = ""
    retries_log: list[dict[str, Any]] = field(default_factory=list)

    @property
    def exhausted(self) -> bool:
        return self.attempts >= self.max_retries

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_resolution": f"{self.original_width}x{self.original_height}",
            "final_resolution": f"{self.current_width}x{self.current_height}",
            "attempts": self.attempts,
            "profile_escalated": self.profile_escalated,
            "retries": self.retries_log,
        }


def build_retry_context(
    width: int,
    height: int,
    vram: VRAMProfileConfig,
) -> RetryContext:
    """Create a RetryContext from current resolution and VRAM config."""
    return RetryContext(
        original_width=width,
        original_height=height,
        current_width=width,
        current_height=height,
        max_retries=vram.oom_max_retries,
        resolution_step_down=vram.oom_resolution_step_down,
    )


def step_down_resolution(ctx: RetryContext) -> tuple[int, int]:
    """Reduce resolution by one step and record the retry.

    Returns the new (width, height), rounded down to a multiple of 8.
    """
    ctx.attempts += 1
    new_w = max(512, ctx.current_width - ctx.resolution_step_down)
    new_h = max(512, ctx.current_height - ctx.resolution_step_down)

    # Round to nearest multiple of 8
    new_w = (new_w // 8) * 8
    new_h = (new_h // 8) * 8

    ctx.retries_log.append({
        "attempt": ctx.attempts,
        "action": "resolution_step_down",
        "from": f"{ctx.current_width}x{ctx.current_height}",
        "to": f"{new_w}x{new_h}",
        "cause": ctx.last_error[:200] if ctx.last_error else "oom",
    })

    logger.warning(
        "[VRAMManager] OOM retry %d/%d: resolution %dx%d → %dx%d",
        ctx.attempts, ctx.max_retries,
        ctx.current_width, ctx.current_height,
        new_w, new_h,
    )

    ctx.current_width = new_w
    ctx.current_height = new_h
    return new_w, new_h


def escalate_to_lowvram(ctx: RetryContext) -> VRAMProfileConfig:
    """Switch to lowvram profile as a last-resort fallback.

    Returns a new VRAMProfileConfig with lowvram settings.
    """
    from .config import resolve_vram_profile

    ctx.profile_escalated = True
    ctx.retries_log.append({
        "attempt": ctx.attempts,
        "action": "profile_escalation",
        "from": "normalvram",
        "to": "lowvram",
        "cause": "oom_retries_exhausted",
    })

    logger.warning(
        "[VRAMManager] Escalating to lowvram profile after %d failed attempts",
        ctx.attempts,
    )

    return resolve_vram_profile(VRAMProfile.LOWVRAM)


# ── Workflow patching ─────────────────────────────────────────────

def strip_preview_nodes(workflow: dict) -> dict:
    """Remove PreviewImage nodes from a workflow dict.

    This saves VRAM by avoiding the decode + preview render path
    that ComfyUI runs for PreviewImage nodes.

    Returns a new workflow dict with preview nodes removed and
    any dangling references cleaned up.
    """
    preview_ids = {
        nid for nid, node in workflow.items()
        if isinstance(node, dict) and node.get("class_type") == "PreviewImage"
    }
    if not preview_ids:
        return workflow

    cleaned = {
        nid: node for nid, node in workflow.items()
        if nid not in preview_ids
    }

    logger.debug(
        "[VRAMManager] Stripped %d PreviewImage node(s) from workflow",
        len(preview_ids),
    )
    return cleaned


def inject_model_unload_node(workflow: dict) -> dict:
    """Add a FreeU / unload-models hint node to the workflow.

    ComfyUI supports a dedicated POST /free endpoint for model
    unloading between passes.  This function is for in-workflow
    unloading when the API-level free is not available.

    Currently returns the workflow unchanged — we use the API-level
    free_models() call instead (see free_models_between_passes).
    """
    return workflow


# ── Model unloading via ComfyUI API ──────────────────────────────

def free_models_between_passes(
    base_url: str,
    unload: bool = True,
) -> bool:
    """POST /free to ComfyUI to unload models between passes.

    Args:
        base_url: ComfyUI server URL.
        unload: Whether to actually send the request.

    Returns:
        True if models were freed, False otherwise.
    """
    if not unload:
        return False

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(
                f"{base_url.rstrip('/')}/free",
                json={"unload_models": True, "free_memory": True},
            )
            if resp.status_code == 200:
                logger.info("[VRAMManager] Models unloaded via /free")
                return True
            logger.warning(
                "[VRAMManager] /free returned HTTP %d", resp.status_code,
            )
    except Exception as e:
        logger.warning("[VRAMManager] Failed to call /free: %s", e)
    return False


# ── Logging helpers ───────────────────────────────────────────────

def log_pass_memory_mode(
    pass_name: str,
    vram: VRAMProfileConfig,
    width: int,
    height: int,
) -> None:
    """Log the estimated memory mode for a pipeline pass."""
    megapixels = (width * height) / 1_000_000
    logger.info(
        "[VRAMManager] pass=%s profile=%s res=%dx%d (%.2f MP) "
        "cpu_vae=%s unload=%s tile=%d",
        pass_name,
        vram.profile.value,
        width, height, megapixels,
        vram.cpu_vae_offload,
        vram.unload_models_between_passes,
        vram.upscale_tile_size,
    )


def log_retry_cause(
    pass_name: str,
    ctx: RetryContext,
) -> None:
    """Log the cause of an OOM retry."""
    logger.warning(
        "[VRAMManager] pass=%s OOM retry cause: attempts=%d/%d "
        "resolution=%dx%d escalated=%s error=%s",
        pass_name,
        ctx.attempts, ctx.max_retries,
        ctx.current_width, ctx.current_height,
        ctx.profile_escalated,
        ctx.last_error[:100] if ctx.last_error else "none",
    )


def log_final_fallback(
    pass_name: str,
    ctx: RetryContext,
    vram: VRAMProfileConfig,
) -> None:
    """Log the final fallback state after all retries."""
    logger.info(
        "[VRAMManager] pass=%s FINAL: profile=%s res=%dx%d "
        "attempts=%d escalated=%s",
        pass_name,
        vram.profile.value,
        ctx.current_width, ctx.current_height,
        ctx.attempts,
        ctx.profile_escalated,
    )


# ── OOM-aware workflow submission ─────────────────────────────────

def submit_with_oom_retry(
    client: Any,
    workflow_builder_fn: Any,
    pass_name: str,
    job_id: str,
    vram: VRAMProfileConfig,
    width: int,
    height: int,
) -> tuple[Any, RetryContext]:
    """Submit a workflow with OOM-aware retry strategy.

    If the first attempt fails with an OOM error, reduces resolution
    and retries.  If retries exhaust, escalates to lowvram profile
    and tries once more.

    Args:
        client: ComfyClient instance.
        workflow_builder_fn: Callable(width, height) → workflow dict.
        pass_name: Pipeline pass name for logging.
        job_id: Job identifier for logging.
        vram: Current VRAMProfileConfig.
        width: Starting width.
        height: Starting height.

    Returns:
        (ComfyJobResult, RetryContext) — the result and retry state.
    """
    ctx = build_retry_context(width, height, vram)

    log_pass_memory_mode(pass_name, vram, width, height)

    # First attempt
    workflow = workflow_builder_fn(ctx.current_width, ctx.current_height)
    if vram.disable_previews:
        workflow = strip_preview_nodes(workflow)

    result = client.submit_workflow(workflow, job_id=job_id, pass_name=pass_name)

    if result.success:
        return result, ctx

    # Check if OOM
    if not vram.oom_retry_enabled or not is_oom_error(result.error):
        return result, ctx

    # OOM retry loop
    while not ctx.exhausted:
        ctx.last_error = result.error
        log_retry_cause(pass_name, ctx)

        new_w, new_h = step_down_resolution(ctx)

        # Free models before retry
        free_models_between_passes(client.base_url, unload=True)

        workflow = workflow_builder_fn(new_w, new_h)
        if vram.disable_previews:
            workflow = strip_preview_nodes(workflow)

        result = client.submit_workflow(workflow, job_id=job_id, pass_name=pass_name)
        if result.success:
            log_final_fallback(pass_name, ctx, vram)
            return result, ctx

        if not is_oom_error(result.error):
            break  # different error — stop retrying

    # Last resort: escalate to lowvram
    if not ctx.profile_escalated and is_oom_error(result.error):
        lowvram = escalate_to_lowvram(ctx)
        new_w = min(ctx.current_width, lowvram.max_resolution)
        new_h = min(ctx.current_height, lowvram.max_resolution)
        new_w = (new_w // 8) * 8
        new_h = (new_h // 8) * 8
        ctx.current_width = new_w
        ctx.current_height = new_h

        free_models_between_passes(client.base_url, unload=True)

        workflow = workflow_builder_fn(new_w, new_h)
        if lowvram.disable_previews:
            workflow = strip_preview_nodes(workflow)

        result = client.submit_workflow(workflow, job_id=job_id, pass_name=pass_name)
        log_final_fallback(pass_name, ctx, lowvram)

    return result, ctx
