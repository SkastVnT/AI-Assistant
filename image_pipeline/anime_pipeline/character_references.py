"""
character_references — Fetch, cache, and serve canonical character reference images.

When the pipeline detects a known anime character, this module:
  1. Checks local cache (storage/character_refs/<danbooru_tag>/)
  2. If missing, downloads canonical reference images from safe sources
  3. Returns base64 images for use in critique comparison

The critique agent can compare the generated image against the reference
to verify eye color, hair style, heterochromia, and other identity anchors.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_CACHE_DIR = Path("storage/character_refs")
_MAX_REFS_PER_CHARACTER = 4
_DOWNLOAD_TIMEOUT = 15.0


@dataclass
class CharacterRefSet:
    """Cached reference images for a known character."""
    character_tag: str = ""
    series_tag: str = ""
    images_b64: list[str] = field(default_factory=list)
    image_paths: list[str] = field(default_factory=list)
    eye_detail: dict = field(default_factory=dict)
    loaded_from_cache: bool = False


# ── Character eye/identity anchors ───────────────────────────────────
# Detailed per-character identity data for critique comparison.
# This supplements the danbooru appearance tags with precise visual details
# that the critique agent needs to verify.

_CHARACTER_IDENTITY: dict[str, dict] = {
    "tokisaki_kurumi": {
        "series": "date_a_live",
        "eye_detail": {
            "type": "heterochromia",
            "left_eye": "golden/yellow (normal pupil)",
            "right_eye": "red with clock face pattern (roman numerals visible in iris)",
            "pupil_detail": "right eye has roman numeral clock face, left eye is normal golden",
            "critical_tags": ["heterochromia", "(yellow_left_eye:1.2)", "(red_right_eye:1.2)", "clock_eyes"],
            "common_errors": [
                "both eyes same color — WRONG, must be heterochromia",
                "clock on wrong eye — clock is on RIGHT eye only",
                "eyes too dark/muddy — yellow eye should be bright gold",
                "missing clock detail — right eye MUST show clock pattern",
            ],
        },
        "hair_detail": {
            "color": "black with slight dark highlights",
            "style": "very long twintails — one side covers right eye partially",
            "accessories": ["red hair ribbons", "gothic headdress with roses"],
        },
        "outfit_default": "black and red gothic lolita dress with frills and corset lacing",
        "skin_tone": "fair/pale, smooth porcelain skin",
        "distinguishing": ["clock motif", "asymmetric eye design", "elegant gothic aesthetic", "confident/playful expression"],
    },
    "yatogami_tohka": {
        "series": "date_a_live",
        "eye_detail": {
            "type": "normal",
            "color": "indigo/dark purple",
            "pupil_detail": "standard anime pupils",
            "critical_tags": ["purple_eyes"],
        },
        "hair_detail": {
            "color": "dark purple/indigo",
            "style": "very long flowing hair",
        },
        "outfit_default": "purple and white astral dress",
    },
    "itsuka_kotori": {
        "series": "date_a_live",
        "eye_detail": {
            "type": "normal",
            "color": "red",
            "critical_tags": ["red_eyes"],
        },
        "hair_detail": {
            "color": "coral pink/light red",
            "style": "long twintails with white ribbons",
        },
    },
    "yuuki_asuna": {
        "series": "sword_art_online",
        "eye_detail": {
            "type": "normal",
            "color": "hazel/light brown",
            "critical_tags": ["brown_eyes"],
        },
        "hair_detail": {
            "color": "chestnut/orange-brown",
            "style": "very long straight with braids",
        },
    },
    "rem_(re:zero)": {
        "series": "re:zero",
        "eye_detail": {
            "type": "normal",
            "color": "light blue",
            "critical_tags": ["blue_eyes"],
        },
        "hair_detail": {
            "color": "light blue",
            "style": "short bob with side swept bangs, hair over one eye",
        },
        "outfit_default": "maid uniform with white headband",
    },
    "emilia_(re:zero)": {
        "series": "re:zero",
        "eye_detail": {
            "type": "normal",
            "color": "purple/violet",
            "critical_tags": ["purple_eyes"],
        },
        "hair_detail": {
            "color": "silver/white",
            "style": "very long straight hair",
        },
        "distinguishing": ["elf ears", "flower hair ornament"],
    },
    "kamado_nezuko": {
        "series": "kimetsu_no_yaiba",
        "eye_detail": {
            "type": "normal",
            "color": "pink/light pink",
            "critical_tags": ["pink_eyes"],
        },
        "hair_detail": {
            "color": "black with pink/orange gradient tips",
            "style": "long wavy",
        },
        "distinguishing": ["bamboo muzzle", "pink kimono"],
    },
    "hu_tao_(genshin_impact)": {
        "series": "genshin_impact",
        "eye_detail": {
            "type": "special",
            "color": "crimson red with flower-shaped pupils",
            "critical_tags": ["red_eyes", "flower_pupils"],
        },
        "hair_detail": {
            "color": "dark brown with red gradient tips",
            "style": "long twintails",
        },
    },
    "raiden_shogun": {
        "series": "genshin_impact",
        "eye_detail": {
            "type": "normal",
            "color": "purple/violet",
            "critical_tags": ["purple_eyes"],
        },
        "hair_detail": {
            "color": "dark purple/indigo",
            "style": "long braided hair",
        },
    },
    "fischl_(genshin_impact)": {
        "series": "genshin_impact",
        "eye_detail": {
            "type": "heterochromia_eyepatch",
            "visible_eye": "green",
            "covered_eye": "hidden by eyepatch",
            "critical_tags": ["green_eyes", "eyepatch"],
        },
        "hair_detail": {
            "color": "blonde",
            "style": "long with side twintails",
        },
    },
    "artoria_pendragon": {
        "series": "fate/stay_night",
        "eye_detail": {
            "type": "normal",
            "color": "emerald green",
            "critical_tags": ["green_eyes"],
        },
        "hair_detail": {
            "color": "blonde",
            "style": "short with ahoge, bun at back",
        },
    },
    "tohsaka_rin": {
        "series": "fate/stay_night",
        "eye_detail": {
            "type": "normal",
            "color": "aqua blue/cyan",
            "critical_tags": ["blue_eyes"],
        },
        "hair_detail": {
            "color": "black",
            "style": "long twintails",
        },
    },
}


def get_character_identity(danbooru_tag: str) -> Optional[dict]:
    """Return detailed identity data for a known character, or None."""
    return _CHARACTER_IDENTITY.get(danbooru_tag)


def get_character_ref_set(danbooru_tag: str) -> CharacterRefSet:
    """Load cached reference images for a character.

    Returns a CharacterRefSet with whatever is available locally.
    Does NOT download from internet (user must place refs manually or
    the pipeline saves generated good results as future refs).
    """
    ref_set = CharacterRefSet(character_tag=danbooru_tag)

    identity = _CHARACTER_IDENTITY.get(danbooru_tag)
    if identity:
        ref_set.series_tag = identity.get("series", "")
        ref_set.eye_detail = identity.get("eye_detail", {})

    cache_dir = _CACHE_DIR / danbooru_tag
    if not cache_dir.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        return ref_set

    # Load cached images (PNG/JPG)
    image_files = sorted(
        [f for f in cache_dir.iterdir() if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )[:_MAX_REFS_PER_CHARACTER]

    for img_path in image_files:
        try:
            img_b64 = base64.b64encode(img_path.read_bytes()).decode("ascii")
            ref_set.images_b64.append(img_b64)
            ref_set.image_paths.append(str(img_path))
        except Exception as e:
            logger.warning("[CharRef] Failed to load %s: %s", img_path, e)

    if ref_set.images_b64:
        ref_set.loaded_from_cache = True
        logger.info(
            "[CharRef] Loaded %d reference(s) for %s from cache",
            len(ref_set.images_b64), danbooru_tag,
        )

    return ref_set


def save_as_reference(danbooru_tag: str, image_b64: str, score: float) -> Optional[str]:
    """Save a high-quality generated image as a future character reference.

    Only saves when score >= 8.5 to maintain reference quality.
    Returns the saved file path or None.
    """
    if score < 8.5:
        return None

    cache_dir = _CACHE_DIR / danbooru_tag
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Check how many refs we already have
    existing = list(cache_dir.glob("*.png"))
    if len(existing) >= _MAX_REFS_PER_CHARACTER:
        # Remove oldest if at capacity
        oldest = min(existing, key=lambda f: f.stat().st_mtime)
        oldest.unlink()
        logger.info("[CharRef] Removed oldest ref: %s", oldest.name)

    ts = time.strftime("%Y%m%d_%H%M%S")
    score_str = f"{score:.1f}".replace(".", "p")
    filename = f"ref_{ts}_s{score_str}.png"
    filepath = cache_dir / filename

    try:
        raw = image_b64.split(",", 1)[-1] if "," in image_b64 else image_b64
        filepath.write_bytes(base64.b64decode(raw))
        logger.info("[CharRef] Saved reference for %s: %s (score=%.1f)", danbooru_tag, filename, score)
        return str(filepath)
    except Exception as e:
        logger.error("[CharRef] Failed to save reference: %s", e)
        return None


def build_identity_critique_context(danbooru_tag: str) -> str:
    """Build a text description of the character's visual identity for critique.

    This is injected into the critique prompt so the LLM can verify
    eye color, heterochromia, hair details, etc.
    """
    identity = _CHARACTER_IDENTITY.get(danbooru_tag)
    if not identity:
        return ""

    parts = [f"CHARACTER IDENTITY REFERENCE for {danbooru_tag} ({identity.get('series', '')}):\n"]

    eye = identity.get("eye_detail", {})
    if eye:
        parts.append(f"- Eyes: {eye.get('type', 'normal')}")
        if eye.get("type") == "heterochromia":
            parts.append(f"  LEFT eye: {eye.get('left_eye', '?')}")
            parts.append(f"  RIGHT eye: {eye.get('right_eye', '?')}")
        elif eye.get("type") == "heterochromia_eyepatch":
            parts.append(f"  Visible eye: {eye.get('visible_eye', '?')}")
            parts.append(f"  Other eye: {eye.get('covered_eye', '?')}")
        else:
            parts.append(f"  Color: {eye.get('color', '?')}")
        if eye.get("pupil_detail"):
            parts.append(f"  Pupil detail: {eye['pupil_detail']}")

    hair = identity.get("hair_detail", {})
    if hair:
        parts.append(f"- Hair: {hair.get('color', '?')}, {hair.get('style', '?')}")
        if hair.get("accessories"):
            parts.append(f"  Hair accessories: {', '.join(hair['accessories'])}")

    if identity.get("outfit_default"):
        parts.append(f"- Default outfit: {identity['outfit_default']}")

    if identity.get("skin_tone"):
        parts.append(f"- Skin tone: {identity['skin_tone']}")

    if identity.get("distinguishing"):
        parts.append(f"- Distinguishing features: {', '.join(identity['distinguishing'])}")

    parts.append("\nVERIFY these identity details match the generated image. "
                 "Score eye_consistency LOW if eye colors don't match the character. "
                 "For heterochromia characters, BOTH eye colors must be correct and distinct.")

    # Add common errors if available
    common_errors = eye.get("common_errors", [])
    if common_errors:
        parts.append("\nCOMMON MISTAKES to watch for:")
        for err in common_errors:
            parts.append(f"  ✗ {err}")

    return "\n".join(parts)
