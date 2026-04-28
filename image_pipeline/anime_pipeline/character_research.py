"""
character_research.py - Deep character research via web search + image download.

Given a character name / series, this module:
  1. Searches the web for the character's visual identity (danbooru wiki, fandom, etc.)
  2. Downloads high-quality reference images and caches them locally
  3. Extracts structured appearance data (eyes, hair, outfit, accessories, body)
  4. Returns a CharacterResearchResult used by the orchestrator to:
     - Feed reference images into the vision analyst
     - Build precise positive/negative prompts
     - Guide the critique agent with ground-truth identity

Cache dir: storage/character_refs/<danbooru_tag>/
Research cache: storage/character_research/<danbooru_tag>/research.json
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Storage paths ────────────────────────────────────────────────────

_STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage"
_REF_DIR = _STORAGE_ROOT / "character_refs"
_RESEARCH_DIR = _STORAGE_ROOT / "character_research"

# ── Research cache TTL (7 days) ──────────────────────────────────────
_RESEARCH_TTL_SECONDS = 7 * 24 * 3600


# ── Seen-URL / byte-hash registry ────────────────────────────────────
# 2026-04-23 user request: reference search MUST always find NEW images
# and never reuse anything already on disk. This registry persists every
# URL ever fetched AND a SHA-256 of the file bytes for that character so
# CDN mirrors / aliased URLs serving identical content are also rejected.
#
# Layout: storage/character_refs/<tag>/seen_urls.json
#   {
#     "url_hashes": {"<md5_of_url>": "<filename>", ...},
#     "byte_hashes": {"<sha256_of_bytes>": "<filename>", ...}
#   }
#
# Override with CHAR_RESEARCH_REUSE_REFS=1 to fall back to the old
# "reuse cached refs" behaviour (e.g. when running offline).

def _seen_registry_path(danbooru_tag: str) -> Path:
    return _REF_DIR / danbooru_tag / "seen_urls.json"


def _load_seen_registry(danbooru_tag: str) -> dict[str, dict[str, str]]:
    """Return {'url_hashes': {...}, 'byte_hashes': {...}} for this character.

    Backfills entries for any pre-existing image files that aren't in the
    registry yet so older runs (which didn't write the registry) still
    contribute to the dedupe set the first time the new code is loaded.
    Never raises; missing/corrupt files yield empty maps.
    """
    import json
    reg: dict[str, dict[str, str]] = {"url_hashes": {}, "byte_hashes": {}}
    path = _seen_registry_path(danbooru_tag)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8")) or {}
            reg["url_hashes"] = dict(data.get("url_hashes") or {})
            reg["byte_hashes"] = dict(data.get("byte_hashes") or {})
        except Exception as e:
            logger.warning("[CharResearch] seen_urls.json unreadable for %s: %s",
                           danbooru_tag, e)

    # Backfill: any image already in the ref dir but absent from the
    # registry should still be treated as seen.
    ref_dir = _REF_DIR / danbooru_tag
    if ref_dir.is_dir():
        existing_files = list(ref_dir.glob("*.png")) + list(ref_dir.glob("*.jpg"))
        new_byte_entries = 0
        for f in existing_files:
            try:
                # Filename-derived url hash for files named web_<hash>.<ext>
                stem = f.stem
                if stem.startswith("web_") and len(stem) >= 12:
                    uh = stem[4:12]
                    reg["url_hashes"].setdefault(uh, f.name)
                # Byte hash backfill
                if not any(v == f.name for v in reg["byte_hashes"].values()):
                    bh = hashlib.sha256(f.read_bytes()).hexdigest()
                    if bh not in reg["byte_hashes"]:
                        reg["byte_hashes"][bh] = f.name
                        new_byte_entries += 1
            except Exception:
                continue
        if new_byte_entries:
            _save_seen_registry(danbooru_tag, reg)
    return reg


def _save_seen_registry(danbooru_tag: str, reg: dict[str, dict[str, str]]) -> None:
    """Persist the seen registry. Never raises."""
    import json
    path = _seen_registry_path(danbooru_tag)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(reg, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("[CharResearch] could not persist seen_urls.json for %s: %s",
                       danbooru_tag, e)


def _url_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8", errors="ignore")).hexdigest()[:8]


def _bytes_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_url_seen(url: str, reg: dict[str, dict[str, str]]) -> bool:
    return _url_hash(url) in reg.get("url_hashes", {})


def _reuse_cached_refs_enabled() -> bool:
    """User-overridable opt-in to reusing cached refs as the primary set."""
    return os.getenv("CHAR_RESEARCH_REUSE_REFS", "0") == "1"


# ── SAA-first local reference collection ─────────────────────────────
# 2026-04-26 user spec: SAA / cached refs MUST be checked BEFORE any
# external web search.  This helper:
#   1. Persists the WAI thumbnail (if available) into character_refs/
#      so subsequent runs see it as a cached file.
#   2. Returns base64 strings for every PNG/JPG already on disk.
# The orchestrator/researcher calls this first; web search is only
# invoked when the local count is below the minimum.

# Threshold above which web image search is skipped because the local
# cache already has "enough" reference images.
# 2026-04-29: Default raised from 0 → 5 per user spec
# ("nên đọc file đã tìm được ở đâu trước, sau đó mới tìm nơi khác").
# Behaviour:
#   * len(local) >= 5  → skip web image search, reuse cache.
#   * len(local) <  5  → run web search to grow the cache.
# Set CHAR_RESEARCH_MIN_LOCAL_REFS=0 to force unlimited web search
# (legacy "Không giới hạn" mode). Set a higher value to require more
# local refs before short-circuiting.
_SAA_MIN_LOCAL_REFS = int(os.getenv("CHAR_RESEARCH_MIN_LOCAL_REFS", "5"))


def _persist_saa_thumbnail(danbooru_tag: str) -> Optional[Path]:
    """Save the SAA WAI thumbnail for ``danbooru_tag`` into character_refs/.

    Returns the path on success, None when no thumbnail or already saved.
    Never raises.
    """
    if not danbooru_tag:
        return None
    ref_dir = _REF_DIR / danbooru_tag
    target = ref_dir / "saa_thumb.png"
    if target.exists():
        return target
    try:
        from .saa_character_db import get_character_thumbnail
    except Exception:
        return None
    try:
        # WAI keys use space-form tags.
        b64 = (
            get_character_thumbnail(danbooru_tag.replace("_", " "))
            or get_character_thumbnail(danbooru_tag)
        )
        if not b64:
            return None
        if "," in b64 and b64.startswith("data:"):
            b64 = b64.split(",", 1)[1]
        ref_dir.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(b64))
        logger.info(
            "[CharResearch] Persisted SAA thumbnail for %s -> %s",
            danbooru_tag, target.name,
        )
        return target
    except Exception as exc:  # noqa: BLE001
        logger.debug("[CharResearch] SAA thumbnail persist failed: %s", exc)
        return None


def _collect_local_refs(
    danbooru_tag: str,
    *,
    max_images: int = 10,
    include_saa: bool = True,
) -> list[str]:
    """Return base64 strings for every cached / SAA reference image.

    Order of inclusion (highest priority first):
      1. SAA thumbnail (persisted on first call) \u2014 always front of list.
      2. Existing PNG/JPG files in storage/character_refs/<tag>/.
    """
    if not danbooru_tag:
        return []
    out: list[str] = []
    ref_dir = _REF_DIR / danbooru_tag
    saa_path = _persist_saa_thumbnail(danbooru_tag) if include_saa else None
    seen: set[str] = set()
    if saa_path and saa_path.exists():
        try:
            out.append(base64.b64encode(saa_path.read_bytes()).decode("ascii"))
            seen.add(saa_path.name)
        except Exception:
            pass
    if ref_dir.exists():
        for p in sorted(ref_dir.glob("*.png")) + sorted(ref_dir.glob("*.jpg")):
            if p.name in seen or p.name == "seen_urls.json":
                continue
            try:
                out.append(base64.b64encode(p.read_bytes()).decode("ascii"))
            except Exception:
                continue
            if len(out) >= max_images:
                break
    if out:
        logger.info(
            "[CharResearch] SAA-first local refs: %d found for %s (saa=%s)",
            len(out), danbooru_tag, bool(saa_path),
        )
    return out


@dataclass
class LayerDetail:
    """Visual detail for a specific body/outfit layer."""
    layer_name: str  # e.g. "eyes", "hair", "outfit_top", "accessories"
    description: str  # natural language description
    tags: list[str] = field(default_factory=list)  # danbooru-style tags
    emphasis: float = 1.0  # prompt weight multiplier


@dataclass
class CharacterResearchResult:
    """Complete research output for a character."""
    danbooru_tag: str
    series_tag: str
    display_name: str = ""
    series_name: str = ""

    # Core identity layers
    eyes: Optional[LayerDetail] = None
    hair: Optional[LayerDetail] = None
    face: Optional[LayerDetail] = None
    outfit: Optional[LayerDetail] = None
    accessories: Optional[LayerDetail] = None
    body: Optional[LayerDetail] = None

    # Aggregated tags
    identity_tags: list[str] = field(default_factory=list)
    appearance_summary: str = ""
    distinguishing_features: list[str] = field(default_factory=list)

    # Reference images (base64)
    reference_images_b64: list[str] = field(default_factory=list)
    reference_image_urls: list[str] = field(default_factory=list)

    # Web search context
    web_description: str = ""
    search_sources: list[str] = field(default_factory=list)

    # Metadata
    confidence: float = 0.0
    cached: bool = False
    research_time_ms: float = 0.0

    # 2026-04-29: source diagnostics so the UI can tell the user where
    # the reference images really came from. Filled in by the research
    # path that built the final reference_images_b64 list.
    local_refs_count: int = 0          # served from storage/character_refs/
    web_refs_count: int = 0            # downloaded via image_search_character
    web_search_skipped: bool = False   # short-circuit triggered (≥ min refs)
    nsfw_intent: bool = False          # NSFW priority chain was used

    def build_positive_tags(self) -> list[str]:
        """Build ordered tag list: character > identity > layers."""
        tags: list[str] = [self.danbooru_tag, self.series_tag]
        for layer in [self.eyes, self.hair, self.face, self.outfit,
                      self.accessories, self.body]:
            if layer:
                for t in layer.tags:
                    if t not in tags:
                        tags.append(
                            f"({t}:{layer.emphasis:.1f})" if layer.emphasis > 1.0 else t
                        )
        # Add remaining identity tags
        for t in self.identity_tags:
            if t not in tags:
                tags.append(t)
        return tags

    def build_critique_context(self) -> str:
        """Build text block for critique agent identity verification."""
        parts = [
            f"CHARACTER: {self.display_name} from {self.series_name} "
            f"(tag: {self.danbooru_tag})\n"
        ]
        if self.eyes:
            parts.append(f"EYES: {self.eyes.description}")
        if self.hair:
            parts.append(f"HAIR: {self.hair.description}")
        if self.face:
            parts.append(f"FACE: {self.face.description}")
        if self.outfit:
            parts.append(f"OUTFIT: {self.outfit.description}")
        if self.accessories:
            parts.append(f"ACCESSORIES: {self.accessories.description}")
        if self.body:
            parts.append(f"BODY: {self.body.description}")
        if self.distinguishing_features:
            parts.append(
                f"KEY FEATURES: {', '.join(self.distinguishing_features)}"
            )
        parts.append(
            "\nScore LOW on eye_consistency if eye colors/patterns don't match. "
            "Score LOW on face_score if expression or face shape is wrong. "
            "Score LOW on clothing_score if outfit doesn't match character."
        )
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for caching (excludes images)."""
        return {
            "danbooru_tag": self.danbooru_tag,
            "series_tag": self.series_tag,
            "display_name": self.display_name,
            "series_name": self.series_name,
            "eyes": _layer_to_dict(self.eyes),
            "hair": _layer_to_dict(self.hair),
            "face": _layer_to_dict(self.face),
            "outfit": _layer_to_dict(self.outfit),
            "accessories": _layer_to_dict(self.accessories),
            "body": _layer_to_dict(self.body),
            "identity_tags": self.identity_tags,
            "appearance_summary": self.appearance_summary,
            "distinguishing_features": self.distinguishing_features,
            "reference_image_urls": self.reference_image_urls,
            "web_description": self.web_description,
            "search_sources": self.search_sources,
            "confidence": self.confidence,
            "timestamp": time.time(),
        }


def _layer_to_dict(layer: Optional[LayerDetail]) -> Optional[dict]:
    if not layer:
        return None
    return {
        "layer_name": layer.layer_name,
        "description": layer.description,
        "tags": layer.tags,
        "emphasis": layer.emphasis,
    }


def _dict_to_layer(d: Optional[dict]) -> Optional[LayerDetail]:
    if not d:
        return None
    return LayerDetail(
        layer_name=d.get("layer_name", ""),
        description=d.get("description", ""),
        tags=d.get("tags", []),
        emphasis=d.get("emphasis", 1.0),
    )


# ════════════════════════════════════════════════════════════════════════
# Character alias database (expanded from vision_analyst)
# ════════════════════════════════════════════════════════════════════════

# Maps lowercase aliases -> (danbooru_tag, series_tag, display_name, series_name)
_CHARACTER_ALIASES: dict[str, tuple[str, str, str, str]] = {
    # Date a Live
    "kurumi": ("tokisaki_kurumi", "date_a_live", "Tokisaki Kurumi", "Date A Live"),
    "tokisaki kurumi": ("tokisaki_kurumi", "date_a_live", "Tokisaki Kurumi", "Date A Live"),
    "tohka": ("yatogami_tohka", "date_a_live", "Yatogami Tohka", "Date A Live"),
    "kotori": ("itsuka_kotori", "date_a_live", "Itsuka Kotori", "Date A Live"),
    "origami": ("tobiichi_origami", "date_a_live", "Tobiichi Origami", "Date A Live"),
    # Sword Art Online
    "asuna": ("yuuki_asuna", "sword_art_online", "Yuuki Asuna", "Sword Art Online"),
    "kirito": ("kirigaya_kazuto", "sword_art_online", "Kirigaya Kazuto", "Sword Art Online"),
    # Re:Zero
    "rem": ("rem_(re:zero)", "re:zero", "Rem", "Re:Zero"),
    "emilia": ("emilia_(re:zero)", "re:zero", "Emilia", "Re:Zero"),
    "ram": ("ram_(re:zero)", "re:zero", "Ram", "Re:Zero"),
    # Demon Slayer
    "nezuko": ("kamado_nezuko", "kimetsu_no_yaiba", "Kamado Nezuko", "Demon Slayer"),
    "tanjiro": ("kamado_tanjiro", "kimetsu_no_yaiba", "Kamado Tanjiro", "Demon Slayer"),
    "shinobu": ("kochou_shinobu", "kimetsu_no_yaiba", "Kochou Shinobu", "Demon Slayer"),
    # Genshin Impact
    "hu tao": ("hu_tao_(genshin_impact)", "genshin_impact", "Hu Tao", "Genshin Impact"),
    "hutao": ("hu_tao_(genshin_impact)", "genshin_impact", "Hu Tao", "Genshin Impact"),
    "raiden shogun": ("raiden_shogun", "genshin_impact", "Raiden Shogun", "Genshin Impact"),
    "raiden": ("raiden_shogun", "genshin_impact", "Raiden Shogun", "Genshin Impact"),
    "fischl": ("fischl_(genshin_impact)", "genshin_impact", "Fischl", "Genshin Impact"),
    "ganyu": ("ganyu_(genshin_impact)", "genshin_impact", "Ganyu", "Genshin Impact"),
    "keqing": ("keqing_(genshin_impact)", "genshin_impact", "Keqing", "Genshin Impact"),
    "nahida": ("nahida_(genshin_impact)", "genshin_impact", "Nahida", "Genshin Impact"),
    "furina": ("furina_(genshin_impact)", "genshin_impact", "Furina", "Genshin Impact"),
    "yae miko": ("yae_miko", "genshin_impact", "Yae Miko", "Genshin Impact"),
    "zhongli": ("zhongli_(genshin_impact)", "genshin_impact", "Zhongli", "Genshin Impact"),
    # Honkai: Star Rail
    "kafka": ("kafka_(honkai:_star_rail)", "honkai:_star_rail", "Kafka", "Honkai: Star Rail"),
    "silver wolf": ("silver_wolf_(honkai:_star_rail)", "honkai:_star_rail", "Silver Wolf", "Honkai: Star Rail"),
    "seele": ("seele_(honkai:_star_rail)", "honkai:_star_rail", "Seele", "Honkai: Star Rail"),
    "firefly": ("firefly_(honkai:_star_rail)", "honkai:_star_rail", "Firefly", "Honkai: Star Rail"),
    # Fate series
    "saber": ("artoria_pendragon", "fate/stay_night", "Artoria Pendragon", "Fate/stay night"),
    "rin": ("tohsaka_rin", "fate/stay_night", "Tohsaka Rin", "Fate/stay night"),
    "sakura": ("matou_sakura", "fate/stay_night", "Matou Sakura", "Fate/stay night"),
    # Naruto
    "hinata": ("hyuuga_hinata", "naruto", "Hyuuga Hinata", "Naruto"),
    "sakura haruno": ("haruno_sakura", "naruto", "Haruno Sakura", "Naruto"),
    # Attack on Titan
    "mikasa": ("mikasa_ackerman", "shingeki_no_kyojin", "Mikasa Ackerman", "Attack on Titan"),
    "historia": ("historia_reiss", "shingeki_no_kyojin", "Historia Reiss", "Attack on Titan"),
    # Spy x Family
    "yor": ("yor_forger", "spy_x_family", "Yor Forger", "Spy x Family"),
    "anya": ("anya_forger", "spy_x_family", "Anya Forger", "Spy x Family"),
    # Bocchi the Rock
    "bocchi": ("gotoh_hitori", "bocchi_the_rock!", "Gotoh Hitori", "Bocchi the Rock!"),
    # Oshi no Ko
    "ai hoshino": ("hoshino_ai", "oshi_no_ko", "Hoshino Ai", "Oshi no Ko"),
    "ruby": ("hoshino_ruby", "oshi_no_ko", "Hoshino Ruby", "Oshi no Ko"),
    # Blue Archive
    "arona": ("arona_(blue_archive)", "blue_archive", "Arona", "Blue Archive"),
    # Frieren
    "frieren": ("frieren", "sousou_no_frieren", "Frieren", "Frieren: Beyond Journey's End"),
    "fern": ("fern_(sousou_no_frieren)", "sousou_no_frieren", "Fern", "Frieren: Beyond Journey's End"),
    # Hololive
    "fubuki": ("shirakami_fubuki", "hololive", "Shirakami Fubuki", "Hololive"),
    "pekora": ("usada_pekora", "hololive", "Usada Pekora", "Hololive"),
    "marine": ("houshou_marine", "hololive", "Houshou Marine", "Hololive"),
    "suisei": ("hoshimachi_suisei", "hololive", "Hoshimachi Suisei", "Hololive"),
    # Jujutsu Kaisen
    "gojo": ("gojo_satoru", "jujutsu_kaisen", "Gojo Satoru", "Jujutsu Kaisen"),
    # Chainsaw Man
    "makima": ("makima_(chainsaw_man)", "chainsaw_man", "Makima", "Chainsaw Man"),
    "power": ("power_(chainsaw_man)", "chainsaw_man", "Power", "Chainsaw Man"),
    # Zenless Zone Zero
    "ellen": ("ellen_joe", "zenless_zone_zero", "Ellen Joe", "Zenless Zone Zero"),
    "ellen joe": ("ellen_joe", "zenless_zone_zero", "Ellen Joe", "Zenless Zone Zero"),
    "miyabi": ("miyabi_(zenless_zone_zero)", "zenless_zone_zero", "Miyabi", "Zenless Zone Zero"),
    "lycaon": ("von_lycaon", "zenless_zone_zero", "Von Lycaon", "Zenless Zone Zero"),
    "anby": ("anby_demara", "zenless_zone_zero", "Anby Demara", "Zenless Zone Zero"),
    "nicole": ("nicole_demara", "zenless_zone_zero", "Nicole Demara", "Zenless Zone Zero"),
    "nicole demara": ("nicole_demara", "zenless_zone_zero", "Nicole Demara", "Zenless Zone Zero"),
    "koleda": ("koleda_belobog", "zenless_zone_zero", "Koleda", "Zenless Zone Zero"),
    "jane doe": ("jane_doe_(zenless_zone_zero)", "zenless_zone_zero", "Jane Doe", "Zenless Zone Zero"),
    "zhu yuan": ("zhu_yuan", "zenless_zone_zero", "Zhu Yuan", "Zenless Zone Zero"),
    "lucy": ("lucy_(zenless_zone_zero)", "zenless_zone_zero", "Lucy", "Zenless Zone Zero"),
    # NIKKE
    "rapi": ("rapi_(nikke)", "goddess_of_victory:_nikke", "Rapi", "NIKKE"),
    "marian": ("marian_(nikke)", "goddess_of_victory:_nikke", "Marian", "NIKKE"),
    "helm": ("helm_(nikke)", "goddess_of_victory:_nikke", "Helm", "NIKKE"),
    "anis": ("anis_(nikke)", "goddess_of_victory:_nikke", "Anis", "NIKKE"),
    # To Love-Ru
    "lala": ("lala_satalin_deviluke", "to_love-ru", "Lala", "To Love-Ru"),
    "momo": ("momo_velia_deviluke", "to_love-ru", "Momo", "To Love-Ru"),
    "yami": ("konjiki_no_yami", "to_love-ru", "Yami", "To Love-Ru"),
    "haruna": ("sairenji_haruna", "to_love-ru", "Haruna", "To Love-Ru"),
    # Oshi no Ko
    "ai hoshino": ("hoshino_ai", "oshi_no_ko", "Hoshino Ai", "Oshi no Ko"),
    "ruby hoshino": ("hoshino_ruby", "oshi_no_ko", "Hoshino Ruby", "Oshi no Ko"),
    "ruby": ("hoshino_ruby", "oshi_no_ko", "Hoshino Ruby", "Oshi no Ko"),
    "kana arima": ("arima_kana", "oshi_no_ko", "Arima Kana", "Oshi no Ko"),
    "akane kurokawa": ("kurokawa_akane", "oshi_no_ko", "Kurokawa Akane", "Oshi no Ko"),
    # Fire Emblem
    "lyn": ("lyndis_(fire_emblem)", "fire_emblem", "Lyndis", "Fire Emblem"),
    "camilla": ("camilla_(fire_emblem)", "fire_emblem", "Camilla", "Fire Emblem"),
    "byleth": ("byleth_(fire_emblem)", "fire_emblem", "Byleth", "Fire Emblem"),
    "edelgard": ("edelgard_von_hresvelg", "fire_emblem", "Edelgard", "Fire Emblem"),
    # KanColle
    "shimakaze": ("shimakaze_(kancolle)", "kantai_collection", "Shimakaze", "KanColle"),
    "kongou": ("kongou_(kancolle)", "kantai_collection", "Kongou", "KanColle"),
    "yamato": ("yamato_(kancolle)", "kantai_collection", "Yamato", "KanColle"),
    # Fate/Hollow Ataraxia
    "caren": ("caren_hortensia", "fate/hollow_ataraxia", "Caren Hortensia", "Fate/Hollow Ataraxia"),
    "bazett": ("bazett_fraga_mcremitz", "fate/hollow_ataraxia", "Bazett", "Fate/Hollow Ataraxia"),
    "ishtar": ("ishtar_(fate)", "fate/grand_order", "Ishtar", "Fate/Grand Order"),
    "ereshkigal": ("ereshkigal_(fate)", "fate/grand_order", "Ereshkigal", "Fate/Grand Order"),
    # Touhou
    "reimu": ("hakurei_reimu", "touhou", "Hakurei Reimu", "Touhou"),
    "marisa": ("kirisame_marisa", "touhou", "Kirisame Marisa", "Touhou"),
    "remilia": ("remilia_scarlet", "touhou", "Remilia Scarlet", "Touhou"),
    "flandre": ("flandre_scarlet", "touhou", "Flandre Scarlet", "Touhou"),
    "sakuya": ("izayoi_sakuya", "touhou", "Izayoi Sakuya", "Touhou"),
}

# ── Series hint keywords for disambiguation ─────────────────────────────
# Maps lowercase keywords that might appear in a prompt → canonical series_tag
_SERIES_HINTS: dict[str, str] = {
    # Genshin Impact
    "genshin": "genshin_impact", "genshin impact": "genshin_impact",
    "gi": "genshin_impact",
    "teyvat": "genshin_impact", "mondstadt": "genshin_impact",
    "liyue": "genshin_impact", "inazuma": "genshin_impact",
    "sumeru": "genshin_impact", "fontaine": "genshin_impact",
    "snezhnaya": "genshin_impact", "natlan": "genshin_impact",
    # Honkai: Star Rail
    "hsr": "honkai:_star_rail", "star rail": "honkai:_star_rail",
    "honkai star rail": "honkai:_star_rail", "astral express": "honkai:_star_rail",
    "stellaron": "honkai:_star_rail", "xianzhou": "honkai:_star_rail",
    "penacony": "honkai:_star_rail", "belobog": "honkai:_star_rail",
    # Honkai Impact 3rd
    "hi3": "honkai_impact_3rd", "honkai impact": "honkai_impact_3rd",
    "honkai 3rd": "honkai_impact_3rd",
    # Zenless Zone Zero
    "zzz": "zenless_zone_zero", "zenless": "zenless_zone_zero",
    "zone zero": "zenless_zone_zero", "zenless zone zero": "zenless_zone_zero",
    "new eridu": "zenless_zone_zero",
    # Date a Live
    "date a live": "date_a_live", "dal": "date_a_live",
    # Sword Art Online
    "sao": "sword_art_online", "sword art": "sword_art_online",
    # Re:Zero
    "re:zero": "re:zero", "re zero": "re:zero", "rezero": "re:zero",
    # Demon Slayer
    "demon slayer": "kimetsu_no_yaiba", "kimetsu": "kimetsu_no_yaiba",
    # Fate
    "fate": "fate/stay_night", "fgo": "fate/grand_order",
    "fate grand order": "fate/grand_order", "fate stay night": "fate/stay_night",
    "fate hollow": "fate/hollow_ataraxia",
    # Naruto
    "naruto": "naruto", "konoha": "naruto",
    # Attack on Titan
    "aot": "shingeki_no_kyojin", "attack on titan": "shingeki_no_kyojin",
    "shingeki": "shingeki_no_kyojin",
    # Spy x Family
    "spy x family": "spy_x_family", "spy family": "spy_x_family",
    # Bocchi the Rock
    "bocchi the rock": "bocchi_the_rock!",
    # Oshi no Ko
    "oshi no ko": "oshi_no_ko",
    # Blue Archive
    "blue archive": "blue_archive",
    # Frieren
    "frieren": "sousou_no_frieren",
    # Hololive
    "hololive": "hololive",
    # Jujutsu Kaisen
    "jjk": "jujutsu_kaisen", "jujutsu kaisen": "jujutsu_kaisen",
    # Chainsaw Man
    "chainsaw man": "chainsaw_man", "csm": "chainsaw_man",
    # NIKKE
    "nikke": "goddess_of_victory:_nikke",
    # To Love-Ru
    "to love": "to_love-ru", "to love-ru": "to_love-ru",
    # Fire Emblem
    "fire emblem": "fire_emblem", "fe3h": "fire_emblem",
    # KanColle
    "kancolle": "kantai_collection", "kantai": "kantai_collection",
    # Touhou
    "touhou": "touhou", "gensokyo": "touhou",
    # Arknights
    "arknights": "arknights",
    # Azur Lane
    "azur lane": "azur_lane",
    # League of Legends
    "lol": "league_of_legends", "league": "league_of_legends",
    # Wuthering Waves
    "wuthering": "wuthering_waves", "wuwa": "wuthering_waves",
}


def _detect_series_hint(text: str) -> Optional[str]:
    """Extract a series hint from the prompt, longest match first."""
    for hint in sorted(_SERIES_HINTS.keys(), key=len, reverse=True):
        if hint in text:
            return _SERIES_HINTS[hint]
    return None


# ── NSFW intent heuristic (2026-04-23 user request) ──────────────────
# Conservative keyword list. Triggering this flips the image-search
# fallback chain so StepFun (NSFW-tolerant) goes first and the safe
# providers are tried only as backup. Target image count drops to 5
# because StepFun's free tier on OpenRouter is rate-limited.
#
# Keep this list TIGHT — every false-positive wastes OpenRouter tokens
# AND silently bypasses safety-filter providers. If a word is ambiguous
# (e.g. "lewd"), prefer not to add it; require explicit anatomical
# vocabulary before flipping the chain.
_NSFW_KEYWORDS: frozenset[str] = frozenset({
    "nsfw", "r-18", "r18", "explicit", "uncensored",
    "nude", "naked", "topless", "bottomless",
    "pussy", "vagina", "vulva", "clitoris", "cervix", "urethra",
    "cock", "penis", "dick", "cum", "semen", "sperm",
    "sex", "fucking", "intercourse", "penetration", "creampie",
    "ahegao", "orgasm",
    "nipple", "nipples", "areola",
    "spread pussy", "spread legs", "leg spread", "legs spread",
    "anal", "anus",
    "loli",  # explicit policy violation flag — handled upstream
})


def _detect_nsfw_intent(user_prompt: str) -> bool:
    """Return True when the user prompt contains explicit anatomical or
    R-18 vocabulary that warrants flipping the image-search chain to
    NSFW-tolerant providers.

    Pure substring match against ``_NSFW_KEYWORDS`` (lowercased). Does
    NOT call any network or LLM — must stay cheap because it runs on
    every research call.
    """
    if not user_prompt:
        return False
    low = user_prompt.lower()
    for kw in _NSFW_KEYWORDS:
        if kw in low:
            return True
    return False


def detect_character(user_prompt: str) -> Optional[tuple[str, str, str, str]]:
    """Detect a known character in the user prompt.

    Delegates to :func:`character_parser.parse_character_identity` so that
    preposition-aware parsing, word-boundary matching, and homonym
    detection are shared across every caller. Kept as a thin wrapper for
    backward compatibility with older imports.

    Returns (danbooru_tag, series_tag, display_name, series_name) or None.
    """
    # Lazy import to avoid a circular import at module load time:
    # character_parser imports the alias/series tables from this module.
    from .character_parser import parse_character_identity

    identity = parse_character_identity(user_prompt)
    if not identity.resolved:
        return None
    return (
        identity.character_tag,
        identity.series_tag,
        identity.character_name,
        identity.series_name,
    )


# ════════════════════════════════════════════════════════════════════════
# Web research: search for character appearance details
# ════════════════════════════════════════════════════════════════════════

def _get_serpapi_key() -> str:
    return os.getenv("SERPAPI_API_KEY", "")


def _get_gemini_key() -> str:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")


def _web_search_character(display_name: str, series_name: str) -> dict:
    """Search the web for character appearance details.

    Uses SerpAPI Google search for structured character info.
    Returns raw search results dict.
    """
    api_key = _get_serpapi_key()
    if not api_key:
        logger.warning("[CharResearch] No SERPAPI_API_KEY, skipping web search")
        return {}

    import httpx

    query = f"{display_name} {series_name} anime character appearance eyes hair outfit danbooru"

    try:
        resp = httpx.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google",
                "q": query,
                "api_key": api_key,
                "num": 8,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = {}
        # Knowledge graph
        kg = data.get("knowledge_graph", {})
        if kg:
            results["knowledge"] = {
                "title": kg.get("title", ""),
                "description": kg.get("description", ""),
                "attributes": kg.get("attributes", {}),
            }

        # Organic results
        organic = data.get("organic_results", [])
        results["snippets"] = []
        for item in organic[:6]:
            results["snippets"].append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", ""),
            })

        return results

    except Exception as e:
        logger.warning("[CharResearch] Web search failed: %s", e)
        return {}


def _image_search_character(
    display_name: str, series_name: str, danbooru_tag: str,
    nsfw_intent: bool = False,
) -> list[dict]:
    """Search for character reference images via SerpAPI image search.

    Returns list of {url, thumbnail, title, source} dicts.

    When ``nsfw_intent`` is True, the SerpAPI pass is reduced to a single
    series-warm + character query (we'll prefer the StepFun NSFW pass via
    the fallback chain instead of burning SerpAPI quota on safe queries
    that won't yield what the user wants).
    """
    api_key = _get_serpapi_key()
    if not api_key:
        return []

    import httpx

    # Character-first queries. The pure-series warm-up was removed
    # 2026-04-23 because it polluted Hu Tao searches with generic
    # Genshin art (group shots, reference sheets, other characters).
    # We still bias toward franchise context by including series_name
    # alongside display_name in every query.
    queries = [
        f"{display_name} {series_name} official art",
        f"{display_name} {series_name} character illustration",
        f"{display_name} anime official art high quality",
        f"{danbooru_tag} anime illustration full body",
    ]
    if nsfw_intent:
        # NSFW: keep the strongest character-specific query only.
        queries = [f"{display_name} {series_name} official art"]

    # ── Relevance filter (2026-04-25 hardening) ─────────────────────
    # Every accepted hit must:
    #   (A) Match the character name as a WHOLE WORD (not substring) —
    #       prevents "magic sparkle effect" from passing as Sparkle and
    #       prevents misspellings like "Sparxie" from passing as Sparkle.
    #   (B) Also match a SERIES token (franchise anchor) when the name
    #       is a common English word (Sparkle, Robin, Sunday, March, …) —
    #       prevents random off-franchise art from leaking in.
    #   (C) NOT look like duo / multi-character art ("X and Y", "X & Y",
    #       "X ft. Y", "X x Y", "X with Y") — those frames are bad refs
    #       because the secondary character dominates a portion of the
    #       canvas and pollutes the identity signal.
    name_tokens: set[str] = {
        t.lower() for t in display_name.replace("-", " ").split() if len(t) > 1
    }
    name_tokens.add(display_name.lower())
    # Strip parenthesised series suffix, e.g. "hu_tao_(genshin_impact)" -> "hu_tao"
    base_tag = danbooru_tag.split("_(")[0]
    name_tokens.add(base_tag)
    name_tokens.add(base_tag.replace("_", " "))

    # Series anchor tokens — split on punctuation/space and keep stems
    # ≥ 4 chars (drops "of", "the", "no", "ga"). For "Honkai: Star Rail"
    # → {"honkai", "star", "rail"}; for "Genshin Impact" → {"genshin",
    # "impact"}; for "Blue Archive" → {"blue", "archive"}.
    series_tokens: set[str] = {
        t.lower()
        for t in re.split(r"[\s\-:_/]+", series_name or "")
        if len(t) >= 4
    }
    # Always add the joined no-punct form too so "honkaistarrail.fandom.com"
    # passes when the series name is "Honkai: Star Rail".
    if series_name:
        series_tokens.add(re.sub(r"[^a-z0-9]", "", series_name.lower()))

    # Common English words that would otherwise produce false-positives
    # without a series anchor. Grow this list when audit finds new ones.
    _AMBIGUOUS_NAMES: frozenset[str] = frozenset({
        "sparkle", "robin", "sunday", "march", "moze", "boothill",
        "bronya", "luna", "nicole", "yuki", "rei", "asuka",
        "ruby", "amber", "diona", "sara", "lisa", "rosa",
        "may", "june", "april", "noel", "noelle",
    })
    name_is_ambiguous = display_name.strip().lower() in _AMBIGUOUS_NAMES

    # Pre-compile word-boundary patterns for the name tokens. Tokens with
    # underscores/spaces get escaped for safety.
    name_patterns = [
        re.compile(r"\b" + re.escape(tok) + r"\b", re.IGNORECASE)
        for tok in sorted(name_tokens) if tok
    ]

    # Duo / multi-character title heuristic. The secondary half is
    # typically capitalised and follows one of these connectors.
    # Note: deliberately omit "x" and "+" (too many false positives in
    # urls/titles like "1500x2000" or hashtags). "&amp;" handled via "&".
    _DUO_RE = re.compile(
        r"\b(?:and|ft\.?|feat\.?|featuring|with|vs\.?)\b\s+[A-Z]"
        r"|\s[&×]\s+[A-Z]",
        re.IGNORECASE,
    )

    def _is_relevant(item: dict) -> bool:
        title = str(item.get("title", ""))
        haystack = " ".join(
            str(item.get(k, "")) for k in ("title", "source", "link", "original")
        )

        # (A) Whole-word name match anywhere in title/source/url.
        if not any(p.search(haystack) for p in name_patterns):
            return False

        # (B) Series anchor required for ambiguous names.
        if name_is_ambiguous and series_tokens:
            haystack_low = haystack.lower()
            if not any(s in haystack_low for s in series_tokens):
                return False

        # (C) Duo / multi-character title rejection. Only inspect the
        # title (URLs and source domains shouldn't trigger this).
        if title and _DUO_RE.search(title):
            return False

        return True

    all_images: list[dict] = []
    seen_urls: set[str] = set()

    # 2026-04-23 user request: use the seen registry for byte-hash dedupe
    # ONLY (in the downloader). URL-hash filtering at search time is too
    # aggressive — it permanently blacklists Hu Tao's actual image URLs
    # after the first run, leaving only off-target series art behind.
    persisted_seen = _load_seen_registry(danbooru_tag)
    skipped_irrelevant = 0

    for query in queries:
        try:
            resp = httpx.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_images",
                    "q": query,
                    "api_key": api_key,
                    "num": 20,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("images_results", [])[:15]:
                url = item.get("original", item.get("link", ""))
                if not url or url in seen_urls:
                    continue
                if not _is_relevant(item):
                    skipped_irrelevant += 1
                    continue
                seen_urls.add(url)
                all_images.append({
                    "url": url,
                    "thumbnail": item.get("thumbnail", ""),
                    "title": item.get("title", ""),
                    "source": item.get("source", ""),
                    "width": item.get("original_width", 0),
                    "height": item.get("original_height", 0),
                })
        except Exception as e:
            logger.warning("[CharResearch] Image search failed for '%s': %s", query, e)

    if skipped_irrelevant:
        logger.info(
            "[CharResearch] Filtered %d off-character SerpAPI hits "
            "(name_tokens=%s, byte-hash registry has %d entries)",
            skipped_irrelevant,
            sorted(t for t in name_tokens if t),
            len(persisted_seen.get("byte_hashes", {})),
        )

    # ── Fallback chain: Gemini → OpenAI → Grok → StepFun (if NSFW) ──
    # Spec §3b: supplement SerpAPI results up to 10 images via LLM
    # web-search providers so we don't ship to the pipeline with <10 refs.
    # When ``nsfw_intent`` is True, the chain is FLIPPED — StepFun goes
    # first (5-image target) because the safe providers will refuse or
    # return generic SFW art that fights the user's actual prompt.
    target_total = 5 if nsfw_intent else 10
    if len(all_images) < target_total:
        try:
            from .image_url_fallback import fetch_image_urls_fallback
            allow_sensitive = (
                nsfw_intent
                or bool(os.getenv("CHAR_RESEARCH_ALLOW_SENSITIVE", "0") == "1")
            )
            extra = fetch_image_urls_fallback(
                display_name=display_name,
                series_name=series_name,
                danbooru_tag=danbooru_tag,
                already_found=all_images,
                target_count=target_total,
                allow_sensitive=allow_sensitive,
                prioritize_sensitive=nsfw_intent,
            )
            if extra:
                # Apply the same relevance filter to fallback-chain URLs
                # so off-character generic art doesn't leak in.
                relevant = [e for e in extra if e.get("url") and _is_relevant(e)]
                dropped = len(extra) - len(relevant)
                if dropped:
                    logger.info(
                        "[CharResearch] Dropped %d off-character fallback URLs",
                        dropped,
                    )
                logger.info(
                    "[CharResearch] Fallback chain added %d image URLs "
                    "(total %d, nsfw_intent=%s)",
                    len(relevant), len(all_images) + len(relevant), nsfw_intent,
                )
                all_images.extend(relevant)
        except Exception as e:
            logger.warning("[CharResearch] Fallback chain failed: %s", e)

    return all_images


def _download_reference_images(
    image_results: list[dict],
    danbooru_tag: str,
    max_images: int = 10,
) -> list[str]:
    """Download reference images and return as base64 strings.

    Behaviour (post 2026-04-23 refresh):
      * Always attempts FRESH downloads from ``image_results`` first.
      * Skips URLs whose md5(url) hash is in the persisted seen registry.
      * After download, computes SHA-256 of the bytes and skips if those
        bytes were ever saved before (catches CDN mirrors / aliases).
      * On every successful save, updates the registry on disk so the
        next run never re-downloads the same content.
      * Cached files in ``storage/character_refs/<tag>/`` are used ONLY
        as a fallback when the fresh fetch yields zero new images, OR
        when ``CHAR_RESEARCH_REUSE_REFS=1`` is set explicitly.

    Always returns a list of base64-encoded image strings.
    """
    import httpx

    ref_dir = _REF_DIR / danbooru_tag
    ref_dir.mkdir(parents=True, exist_ok=True)

    registry = _load_seen_registry(danbooru_tag)
    fresh_b64: list[str] = []
    registry_dirty = False

    # Honour explicit opt-in to old behaviour.
    if _reuse_cached_refs_enabled():
        existing = sorted(ref_dir.glob("*.png")) + sorted(ref_dir.glob("*.jpg"))
        if existing:
            logger.info(
                "[CharResearch] CHAR_RESEARCH_REUSE_REFS=1 — using %d cached refs for %s",
                len(existing), danbooru_tag,
            )
            for path in existing[:max_images]:
                try:
                    fresh_b64.append(
                        base64.b64encode(path.read_bytes()).decode("ascii")
                    )
                except Exception:
                    pass
            if fresh_b64:
                return fresh_b64[:max_images]

    # Fresh-only download loop
    for item in image_results:
        if len(fresh_b64) >= max_images:
            break

        url = item.get("url", "")
        if not url:
            continue

        # Filter: skip tiny images, gifs, webp
        w = item.get("width", 0)
        h = item.get("height", 0)
        if w and h and (w < 300 or h < 300):
            continue
        if any(url.lower().endswith(ext) for ext in [".gif", ".webp", ".svg", ".ico"]):
            continue

        try:
            resp = httpx.get(
                url,
                timeout=10,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ImageBot/1.0)"},
            )
            if resp.status_code != 200:
                continue

            content_type = resp.headers.get("content-type", "")
            if "image" not in content_type:
                continue

            img_data = resp.content
            if len(img_data) < 5000:
                continue
            if len(img_data) > 10_000_000:
                continue

            # Byte-hash dedupe: if these exact bytes were ever cached for
            # this character (under any URL), reject.
            byte_hash = _bytes_hash(img_data)
            if byte_hash in registry["byte_hashes"]:
                logger.info(
                    "[CharResearch] Rejected duplicate-by-bytes from %s (matches %s)",
                    url[:60], registry["byte_hashes"][byte_hash],
                )
                # Still mark URL as seen so we don't retry it.
                registry["url_hashes"][_url_hash(url)] = registry["byte_hashes"][byte_hash]
                registry_dirty = True
                continue

            ext = ".png" if "png" in content_type else ".jpg"
            cache_path = ref_dir / f"web_{_url_hash(url)}{ext}"
            cache_path.write_bytes(img_data)

            # Record both URL hash and byte hash as seen
            registry["url_hashes"][_url_hash(url)] = cache_path.name
            registry["byte_hashes"][byte_hash] = cache_path.name
            registry_dirty = True

            fresh_b64.append(base64.b64encode(img_data).decode("ascii"))
            logger.info(
                "[CharResearch] Downloaded FRESH ref: %s (%d KB)",
                cache_path.name, len(img_data) // 1024,
            )

        except Exception as e:
            logger.debug("[CharResearch] Failed to download %s: %s", url[:80], e)

    if registry_dirty:
        _save_seen_registry(danbooru_tag, registry)

    if fresh_b64:
        logger.info(
            "[CharResearch] Returned %d FRESH reference images for %s "
            "(no cached reuse)",
            len(fresh_b64), danbooru_tag,
        )
        return fresh_b64[:max_images]

    # Last-resort fallback: if every search source rejected, use whatever
    # we already have on disk so the pipeline doesn't run blind.
    existing = sorted(ref_dir.glob("*.png")) + sorted(ref_dir.glob("*.jpg"))
    if existing:
        logger.warning(
            "[CharResearch] No fresh refs found for %s — falling back to "
            "%d cached refs as last resort",
            danbooru_tag, len(existing),
        )
        out: list[str] = []
        for path in existing[:max_images]:
            try:
                out.append(base64.b64encode(path.read_bytes()).decode("ascii"))
            except Exception:
                pass
        return out

    logger.warning(
        "[CharResearch] No reference images available for %s (fresh+cached both empty)",
        danbooru_tag,
    )
    return []


# ════════════════════════════════════════════════════════════════════════
# LLM-based appearance extraction from web search results
# ════════════════════════════════════════════════════════════════════════

_APPEARANCE_EXTRACTION_PROMPT = """\
You are an anime character appearance analyst. Given web search results about \
an anime character, extract their EXACT visual appearance details.

Return ONLY a JSON object:
{{
  "eyes": {{
    "description": "detailed eye description including color, shape, special features",
    "tags": ["danbooru_tag1", "tag2"],
    "emphasis": 1.0
  }},
  "hair": {{
    "description": "hair color, length, style, accessories",
    "tags": ["danbooru_tag1", "tag2"],
    "emphasis": 1.0
  }},
  "face": {{
    "description": "face shape, expression tendency, any markings",
    "tags": ["tag1"],
    "emphasis": 1.0
  }},
  "outfit": {{
    "description": "default/iconic outfit description",
    "tags": ["danbooru_tag1", "tag2"],
    "emphasis": 1.0
  }},
  "accessories": {{
    "description": "notable accessories, weapons, items",
    "tags": ["tag1"],
    "emphasis": 1.0
  }},
  "body": {{
    "description": "body type, skin tone, notable features",
    "tags": ["tag1"],
    "emphasis": 1.0
  }},
  "identity_tags": ["most important 8-12 danbooru-style tags for this character"],
  "distinguishing_features": ["list of 3-5 most unique visual traits"],
  "appearance_summary": "2-3 sentence visual summary"
}}

Rules:
- Use danbooru tag format: "blue_eyes", "long_hair", "school_uniform"
- For heterochromia, specify EACH eye color separately
- Set emphasis > 1.0 (up to 1.3) for the character's MOST distinctive features
- Be PRECISE about colors - "golden yellow" not just "yellow"
- Include body type tags: "1girl"/"1boy", "slim", "petite", etc.

Character: {display_name} from {series_name}
Web search context:
{search_context}
"""


def _extract_appearance_from_search(
    display_name: str,
    series_name: str,
    search_results: dict,
) -> Optional[dict]:
    """Use LLM to extract structured appearance from web search snippets."""
    snippets = search_results.get("snippets", [])
    knowledge = search_results.get("knowledge", {})

    if not snippets and not knowledge:
        return None

    # Build context
    context_parts = []
    if knowledge:
        context_parts.append(
            f"Knowledge Graph: {knowledge.get('title', '')} - "
            f"{knowledge.get('description', '')}"
        )
        for k, v in knowledge.get("attributes", {}).items():
            context_parts.append(f"  {k}: {v}")

    for s in snippets[:5]:
        context_parts.append(f"[{s['title']}] {s['snippet']}")

    search_context = "\n".join(context_parts)

    prompt = _APPEARANCE_EXTRACTION_PROMPT.format(
        display_name=display_name,
        series_name=series_name,
        search_context=search_context,
    )

    # Try Gemini first
    gemini_key = _get_gemini_key()
    if gemini_key:
        result = _llm_extract_gemini(prompt, gemini_key)
        if result:
            return result

    # Fallback: OpenAI
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        result = _llm_extract_openai(prompt, openai_key)
        if result:
            return result

    return None


def _llm_extract_gemini(prompt: str, api_key: str) -> Optional[dict]:
    """Extract appearance via Gemini."""
    import httpx

    try:
        resp = httpx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-2.0-flash:generateContent",
            headers={"X-goog-api-key": api_key},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 800,
                    "responseMimeType": "application/json",
                },
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        return _parse_appearance_json(text)
    except Exception as e:
        logger.warning("[CharResearch] Gemini extraction failed: %s", e)
        return None


def _llm_extract_openai(prompt: str, api_key: str) -> Optional[dict]:
    """Extract appearance via OpenAI."""
    import httpx

    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return _parse_appearance_json(text)
    except Exception as e:
        logger.warning("[CharResearch] OpenAI extraction failed: %s", e)
        return None


def _parse_appearance_json(text: str) -> Optional[dict]:
    """Parse appearance JSON from LLM output."""
    try:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except (json.JSONDecodeError, KeyError):
        return None


# ════════════════════════════════════════════════════════════════════════
# Vision-based reference analysis (analyze downloaded images)
# ════════════════════════════════════════════════════════════════════════

_VISION_REF_PROMPT = """\
Analyze this anime character reference image. Return ONLY a JSON object:
{{
  "eyes": {{"color": "exact color(s)", "shape": "description", "special": "any unique features"}},
  "hair": {{"color": "exact color", "length": "short/medium/long/very_long", "style": "description"}},
  "outfit": {{"description": "what they are wearing", "colors": ["primary colors"]}},
  "body_type": "description",
  "pose": "current pose in image",
  "accessories": ["list of accessories"],
  "art_quality": "low/medium/high/excellent"
}}

Character hint: {display_name} from {series_name}
"""


def _analyze_reference_image(
    image_b64: str,
    display_name: str,
    series_name: str,
) -> Optional[dict]:
    """Analyze a single reference image with vision LLM."""
    gemini_key = _get_gemini_key()
    if not gemini_key:
        return None

    import httpx

    prompt = _VISION_REF_PROMPT.format(
        display_name=display_name, series_name=series_name,
    )

    raw = image_b64.split(",", 1)[-1] if "," in image_b64 else image_b64

    try:
        resp = httpx.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-2.0-flash:generateContent",
            headers={"X-goog-api-key": gemini_key},
            json={
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/png", "data": raw}},
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 500,
                    "responseMimeType": "application/json",
                },
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        return _parse_appearance_json(text)
    except Exception as e:
        logger.warning("[CharResearch] Vision ref analysis failed: %s", e)
        return None


# ════════════════════════════════════════════════════════════════════════
# Main research pipeline
# ════════════════════════════════════════════════════════════════════════

def _load_cached_research(danbooru_tag: str) -> Optional[CharacterResearchResult]:
    """Load cached research if still valid."""
    cache_file = _RESEARCH_DIR / danbooru_tag / "research.json"
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        ts = data.get("timestamp", 0)
        if time.time() - ts > _RESEARCH_TTL_SECONDS:
            logger.info("[CharResearch] Cache expired for %s", danbooru_tag)
            return None

        result = CharacterResearchResult(
            danbooru_tag=data["danbooru_tag"],
            series_tag=data["series_tag"],
            display_name=data.get("display_name", ""),
            series_name=data.get("series_name", ""),
            eyes=_dict_to_layer(data.get("eyes")),
            hair=_dict_to_layer(data.get("hair")),
            face=_dict_to_layer(data.get("face")),
            outfit=_dict_to_layer(data.get("outfit")),
            accessories=_dict_to_layer(data.get("accessories")),
            body=_dict_to_layer(data.get("body")),
            identity_tags=data.get("identity_tags", []),
            appearance_summary=data.get("appearance_summary", ""),
            distinguishing_features=data.get("distinguishing_features", []),
            reference_image_urls=data.get("reference_image_urls", []),
            web_description=data.get("web_description", ""),
            search_sources=data.get("search_sources", []),
            confidence=data.get("confidence", 0.0),
            cached=True,
        )
        logger.info("[CharResearch] Loaded cached research for %s (conf=%.2f)",
                     danbooru_tag, result.confidence)
        return result
    except Exception as e:
        logger.warning("[CharResearch] Cache load failed: %s", e)
        return None


def _save_research_cache(result: CharacterResearchResult) -> None:
    """Save research to cache."""
    cache_dir = _RESEARCH_DIR / result.danbooru_tag
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "research.json"
    try:
        cache_file.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("[CharResearch] Saved research cache: %s", cache_file)
    except Exception as e:
        logger.warning("[CharResearch] Cache save failed: %s", e)


def research_character(
    user_prompt: str,
    user_reference_images: Optional[list[str]] = None,
    force_refresh: bool = False,
) -> Optional[CharacterResearchResult]:
    """Full character research pipeline.

    Steps:
      1. Detect character from user prompt
      2. Check cache (skip web search if valid cache exists)
      3. Web search for character appearance info
      4. Image search + download reference images
      5. LLM extraction of structured appearance data
      6. Vision analysis of reference images
      7. Merge all data into CharacterResearchResult
      8. Cache the result

    Args:
        user_prompt: The user's generation request text
        user_reference_images: Optional user-uploaded reference images (base64)
        force_refresh: Skip cache, re-research from web

    Returns:
        CharacterResearchResult or None if no character detected
    """
    t0 = time.time()

    # Step 1: Detect character
    char_info = detect_character(user_prompt)
    if not char_info:
        logger.info("[CharResearch] No known character detected in prompt")
        return None

    danbooru_tag, series_tag, display_name, series_name = char_info
    logger.info("[CharResearch] Character detected: %s (%s)", display_name, series_name)

    # Detect NSFW intent ONCE per research call. Threaded into image
    # search to flip provider priority + halve target count.
    nsfw_intent = _detect_nsfw_intent(user_prompt)
    if nsfw_intent:
        logger.info(
            "[CharResearch] NSFW intent detected — switching image search to "
            "StepFun-priority chain (target=5)",
        )

    # Step 2: Check cache
    # 2026-04-26: SAA-first — ALWAYS gather local refs (incl. SAA thumb)
    # before any web call so external search becomes a true fallback.
    local_refs = _collect_local_refs(danbooru_tag, max_images=10)
    # When _SAA_MIN_LOCAL_REFS <= 0 (default) the cap is disabled — web
    # search ALWAYS runs so the ref cache keeps growing. Set a positive
    # int via CHAR_RESEARCH_MIN_LOCAL_REFS to opt back into capping.
    skip_web_image_search = (
        _SAA_MIN_LOCAL_REFS > 0 and len(local_refs) >= _SAA_MIN_LOCAL_REFS
    )

    if not force_refresh:
        cached = _load_cached_research(danbooru_tag)
        if cached:
            if skip_web_image_search:
                logger.info(
                    "[CharResearch] Cache+SAA path: %d local refs >= %d — "
                    "skipping web image search for %s",
                    len(local_refs), _SAA_MIN_LOCAL_REFS, danbooru_tag,
                )
                cached.reference_images_b64 = local_refs[:10]
            else:
                # 2026-04-23 user request: even when research metadata is
                # cached, ALWAYS attempt a fresh image search so reference
                # images don't get reused across runs. The downloader has
                # its own seen-URL+byte-hash registry that guarantees no
                # duplicate is ever returned.
                try:
                    fresh_results = _image_search_character(
                        display_name, series_name, danbooru_tag,
                        nsfw_intent=nsfw_intent,
                    )
                except Exception as e:
                    logger.warning(
                        "[CharResearch] cache-path fresh search failed: %s", e,
                    )
                    fresh_results = [{"url": u} for u in cached.reference_image_urls]

                cached.reference_images_b64 = (
                    local_refs
                    + _download_reference_images(
                        fresh_results, danbooru_tag, max_images=10,
                    )
                )[:12]
                # Refresh the cached URL list so subsequent runs see the new
                # set rather than perpetually circling the original 5.
                if fresh_results:
                    cached.reference_image_urls = [
                        r.get("url", "") for r in fresh_results[:6] if r.get("url")
                    ]
            # Add user references
            if user_reference_images:
                cached.reference_images_b64 = (
                    user_reference_images[:2] + cached.reference_images_b64
                )[:12]
            cached.research_time_ms = (time.time() - t0) * 1000
            cached.local_refs_count = len(local_refs)
            cached.web_refs_count = max(
                0, len(cached.reference_images_b64) - len(local_refs)
                - (len(user_reference_images or []) if user_reference_images else 0)
            )
            cached.web_search_skipped = skip_web_image_search
            cached.nsfw_intent = nsfw_intent
            return cached

    # Step 3: Web search
    logger.info("[CharResearch] Searching web for %s appearance...", display_name)
    search_results = _web_search_character(display_name, series_name)

    # Step 4: Image search + download
    if skip_web_image_search:
        logger.info(
            "[CharResearch] Fresh path: %d local refs satisfy minimum (%d) — "
            "skipping web image search for %s",
            len(local_refs), _SAA_MIN_LOCAL_REFS, danbooru_tag,
        )
        image_results = []
        ref_images = list(local_refs)
    else:
        logger.info("[CharResearch] Searching for reference images...")
        image_results = _image_search_character(
            display_name, series_name, danbooru_tag, nsfw_intent=nsfw_intent,
        )
        # Local refs (incl. SAA thumb) come first; web fills the rest.
        ref_images = (
            local_refs
            + _download_reference_images(
                image_results, danbooru_tag, max_images=10,
            )
        )[:12]

    # Add user-uploaded references (highest priority)
    if user_reference_images:
        ref_images = user_reference_images[:2] + ref_images
        ref_images = ref_images[:12]

    # Step 5: LLM extraction from web search
    appearance_data = _extract_appearance_from_search(
        display_name, series_name, search_results,
    )

    # Step 6: Vision analysis of best reference image
    vision_data = None
    if ref_images:
        vision_data = _analyze_reference_image(
            ref_images[0], display_name, series_name,
        )

    # Step 7: Build result
    result = CharacterResearchResult(
        danbooru_tag=danbooru_tag,
        series_tag=series_tag,
        display_name=display_name,
        series_name=series_name,
        reference_images_b64=ref_images,
        reference_image_urls=[img["url"] for img in image_results[:6]],
        search_sources=[s["link"] for s in search_results.get("snippets", [])[:4]],
    )

    if appearance_data:
        result.eyes = _dict_to_layer_from_appearance(appearance_data.get("eyes"), "eyes")
        result.hair = _dict_to_layer_from_appearance(appearance_data.get("hair"), "hair")
        result.face = _dict_to_layer_from_appearance(appearance_data.get("face"), "face")
        result.outfit = _dict_to_layer_from_appearance(appearance_data.get("outfit"), "outfit")
        result.accessories = _dict_to_layer_from_appearance(
            appearance_data.get("accessories"), "accessories",
        )
        result.body = _dict_to_layer_from_appearance(appearance_data.get("body"), "body")
        result.identity_tags = appearance_data.get("identity_tags", [])
        result.appearance_summary = appearance_data.get("appearance_summary", "")
        result.distinguishing_features = appearance_data.get(
            "distinguishing_features", [],
        )
        result.confidence = 0.85
    else:
        result.confidence = 0.4

    # Enrich with vision data
    if vision_data:
        _merge_vision_data(result, vision_data)
        result.confidence = min(1.0, result.confidence + 0.1)

    # Web description
    kg = search_results.get("knowledge", {})
    if kg:
        result.web_description = kg.get("description", "")

    # Step 8: Cache
    _save_research_cache(result)

    result.research_time_ms = (time.time() - t0) * 1000
    result.local_refs_count = len(local_refs)
    result.web_refs_count = max(
        0, len(ref_images) - len(local_refs)
        - (len(user_reference_images or []) if user_reference_images else 0)
    )
    result.web_search_skipped = skip_web_image_search
    result.nsfw_intent = nsfw_intent
    logger.info(
        "[CharResearch] Research complete: %s (conf=%.2f, %d refs [%d local + %d web], skip_web=%s, %.0fms)",
        danbooru_tag, result.confidence, len(ref_images),
        result.local_refs_count, result.web_refs_count,
        result.web_search_skipped, result.research_time_ms,
    )

    return result


def _dict_to_layer_from_appearance(
    data: Any, layer_name: str,
) -> Optional[LayerDetail]:
    """Convert LLM appearance extraction dict to LayerDetail."""
    if not data:
        return None
    if isinstance(data, dict):
        return LayerDetail(
            layer_name=layer_name,
            description=data.get("description", str(data)),
            tags=data.get("tags", []),
            emphasis=data.get("emphasis", 1.0),
        )
    if isinstance(data, str):
        return LayerDetail(
            layer_name=layer_name,
            description=data,
            tags=[],
            emphasis=1.0,
        )
    return None


def _merge_vision_data(result: CharacterResearchResult, vision: dict) -> None:
    """Merge vision analysis data into research result."""
    # Enrich eye details from actual image
    if "eyes" in vision and result.eyes:
        v_eyes = vision["eyes"]
        if isinstance(v_eyes, dict):
            color = v_eyes.get("color", "")
            special = v_eyes.get("special", "")
            if color and color not in result.eyes.description:
                result.eyes.description += f" (verified: {color})"
            if special:
                result.eyes.description += f" [{special}]"

    # Enrich hair from actual image
    if "hair" in vision and result.hair:
        v_hair = vision["hair"]
        if isinstance(v_hair, dict):
            color = v_hair.get("color", "")
            if color and color not in result.hair.description:
                result.hair.description += f" (verified: {color})"

    # Enrich outfit
    if "outfit" in vision and result.outfit:
        v_outfit = vision["outfit"]
        if isinstance(v_outfit, dict):
            desc = v_outfit.get("description", "")
            if desc and len(desc) > len(result.outfit.description):
                result.outfit.description = desc
