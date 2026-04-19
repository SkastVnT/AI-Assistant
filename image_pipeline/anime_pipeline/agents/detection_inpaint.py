"""
DetectionInpaintAgent — ADetailer-style multi-region detection + inpaint pass.

Runs AFTER the beauty pass. For each detected region:
  1. Detect regions with YOLO via DetectionDetailAgent (27 models)
  2. Build region-specific prompts (quality + region focus + LoRAs)
  3. Submit masked inpaint workflow to ComfyUI
  4. Chain results: output of each pass becomes input of the next

The agent uses the same checkpoint as the beauty pass but with region-specific
LoRA stacks and prompt enhancements for maximum detail quality.

Detection tiers (processed in order):
  Tier 1: face, full_eyes, eyes, mouth, hand — core anatomy
  Tier 2: animal_ear, hair, torso, armpit, feet — body detail
  Tier 3: clothes, underwear, thighhigh, swimsuit, leotard — clothing
  Tier 4: text_watermark, censor_bar — cleanup
  Tier 5: breasts, nipples, genital, pubic_area — NSFW regions
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Optional

from ..comfy_client import ComfyClient
from ..config import AnimePipelineConfig
from ..schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
    IntermediateImage,
    PassConfig,
)
from ..workflow_builder import WorkflowBuilder
from .detection_detail import (
    DetectedRegion,
    DetectionDetailAgent,
    DetectionModelConfig,
    DetectionResult,
    DEFAULT_DETECTION_LAYERS,
)

logger = logging.getLogger(__name__)

# ── Processing order — regions are inpainted in this sequence ──────
# Face first (highest visual impact), cleanup last.
# full_eyes and eyes are deduplicated in DetectionDetailAgent.

REGION_PROCESSING_ORDER: list[str] = [
    # Tier 1: Core anatomy
    "face", "full_eyes", "eyes", "mouth", "hand",
    # Tier 2: Body detail
    "animal_ear", "hair", "torso", "armpit", "female_body", "person_female", "feet",
    # Tier 3: Clothing and accessories
    "clothes", "underwear", "thighhigh", "swimsuit", "leotard",
    # Tier 4: Cleanup
    "text_watermark", "censor_bar",
    # Tier 5: NSFW-specific
    "breasts", "nipples", "genital", "pubic_area",
    # Tier 6: Disabled by default (broad/multi-class, user can enable)
    "nsfw_allinone", "multiclass", "face_bbox", "hand_bbox",
]

# ── Region-specific LoRA stacks ────────────────────────────────────

_REGION_LORA_MAP: dict[str, list[dict[str, Any]]] = {
    # Tier 1: Core anatomy
    "face": [
        {"name": "Anime_artistic_2.safetensors", "strength_model": 0.55, "strength_clip": 0.45},
    ],
    "full_eyes": [
        {"name": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "strength_model": 0.50, "strength_clip": 0.40},
        {"name": "eye_check_by_hand.safetensors", "strength_model": 0.35, "strength_clip": 0.25},
    ],
    "eyes": [
        {"name": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors", "strength_model": 0.45, "strength_clip": 0.35},
        {"name": "eye_check_by_hand.safetensors", "strength_model": 0.35, "strength_clip": 0.25},
    ],
    "mouth": [],
    "hand": [],
    # Tier 2: Body detail
    "animal_ear": [],
    "hair": [],
    "torso": [],
    "armpit": [],
    "female_body": [],
    "person_female": [],
    "feet": [],
    # Tier 3: Clothing
    "clothes": [],
    "underwear": [],
    "thighhigh": [],
    "swimsuit": [],
    "leotard": [],
    # Tier 4: Cleanup (no LoRAs — denoise handles removal)
    "text_watermark": [],
    "censor_bar": [],
    # Tier 5: NSFW
    "breasts": [],
    "nipples": [],
    "genital": [],
    "pubic_area": [],
    # Tier 6: Disabled multi-class
    "nsfw_allinone": [],
    "multiclass": [],
    "face_bbox": [
        {"name": "Anime_artistic_2.safetensors", "strength_model": 0.55, "strength_clip": 0.45},
    ],
    "hand_bbox": [],
}

# ── Quality tags per region ────────────────────────────────────────

_QUALITY_PREFIX = "masterpiece, best quality, very aesthetic, absurdres"

_REGION_POSITIVE: dict[str, str] = {
    # Tier 1: Core anatomy
    "face": (
        f"{_QUALITY_PREFIX}, "
        "beautiful detailed face, detailed skin texture, "
        "perfect eye symmetry, clear iris, sharp eyelashes, "
        "detailed eyebrows, smooth facial shading, vivid expression"
    ),
    "full_eyes": (
        f"{_QUALITY_PREFIX}, "
        "ultra detailed eyes, intricate iris texture, clear limbal ring, "
        "vivid catchlight, sharp eyelash strands, beautiful anime eyes, "
        "balanced eye symmetry, perfect pupils, gleaming eyes, "
        "matching iris color"
    ),
    "eyes": (
        f"{_QUALITY_PREFIX}, "
        "ultra detailed eyes, intricate iris texture, clear limbal ring, "
        "vivid catchlight, sharp eyelash strands, beautiful anime eyes, "
        "balanced eye symmetry, perfect pupils, gleaming eyes"
    ),
    "mouth": (
        f"{_QUALITY_PREFIX}, "
        "detailed mouth, beautiful lips, correct teeth, "
        "natural smile, detailed oral anatomy, well-shaped lips"
    ),
    "hand": (
        f"{_QUALITY_PREFIX}, "
        "detailed hands, correct finger count, five fingers, "
        "anatomically correct hands, well-drawn hands, "
        "detailed fingernails, proper finger proportions"
    ),
    # Tier 2: Body detail
    "animal_ear": (
        f"{_QUALITY_PREFIX}, "
        "detailed fluffy animal ears, soft fur texture, "
        "detailed ear interior, beautiful kemonomimi, "
        "realistic fur shading"
    ),
    "hair": (
        f"{_QUALITY_PREFIX}, "
        "detailed hair strands, flowing hair, "
        "silky hair texture, individual hair strands visible, "
        "beautiful hair highlights, glossy hair shading"
    ),
    "torso": (
        f"{_QUALITY_PREFIX}, "
        "detailed body, smooth skin, "
        "detailed torso, proper body anatomy, "
        "beautiful midriff, detailed navel"
    ),
    "armpit": (
        f"{_QUALITY_PREFIX}, "
        "detailed armpit, smooth skin, proper arm anatomy, "
        "natural skin tone"
    ),
    "female_body": (
        f"{_QUALITY_PREFIX}, "
        "detailed body, proper anatomy, beautiful figure, "
        "smooth skin texture, proper proportions"
    ),
    "person_female": (
        f"{_QUALITY_PREFIX}, "
        "detailed character, proper anatomy, beautiful, "
        "well-proportioned figure"
    ),
    "feet": (
        f"{_QUALITY_PREFIX}, "
        "detailed feet, correct toes, proper foot anatomy, "
        "five toes, well-drawn feet, detailed toenails"
    ),
    # Tier 3: Clothing
    "clothes": (
        f"{_QUALITY_PREFIX}, "
        "detailed clothing, proper fabric texture, "
        "realistic cloth folds, detailed outfit, "
        "well-defined seams, fabric shading"
    ),
    "underwear": (
        f"{_QUALITY_PREFIX}, "
        "detailed underwear, proper fabric texture, "
        "realistic lingerie, lace detail, "
        "fabric pattern, delicate material"
    ),
    "thighhigh": (
        f"{_QUALITY_PREFIX}, "
        "detailed thigh highs, proper fabric texture, "
        "realistic stockings, elastic band detail, "
        "sheer fabric, proper transparency"
    ),
    "swimsuit": (
        f"{_QUALITY_PREFIX}, "
        "detailed swimsuit, proper fabric texture, "
        "realistic material, tight fit, "
        "well-defined edges"
    ),
    "leotard": (
        f"{_QUALITY_PREFIX}, "
        "detailed leotard, proper fabric texture, "
        "realistic material, strapless design, "
        "well-defined edges, fabric tension"
    ),
    # Tier 4: Cleanup
    "text_watermark": (
        f"{_QUALITY_PREFIX}, "
        "clean background, smooth area, no text, "
        "no watermark, no speech bubble, "
        "natural background, seamless fill"
    ),
    "censor_bar": (
        f"{_QUALITY_PREFIX}, "
        "clean uncensored area, detailed skin, "
        "natural anatomy, smooth texture, "
        "seamless skin"
    ),
    # Tier 5: NSFW
    "breasts": (
        f"{_QUALITY_PREFIX}, "
        "detailed breasts, proper anatomy, "
        "smooth skin texture, natural shape"
    ),
    "nipples": (
        f"{_QUALITY_PREFIX}, "
        "detailed nipples, proper anatomy, "
        "natural areola, smooth skin"
    ),
    "genital": (
        f"{_QUALITY_PREFIX}, "
        "detailed anatomy, natural skin texture, "
        "proper anatomy, smooth skin"
    ),
    "pubic_area": (
        f"{_QUALITY_PREFIX}, "
        "detailed skin texture, natural body, proper anatomy"
    ),
    # Tier 6: Multi-class (broad prompts)
    "nsfw_allinone": (
        f"{_QUALITY_PREFIX}, "
        "detailed anatomy, natural skin, proper proportions"
    ),
    "multiclass": (
        f"{_QUALITY_PREFIX}, "
        "detailed anatomy, proper proportions"
    ),
    "face_bbox": (
        f"{_QUALITY_PREFIX}, "
        "beautiful detailed face, perfect features, "
        "detailed skin texture, vivid expression"
    ),
    "hand_bbox": (
        f"{_QUALITY_PREFIX}, "
        "detailed hands, correct fingers, well-drawn hands"
    ),
}

_REGION_NEGATIVE: dict[str, str] = {
    # Tier 1: Core anatomy
    "face": (
        "blurry face, asymmetrical eyes, deformed face, ugly face, "
        "bad anatomy face, extra eyes, missing eyes, bad nose, "
        "distorted face, low quality face"
    ),
    "full_eyes": (
        "lazy eye, cross-eye, uneven pupils, blurry iris, "
        "malformed eyelids, bad eyes, missing eye, "
        "heterochromia, different eye colors, mismatched irises"
    ),
    "eyes": (
        "lazy eye, cross-eye, uneven pupils, blurry iris, "
        "malformed eyelids, bad eyes, missing eye, "
        "heterochromia, different eye colors, mismatched irises"
    ),
    "mouth": (
        "blurry mouth, deformed lips, bad teeth, "
        "crooked mouth, missing teeth, unnatural smile"
    ),
    "hand": (
        "bad hands, extra fingers, missing fingers, "
        "fused fingers, deformed hands, mutated hands, "
        "too many fingers, six fingers, four fingers"
    ),
    # Tier 2: Body detail
    "animal_ear": (
        "blurry ears, deformed ears, flat ears, "
        "bad fur, missing ears"
    ),
    "hair": (
        "blurry hair, flat hair, bad hair texture, "
        "messy unnatural hair, bald patches"
    ),
    "torso": (
        "bad anatomy, deformed body, blurry torso, "
        "extra limbs"
    ),
    "armpit": (
        "blurry skin, deformed arm, bad anatomy"
    ),
    "female_body": (
        "bad anatomy, deformed body, extra limbs, "
        "missing limbs, unnatural proportions"
    ),
    "person_female": (
        "bad anatomy, deformed, extra limbs"
    ),
    "feet": (
        "extra toes, missing toes, deformed feet, "
        "bad feet anatomy, six toes"
    ),
    # Tier 3: Clothing
    "clothes": (
        "blurry clothing, deformed fabric, flat texture, "
        "bad clothing design"
    ),
    "underwear": (
        "blurry fabric, deformed underwear, bad texture"
    ),
    "thighhigh": (
        "blurry stockings, deformed fabric, bad texture"
    ),
    "swimsuit": (
        "blurry fabric, deformed swimsuit, bad texture"
    ),
    "leotard": (
        "blurry fabric, deformed leotard, bad texture"
    ),
    # Tier 4: Cleanup
    "text_watermark": (
        "text, watermark, speech bubble, logo, signature, "
        "username, copyright, url, timestamp"
    ),
    "censor_bar": (
        "censored, mosaic, bar, black bar, white bar, "
        "pixelated, blurred region"
    ),
    # Tier 5: NSFW
    "breasts": (
        "deformed breasts, bad anatomy, asymmetrical, unnatural"
    ),
    "nipples": (
        "deformed nipples, bad anatomy, unnatural"
    ),
    "genital": (
        "deformed anatomy, bad anatomy, unnatural"
    ),
    "pubic_area": (
        "deformed, unnatural, bad anatomy"
    ),
    # Tier 6: Multi-class
    "nsfw_allinone": (
        "deformed anatomy, bad anatomy"
    ),
    "multiclass": (
        "deformed, bad anatomy"
    ),
    "face_bbox": (
        "blurry face, deformed face, ugly face"
    ),
    "hand_bbox": (
        "bad hands, extra fingers, deformed hands"
    ),
}


class DetectionInpaintAgent:
    """ADetailer-style detection + inpaint agent for the anime pipeline.

    Sits between beauty_pass and critique in the orchestrator.
    Runs ALL detected region types in priority order (REGION_PROCESSING_ORDER).

    Each region pass:
      - Detects regions using YOLO models (27 models available)
      - Creates feathered masks for each detection
      - Builds and submits a ComfyUI inpaint workflow
      - Uses region-specific LoRAs and prompts
      - Chains: output of one pass is input of the next
    """

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._builder = WorkflowBuilder()
        self._client = ComfyClient(
            base_url=config.comfyui_url,
            debug_mode=config.save_intermediates,
            debug_dir=config.intermediate_dir,
        )

        # Detection layer config from config or defaults — MUST load before detector
        self._detection_layers = self._load_detection_config()
        self._detector = DetectionDetailAgent(
            detection_layers=self._detection_layers,
        )
        self._enabled = config.detection_inpaint_enabled

    def is_available(self) -> bool:
        """Check if detection libraries are available."""
        return self._detector.available() and self._enabled

    def execute(self, job: AnimePipelineJob) -> None:
        """Run detection-inpaint pipeline on the latest beauty pass output.

        Modifies `job` in-place: appends intermediates, updates final_image_b64.
        """
        t0 = time.time()

        if not self.is_available():
            logger.info("[DetectionInpaint] Skipped — detection not available")
            return

        # Get the latest image (from beauty pass)
        current_image_b64 = self._get_latest_image(job)
        if not current_image_b64:
            logger.warning("[DetectionInpaint] No source image available, skipping")
            return

        # Get base prompt from job for context
        base_positive = self._get_base_positive(job)
        base_negative = self._config.negative_base

        # Get checkpoint (same as beauty pass)
        checkpoint = self._config.final_model.checkpoint or self._config.beauty_model.checkpoint
        clip_skip = self._config.final_model.clip_skip or 2

        # Run detection
        detection = self._detector.detect(current_image_b64)
        if detection.total_regions == 0:
            logger.info("[DetectionInpaint] No regions detected, skipping")
            job.stage_timings_ms["detection_inpaint"] = (time.time() - t0) * 1000
            return

        logger.info(
            "[DetectionInpaint] Found %d regions — starting inpaint passes",
            detection.total_regions,
        )

        # Process regions in priority order (REGION_PROCESSING_ORDER)
        # Each pass chains: output becomes input of next
        # Unknown region types (from config) are processed after known ones

        ordered_types: list[str] = []
        detected_types = set(detection.all_region_types)

        # First: known order
        for rtype in REGION_PROCESSING_ORDER:
            if rtype in detected_types:
                ordered_types.append(rtype)
                detected_types.discard(rtype)

        # Then: any remaining unknown types from config
        for rtype in sorted(detected_types):
            ordered_types.append(rtype)

        passes_run = 0
        total_region_count = 0
        for region_type in ordered_types:
            regions = detection.get(region_type)
            if not regions:
                continue

            total_region_count += len(regions)

            layer_cfg = self._detector.get_layer_config(region_type)
            if not layer_cfg:
                continue

            # Merge prompts: base context + region-specific detail
            region_positive = self._merge_prompt(
                base_positive,
                _REGION_POSITIVE.get(region_type, ""),
                layer_cfg.prompt_suffix,
            )
            region_negative = self._merge_prompt(
                base_negative,
                _REGION_NEGATIVE.get(region_type, ""),
                layer_cfg.negative_suffix,
            )

            # Region-specific LoRAs
            region_loras = list(_REGION_LORA_MAP.get(region_type, []))
            # Also include default LoRAs from config at reduced strength
            for lora in self._config.default_loras:
                reduced = dict(lora)
                reduced["strength_model"] = float(reduced.get("strength_model", reduced.get("strength", 0.5))) * 0.7
                reduced["strength_clip"] = float(reduced.get("strength_clip", reduced.get("strength", 0.5))) * 0.7
                region_loras.append(reduced)

            # Build PassConfig for this region
            seed = random.randint(1, 2**31 - 1)
            pc = PassConfig(
                pass_name=f"detail_{region_type}",
                model_slot="final",
                checkpoint=checkpoint,
                width=0,   # not used for inpaint (inherits from source)
                height=0,
                sampler=self._config.final_model.sampler,
                scheduler=self._config.final_model.scheduler,
                steps=max(15, min(25, self._config.final_model.steps - 5)),
                cfg=self._config.final_model.cfg,
                denoise=layer_cfg.denoise,
                seed=seed,
                positive_prompt=region_positive,
                negative_prompt=region_negative,
                lora_models=region_loras,
            )

            # Build and submit workflow
            try:
                if len(regions) == 1:
                    workflow = self._builder.build_detection_inpaint(
                        pc, current_image_b64, regions[0].mask_b64, seed,
                        clip_skip=clip_skip, region_label=region_type,
                    )
                else:
                    masks = [r.mask_b64 for r in regions]
                    workflow = self._builder.build_multi_region_inpaint(
                        pc, current_image_b64, masks, seed,
                        clip_skip=clip_skip, region_label=region_type,
                    )

                result = self._client.submit_workflow(
                    workflow,
                    job_id=job.job_id,
                    pass_name=f"detail_{region_type}",
                )

                if result.success and result.images_b64:
                    current_image_b64 = result.images_b64[0]
                    job.intermediates.append(IntermediateImage(
                        stage=f"detail_{region_type}",
                        image_b64=current_image_b64,
                        metadata={
                            "region_type": region_type,
                            "regions_count": len(regions),
                            "denoise": layer_cfg.denoise,
                            "seed": seed,
                            "detections": [r.to_dict() for r in regions],
                        },
                    ))
                    passes_run += 1
                    logger.info(
                        "[DetectionInpaint] %s pass completed (%d regions, %.0fms)",
                        region_type, len(regions), result.duration_ms,
                    )
                else:
                    logger.warning(
                        "[DetectionInpaint] %s pass failed: %s",
                        region_type, result.error or "no output",
                    )

            except Exception as e:
                logger.warning("[DetectionInpaint] %s pass error: %s", region_type, e)
                continue

        # Update job with the final chained image
        if passes_run > 0:
            job.final_image_b64 = current_image_b64
            job.stages_executed.append("detection_inpaint")
            job.models_used.append("yolo_detection")

        # Free detection models
        self._detector.unload_models()

        job.stage_timings_ms["detection_inpaint"] = (time.time() - t0) * 1000
        logger.info(
            "[DetectionInpaint] Completed %d passes (%d regions) in %.0fms",
            passes_run, total_region_count,
            job.stage_timings_ms["detection_inpaint"],
        )

    # ── Helpers ──────────────────────────────────────────────────────

    def _get_latest_image(self, job: AnimePipelineJob) -> str:
        """Get the most recent image from intermediates (beauty pass output)."""
        for img in reversed(job.intermediates):
            if img.image_b64:
                return img.image_b64
        return job.final_image_b64 or ""

    def _get_base_positive(self, job: AnimePipelineJob) -> str:
        """Extract base positive prompt from job's layer plan."""
        if job.layer_plan and job.layer_plan.passes:
            # Use the beauty pass prompt as base context
            for p in reversed(job.layer_plan.passes):
                if p.pass_name in ("beauty", "beauty_pass") and p.positive_prompt:
                    return p.positive_prompt
            # Fallback to first pass
            if job.layer_plan.passes[0].positive_prompt:
                return job.layer_plan.passes[0].positive_prompt
        return self._config.quality_prefix + ", " + job.user_prompt

    def _merge_prompt(self, *parts: str) -> str:
        """Merge prompt parts, deduplicating tags."""
        seen = set()
        tags = []
        for part in parts:
            for tag in part.split(","):
                tag = tag.strip()
                if tag and tag.lower() not in seen:
                    seen.add(tag.lower())
                    tags.append(tag)
        return ", ".join(tags)

    def _load_detection_config(self) -> list[DetectionModelConfig]:
        """Load detection layer configs from pipeline config or defaults."""
        yaml_layers = self._config.detection_inpaint_layers
        if not yaml_layers:
            return list(DEFAULT_DETECTION_LAYERS)

        layers = []
        for raw in yaml_layers:
            layer = DetectionModelConfig(
                model_path=raw.get("model_path", ""),
                region_type=raw.get("region_type", "face"),
                confidence_threshold=float(raw.get("confidence_threshold", 0.3)),
                enabled=bool(raw.get("enabled", True)),
                denoise=float(raw.get("denoise", 0.35)),
                padding_ratio=float(raw.get("padding_ratio", 0.25)),
                feather_radius=int(raw.get("feather_radius", 20)),
                prompt_suffix=raw.get("prompt_suffix", ""),
                negative_suffix=raw.get("negative_suffix", ""),
            )
            layers.append(layer)

            # Load region-specific LoRAs from YAML config
            yaml_loras = raw.get("loras", [])
            if isinstance(yaml_loras, list) and yaml_loras:
                _REGION_LORA_MAP[layer.region_type] = yaml_loras

        return layers or list(DEFAULT_DETECTION_LAYERS)
