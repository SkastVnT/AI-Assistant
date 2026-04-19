"""
StructureLockAgent — Stage 4: Extract control layers from composition image.

Runs ControlNet preprocessors (lineart, depth, canny) on the composition
to lock structure before the beauty redraw pass.

Delegates workflow construction to WorkflowBuilder.build_structure_lock_layer()
and ComfyUI submission to ComfyClient.submit_workflow().

Each layer is processed independently with fault isolation:
if one preprocessor fails or produces empty output, the others continue.
Only required (non-optional) layer failures propagate as errors.

Priority order (from config):
    lineart = highest priority — silhouette and contour
    depth   = medium priority — scene layout
    canny   = optional, low-to-medium — hard edges
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from ..comfy_client import ComfyClient
from ..config import AnimePipelineConfig, StructureLayerConfig
from ..schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
    StructureLayer,
    StructureLayerType,
)
from ..workflow_builder import WorkflowBuilder

logger = logging.getLogger(__name__)

# Minimum base64 size to consider a preprocessor output valid.
# A nearly-empty PNG (~68 bytes) → ~92 chars base64.  Use 200 as threshold.
_MIN_HINT_B64_LENGTH = 200


# ── Quality check ─────────────────────────────────────────────────

def validate_hint_image(image_b64: str, layer_type: str) -> bool:
    """Check if a preprocessor hint image is usable.

    Returns False (skip gracefully) when:
      - No image data returned
      - Image data suspiciously small (likely empty/broken preprocessor output)
    """
    if not image_b64:
        logger.warning(
            "[StructureLock] %s: preprocessor returned no image", layer_type,
        )
        return False
    if len(image_b64) < _MIN_HINT_B64_LENGTH:
        logger.warning(
            "[StructureLock] %s: preprocessor output too small (%d chars), "
            "likely empty or broken — skipping",
            layer_type, len(image_b64),
        )
        return False
    return True


# ═══════════════════════════════════════════════════════════════════
# StructureLockAgent
# ═══════════════════════════════════════════════════════════════════

class StructureLockAgent:
    """Extract control layers (lineart, depth, canny) from composition image.

    Uses WorkflowBuilder for preprocessor workflow construction and
    ComfyClient for submission + polling.

    Control behavior is configurable per layer:
      - ``enabled`` — skip layer entirely when False
      - ``strength`` — ControlNet influence (0.0–1.0)
      - ``start_percent`` / ``end_percent`` — when the control applies
      - ``optional`` — if True, failures are logged but do not raise
      - ``priority`` — extraction order (lower = higher priority)

    Quality guard: if a preprocessor returns an empty or too-small
    image, the layer is skipped gracefully instead of crashing.
    """

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._builder = WorkflowBuilder()
        self._client = ComfyClient(base_url=config.comfyui_url)

    def execute(self, job: AnimePipelineJob) -> AnimePipelineJob:
        """Run structure lock — extract control layers from composition image."""
        job.status = AnimePipelineStatus.STRUCTURE_LOCKING
        t0 = time.time()

        # Get composition image (or user-supplied sketch)
        comp_image = self._get_source_image(job)
        if not comp_image:
            logger.warning("[StructureLock] No composition image found, skipping")
            job.mark_stage("structure_lock", 0.0)
            return job

        # Resolve which layers to extract (enabled, sorted by priority)
        layers = self._resolve_layers()
        if not layers:
            logger.info("[StructureLock] No enabled layers, skipping")
            job.mark_stage("structure_lock", 0.0)
            return job

        for lc in layers:
            try:
                layer_b64 = self._extract_layer(comp_image, lc)

                if not validate_hint_image(layer_b64 or "", lc.layer_type):
                    if not lc.optional:
                        logger.warning(
                            "[StructureLock] Required layer %s produced unusable output",
                            lc.layer_type,
                        )
                    continue

                # Store extracted layer on job
                job.structure_layers.append(StructureLayer(
                    layer_type=StructureLayerType(lc.layer_type),
                    image_b64=layer_b64,
                    preprocessor=lc.preprocessor,
                    controlnet_model=lc.controlnet_model,
                    strength=lc.strength,
                    start_percent=lc.start_percent,
                    end_percent=lc.end_percent,
                ))

                # Save as debug artifact
                job.add_intermediate(
                    f"structure_{lc.layer_type}", layer_b64,
                    preprocessor=lc.preprocessor,
                )
                logger.info("[StructureLock] Extracted %s layer", lc.layer_type)

                # Populate image_b64 on matching control_inputs in plan passes
                if job.layer_plan:
                    for pc in job.layer_plan.passes:
                        for ci in pc.control_inputs:
                            if ci.layer_type == lc.layer_type and not ci.image_b64:
                                ci.image_b64 = layer_b64

            except Exception as e:
                logger.warning(
                    "[StructureLock] Failed to extract %s: %s",
                    lc.layer_type, e,
                )
                if not lc.optional:
                    raise

        latency = (time.time() - t0) * 1000
        job.mark_stage("structure_lock", latency)
        logger.info(
            "[StructureLock] Done in %.0fms, %d layers extracted",
            latency, len(job.structure_layers),
        )
        return job

    # ── Public API ────────────────────────────────────────────────────

    def build_structure_lock_workflow(
        self,
        input_image_b64: str,
        control_configs: list[StructureLayerConfig] | None = None,
    ) -> dict[str, dict]:
        """Build preprocessor workflows for all enabled layers.

        Useful for testing, debugging, or external submission.

        Args:
            input_image_b64: Source image (composition output or user sketch).
            control_configs: Override layer configs. Uses pipeline config if None.

        Returns:
            Dict mapping ``layer_type`` → ComfyUI workflow dict.
        """
        layers = control_configs if control_configs is not None else self._resolve_layers()
        result: dict[str, dict] = {}
        for lc in layers:
            if not lc.enabled:
                continue
            result[lc.layer_type] = self._builder.build_structure_lock_layer(
                input_image_b64, lc,
            )
        return result

    def get_enabled_layers(self) -> list[StructureLayerConfig]:
        """Return enabled structure layer configs, sorted by priority."""
        return self._resolve_layers()

    # ── Internals ─────────────────────────────────────────────────────

    def _resolve_layers(self) -> list[StructureLayerConfig]:
        """Get enabled layers from config, sorted by priority, respecting max_simultaneous."""
        layers = [lc for lc in self._config.structure_layers if lc.enabled]
        layers.sort(key=lambda lc: lc.priority)

        max_layers = self._config.max_simultaneous_layers
        if len(layers) > max_layers:
            dropped = layers[max_layers:]
            layers = layers[:max_layers]
            logger.info(
                "[StructureLock] Limiting to %d layers (dropped: %s)",
                max_layers, [lc.layer_type for lc in dropped],
            )

        return layers

    def _get_source_image(self, job: AnimePipelineJob) -> Optional[str]:
        """Get source image for structure extraction.

        Priority:
          1. Composition pass output (most common)
          2. User-supplied source image (sketch / reference edit)
        """
        for img in reversed(job.intermediates):
            if img.stage == "composition_pass":
                return img.image_b64
        return job.source_image_b64 or None

    def _extract_layer(
        self,
        source_b64: str,
        layer_config: StructureLayerConfig,
    ) -> Optional[str]:
        """Run a preprocessor on the source image via ComfyUI.

        Returns the extracted hint image as base64, or None on failure.
        """
        workflow = self._builder.build_structure_lock_layer(
            source_b64, layer_config,
        )
        result = self._client.submit_workflow(
            workflow,
            job_id="",
            pass_name=f"structure_lock_{layer_config.layer_type}",
        )

        if not result.success:
            logger.warning(
                "[StructureLock] %s preprocessor failed: %s",
                layer_config.layer_type, result.error,
            )
            return None

        if not result.images_b64:
            return None

        return result.images_b64[0]
