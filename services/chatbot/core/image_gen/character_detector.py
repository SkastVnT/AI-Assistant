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
    lora_file: str                    # e.g. "Firefly-1024-v1.safetensors", "" if none
    weight: float = 0.85
    trigger_words: list[str] = field(default_factory=list)
    base: str = "sdxl"                # "sdxl" or "sd15"
    franchise: str = ""               # "hsr", "genshin", "opm", etc.
    traits: list[str] = field(default_factory=list)  # canonical appearance tags


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

    @property
    def trait_tags(self) -> list[str]:
        """Flat deduplicated canonical appearance tags from all detected characters."""
        seen: set[str] = set()
        out: list[str] = []
        for c in self.characters:
            for t in c.traits:
                if t not in seen:
                    seen.add(t)
                    out.append(t)
        return out


# ─── Character Alias Table ───────────────────────────────────────────────
# Maps every known alias (Vietnamese, English, short-form, full name,
# misspelling) to the catalog key in LORA_CATALOG.
# Order matters: longer aliases first to avoid partial matches.

CHARACTER_ALIASES: dict[str, list[str]] = {
    # ── Honkai Star Rail ─────────────────────────────────────────────────
    "sparkle": [
        "sparkle", "bạch lộ", "백로",
    ],
    "firefly": [
        "firefly", "fire fly", "hotaru", "đom đóm",
        "sam", "SAM",  # her other identity
    ],    "huohuo": [
        "huohuo", "huo huo", "hỏa hỏa",
    ],
    "stelle": [
        "stelle", "trailblazer female", "khai phá giả nữ",
    ],
    "silver_wolf": [
        "silver wolf", "silverwolf", "sói bạc",
    ],    "kafka": [
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

    # ── NSFW LoRAs — keyword-triggered (Illustrious XL base) ─────────────
    "xray_ilxl": [
        "xray", "x-ray", "x ray", "xuyên thấu", "nội soi",
        "see-through body", "transparent body",
    ],
    "speculum_ilxl": [
        "speculum", "mỏ vịt",
    ],
    "speculum_insertion_ilxl": [
        "speculum insertion",
    ],
    "vibrator_clit_ilxl": [
        "vibrator on clitoris",
    ],
    "vibrator_panties_ilxl": [
        "vibrator under panties", "vibrator panties",
    ],
    "spread_anal_il": [
        "spread pussy", "extreme spread", "anal spread",
    ],
    "cameltoe_ilxl": [
        "cameltoe", "camel toe",
    ],

    # ── NSFW LoRAs — keyword-triggered (SDXL base) ───────────────────────
    "xray_window": [
        "x-ray window", "xray window",
    ],
    "xray_creampie": [
        "xray creampie", "x-ray creampie",
    ],
    "xray_cum": [
        "cum inflation", "xray inflation",
    ],
    "tape_gape": [
        "tape gape",
    ],
    "tape_spread": [
        "tape spread",
    ],
    "taped_eyes_il": [
        # English natural phrases
        "taped eyes", "eyes taped", "eyes taped open", "taped eyes open",
        "eyes forced open", "eyes held open", "forced eyes open",
        "duct tape eyes", "tape on eyes", "eyelids taped",
        "unconscious taped eyes",
        # Vietnamese natural phrases
        "mắt dán băng", "băng dán mắt", "dán băng mắt",
        "mắt bị dán", "mắt bị buộc mở", "mắt bị giữ mở",
        "mắt trợn dán băng", "bất tỉnh mắt dán",
    ],
    "sleeping_eyes_open_il": [
        # English
        "0utc0ld",
        "unconscious eyes open", "sleeping with eyes open", "eyes open while sleeping",
        "eyes open unconscious", "open eyes unconscious", "glazed open eyes",
        # Vietnamese
        "ngủ mở mắt", "mắt mở khi ngủ", "bất tỉnh mắt mở",
        "mắt mở lúc ngủ", "ngủ mà mắt mở",
    ],
    "unconscious_taped_combo": [
        # Vietnamese combo phrases — primary triggers
        "ngủ mở mắt dán băng", "mắt mở dán băng",
        "mắt bị dán khi ngủ", "bất tỉnh mắt dán băng",
        "dán băng mắt khi ngủ", "mắt mở cố định băng dính",
        "băng dính cố định mắt mở",
        # English combo phrases
        "sleeping eyes taped open", "unconscious taped eyes open",
        "eyes forced open taped", "taped sleeping eyes",
        "unconscious with taped open eyes", "sleep taped eyes",
    ],
    "vibrator_thigh": [
        "vibrator thighhighs", "vibrator thigh highs",
    ],
    "vibrator_underwear": [
        "vibrator in underwear",
    ],
    "cervix": [
        "cervix view", "cervix",
    ],
    "armpit_hair": [
        "armpit hair", "hairy armpit",
    ],
}

# ── Franchise metadata (for checkpoint selection) ────────────────────────
CHARACTER_FRANCHISE: dict[str, str] = {
    "sparkle": "hsr",
    "firefly": "hsr", "kafka": "hsr", "jingliu": "hsr",
    "seele": "hsr", "clara": "hsr", "march7th": "hsr",
    "bronya": "hsr", "trailblazer": "hsr",
    "huohuo": "hsr", "stelle": "hsr", "silver_wolf": "hsr",
    "firefly_pony": "hsr",
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
    # Eye effect LoRAs — preset handles actual stacking weights
    "sleeping_eyes_open_il": 0.80,
    "unconscious_taped_combo": 0.75,
}
DEFAULT_WEIGHT = 0.85

# ── Canonical appearance tags per character ───────────────────────────────
# These are injected as hard tags into the prompt BEFORE enhancement so the
# LLM does not need to know or guess the character's appearance.
# Format: Danbooru-style tags (appearance only, NOT outfit or scene).
CHARACTER_TRAITS: dict[str, list[str]] = {
    # ── Honkai Star Rail ─────────────────────────────────────────────────
    "sparkle":     ["black hair", "long hair", "wavy hair", "purple eyes", "flower-shaped pupils", "hair ornament", "multicolored hair"],
    "firefly":     ["grey hair", "short hair", "green eyes"],
    "kafka":       ["purple hair", "long hair", "purple eyes"],
    "jingliu":     ["white hair", "long hair", "blue eyes"],
    "seele":       ["purple hair", "long hair", "twin braids", "blue eyes"],
    "clara":       ["pink hair", "long hair", "blue eyes", "hair ribbon"],
    "march7th":    ["pink hair", "medium hair", "blue eyes", "hair clip"],
    "bronya":      ["silver hair", "long hair", "blue eyes", "hair ornament"],
    "trailblazer": ["black hair", "short hair", "brown eyes"],

    # ── Genshin Impact ───────────────────────────────────────────────────
    "nahida":      ["green hair", "short hair", "green eyes", "small stature", "ahoge"],
    "furina":      ["light blue hair", "white hair streaks", "medium hair", "blue eyes", "ahoge"],
    "eula":        ["blonde hair", "long hair", "blue eyes"],
    "raiden":      ["purple hair", "long hair", "purple eyes"],
    "yae_miko":    ["pink hair", "long hair", "fox ears", "fox tail", "purple eyes"],

    # ── Other ────────────────────────────────────────────────────────────
    "tatsumaki":   ["green hair", "short hair", "green eyes", "small stature"],
    "atri":        ["light blue hair", "twintails", "blue eyes"],
}

# ── Best checkpoint per base model ───────────────────────────────────────
BEST_CHECKPOINTS = {
    "sdxl":  "noobaiXLVpred_v11.safetensors",           # NoobAI V-Pred — default SDXL anime
    "ilxl":  "ChenkinNoob-XL-V0.2.safetensors",         # NoobAI/Illustrious XL — best for ILXL LoRAs
    "sd15":  "abyssorangemix3AOM3_aom3a1b.safetensors",  # SD 1.5
}

# ── Preset mapping for known characters ──────────────────────────────────
# If a WORKFLOW_PRESETS entry already exists for this character, prefer it.
CHARACTER_PRESET_MAP: dict[str, str] = {
    "jingliu": "anime_hsr_jingliu",
    "firefly": "anime_hsr_firefly",
    "furina":  "anime_genshin_furina",
    # Combo preset: sleeping-eyes-open + taped-eyes stacked
    "unconscious_taped_combo": "anime_unconscious_taped_eyes",
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
        Includes characters that have known traits even if they have no LoRA.
        """
        patterns = []
        # Include characters in catalog OR characters with known traits
        recognisable = set(self._catalog.keys()) | set(CHARACTER_TRAITS.keys())
        for key, aliases in CHARACTER_ALIASES.items():
            if key not in recognisable:
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
            entry = self._catalog.get(key)  # may be None if trait-only
            characters.append(CharacterMatch(
                key=key,
                display_name=self._display_name(key),
                lora_file=entry["file"] if entry else "",
                weight=CHARACTER_WEIGHTS.get(key, DEFAULT_WEIGHT) if entry else 0.0,
                trigger_words=entry.get("trigger", []) if entry else [],
                base=entry.get("base", "sdxl") if entry else "sdxl",
                franchise=CHARACTER_FRANCHISE.get(key, ""),
                traits=CHARACTER_TRAITS.get(key, []),
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
        Pick the best checkpoint for the set of detected characters/LoRAs.
        Priority: ilxl > sdxl > sd15 for mixed sets.
        """
        bases = {c.base for c in characters}
        if bases == {"ilxl"}:
            return BEST_CHECKPOINTS["ilxl"]
        elif bases == {"sd15"}:
            return BEST_CHECKPOINTS["sd15"]
        elif "ilxl" in bases:
            # If any LoRA is ILXL, use Illustrious checkpoint (better compatibility)
            return BEST_CHECKPOINTS["ilxl"]
        else:
            # sdxl or mixed sdxl+sd15 → use SDXL
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
