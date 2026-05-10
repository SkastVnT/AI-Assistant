"""
image_pipeline.anime_pipeline.agents.detection_detail — YOLO-based region detection + inpaint detail pass.

ADetailer-style workflow:
  1. Run YOLO detection models on the beauty-pass output to find face, eyes, hands
  2. Generate feathered masks from bounding boxes
  3. Build ComfyUI inpaint workflows per detected region
  4. Submit each inpaint pass to ComfyUI for region-specific detail enhancement
  5. Composite the results back into the base image

Detection models (from ComfyUI/models/ultralytics/):
  - bbox/face_yolov8n.pt        → face detection
  - bbox/hand_yolov8n.pt        → hand detection
  - bbox/eyesDetection_v10.zip  → eye detection
  - segm/adetailerAnimeGirlFace_segment.zip → face segmentation

This agent runs detection in Python (ultralytics) and builds
inpaint workflows for ComfyUI, so it works without needing
ComfyUI-Impact-Pack custom nodes.
"""

from __future__ import annotations

import base64
import io
import logging
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Lazy imports (heavy deps) ───────────────────────────────────────

_PIL_AVAILABLE = False
_ULTRALYTICS_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFilter
    _PIL_AVAILABLE = True
except ImportError:
    pass

try:
    from ultralytics import YOLO
    _ULTRALYTICS_AVAILABLE = True
except ImportError:
    pass


# ── Data contracts ──────────────────────────────────────────────────

@dataclass
class DetectedRegion:
    """A single detected region (face, eye, hand, etc.)."""
    region_type: str       # "face", "eyes", "hand"
    x1: int = 0
    y1: int = 0
    x2: int = 0
    y2: int = 0
    confidence: float = 0.0
    mask_b64: str = ""     # feathered mask as base64 PNG
    label: str = ""

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_type": self.region_type,
            "bbox": [self.x1, self.y1, self.x2, self.y2],
            "confidence": round(self.confidence, 3),
            "label": self.label,
            "width": self.width,
            "height": self.height,
        }


@dataclass
class DetectionResult:
    """All detected regions for a single image — supports arbitrary region types."""
    # Generic region storage: maps region_type → list of detections
    regions: dict[str, list[DetectedRegion]] = field(default_factory=dict)
    latency_ms: float = 0.0

    # ── Backward-compatible accessors ────────────────────────────────
    @property
    def faces(self) -> list[DetectedRegion]:
        return self.regions.get("face", [])

    @property
    def eyes(self) -> list[DetectedRegion]:
        return self.regions.get("eyes", []) + self.regions.get("full_eyes", [])

    @property
    def hands(self) -> list[DetectedRegion]:
        return self.regions.get("hand", [])

    def get(self, region_type: str) -> list[DetectedRegion]:
        """Get detections for any region type."""
        return self.regions.get(region_type, [])

    def add(self, region: DetectedRegion) -> None:
        """Add a detected region to the appropriate list."""
        if region.region_type not in self.regions:
            self.regions[region.region_type] = []
        self.regions[region.region_type].append(region)

    @property
    def all_region_types(self) -> list[str]:
        """Return all region types that have detections."""
        return [k for k, v in self.regions.items() if v]

    @property
    def total_regions(self) -> int:
        return sum(len(v) for v in self.regions.values())

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {}
        for rtype, regions in self.regions.items():
            d[rtype] = [r.to_dict() for r in regions]
        d["total_regions"] = self.total_regions
        d["latency_ms"] = round(self.latency_ms, 1)
        return d


# ── Detection model registry ───────────────────────────────────────

@dataclass
class DetectionModelConfig:
    """Configuration for a YOLO detection model."""
    model_path: str         # Relative to ComfyUI/models/ultralytics/
    region_type: str        # "face", "eyes", "hand"
    confidence_threshold: float = 0.3
    enabled: bool = True
    # Inpaint settings for regions detected by this model
    denoise: float = 0.35
    padding_ratio: float = 0.25   # expand bbox by this ratio for context
    feather_radius: int = 20      # mask feathering in pixels
    prompt_suffix: str = ""       # appended to positive prompt for this region
    negative_suffix: str = ""     # appended to negative prompt


# Default detection layer configs — ordered by priority tier:
#   Tier 1: Core anatomy (face, eyes, mouth, hand) — highest impact
#   Tier 2: Body regions (body, hair, ears, torso, armpit)
#   Tier 3: Clothing (clothes, underwear, thighhigh, swimsuit, leotard)
#   Tier 4: Cleanup (text/watermark, censor bar)
#   Tier 5: NSFW-specific (always last)
#
# ALL models from ComfyUI/models/ultralytics/ are registered here.
# Disable individual layers in anime_pipeline.yaml to skip them.

DEFAULT_DETECTION_LAYERS: list[DetectionModelConfig] = [
    # ── Tier 1: Core anatomy ─────────────────────────────────────────

    # 1. Anime girl face — segmentation (precise, excludes males)
    DetectionModelConfig(
        model_path="segm/adetailerAnimeGirlFace_segment.zip",
        region_type="face",
        confidence_threshold=0.35,
        denoise=0.42,  # was 0.35 — needs more strength to fix structural face issues
        padding_ratio=0.20,  # was 0.15 — wider context for better eye/eyebrow coherence
        feather_radius=26,
        prompt_suffix=(
            "beautiful detailed face, detailed skin texture, "
            "perfect eye symmetry, clear iris, sharp eyelashes, "
            "detailed eyebrows, smooth facial shading, vivid expression, "
            "natural skin tone, perfect nose shape, well-defined jaw"
        ),
        negative_suffix=(
            "blurry face, asymmetrical eyes, deformed face, ugly face, "
            "bad anatomy face, extra eyes, missing eyes, flat face, "
            "distorted features, bad nose, bad mouth"
        ),
    ),

    # 2. Full eyes detection (both eyes as pair — prevents mismatched irises)
    DetectionModelConfig(
        model_path="bbox/fullEyesDetection_v10.zip",
        region_type="full_eyes",
        confidence_threshold=0.30,
        denoise=0.48,  # was 0.30 — needs to be high enough to structurally fix broken eyes
        padding_ratio=0.35,  # wider crop = more context for iris/catchlight coherence
        feather_radius=16,
        prompt_suffix=(
            "ultra detailed eyes, intricate iris texture, clear limbal ring, "
            "vivid catchlight, sharp eyelash strands, beautiful anime eyes, "
            "balanced eye symmetry, perfect pupils, gleaming eyes, "
            "bright specular highlight, detailed iris pattern"
        ),
        negative_suffix=(
            "lazy eye, cross-eye, uneven pupils, blurry iris, "
            "malformed eyelids, bad eyes, missing eye, "
            "flat eyes, dull eyes, lifeless eyes"
        ),
    ),

    # 3. Individual eye detection (fallback if full_eyes misses)
    DetectionModelConfig(
        model_path="bbox/eyesDetection_v10.zip",
        region_type="eyes",
        confidence_threshold=0.30,
        denoise=0.45,  # was 0.28 — too low to fix structurally broken eyes
        padding_ratio=0.30,
        feather_radius=14,
        prompt_suffix=(
            "detailed eye, perfect iris, clear pupil, "
            "sharp eyelashes, beautiful anime eye, "
            "vivid catchlight, bright specular highlight"
        ),
        negative_suffix=(
            "blurry eye, deformed pupil, bad iris, flat eye, dull eye"
        ),
    ),

    # 4. Mouth detection (2D anime-optimized, yolo11n)
    DetectionModelConfig(
        model_path="segm/adetailer2dMouth_v10.pt",
        region_type="mouth",
        confidence_threshold=0.50,  # was 0.55 — slightly lower to catch subtle mouths
        denoise=0.38,  # was 0.30 — more strength for lip/teeth repair
        padding_ratio=0.25,  # was 0.20 — include chin/upper lip context
        feather_radius=16,
        prompt_suffix=(
            "detailed mouth, beautiful lips, correct teeth, "
            "natural smile, detailed oral anatomy, "
            "well-shaped lips, natural lip color, lip gloss"
        ),
        negative_suffix=(
            "blurry mouth, deformed lips, bad teeth, "
            "crooked mouth, missing teeth, unnatural smile, "
            "open wound, gaping mouth"
        ),
    ),

    # 5. Hand segmentation (trained on 2D/anime, better than generic yolov8n)
    DetectionModelConfig(
        model_path="segm/handDetailer_v2V9c.zip",
        region_type="hand",
        confidence_threshold=0.30,
        denoise=0.50,  # was 0.38 — hands need aggressive rebuild for finger count
        padding_ratio=0.25,  # was 0.20 — include wrist context for anatomy coherence
        feather_radius=20,
        prompt_suffix=(
            "detailed hands, correct finger count, five fingers, "
            "anatomically correct hands, well-drawn hands, "
            "detailed fingernails, proper finger proportions, "
            "natural hand pose, distinct fingers, clear knuckles"
        ),
        negative_suffix=(
            "bad hands, extra fingers, missing fingers, "
            "fused fingers, deformed hands, mutated hands, "
            "too many fingers, six fingers, four fingers, "
            "blob hands, mitten hands"
        ),
    ),

    # 6. Generic face bbox (backup if segm misses — includes males)
    DetectionModelConfig(
        model_path="bbox/face_yolov8n.pt",
        region_type="face_bbox",
        confidence_threshold=0.40,
        denoise=0.32,
        padding_ratio=0.15,
        feather_radius=22,
        enabled=False,  # disabled by default — segm version preferred
        prompt_suffix=(
            "beautiful detailed face, perfect features, "
            "detailed skin texture, vivid expression"
        ),
        negative_suffix=(
            "blurry face, deformed face, ugly face"
        ),
    ),

    # 7. Generic hand bbox (backup if segm misses)
    DetectionModelConfig(
        model_path="bbox/hand_yolov8n.pt",
        region_type="hand_bbox",
        confidence_threshold=0.35,
        denoise=0.35,
        padding_ratio=0.18,
        feather_radius=16,
        enabled=False,  # disabled by default — segm version preferred
        prompt_suffix=(
            "detailed hands, correct fingers, well-drawn hands"
        ),
        negative_suffix=(
            "bad hands, extra fingers, deformed hands"
        ),
    ),

    # ── Tier 2: Body regions ─────────────────────────────────────────

    # 8. Animal ear detection (cat ears, fox ears, etc.)
    DetectionModelConfig(
        model_path="bbox/animalEarDetection_v10.zip",
        region_type="animal_ear",
        confidence_threshold=0.35,
        denoise=0.38,  # was 0.30 — more strength for fur texture and ear shape
        padding_ratio=0.28,  # was 0.25 — wider context for head integration
        feather_radius=16,
        prompt_suffix=(
            "detailed fluffy animal ears, soft fur texture, "
            "detailed ear interior, beautiful kemonomimi, "
            "realistic fur shading, proper ear anatomy, "
            "individual fur strands visible"
        ),
        negative_suffix=(
            "blurry ears, deformed ears, flat ears, bad fur, "
            "missing ears, melted ears, plastic texture"
        ),
    ),

    # 9. Anime girl hair detection (yolo11n-based)
    DetectionModelConfig(
        model_path="segm/AdetailerAnimeGirlHair_v10.pt",
        region_type="hair",
        confidence_threshold=0.40,
        denoise=0.35,  # was 0.28 — more strength for proper strand detail
        padding_ratio=0.20,  # was 0.15 — include scalp/shoulder for flow context
        feather_radius=22,
        prompt_suffix=(
            "detailed hair strands, flowing hair, "
            "silky hair texture, individual hair strands visible, "
            "beautiful hair highlights, hair shading, "
            "lustrous hair, fine hair detail, hair volume"
        ),
        negative_suffix=(
            "blurry hair, flat hair, bad hair texture, "
            "messy unnatural hair, bald patches, "
            "plastic hair, no hair detail"
        ),
    ),

    # 10. Belly/torso/stomach segmentation
    DetectionModelConfig(
        model_path="segm/adetailer2dBellyTorso_v242Lg.zip",
        region_type="torso",
        confidence_threshold=0.40,
        denoise=0.33,  # was 0.28 — slightly more to fix skin/anatomy artifacts
        padding_ratio=0.18,  # was 0.15 — slightly wider for waist context
        feather_radius=22,
        prompt_suffix=(
            "detailed body, smooth skin, "
            "detailed torso, proper body anatomy, "
            "beautiful midriff, detailed navel, "
            "natural skin texture, proper body proportions"
        ),
        negative_suffix=(
            "bad anatomy, deformed body, blurry torso, "
            "extra ribs, deformed navel, unnatural waist"
        ),
    ),

    # 11. Armpit detection (yolov8 bbox + segmentation)
    DetectionModelConfig(
        model_path="segm/adetailer2dArmpitYolov8_v10Segmentation.zip",
        region_type="armpit",
        confidence_threshold=0.55,  # was 0.60 — slightly lower to catch partially hidden armpits
        denoise=0.35,  # was 0.28 — more strength for skin texture
        padding_ratio=0.22,  # was 0.20
        feather_radius=14,
        prompt_suffix=(
            "detailed armpit, smooth skin, proper arm anatomy, "
            "natural skin texture, clean skin detail"
        ),
        negative_suffix=(
            "blurry skin, deformed arm, bad skin texture"
        ),
    ),

    # 12. Female body detection (full body segmentation)
    DetectionModelConfig(
        model_path="segm/femaleBodyDetection_yolo26.pt",
        region_type="female_body",
        confidence_threshold=0.40,
        denoise=0.25,
        padding_ratio=0.10,
        feather_radius=24,
        enabled=False,  # disabled by default — use specific regions instead
        prompt_suffix=(
            "detailed body, proper anatomy, beautiful figure, "
            "smooth skin texture"
        ),
        negative_suffix=(
            "bad anatomy, deformed body, extra limbs"
        ),
    ),

    # 13. Person female detection (bbox)
    DetectionModelConfig(
        model_path="bbox/personFemale_v10.pt",
        region_type="person_female",
        confidence_threshold=0.40,
        denoise=0.22,
        padding_ratio=0.08,
        feather_radius=20,
        enabled=False,  # disabled by default — too broad, use specific regions
        prompt_suffix=(
            "detailed character, proper anatomy, beautiful"
        ),
        negative_suffix=(
            "bad anatomy, deformed"
        ),
    ),

    # 14. Feet/soles detection (bbox)
    DetectionModelConfig(
        model_path="bbox/reignyolov8nsolesPt_solesDetectionV10.pt",
        region_type="feet",
        confidence_threshold=0.45,  # was 0.50 — slightly lower to catch angled feet
        denoise=0.42,  # was 0.32 — more strength for toe count repair
        padding_ratio=0.25,  # was 0.20 — include ankle for proportion coherence
        feather_radius=18,
        prompt_suffix=(
            "detailed feet, correct toes, proper foot anatomy, "
            "five toes, well-drawn feet, detailed toenails, "
            "natural foot arch, clear toe separation"
        ),
        negative_suffix=(
            "extra toes, missing toes, deformed feet, "
            "bad feet anatomy, six toes, fused toes, "
            "blob feet, mitten feet"
        ),
    ),

    # ── Tier 3: Clothing and accessories ─────────────────────────────

    # 15. Clothes detection (tops — suit, shirt, sweater, bikini, etc.)
    DetectionModelConfig(
        model_path="segm/clothesDetection_tops.zip",
        region_type="clothes",
        confidence_threshold=0.45,
        denoise=0.35,  # was 0.30 — more strength for fabric detail
        padding_ratio=0.14,  # was 0.12 — slightly wider for seam context
        feather_radius=18,
        prompt_suffix=(
            "detailed clothing, proper fabric texture, "
            "realistic cloth folds, detailed outfit, "
            "clean fabric shading, proper clothing wrinkles, "
            "material detail, button and seam detail"
        ),
        negative_suffix=(
            "blurry clothing, deformed fabric, flat texture, "
            "missing clothing detail, torn fabric"
        ),
    ),

    # 16. Women's underwear detection (segmentation)
    DetectionModelConfig(
        model_path="segm/womensUnderwear_pantiesSegV3b.pt",
        region_type="underwear",
        confidence_threshold=0.45,
        denoise=0.35,  # was 0.30 — more strength for fabric detail
        padding_ratio=0.15,
        feather_radius=14,
        prompt_suffix=(
            "detailed underwear, proper fabric texture, "
            "realistic lingerie, lace detail, "
            "clean fabric shading, elastic band detail"
        ),
        negative_suffix=(
            "blurry fabric, deformed underwear, "
            "missing detail, flat texture"
        ),
    ),

    # 17. Thigh high detection (stockings, thigh highs)
    DetectionModelConfig(
        model_path="bbox/thighhighDetectionFor_thighhighv50.pt",
        region_type="thighhigh",
        confidence_threshold=0.48,  # was 0.50
        denoise=0.34,  # was 0.28 — more strength for stocking texture
        padding_ratio=0.18,  # was 0.15 — wider for garter/thigh context
        feather_radius=16,
        prompt_suffix=(
            "detailed thigh highs, proper fabric texture, "
            "realistic stockings, elastic band detail, "
            "transparent stocking texture, leg contour through fabric"
        ),
        negative_suffix=(
            "blurry stockings, deformed fabric, flat texture"
        ),
    ),

    # 18. One-piece swimsuit detection (segmentation)
    DetectionModelConfig(
        model_path="segm/adetailer2dOnePieceSwimsuit_v1042.zip",
        region_type="swimsuit",
        confidence_threshold=0.45,
        denoise=0.34,  # was 0.30 — more strength for fabric/strap detail
        padding_ratio=0.14,  # was 0.12
        feather_radius=16,
        prompt_suffix=(
            "detailed swimsuit, proper fabric texture, "
            "realistic material, tight fit, "
            "clean strap detail, proper body contour"
        ),
        negative_suffix=(
            "blurry fabric, deformed swimsuit, flat texture"
        ),
    ),

    # 19. Strapless leotard detection (segmentation)
    DetectionModelConfig(
        model_path="segm/adetailer2dStrapless_v10Yolo8n.zip",
        region_type="leotard",
        confidence_threshold=0.45,
        denoise=0.33,  # was 0.28 — more strength for fabric detail
        padding_ratio=0.14,  # was 0.12
        feather_radius=16,
        prompt_suffix=(
            "detailed leotard, proper fabric texture, "
            "realistic material, strapless design, "
            "tight fit, body contour, clean edges"
        ),
        negative_suffix=(
            "blurry fabric, deformed leotard, flat texture"
        ),
    ),

    # ── Tier 4: Cleanup / post-processing ────────────────────────────

    # 20. Text / speech bubble / watermark detection
    DetectionModelConfig(
        model_path="bbox/adetailerForTextSpeech_v20.zip",
        region_type="text_watermark",
        confidence_threshold=0.50,
        denoise=0.75,  # high denoise to fully remove text
        padding_ratio=0.10,
        feather_radius=12,
        prompt_suffix=(
            "clean background, smooth area, no text, "
            "no watermark, no speech bubble"
        ),
        negative_suffix=(
            "text, watermark, speech bubble, logo, signature, "
            "username, copyright"
        ),
    ),

    # 21. Bar censor detection
    DetectionModelConfig(
        model_path="bbox/barCensorDetection_yolo26.pt",
        region_type="censor_bar",
        confidence_threshold=0.40,
        denoise=0.80,  # very high to fully remove censorship
        padding_ratio=0.10,
        feather_radius=10,
        prompt_suffix=(
            "clean uncensored area, detailed skin, "
            "natural anatomy, smooth texture"
        ),
        negative_suffix=(
            "censored, mosaic, bar, black bar, white bar"
        ),
    ),

    # ── Tier 5: NSFW-specific regions ────────────────────────────────

    # 22. Breast detection (bbox)
    DetectionModelConfig(
        model_path="bbox/boobaDetection_v11.zip",
        region_type="breasts",
        confidence_threshold=0.40,
        denoise=0.40,  # was 0.30 — more strength for shape and skin detail
        padding_ratio=0.18,  # was 0.15 — wider for chest/torso context
        feather_radius=18,
        prompt_suffix=(
            "detailed breasts, proper anatomy, "
            "smooth skin texture, natural shape, "
            "realistic skin shading, proper cleavage, "
            "natural contour, beautiful proportions"
        ),
        negative_suffix=(
            "deformed breasts, bad anatomy, asymmetrical, "
            "unnatural shape, saggy, plastic looking"
        ),
    ),

    # 23. Nipple detection (segmentation)
    DetectionModelConfig(
        model_path="segm/adetailerNipples_v20Segm.zip",
        region_type="nipples",
        confidence_threshold=0.40,
        denoise=0.38,  # was 0.30 — more strength for areola detail
        padding_ratio=0.22,  # was 0.20 — include breast context
        feather_radius=12,
        prompt_suffix=(
            "detailed nipples, proper anatomy, "
            "natural areola, smooth skin, "
            "realistic skin texture, proper areola color"
        ),
        negative_suffix=(
            "deformed nipples, bad anatomy, "
            "missing nipples, extra nipples"
        ),
    ),

    # 24. NSFW region detection (genital area)
    DetectionModelConfig(
        model_path="bbox/pussyAdetailer_v5SegBboxYolo11s.zip",
        region_type="genital",
        confidence_threshold=0.38,  # was 0.40 — slightly lower to catch angled views
        denoise=0.42,  # was 0.32 — needs more strength for detail accuracy
        padding_ratio=0.20,  # was 0.18 — wider for thigh/hip context
        feather_radius=14,
        prompt_suffix=(
            "detailed anatomy, natural skin texture, "
            "proper anatomy, smooth skin, "
            "realistic anatomical detail, natural proportions"
        ),
        negative_suffix=(
            "deformed anatomy, bad anatomy, unnatural, "
            "censored, mosaic, blur"
        ),
    ),

    # 25. Pubic hair detection (bbox)
    DetectionModelConfig(
        model_path="bbox/adetailer2dFemalePubic_v10.zip",
        region_type="pubic_area",
        confidence_threshold=0.42,  # was 0.45
        denoise=0.38,  # was 0.28 — significantly more for proper detail
        padding_ratio=0.18,  # was 0.15 — wider for hip context
        feather_radius=14,
        prompt_suffix=(
            "detailed skin texture, natural body, proper anatomy, "
            "realistic skin shading, natural proportions"
        ),
        negative_suffix=(
            "deformed, unnatural, bad anatomy, "
            "censored, mosaic, blur"
        ),
    ),

    # 26. Anime NSFW all-in-one detection (multi-class)
    DetectionModelConfig(
        model_path="segm/animeNSFWDetection_v50Variant1.zip",
        region_type="nsfw_allinone",
        confidence_threshold=0.40,
        denoise=0.30,
        padding_ratio=0.15,
        feather_radius=16,
        enabled=False,  # disabled by default — use specific models above
        prompt_suffix=(
            "detailed anatomy, natural skin, proper proportions"
        ),
        negative_suffix=(
            "deformed anatomy, bad anatomy"
        ),
    ),

    # 27. Multi-class face/body adetailer (face/anus/penis/breasts/vagina/nipples)
    DetectionModelConfig(
        model_path="bbox/adetailers_facef.pt",
        region_type="multiclass",
        confidence_threshold=0.40,
        denoise=0.30,
        padding_ratio=0.15,
        feather_radius=18,
        enabled=False,  # disabled by default — use specific models above
        prompt_suffix=(
            "detailed anatomy, proper proportions"
        ),
        negative_suffix=(
            "deformed, bad anatomy"
        ),
    ),
]


class DetectionDetailAgent:
    """Runs YOLO detection on an image and builds inpaint masks for each region.

    Usage:
        agent = DetectionDetailAgent(comfyui_models_dir)
        result = agent.detect(image_b64)
        for region in result.faces + result.eyes + result.hands:
            # region.mask_b64 is a feathered mask ready for ComfyUI inpaint
            workflow = builder.build_detection_inpaint(...)
    """

    def __init__(
        self,
        comfyui_models_dir: str | Path = "",
        detection_layers: list[DetectionModelConfig] | None = None,
    ):
        if not comfyui_models_dir:
            # Default: ComfyUI/models relative to repo root
            repo_root = Path(__file__).resolve().parents[3]
            comfyui_models_dir = repo_root / "ComfyUI" / "models"

        self._models_dir = Path(comfyui_models_dir)
        self._ultralytics_dir = self._models_dir / "ultralytics"
        self._layers = detection_layers or DEFAULT_DETECTION_LAYERS
        self._loaded_models: dict[str, Any] = {}  # cache loaded YOLO models

    def available(self) -> bool:
        """Check if detection is possible (PIL + ultralytics installed)."""
        return _PIL_AVAILABLE and _ULTRALYTICS_AVAILABLE

    def detect(self, image_b64: str) -> DetectionResult:
        """Run all detection models on the image, return detected regions with masks.

        Each region includes a feathered mask (base64 PNG) suitable for
        ComfyUI's SetLatentNoiseMask inpaint workflow.
        """
        if not self.available():
            logger.warning("[DetectionDetail] PIL or ultralytics not available, skipping detection")
            return DetectionResult()

        t0 = time.time()
        img = self._decode_image(image_b64)
        if img is None:
            return DetectionResult()

        result = DetectionResult()
        img_w, img_h = img.size

        for layer in self._layers:
            if not layer.enabled:
                continue

            model_path = self._ultralytics_dir / layer.model_path
            if not model_path.exists():
                logger.debug("[DetectionDetail] Model not found: %s", model_path)
                continue

            try:
                model = self._get_model(str(model_path))
                detections = model(img, conf=layer.confidence_threshold, verbose=False)

                for det in detections:
                    if det.boxes is None:
                        continue
                    for box in det.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        conf = float(box.conf[0].cpu().numpy())

                        # Expand bbox with padding
                        pad_w = int((x2 - x1) * layer.padding_ratio)
                        pad_h = int((y2 - y1) * layer.padding_ratio)
                        x1 = max(0, x1 - pad_w)
                        y1 = max(0, y1 - pad_h)
                        x2 = min(img_w, x2 + pad_w)
                        y2 = min(img_h, y2 + pad_h)

                        # Create feathered mask
                        mask_b64 = self._create_feathered_mask(
                            img_w, img_h, x1, y1, x2, y2,
                            feather_radius=layer.feather_radius,
                        )

                        region = DetectedRegion(
                            region_type=layer.region_type,
                            x1=x1, y1=y1, x2=x2, y2=y2,
                            confidence=conf,
                            mask_b64=mask_b64,
                            label=f"{layer.region_type}_{conf:.2f}",
                        )

                        result.add(region)

            except Exception as e:
                logger.warning("[DetectionDetail] Detection failed for %s: %s", layer.model_path, e)
                continue

        # Deduplicate: remove individual eye detections if full_eyes already found
        if result.get("full_eyes") and result.get("eyes"):
            result.regions["eyes"] = self._filter_nested_regions(
                result.regions["eyes"],
                result.regions["full_eyes"],
            )

        # Deduplicate: remove eye detections that are inside face regions
        for eye_type in ("eyes", "full_eyes"):
            if result.get(eye_type) and result.faces:
                result.regions[eye_type] = self._filter_nested_regions(
                    result.regions[eye_type], result.faces,
                )

        # Deduplicate: remove nipple detections inside breast regions
        if result.get("nipples") and result.get("breasts"):
            result.regions["nipples"] = self._filter_nested_regions(
                result.regions["nipples"],
                result.regions["breasts"],
            )

        result.latency_ms = (time.time() - t0) * 1000
        region_summary = ", ".join(
            f"{rtype}={len(regions)}"
            for rtype, regions in result.regions.items()
            if regions
        )
        logger.info(
            "[DetectionDetail] Detected %d regions (%s) in %.0fms",
            result.total_regions, region_summary, result.latency_ms,
        )
        return result

    def get_layer_config(self, region_type: str) -> Optional[DetectionModelConfig]:
        """Get the detection layer config for a region type."""
        for layer in self._layers:
            if layer.region_type == region_type:
                return layer
        return None

    # ── Internal helpers ─────────────────────────────────────────────

    def _get_model(self, model_path: str) -> Any:
        """Load or return cached YOLO model. Auto-extracts .zip archives first."""
        if model_path not in self._loaded_models:
            load_path = self._resolve_model_path(model_path)
            self._loaded_models[model_path] = YOLO(load_path)
        return self._loaded_models[model_path]

    def _resolve_model_path(self, model_path: str) -> str:
        """If model_path is a .zip, extract the .pt inside and return the .pt path.
        The extracted file is cached next to the .zip so extraction only runs once.
        """
        p = Path(model_path)
        if p.suffix.lower() != ".zip":
            return model_path

        extract_dir = p.parent / "_extracted"
        cached_pt = extract_dir / (p.stem + ".pt")
        if cached_pt.exists():
            return str(cached_pt)

        if not p.exists():
            return model_path  # let YOLO produce the normal "not found" error

        try:
            with zipfile.ZipFile(p, "r") as zf:
                pt_names = [n for n in zf.namelist() if n.lower().endswith(".pt")]
                if not pt_names:
                    logger.warning(
                        "[DetectionDetail] No .pt file found inside %s, trying raw load", p.name
                    )
                    return model_path
                # Pick the first .pt (CivitAI zips usually contain exactly one)
                pt_name = pt_names[0]
                extract_dir.mkdir(parents=True, exist_ok=True)
                with zf.open(pt_name) as src, open(cached_pt, "wb") as dst:
                    dst.write(src.read())
            logger.info(
                "[DetectionDetail] Extracted %s → %s", p.name, cached_pt.name
            )
            return str(cached_pt)
        except Exception as exc:
            logger.warning(
                "[DetectionDetail] Failed to extract %s: %s — trying raw load", p.name, exc
            )
            return model_path

    def _decode_image(self, image_b64: str) -> Optional[Any]:
        """Decode base64 image to PIL Image."""
        try:
            data = base64.b64decode(image_b64)
            return Image.open(io.BytesIO(data)).convert("RGB")
        except Exception as e:
            logger.error("[DetectionDetail] Failed to decode image: %s", e)
            return None

    def _create_feathered_mask(
        self,
        img_w: int,
        img_h: int,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        feather_radius: int = 20,
    ) -> str:
        """Create a feathered white-on-black mask for the bounding box region.

        Returns base64-encoded PNG. White = inpaint area, black = preserve.
        """
        mask = Image.new("L", (img_w, img_h), 0)
        draw = ImageDraw.Draw(mask)
        draw.rectangle([x1, y1, x2, y2], fill=255)

        if feather_radius > 0:
            mask = mask.filter(ImageFilter.GaussianBlur(radius=feather_radius))

        buf = io.BytesIO()
        mask.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    def _filter_nested_regions(
        self,
        inner: list[DetectedRegion],
        outer: list[DetectedRegion],
    ) -> list[DetectedRegion]:
        """Remove inner regions that are completely inside an outer region.

        This prevents double-inpainting eyes that are already covered by face detection.
        Only removes if >80% overlap.
        """
        if not outer or not inner:
            return inner

        filtered = []
        for i_region in inner:
            is_nested = False
            for o_region in outer:
                # Calculate overlap
                ox1 = max(i_region.x1, o_region.x1)
                oy1 = max(i_region.y1, o_region.y1)
                ox2 = min(i_region.x2, o_region.x2)
                oy2 = min(i_region.y2, o_region.y2)
                if ox1 < ox2 and oy1 < oy2:
                    overlap_area = (ox2 - ox1) * (oy2 - oy1)
                    if i_region.area > 0 and overlap_area / i_region.area > 0.80:
                        is_nested = True
                        break
            if not is_nested:
                filtered.append(i_region)
        return filtered

    def unload_models(self) -> None:
        """Free YOLO model memory."""
        self._loaded_models.clear()
