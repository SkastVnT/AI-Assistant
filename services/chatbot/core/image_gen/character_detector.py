"""
CharacterDetector — automatically detects character names in the user's prompt
and resolves the corresponding LoRA models from the catalog.

When a user says "tạo ảnh Firefly mặc áo dài" or "draw Jingliu in a garden",
the detector finds "Firefly" / "Jingliu", looks up their LoRA in LORA_CATALOG,
picks the right checkpoint, and returns everything the router needs.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CharacterMatch:
    """A detected character with its LoRA info."""
    key: str                          # catalog key e.g. "firefly"
    display_name: str                 # human name e.g. "Firefly"
    lora_file: str                    # e.g. "Firefly-1024-v1.safetensors"
    weight: float = 0.85
    trigger_words: list[str] = field(default_factory=list)
    base: str = "sdxl"                # "sdxl" or "sd15"
    franchise: str = ""               # "hsr", "genshin", "opm", etc.


@dataclass
class DetectionResult:
    """Result of character detection on a prompt."""
    characters: list[CharacterMatch] = field(default_factory=list)
    suggested_checkpoint: Optional[str] = None
    suggested_preset_id: Optional[str] = None
    clean_prompt: str = ""            # prompt with aliases normalised

    @property
    def has_characters(self) -> bool:
        return len(self.characters) > 0


# ─── Character Alias Table ───────────────────────────────────────────────
# Maps every known alias (Vietnamese, English, short-form, full name,
# misspelling) to the catalog key in LORA_CATALOG.
# Order matters: longer aliases first to avoid partial matches.

CHARACTER_ALIASES: dict[str, list[str]] = {
    # ── Honkai Star Rail ─────────────────────────────────────────────────
    "firefly": [
        "firefly", "fire fly", "hotaru", "đom đóm",
        "sam", "SAM",  # her other identity
    ],
    "kafka": [
        "kafka",
    ],
    "jingliu": [
        "jingliu", "jing liu", "cảnh lưu",
    ],
    "seele": [
        "seele", "seele vollerei",
    ],
    "clara": [
        "clara", "klara",
    ],
    "march7th": [
        "march 7th", "march7th", "march 7", "ba tháng bảy",
        "tháng ba", "march",
    ],
    "bronya": [
        "bronya rand", "bronya", "bronya zaychik",
    ],
    "trailblazer": [
        "trailblazer", "stelle", "caelus",
        "khai phá giả", "nhân vật chính hsr",
    ],

    # ── Genshin Impact ───────────────────────────────────────────────────
    "nahida": [
        "nahida", "kusanali", "lesser lord kusanali",
        "tiểu cát thảo", "nữ thần cỏ",
    ],
    "furina": [
        "furina", "focalors", "thủy thần",
    ],
    "eula": [
        "eula", "eula lawrence",
    ],
    "raiden": [
        "raiden shogun", "raiden", "ei", "baal",
        "lôi thần", "tướng quân sấm sét",
    ],
    "yae_miko": [
        "yae miko", "yae", "miko",
        "bát trùng thần tử",
    ],

    # ── Other ────────────────────────────────────────────────────────────
    "tatsumaki": [
        "tatsumaki", "tornado of terror", "cuồng phong",
    ],
    "atri": [
        "atri",
    ],
    "maki_custom": [
        "maki",
    ],
}

# ── Franchise metadata (for checkpoint selection) ────────────────────────
CHARACTER_FRANCHISE: dict[str, str] = {
    "firefly": "hsr", "kafka": "hsr", "jingliu": "hsr",
    "seele": "hsr", "clara": "hsr", "march7th": "hsr",
    "bronya": "hsr", "trailblazer": "hsr",
    "nahida": "genshin", "furina": "genshin", "eula": "genshin",
    "raiden": "genshin", "yae_miko": "genshin",
    "tatsumaki": "opm", "atri": "anime",
    "maki_custom": "custom",
}

# ── Default weights per character (some need lighter touch) ──────────────
CHARACTER_WEIGHTS: dict[str, float] = {
    "firefly": 0.85,
    "kafka": 0.85,
    "jingliu": 0.85,
    "furina": 0.80,
    "raiden": 0.80,
    "detail_tweaker": 0.5,
}
DEFAULT_WEIGHT = 0.85

# ── Best checkpoint per base model ───────────────────────────────────────
BEST_CHECKPOINTS = {
    "sdxl": "animagine-xl-3.1.safetensors",
    "sd15": "counterfeit_v30.safetensors",
}

# ── Preset mapping for known characters ──────────────────────────────────
# If a WORKFLOW_PRESETS entry already exists for this character, prefer it.
CHARACTER_PRESET_MAP: dict[str, str] = {
    "jingliu": "anime_hsr_jingliu",
    "firefly": "anime_hsr_firefly",
    "furina":  "anime_genshin_furina",
}


class CharacterDetector:
    """
    Detects character names in a prompt and resolves LoRA + checkpoint info.
    
    Usage:
        detector = CharacterDetector(lora_catalog)
        result = detector.detect("tạo ảnh Firefly mặc áo dài")
        # result.characters = [CharacterMatch(key="firefly", ...)]
        # result.suggested_checkpoint = "animagine-xl-3.1.safetensors"
    """

    def __init__(self, lora_catalog: dict):
        self._catalog = lora_catalog
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> list[tuple[re.Pattern, str]]:
        """
        Build sorted regex patterns from CHARACTER_ALIASES.
        Longer aliases first → avoids 'march' matching before 'march 7th'.
        """
        patterns = []
        for key, aliases in CHARACTER_ALIASES.items():
            # Only include characters that exist in the catalog
            if key not in self._catalog:
                continue
            # Sort aliases: longest first
            sorted_aliases = sorted(aliases, key=len, reverse=True)
            for alias in sorted_aliases:
                # Word boundary match, case-insensitive
                escaped = re.escape(alias)
                pat = re.compile(r"(?<!\w)" + escaped + r"(?!\w)", re.IGNORECASE)
                patterns.append((pat, key))
        return patterns

    def detect(self, prompt: str) -> DetectionResult:
        """
        Scan prompt for known character names.
        Returns DetectionResult with matched characters and suggestions.
        """
        found_keys: list[str] = []
        found_positions: list[tuple[int, int, str]] = []  # (start, end, key)

        for pat, key in self._patterns:
            if key in found_keys:
                continue  # already matched this character
            m = pat.search(prompt)
            if m:
                found_keys.append(key)
                found_positions.append((m.start(), m.end(), key))

        if not found_keys:
            return DetectionResult(clean_prompt=prompt)

        # Build CharacterMatch list
        characters: list[CharacterMatch] = []
        for key in found_keys:
            entry = self._catalog[key]
            characters.append(CharacterMatch(
                key=key,
                display_name=self._display_name(key),
                lora_file=entry["file"],
                weight=CHARACTER_WEIGHTS.get(key, DEFAULT_WEIGHT),
                trigger_words=entry.get("trigger", []),
                base=entry.get("base", "sdxl"),
                franchise=CHARACTER_FRANCHISE.get(key, ""),
            ))

        # Pick checkpoint based on detected characters' base model
        checkpoint = self._select_checkpoint(characters)

        # If there's an exact-match preset, suggest it
        preset_id = None
        if len(characters) == 1:
            preset_id = CHARACTER_PRESET_MAP.get(characters[0].key)

        logger.info(
            f"[CharacterDetector] Detected {[c.display_name for c in characters]} "
            f"→ checkpoint={checkpoint}, preset={preset_id}"
        )

        return DetectionResult(
            characters=characters,
            suggested_checkpoint=checkpoint,
            suggested_preset_id=preset_id,
            clean_prompt=prompt,
        )

    def _select_checkpoint(self, characters: list[CharacterMatch]) -> str:
        """
        Pick the best checkpoint for the set of detected characters.
        If all are SDXL → use SDXL checkpoint.
        If any are SD1.5 → use SD1.5 checkpoint (LoRA compatibility).
        If mixed → prefer SDXL (SD1.5 LoRAs are often adapted).
        """
        bases = {c.base for c in characters}
        if bases == {"sdxl"}:
            return BEST_CHECKPOINTS["sdxl"]
        elif bases == {"sd15"}:
            return BEST_CHECKPOINTS["sd15"]
        else:
            # Mixed: prefer SDXL — most modern LoRAs have SDXL versions
            return BEST_CHECKPOINTS["sdxl"]

    @staticmethod
    def _display_name(key: str) -> str:
        """Convert catalog key to display name."""
        aliases = CHARACTER_ALIASES.get(key, [key])
        # Return the first alias, title-cased
        name = aliases[0] if aliases else key
        return name.title()

    def get_all_characters(self) -> list[dict]:
        """List all detectable characters for API/UI."""
        result = []
        for key in CHARACTER_ALIASES:
            if key not in self._catalog:
                continue
            entry = self._catalog[key]
            result.append({
                "key": key,
                "name": self._display_name(key),
                "aliases": CHARACTER_ALIASES[key],
                "franchise": CHARACTER_FRANCHISE.get(key, ""),
                "base": entry.get("base", "sdxl"),
                "lora_file": entry["file"],
                "category": entry.get("category", "character"),
            })
        return result
