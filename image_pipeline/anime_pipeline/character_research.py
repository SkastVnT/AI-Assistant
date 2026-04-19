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
}


def detect_character(user_prompt: str) -> Optional[tuple[str, str, str, str]]:
    """Detect a known character in the user prompt.

    Returns (danbooru_tag, series_tag, display_name, series_name) or None.
    """
    lower = user_prompt.lower()
    # Try longest alias first to avoid partial matches (e.g. "sakura haruno" before "sakura")
    for alias in sorted(_CHARACTER_ALIASES.keys(), key=len, reverse=True):
        if alias in lower:
            return _CHARACTER_ALIASES[alias]
    return None


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
) -> list[dict]:
    """Search for character reference images via SerpAPI image search.

    Returns list of {url, thumbnail, title, source} dicts.
    """
    api_key = _get_serpapi_key()
    if not api_key:
        return []

    import httpx

    # Search with specific quality terms
    queries = [
        f"{display_name} {series_name} anime official art high quality",
        f"{danbooru_tag} anime illustration full body",
    ]

    all_images: list[dict] = []
    seen_urls: set[str] = set()

    for query in queries:
        try:
            resp = httpx.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_images",
                    "q": query,
                    "api_key": api_key,
                    "num": 8,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("images_results", [])[:6]:
                url = item.get("original", item.get("link", ""))
                if url and url not in seen_urls:
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

    return all_images


def _download_reference_images(
    image_results: list[dict],
    danbooru_tag: str,
    max_images: int = 3,
) -> list[str]:
    """Download reference images and return as base64 strings.

    Also caches them to storage/character_refs/<tag>/.
    Filters for reasonable image sizes and formats.
    """
    import httpx

    ref_dir = _REF_DIR / danbooru_tag
    ref_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[str] = []

    # Check existing cache first
    existing = sorted(ref_dir.glob("*.png")) + sorted(ref_dir.glob("*.jpg"))
    if existing:
        logger.info("[CharResearch] Found %d cached refs for %s", len(existing), danbooru_tag)
        for path in existing[:max_images]:
            try:
                img_data = path.read_bytes()
                b64 = base64.b64encode(img_data).decode("ascii")
                downloaded.append(b64)
            except Exception:
                pass
        if len(downloaded) >= max_images:
            return downloaded[:max_images]

    # Download new images
    for item in image_results:
        if len(downloaded) >= max_images:
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
            if len(img_data) < 5000:  # too small
                continue
            if len(img_data) > 10_000_000:  # too large (>10MB)
                continue

            # Save to cache
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            ext = ".png" if "png" in content_type else ".jpg"
            cache_path = ref_dir / f"web_{url_hash}{ext}"
            cache_path.write_bytes(img_data)

            b64 = base64.b64encode(img_data).decode("ascii")
            downloaded.append(b64)
            logger.info("[CharResearch] Downloaded ref: %s (%d KB)",
                        cache_path.name, len(img_data) // 1024)

        except Exception as e:
            logger.debug("[CharResearch] Failed to download %s: %s", url[:80], e)

    return downloaded[:max_images]


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
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={api_key}",
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
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={gemini_key}",
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

    # Step 2: Check cache
    if not force_refresh:
        cached = _load_cached_research(danbooru_tag)
        if cached:
            # Still load reference images (may have new ones from previous runs)
            cached.reference_images_b64 = _download_reference_images(
                [{"url": u} for u in cached.reference_image_urls],
                danbooru_tag,
                max_images=3,
            )
            # Add user references
            if user_reference_images:
                cached.reference_images_b64 = (
                    user_reference_images[:2] + cached.reference_images_b64
                )[:4]
            cached.research_time_ms = (time.time() - t0) * 1000
            return cached

    # Step 3: Web search
    logger.info("[CharResearch] Searching web for %s appearance...", display_name)
    search_results = _web_search_character(display_name, series_name)

    # Step 4: Image search + download
    logger.info("[CharResearch] Searching for reference images...")
    image_results = _image_search_character(display_name, series_name, danbooru_tag)
    ref_images = _download_reference_images(image_results, danbooru_tag, max_images=3)

    # Add user-uploaded references (highest priority)
    if user_reference_images:
        ref_images = user_reference_images[:2] + ref_images
        ref_images = ref_images[:4]

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
    logger.info(
        "[CharResearch] Research complete: %s (conf=%.2f, %d refs, %.0fms)",
        danbooru_tag, result.confidence, len(ref_images), result.research_time_ms,
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
