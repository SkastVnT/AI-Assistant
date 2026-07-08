"""
DetectionInpaintAgent — ADetailer-style multi-region detection + inpaint pass.

Runs INSIDE the beauty-critique loop, after beauty pass and before critique.
For each detected region:
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
import re
import time
from pathlib import Path
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


def _is_job_cancel_requested(job_id: str) -> bool:
    """Best-effort check against the chatbot job queue cancel flag.

    Used as an instant-cancel checkpoint between region inpaint
    iterations so the agent stops submitting new ComfyUI workflows
    once the user clicks Stop. Silently returns ``False`` outside
    the chatbot process (tests, standalone usage).
    """
    if not job_id:
        return False
    try:
        from core.job_queue import get_queue  # type: ignore[import-not-found]

        return bool(get_queue().is_cancel_requested(job_id))
    except Exception:
        return False


# ── Processing order — regions are inpainted in this sequence ──────
# Face first (highest visual impact), cleanup last.
# full_eyes and eyes are deduplicated in DetectionDetailAgent.

REGION_PROCESSING_ORDER: list[str] = [
    # Tier 1: Core anatomy
    "face",
    "full_eyes",
    "eyes",
    "mouth",
    "hand",
    # Tier 1b (spec §6a): fine-grained face sub-regions — run AFTER face so
    # the layer painter has face bbox context to sub-mask from.
    "eyebrows",
    "nose",
    "lips",
    "iris",
    "pupil",
    "sclera",
    # Tier 1c: hand sub-region
    "fingernails",
    # Tier 2: Body detail
    "animal_ear",
    "hair",
    "neck",
    "torso",
    "navel",
    "armpit",
    "female_body",
    "person_female",
    "thigh",
    "leg",
    "feet",
    # Tier 3: Clothing and accessories
    "clothes",
    "underwear",
    "thighhigh",
    "swimsuit",
    "leotard",
    # Tier 4: Cleanup
    "text_watermark",
    "censor_bar",
    # Tier 5: NSFW-specific
    "breasts",
    "nipples",
    "genital",
    "pubic_area",
    # Tier 6: Disabled by default (broad/multi-class, user can enable)
    "nsfw_allinone",
    "multiclass",
    "face_bbox",
    "hand_bbox",
]

# ── Region-specific LoRA stacks ────────────────────────────────────

def _region_allowed_for_job(region_type: str, job: AnimePipelineJob) -> bool:
    """FULL NSFW mode: all detected regions are allowed."""
    return True


_REGION_LORA_MAP: dict[str, list[dict[str, Any]]] = {
    # Tier 1: Core anatomy
    "face": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.65,
            "strength_clip": 0.55,
        },  # was 0.55
    ],
    "full_eyes": [
        {
            "name": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
            "strength_model": 0.70,
            "strength_clip": 0.60,
        },
        {
            "name": "eye_check_by_hand.safetensors",
            "strength_model": 0.50,
            "strength_clip": 0.40,
        },
    ],
    "eyes": [
        {
            "name": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
            "strength_model": 0.65,
            "strength_clip": 0.55,
        },
        {
            "name": "eye_check_by_hand.safetensors",
            "strength_model": 0.50,
            "strength_clip": 0.40,
        },
    ],
    "mouth": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.45,
            "strength_clip": 0.35,
        },
    ],
    "hand": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.50,
            "strength_clip": 0.40,
        },
    ],
    # Tier 2: Body detail
    "animal_ear": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.40,
            "strength_clip": 0.30,
        },
    ],
    "hair": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.45,
            "strength_clip": 0.35,
        },
    ],
    "torso": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.25,
        },
    ],
    "armpit": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.30,
            "strength_clip": 0.20,
        },
    ],
    "female_body": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.25,
        },
    ],
    "person_female": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.30,
            "strength_clip": 0.20,
        },
    ],
    "feet": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.40,
            "strength_clip": 0.30,
        },
    ],
    # Tier 3: Clothing
    "clothes": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.40,
            "strength_clip": 0.30,
        },
    ],
    "underwear": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.25,
        },
    ],
    "thighhigh": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.25,
        },
    ],
    "swimsuit": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.25,
        },
    ],
    "leotard": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.25,
        },
    ],
    # Tier 4: Cleanup (no LoRAs — denoise handles removal)
    "text_watermark": [],
    "censor_bar": [],
    # Tier 5: NSFW
    "breasts": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.40,
            "strength_clip": 0.30,
        },
    ],
    "nipples": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.25,
        },
    ],
    "genital": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.25,
        },
    ],
    "pubic_area": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.30,
            "strength_clip": 0.20,
        },
    ],
    # Tier 6: Disabled multi-class
    "nsfw_allinone": [],
    "multiclass": [],
    "face_bbox": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.55,
            "strength_clip": 0.45,
        },
    ],
    "hand_bbox": [],
    # ── Spec §6a: fine-grained sub-regions ──────────────────────────
    # These share YOLO detectors with their parent region but are
    # applied by the layer painter with tighter sub-masks (PIL) so the
    # prompt/LoRA strength can target a smaller area.
    "eyebrows": [
        {
            "name": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.30,
        },
    ],
    "nose": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.25,
        },
    ],
    "lips": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.40,
            "strength_clip": 0.30,
        },
    ],
    "iris": [
        {
            "name": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
            "strength_model": 0.70,
            "strength_clip": 0.60,
        },
    ],
    "pupil": [
        {
            "name": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
            "strength_model": 0.60,
            "strength_clip": 0.50,
        },
    ],
    "sclera": [
        {
            "name": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",
            "strength_model": 0.45,
            "strength_clip": 0.35,
        },
    ],
    "fingernails": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.35,
            "strength_clip": 0.25,
        },
    ],
    "navel": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.30,
            "strength_clip": 0.20,
        },
    ],
    "neck": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.30,
            "strength_clip": 0.20,
        },
    ],
    "thigh": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.30,
            "strength_clip": 0.20,
        },
    ],
    "leg": [
        {
            "name": "Anime_artistic_2.safetensors",
            "strength_model": 0.30,
            "strength_clip": 0.20,
        },
    ],
}

# ── Auto-discovery of supplemental LoRAs ───────────────────────────
# After bulk_model_downloader.py drops files into ComfyUI/models/loras/effects/<sub>/,
# discovered .safetensors become *candidates* for the matching region(s).
# Unlike the hand-curated stacks above they are PROMPT-GATED: an effect LoRA
# (drool, ahegao, mouth-pull, …) only attaches when the job prompt actually
# asks for that effect. Unconditional stacking poisoned renders — a gentle
# closed-mouth smile once shipped with ~14 off-topic mouth LoRAs attached.

# Subfolder name → list of region_type keys it should be merged into
_EFFECT_SUBDIR_REGION_MAP: dict[str, tuple[str, ...]] = {
    "eyes": ("full_eyes", "eyes", "iris", "pupil", "sclera"),
    "mouth": ("mouth", "lips"),
    "expression": ("face", "mouth"),
    "drunk": ("face",),
    "sleep": ("face", "full_eyes", "eyes"),
    "drool": ("mouth", "lips"),
    "legs": ("leg", "thigh", "feet"),
    "pose": (),  # poses are control-layer concepts, not region LoRAs
    "outfit": ("clothes",),
    "style": (),  # styles are global, not region-specific
    "nsfw": ("breasts", "nipples", "genital", "pubic_area", "underwear"),
}

# Default supplemental strengths — kept lower than hand-curated entries so
# auto-discovered LoRAs reinforce rather than dominate.
_AUTO_LORA_STRENGTH_MODEL = 0.45
_AUTO_LORA_STRENGTH_CLIP = 0.35

# Hard cap per region pass — even with a matching prompt, stacking many
# effect LoRAs degrades quality and slows ComfyUI model patching.
_AUTO_EFFECT_MAX_PER_REGION = 2

# Candidate store: region_type → entries carrying a private "_match_terms"
# tuple used for prompt gating (stripped before the entry reaches a workflow).
_AUTO_EFFECT_LORAS: dict[str, list[dict[str, Any]]] = {}

# Generic anatomy words never count as evidence that the user asked for a
# specific effect ("closed mouth, smile" must NOT pull in mouth-pull LoRAs).
_MATCH_TERM_STOPLIST = {
    "mouth", "lips", "lip", "face", "eye", "eyes", "iris", "pupil",
    "smile", "expression", "open mouth", "closed mouth", "teeth",
    "girl", "1girl", "boy", "1boy", "solo", "anime", "detail", "detailed",
    "effect", "effects", "concept", "quality", "masterpiece",
    # model-family / packaging tokens that leak in from filenames
    "sd15", "sdxl", "pony", "illustrious", "noobai", "lora", "locon",
    "safetensors", "final", "version",
}


def _norm_term(s: str) -> str:
    """Lowercase, underscores→spaces, collapsed whitespace."""
    return " ".join(str(s).lower().replace("_", " ").split())


def _registry_match_terms() -> dict[str, tuple[str, ...]]:
    """basename.lower() → match terms from configs/lora_registry.yaml.

    Terms come from each entry's ``trigger_words`` + ``keywords`` (NOT
    ``tags`` — tags like "mouth"/"expression" are exactly the generic words
    the stoplist exists to block). Loaded once; failures yield an empty map.
    """
    cached = getattr(_registry_match_terms, "_cache", None)
    if cached is not None:
        return cached
    terms_by_name: dict[str, tuple[str, ...]] = {}
    try:
        import yaml  # local import — registry parsing is optional

        from ..lora_manager import _LORA_REGISTRY_YAML  # type: ignore

        data = yaml.safe_load(_LORA_REGISTRY_YAML.read_text(encoding="utf-8")) or {}
        for section in data.values():
            if not isinstance(section, list):
                continue
            for entry in section:
                if not isinstance(entry, dict) or not entry.get("name"):
                    continue
                raw_terms: list[str] = []
                for key in ("trigger_words", "keywords"):
                    val = entry.get(key) or []
                    if isinstance(val, str):
                        val = [val]
                    for item in val:
                        # trigger strings are often comma-joined tag lists
                        raw_terms.extend(str(item).split(","))
                terms = tuple(
                    dict.fromkeys(
                        t
                        for t in (_norm_term(x) for x in raw_terms)
                        if len(t) >= 4 and t not in _MATCH_TERM_STOPLIST
                    )
                )
                if terms:
                    terms_by_name[Path(str(entry["name"])).name.lower()] = terms
    except Exception as exc:  # noqa: BLE001 — registry is best-effort
        logger.debug("[DetectionInpaint] lora_registry match terms skipped: %s", exc)
    _registry_match_terms._cache = terms_by_name  # type: ignore[attr-defined]
    return terms_by_name


def _filename_match_terms(filename: str, sub_name: str) -> tuple[str, ...]:
    """Fallback match terms from a LoRA filename + its effects/ subfolder."""
    tokens = re.split(r"[^a-z0-9]+", Path(filename).stem.lower())
    terms = [
        t
        for t in tokens
        if len(t) >= 4 and not t.isdigit() and t not in _MATCH_TERM_STOPLIST
    ]
    sub = _norm_term(sub_name)
    if len(sub) >= 4 and sub not in _MATCH_TERM_STOPLIST:
        terms.append(sub)
    return tuple(dict.fromkeys(terms))


def _auto_discover_effect_loras() -> None:
    """Scan ComfyUI/models/loras/effects/<sub>/ into _AUTO_EFFECT_LORAS.

    Skipped silently if the directory is missing or scanning fails. Entries
    are candidates only — attachment happens per job via
    ``effect_loras_for_prompt`` when the prompt matches.
    """
    try:
        from ..lora_manager import _COMFYUI_LORA_ROOT  # type: ignore
    except Exception:
        return

    effects_root = _COMFYUI_LORA_ROOT / "effects"
    if not effects_root.is_dir():
        return

    registry_terms = _registry_match_terms()
    discovered = 0
    for sub_name, region_types in _EFFECT_SUBDIR_REGION_MAP.items():
        if not region_types:
            continue
        sub_dir = effects_root / sub_name
        if not sub_dir.is_dir():
            continue
        for f in sub_dir.glob("*.safetensors"):
            terms = registry_terms.get(f.name.lower()) or _filename_match_terms(
                f.name, sub_name
            )
            if not terms:
                continue  # nothing safe to gate on — never attach blindly
            entry = {
                "name": f"effects/{sub_name}/{f.name}",
                "strength_model": _AUTO_LORA_STRENGTH_MODEL,
                "strength_clip": _AUTO_LORA_STRENGTH_CLIP,
                "_match_terms": terms,
            }
            for region in region_types:
                stack = _AUTO_EFFECT_LORAS.setdefault(region, [])
                # Dedupe by basename so re-imports don't double-stack
                names = {Path(item.get("name", "")).name for item in stack}
                if f.name not in names:
                    stack.append(entry)
                    discovered += 1

    if discovered:
        logger.info(
            "[DetectionInpaint] Discovered %d prompt-gated effect LoRA "
            "candidate(s) across effects/ subfolders.",
            discovered,
        )


def effect_loras_for_prompt(
    region_type: str,
    prompt_text: str,
    *,
    max_count: int = _AUTO_EFFECT_MAX_PER_REGION,
) -> list[dict[str, Any]]:
    """Return auto-discovered effect LoRAs whose match terms appear in *prompt_text*.

    Entries are copies with the private ``_match_terms`` key stripped, capped
    at *max_count* per region. No prompt evidence → no attachment.
    """
    candidates = _AUTO_EFFECT_LORAS.get(region_type)
    if not candidates:
        return []
    prompt_norm = _norm_term(prompt_text)
    if not prompt_norm:
        return []
    selected: list[dict[str, Any]] = []
    for entry in candidates:
        terms = entry.get("_match_terms") or ()
        matched = next((t for t in terms if t in prompt_norm), None)
        if matched is None:
            continue
        clean = {k: v for k, v in entry.items() if k != "_match_terms"}
        selected.append(clean)
        logger.info(
            "[DetectionInpaint] Effect LoRA %s attached to %s (prompt matched %r)",
            Path(str(entry.get("name", ""))).name,
            region_type,
            matched,
        )
        if len(selected) >= max_count:
            break
    return selected


# Run discovery at import. Failures must not break module load.
try:
    _auto_discover_effect_loras()
except Exception as _exc:  # pragma: no cover - defensive
    logger.debug("[DetectionInpaint] effect LoRA auto-discovery skipped: %s", _exc)

# ── Quality tags per region ────────────────────────────────────────

# Skip any region whose bounding-box area exceeds this fraction of the full image.
# Prevents YOLO from spending time inpainting background figures that dominate the frame
# (e.g. a full-body background character covering 60-70% of the image).
# Foreground characters in portrait renders typically cover 10-30% per region.
_MAX_INPAINT_AREA_FRACTION: float = 0.55

_QUALITY_PREFIX = (
    "masterpiece, best quality, amazing quality, very aesthetic, absurdres, newest"
)

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
        f"{_QUALITY_PREFIX}, detailed skin texture, natural body, proper anatomy"
    ),
    # Tier 6: Multi-class (broad prompts)
    "nsfw_allinone": (
        f"{_QUALITY_PREFIX}, detailed anatomy, natural skin, proper proportions"
    ),
    "multiclass": (f"{_QUALITY_PREFIX}, detailed anatomy, proper proportions"),
    "face_bbox": (
        f"{_QUALITY_PREFIX}, "
        "beautiful detailed face, perfect features, "
        "detailed skin texture, vivid expression"
    ),
    "hand_bbox": (
        f"{_QUALITY_PREFIX}, detailed hands, correct fingers, well-drawn hands"
    ),
    # ── Spec §6a: fine-grained sub-regions ──────────────────────────
    "eyebrows": (
        f"{_QUALITY_PREFIX}, "
        "detailed eyebrows, clean brow shape, individual brow hairs, "
        "matching eyebrow color, proper arch, natural eyebrow density"
    ),
    "nose": (
        f"{_QUALITY_PREFIX}, "
        "perfect nose shape, subtle nose bridge, detailed nostrils, "
        "proportional nose, natural nose shading"
    ),
    "lips": (
        f"{_QUALITY_PREFIX}, "
        "beautiful detailed lips, soft lip shading, clean lip line, "
        "natural lip color, glossy highlight, symmetric lip shape"
    ),
    "iris": (
        f"{_QUALITY_PREFIX}, "
        "ultra detailed iris, intricate iris texture, radial iris pattern, "
        "clear limbal ring, vivid iris color, sharp iris definition, "
        "matching iris color both eyes"
    ),
    "pupil": (
        f"{_QUALITY_PREFIX}, "
        "perfectly round pupils, matching pupil size, centered pupil, "
        "deep black pupil, sharp pupil edge"
    ),
    "sclera": (
        f"{_QUALITY_PREFIX}, "
        "clean white sclera, smooth eye white, natural subtle shading, "
        "no redness, bright sclera"
    ),
    "fingernails": (
        f"{_QUALITY_PREFIX}, "
        "detailed fingernails, natural nail shape, glossy nail polish, "
        "clean nail edges, proper nail proportions, detailed nail color"
    ),
    "navel": (
        f"{_QUALITY_PREFIX}, "
        "detailed navel, proper navel shape, smooth skin around navel, "
        "natural belly contour"
    ),
    "neck": (
        f"{_QUALITY_PREFIX}, "
        "smooth neck, detailed collarbone, proper neck proportions, "
        "natural skin texture"
    ),
    "thigh": (
        f"{_QUALITY_PREFIX}, "
        "detailed thighs, smooth skin, proper thigh proportions, "
        "natural muscle shading"
    ),
    "leg": (
        f"{_QUALITY_PREFIX}, "
        "detailed legs, smooth skin, proper leg anatomy, "
        "natural calf shading, well-proportioned"
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
        "flat eyes, dull eyes, lifeless eyes"
    ),
    "eyes": (
        "lazy eye, cross-eye, uneven pupils, blurry iris, "
        "malformed eyelids, bad eyes, missing eye, "
        "flat eyes, dull eyes, lifeless eyes"
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
    "animal_ear": ("blurry ears, deformed ears, flat ears, bad fur, missing ears"),
    "hair": (
        "blurry hair, flat hair, bad hair texture, messy unnatural hair, bald patches"
    ),
    "torso": ("bad anatomy, deformed body, blurry torso, extra limbs"),
    "armpit": ("blurry skin, deformed arm, bad anatomy"),
    "female_body": (
        "bad anatomy, deformed body, extra limbs, missing limbs, unnatural proportions"
    ),
    "person_female": ("bad anatomy, deformed, extra limbs"),
    "feet": ("extra toes, missing toes, deformed feet, bad feet anatomy, six toes"),
    # Tier 3: Clothing
    "clothes": ("blurry clothing, deformed fabric, flat texture, bad clothing design"),
    "underwear": ("blurry fabric, deformed underwear, bad texture"),
    "thighhigh": ("blurry stockings, deformed fabric, bad texture"),
    "swimsuit": ("blurry fabric, deformed swimsuit, bad texture"),
    "leotard": ("blurry fabric, deformed leotard, bad texture"),
    # Tier 4: Cleanup
    "text_watermark": (
        "text, watermark, speech bubble, logo, signature, "
        "username, copyright, url, timestamp"
    ),
    "censor_bar": (
        "censored, mosaic, bar, black bar, white bar, pixelated, blurred region"
    ),
    # Tier 5: NSFW
    "breasts": ("deformed breasts, bad anatomy, asymmetrical, unnatural"),
    "nipples": ("deformed nipples, bad anatomy, unnatural"),
    "genital": ("deformed anatomy, bad anatomy, unnatural"),
    "pubic_area": ("deformed, unnatural, bad anatomy"),
    # Tier 6: Multi-class
    "nsfw_allinone": ("deformed anatomy, bad anatomy"),
    "multiclass": ("deformed, bad anatomy"),
    "face_bbox": ("blurry face, deformed face, ugly face"),
    "hand_bbox": ("bad hands, extra fingers, deformed hands"),
    # ── Spec §6a: fine-grained sub-regions ──────────────────────────
    "eyebrows": (
        "deformed eyebrows, missing eyebrows, asymmetrical brows, "
        "unibrow, bushy mess, wrong brow color"
    ),
    "nose": ("deformed nose, missing nose, crooked nose, oversized nose"),
    "lips": (
        "deformed lips, asymmetric lips, bad lip shading, cracked lips, off-color lips"
    ),
    "iris": (
        "mismatched iris color, blurry iris, flat iris, "
        "featureless iris, wrong eye color"
    ),
    "pupil": ("uneven pupil size, off-center pupil, deformed pupil, square pupil"),
    "sclera": ("red sclera, bloodshot, yellow sclera, dirty eye white, veiny sclera"),
    "fingernails": ("bad nails, missing nails, deformed fingernails, dirty nails"),
    "navel": ("deformed navel, missing navel, extra navel"),
    "neck": ("deformed neck, long neck, too-short neck, bad collarbone"),
    "thigh": ("deformed thighs, bad thigh anatomy, asymmetric thighs"),
    "leg": ("deformed legs, extra legs, missing leg, bad leg anatomy"),
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
        # Set per-execute() by detect_eye_taped_intent or job.metadata override.
        self._eye_taped_active: bool = False

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

        # Eye-taped intent: detect ONCE per execute() so all eye-region
        # passes use the same decision. Honour an explicit override via
        # job.metadata['eye_taped'] (UI toggle) but otherwise sniff the
        # user prompt directly.
        meta_override = (
            (job.metadata or {}).get("eye_taped") if hasattr(job, "metadata") else None
        )
        if isinstance(meta_override, bool):
            self._eye_taped_active = meta_override
        else:
            try:
                from ..eye_taped_lora import detect_eye_taped_intent

                self._eye_taped_active = detect_eye_taped_intent(
                    getattr(job, "user_prompt", "")
                )
            except Exception:  # noqa: BLE001 — never block the pipeline
                self._eye_taped_active = False
        if self._eye_taped_active:
            logger.info(
                "[DetectionInpaint] eye-taped intent ACTIVE — stacking "
                "high-strength eye-tape LoRAs on eye/face passes"
            )

        # Get the latest image (from beauty pass)
        current_image_b64 = self._get_latest_image(job)
        if not current_image_b64:
            logger.warning("[DetectionInpaint] No source image available, skipping")
            return

        # Compute image area once for region-size filtering below.
        image_area = self._get_image_area(current_image_b64)

        # Get base prompt from job for context
        base_positive = self._get_base_positive(job)
        base_negative = self._config.negative_base

        # Get checkpoint (same as beauty pass)
        checkpoint = (
            self._config.final_model.checkpoint or self._config.beauty_model.checkpoint
        )
        clip_skip = self._config.final_model.clip_skip or 2

        # Run detection
        detection = self._detector.detect(current_image_b64)
        # Spec §8/§9: expose the latest detection result to downstream
        # consumers (layer_painter needs face + eye bboxes).
        self.last_result = detection
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
            if not _region_allowed_for_job(region_type, job):
                logger.info(
                    "[DetectionInpaint] Skipping %s for content_mode=%s",
                    region_type,
                    getattr(job, "content_mode", "sfw"),
                )
                continue
            elapsed_ms = (time.time() - t0) * 1000
            if passes_run >= self._config.detection_inpaint_max_passes:
                logger.info("[DetectionInpaint] Reached configured pass cap")
                break
            if elapsed_ms >= self._config.detection_inpaint_time_budget_ms:
                logger.info("[DetectionInpaint] Reached configured time budget")
                break
            # Instant-cancel checkpoint: abort before submitting the
            # next region's inpaint workflow when the user clicked Stop.
            if _is_job_cancel_requested(getattr(job, "job_id", "")):
                logger.info(
                    "[DetectionInpaint] job=%s cancel requested — stopping region loop at %s (passes_run=%d)",
                    getattr(job, "job_id", "?"),
                    region_type,
                    passes_run,
                )
                break
            regions = detection.get(region_type)
            if not regions:
                continue
            regions = regions[: self._config.detection_inpaint_max_regions_per_pass]

            # Skip regions that cover more than _MAX_INPAINT_AREA_FRACTION of the
            # image — these are likely background figures, not detail-fixable subjects.
            if image_area > 0:
                combined_area = sum(r.area for r in regions)
                area_fraction = combined_area / image_area
                if area_fraction > _MAX_INPAINT_AREA_FRACTION:
                    logger.info(
                        "[DetectionInpaint] Skipping %s — combined region area %.0f%% "
                        "exceeds cap %.0f%% (likely background figure)",
                        region_type,
                        area_fraction * 100,
                        _MAX_INPAINT_AREA_FRACTION * 100,
                    )
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

            # Region-specific LoRAs (filtered to ones actually present on disk)
            region_loras = self._filter_existing_loras(
                list(_REGION_LORA_MAP.get(region_type, [])),
                region_type=region_type,
            )
            # Prompt-gated effect LoRAs (drool/ahegao/mouth-pull/…): only
            # attach when the user prompt or planned prompt actually asks
            # for the effect — never blanket-stack a whole effects/ folder.
            region_loras.extend(
                effect_loras_for_prompt(
                    region_type,
                    f"{getattr(job, 'user_prompt', '')} {base_positive}",
                )
            )
            # Also include default LoRAs from config at reduced strength
            for lora in self._config.default_loras:
                reduced = dict(lora)
                reduced["strength_model"] = (
                    float(reduced.get("strength_model", reduced.get("strength", 0.5)))
                    * 0.7
                )
                reduced["strength_clip"] = (
                    float(reduced.get("strength_clip", reduced.get("strength", 0.5)))
                    * 0.7
                )
                region_loras.append(reduced)

            # Eye-taped LoRA stack (Layer 4 sub-effect, opt-in via prompt
            # intent). Stacks AT FULL STRENGTH on top of the standard eye
            # LoRAs because the user spec explicitly requests "cuc cao".
            if region_type in ("full_eyes", "eyes", "face", "eyebrows"):
                if self._eye_taped_active:
                    from ..eye_taped_lora import (
                        build_eye_taped_lora_stack,
                        EYE_TAPED_POSITIVE,
                        EYE_TAPED_NEGATIVE,
                    )

                    region_loras.extend(
                        build_eye_taped_lora_stack(
                            character_name=getattr(job, "character_name", ""),
                            character_tag=getattr(job, "character_tag", ""),
                        )
                    )
                    region_positive = self._merge_prompt(
                        region_positive,
                        EYE_TAPED_POSITIVE,
                    )
                    region_negative = self._merge_prompt(
                        region_negative,
                        EYE_TAPED_NEGATIVE,
                    )

            region_loras = self._filter_existing_loras(
                region_loras, region_type=region_type
            )

            # Build PassConfig for this region
            seed = random.randint(1, 2**31 - 1)
            pc = PassConfig(
                pass_name=f"detail_{region_type}",
                model_slot="final",
                checkpoint=checkpoint,
                width=0,  # not used for inpaint (inherits from source)
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
                        pc,
                        current_image_b64,
                        regions[0].mask_b64,
                        seed,
                        clip_skip=clip_skip,
                        region_label=region_type,
                    )
                else:
                    masks = [r.mask_b64 for r in regions]
                    workflow = self._builder.build_multi_region_inpaint(
                        pc,
                        current_image_b64,
                        masks,
                        seed,
                        clip_skip=clip_skip,
                        region_label=region_type,
                    )

                result = self._client.submit_workflow(
                    workflow,
                    job_id=job.job_id,
                    pass_name=f"detail_{region_type}",
                )

                if result.success and result.images_b64:
                    current_image_b64 = result.images_b64[0]
                    job.intermediates.append(
                        IntermediateImage(
                            stage=f"detail_{region_type}",
                            image_b64=current_image_b64,
                            metadata={
                                "region_type": region_type,
                                "regions_count": len(regions),
                                "denoise": layer_cfg.denoise,
                                "seed": seed,
                                "detections": [r.to_dict() for r in regions],
                            },
                        )
                    )
                    passes_run += 1
                    logger.info(
                        "[DetectionInpaint] %s pass completed (%d regions, %.0fms)",
                        region_type,
                        len(regions),
                        result.duration_ms,
                    )
                else:
                    logger.warning(
                        "[DetectionInpaint] %s pass failed: %s",
                        region_type,
                        result.error or "no output",
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
            passes_run,
            total_region_count,
            job.stage_timings_ms["detection_inpaint"],
        )

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _get_image_area(image_b64: str) -> int:
        """Return pixel area of a base64-encoded image, or 0 if unavailable."""
        try:
            import base64 as _b64
            import io

            from PIL import Image as _Image

            data = _b64.b64decode(image_b64)
            with _Image.open(io.BytesIO(data)) as img:
                return img.width * img.height
        except Exception:
            return 0

    def _get_latest_image(self, job: AnimePipelineJob) -> str:
        """Get the most recent *render* image from intermediates.

        Skips non-render artifacts whose ``image_b64`` is a control hint
        (lineart / depth / canny / mask) rather than a finished frame.
        Without this filter the lineart produced by ``structure_lock``
        would be picked as the source for inpainting, turning the final
        result into a black-and-white edge map.
        """
        _NON_RENDER_PREFIXES = (
            "structure_",
            "mask_",
            "hint_",
            "control_",
            "preprocess_",
        )
        _NON_RENDER_EXACT = {
            "lineart",
            "lineart_anime",
            "depth",
            "canny",
            "pre_upscale",
            "upscale_hint",
        }
        for img in reversed(job.intermediates):
            if not img.image_b64:
                continue
            stage = (img.stage or "").lower()
            if stage in _NON_RENDER_EXACT:
                continue
            if any(stage.startswith(p) for p in _NON_RENDER_PREFIXES):
                continue
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

    @staticmethod
    def _filter_existing_loras(
        loras: list[dict[str, Any]],
        *,
        region_type: str = "",
    ) -> list[dict[str, Any]]:
        """Drop region LoRAs whose .safetensors is not on disk.

        Prevents ComfyUI from aborting an inpaint pass when the hardcoded
        helper LoRAs (e.g., ``Anime_artistic_2.safetensors``) are missing.
        The pass still runs with prompts only — no LoRAs is safer than a
        dangling reference.

        Also drops files that exist on disk but are not in ComfyUI's cached
        ``LoraLoader`` dropdown (happens when bulk_model_downloader drops
        files into ``effects/<sub>/`` AFTER ComfyUI started — ComfyUI then
        rejects the workflow with HTTP 400 ``value_not_in_list``).
        """
        from ..lora_manager import lora_file_exists, lora_known_to_comfyui

        kept: list[dict[str, Any]] = []
        dropped_disk: list[str] = []
        dropped_comfy: list[str] = []
        for lora in loras:
            name = lora.get("name", "") if isinstance(lora, dict) else ""
            if not name:
                continue
            if not lora_file_exists(name):
                dropped_disk.append(name)
                continue
            if not lora_known_to_comfyui(name):
                dropped_comfy.append(name)
                continue
            kept.append(lora)

        if dropped_disk:
            logger.warning(
                "[DetectionInpaint] Dropping missing LoRA(s) for region %r: %s",
                region_type or "?",
                dropped_disk,
            )
        if dropped_comfy:
            logger.warning(
                "[DetectionInpaint] Dropping LoRA(s) unknown to ComfyUI for region %r "
                "(restart ComfyUI to refresh its LoraLoader cache): %s",
                region_type or "?",
                dropped_comfy,
            )
        return kept

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

    # ── Eye Emergency ─────────────────────────────────────────────────

    # Eye-specific region types processed in eye_focus mode
    _EYE_REGION_TYPES = ("full_eyes", "eyes", "face")

    def execute_eye_focus(
        self,
        job: "AnimePipelineJob",
        denoise_override: float = 0.55,
        reference_eye_crops: Optional[list[str]] = None,
        eye_issues: Optional[list[str]] = None,
        character_eye_description: str = "",
    ) -> None:
        """Emergency eye-focused inpaint — higher denoise, eye regions only.

        Called when critique reports eye_consistency_score < 7.
        Runs YOLO detection for eye/face regions only and inpaints them
        with boosted denoise to force stronger correction.

        Args:
            job: Pipeline job (modified in-place).
            denoise_override: Inpaint strength (default 0.55, higher than normal 0.35).
            reference_eye_crops: Optional cropped eye images from reference photos.
            eye_issues: Specific issues from critique (appended to negative prompt).
            character_eye_description: Character's canonical eye description from research.
        """
        t0 = time.time()

        if not self.is_available():
            logger.info("[DetectionInpaint] Eye focus skipped — not available")
            return

        current_image_b64 = self._get_latest_image(job)
        if not current_image_b64:
            return

        base_positive = self._get_base_positive(job)
        checkpoint = (
            self._config.final_model.checkpoint or self._config.beauty_model.checkpoint
        )
        clip_skip = self._config.final_model.clip_skip or 2
        base_negative = self._config.negative_base

        # Run detection — eyes + face only
        detection = self._detector.detect(current_image_b64)
        if detection.total_regions == 0:
            logger.info("[DetectionInpaint] Eye focus: no eye/face regions detected")
            return

        # Build eye-boosted positive prompt
        eye_extra = ""
        if character_eye_description:
            eye_extra = f", {character_eye_description}"
        issue_tags = ""
        if eye_issues:
            issue_tags = ", " + ", ".join(f"fix: {iss}" for iss in eye_issues[:3])

        eye_negative_extra = ""
        if eye_issues:
            eye_negative_extra = ", " + ", ".join(eye_issues[:5])

        passes_run = 0
        for region_type in self._EYE_REGION_TYPES:
            # Instant-cancel checkpoint for eye-emergency pass: the
            # beauty-critique loop may trigger this AFTER the user
            # clicked Stop; refuse to submit new ComfyUI workflows.
            if _is_job_cancel_requested(getattr(job, "job_id", "")):
                logger.info(
                    "[DetectionInpaint] job=%s cancel requested — skipping eye_emergency_%s",
                    getattr(job, "job_id", "?"),
                    region_type,
                )
                break
            regions = detection.get(region_type)
            if not regions:
                continue

            layer_cfg = self._detector.get_layer_config(region_type)
            if not layer_cfg:
                continue

            # Boosted positive: standard eye tags + character-specific eye desc
            region_positive = self._merge_prompt(
                base_positive,
                _REGION_POSITIVE.get(region_type, ""),
                layer_cfg.prompt_suffix,
                "ultra detailed eyes, perfect iris, perfect pupil symmetry,"
                " sharp catchlight, vivid eye color, matching eye colors"
                + eye_extra
                + issue_tags,
            )
            region_negative = self._merge_prompt(
                base_negative,
                _REGION_NEGATIVE.get(region_type, ""),
                layer_cfg.negative_suffix,
                "blurry eyes, lazy eye, mismatched eye colors, wrong eye color,"
                " cross-eyed, lifeless eyes, flat eyes" + eye_negative_extra,
            )

            region_loras = self._filter_existing_loras(
                list(_REGION_LORA_MAP.get(region_type, [])),
                region_type=region_type,
            )

            seed = random.randint(1, 2**31 - 1)
            pc = PassConfig(
                pass_name=f"eye_emergency_{region_type}",
                model_slot="final",
                checkpoint=checkpoint,
                width=0,
                height=0,
                sampler=self._config.final_model.sampler,
                scheduler=self._config.final_model.scheduler,
                steps=max(20, min(30, self._config.final_model.steps)),
                cfg=self._config.final_model.cfg
                + 0.5,  # slightly higher cfg for eye detail
                denoise=denoise_override,  # boosted
                seed=seed,
                positive_prompt=region_positive,
                negative_prompt=region_negative,
                lora_models=region_loras,
            )

            try:
                if len(regions) == 1:
                    workflow = self._builder.build_detection_inpaint(
                        pc,
                        current_image_b64,
                        regions[0].mask_b64,
                        seed,
                        clip_skip=clip_skip,
                        region_label=region_type,
                    )
                else:
                    masks = [r.mask_b64 for r in regions]
                    workflow = self._builder.build_multi_region_inpaint(
                        pc,
                        current_image_b64,
                        masks,
                        seed,
                        clip_skip=clip_skip,
                        region_label=region_type,
                    )

                result = self._client.submit_workflow(
                    workflow,
                    job_id=job.job_id,
                    pass_name=f"eye_emergency_{region_type}",
                )

                if result.success and result.images_b64:
                    current_image_b64 = result.images_b64[0]
                    job.intermediates.append(
                        IntermediateImage(
                            stage=f"detail_{region_type}_emergency",
                            image_b64=current_image_b64,
                            metadata={
                                "region_type": region_type,
                                "denoise": denoise_override,
                                "eye_emergency": True,
                                "seed": seed,
                                "regions_count": len(regions),
                            },
                        )
                    )
                    passes_run += 1
                    logger.info(
                        "[DetectionInpaint] Eye emergency %s done (denoise=%.2f, %.0fms)",
                        region_type,
                        denoise_override,
                        result.duration_ms,
                    )
                else:
                    logger.warning(
                        "[DetectionInpaint] Eye emergency %s failed: %s",
                        region_type,
                        result.error or "no output",
                    )
            except Exception as exc:
                logger.warning(
                    "[DetectionInpaint] Eye emergency %s error: %s", region_type, exc
                )

        if passes_run > 0:
            job.final_image_b64 = current_image_b64

        latency = (time.time() - t0) * 1000
        logger.info(
            "[DetectionInpaint] Eye focus completed %d passes in %.0fms",
            passes_run,
            latency,
        )
