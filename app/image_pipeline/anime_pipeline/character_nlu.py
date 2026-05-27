"""
character_nlu — natural-language → SAA character key.

Reads a free-form prompt (Vietnamese or English) like

    "Tạo ảnh Hoshino trong Blue Archive đang đứng trên cánh đồng hoa"
    "Draw Hoshino from Blue Archive in a flower field"
    "Vẽ Nahida (Genshin Impact) cute"

and returns the SAA WAI database key of the most likely character, e.g.
``hoshino_(blue_archive)``.

Strategy:
  1. Strip Vietnamese imperative verbs ("vẽ", "tạo ảnh", ...).
  2. Look for the patterns
       <name> <connector> <franchise>
       <name> (<franchise>)
     where ``<connector>`` ∈ {trong, của, in, from, of}.
  3. Build a candidate SAA tag ``"<name> (<franchise>)"`` and resolve via
     ``saa_character_db.lookup_character``. The SAA matcher already does
     normalisation + containment, so a slightly noisy name still hits.
  4. If no franchise is named, fall back to a bare name lookup.

Returns None when no plausible character is detected — callers should
treat that as "use the prompt verbatim".
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# Vietnamese / English imperative + filler words that precede the
# subject in chat prompts. We strip them only from the *front* so the
# remainder still carries the scene description ("đang đứng …").
_LEADING_VERBS = re.compile(
    r"^\s*(?:"
    r"hãy\s+|làm\s+ơn\s+|please\s+|"
    r"vẽ\s+|tạo\s+(?:một\s+|1\s+)?(?:bức\s+|tấm\s+)?ảnh\s+(?:của\s+|về\s+)?|"
    r"tạo\s+ảnh\s+(?:của\s+|về\s+)?|"
    r"generate\s+(?:an?\s+)?image\s+of\s+|"
    r"draw\s+(?:me\s+)?(?:an?\s+)?(?:picture\s+of\s+)?|"
    r"create\s+(?:an?\s+)?image\s+of\s+|"
    r"show\s+me\s+(?:an?\s+)?(?:picture\s+of\s+)?|"
    r"sinh\s+ảnh\s+(?:của\s+|về\s+)?"
    r")",
    re.IGNORECASE,
)

# Connectors that map "<name> X <franchise>" together. Order: longest first.
_CONNECTORS = [
    "trong game",
    "trong series",
    "trong anime",
    "of the",
    "trong",
    "của",
    "from",
    "in the",
    "in",
    "of",
]

# Build a single regex that captures (name, connector, franchise).
# name: 1–4 word tokens of letters / digits / Vietnamese chars / dots / dashes / apostrophes.
_NAME_TOKEN = r"[A-Za-zÀ-ỹĐđ0-9][A-Za-zÀ-ỹĐđ0-9'.\-]*"
_NAME_GROUP = rf"(?P<name>{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{0,3}})"
_FRAN_GROUP = rf"(?P<franchise>{_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{0,4}})"

_CONN_RE = "|".join(re.escape(c) for c in _CONNECTORS)

# Pattern A: "Name <connector> Franchise"
_PAT_NAME_CONN_FRAN = re.compile(
    rf"\b{_NAME_GROUP}\s+(?:{_CONN_RE})\s+{_FRAN_GROUP}\b",
    re.IGNORECASE,
)

# Pattern B: "Name (Franchise)" — already SAA-style.
_PAT_NAME_PAREN = re.compile(
    rf"\b{_NAME_GROUP}\s*\(\s*{_FRAN_GROUP}\s*\)",
    re.IGNORECASE,
)

# Stop words we never want to treat as a "name" (false positives from
# Vietnamese sentences like "ảnh trong vườn").
_NAME_STOPWORDS = {
    "ảnh",
    "anh",
    "em",
    "chị",
    "cô",
    "cậu",
    "bạn",
    "image",
    "picture",
    "photo",
    "art",
    "anime",
    "manga",
    "game",
    "series",
    "một",
    "một bức",
    "1",
    "the",
    "a",
    "an",
}


def _looks_like_name(s: str) -> bool:
    """Reject tokens that are obviously not a character name."""
    if not s:
        return False
    low = s.strip().lower()
    if low in _NAME_STOPWORDS:
        return False
    # Pure number / pure punctuation
    if not re.search(r"[A-Za-zÀ-ỹĐđ]", s):
        return False
    return True


def _try_saa(query: str) -> Optional[tuple[str, str]]:
    """Return (saa_key, display_name) or None.

    saa_key is the canonical danbooru-style key (spaces → underscores)
    suitable for ``character_key`` in the anime-pipeline payload.
    """
    try:
        from image_pipeline.anime_pipeline.saa_character_db import lookup_character
    except Exception as exc:
        logger.debug("[character_nlu] SAA unavailable: %s", exc)
        return None

    hit = lookup_character(query)
    if hit is None:
        return None
    if hit.match_score < 0.55:
        # Too fuzzy — likely a noun, not a character.
        return None
    return hit.danbooru_tag, hit.display_name


def extract_character_key(prompt: str) -> Optional[str]:
    """Return SAA-format ``character_key`` derived from natural prompt,
    or None when nothing matches.

    Examples:
        "Tạo ảnh Hoshino trong Blue Archive đang đứng …"
            → "hoshino_(blue_archive)"
        "Draw Nahida from Genshin Impact"
            → "nahida_(genshin_impact)"
        "Vẽ Furina (Genshin) cute"
            → "furina_(genshin_impact)"
        "Vẽ một bông hoa"
            → None
    """
    if not prompt or not isinstance(prompt, str):
        return None

    text = _LEADING_VERBS.sub("", prompt).strip()
    if not text:
        return None

    # Try paren pattern first — it's the most explicit.
    for pat in (_PAT_NAME_PAREN, _PAT_NAME_CONN_FRAN):
        for m in pat.finditer(text):
            name = m.group("name").strip()
            fran = m.group("franchise").strip()
            # Trim trailing scene words from franchise: "Blue Archive đang đứng"
            # → keep only the leading 1–3 capitalised / known-franchise tokens.
            fran = _trim_franchise_tail(fran)
            if not _looks_like_name(name) or not fran:
                continue
            query = f"{name} ({fran})"
            hit = _try_saa(query)
            if hit:
                key, display = hit
                logger.info(
                    "[character_nlu] '%s' → %s (%s)",
                    query,
                    key,
                    display,
                )
                return key

    # Fallback: try the first 1–3 leading tokens as a bare name.
    leading = re.match(rf"\s*({_NAME_TOKEN}(?:\s+{_NAME_TOKEN}){{0,2}})", text)
    if leading:
        bare = leading.group(1).strip()
        if _looks_like_name(bare) and len(bare) >= 3:
            hit = _try_saa(bare)
            if hit:
                key, display = hit
                logger.info(
                    "[character_nlu] bare '%s' → %s (%s)",
                    bare,
                    key,
                    display,
                )
                return key

    return None


# Common franchise keywords we trust as "real" franchise tokens.
# When the regex over-captures ("Blue Archive đang đứng"), we trim back
# to the longest known franchise prefix.
_KNOWN_FRANCHISE_HEADS = {
    "blue",
    "genshin",
    "honkai",
    "star",
    "rail",
    "impact",
    "arknights",
    "azur",
    "lane",
    "fate",
    "grand",
    "order",
    "kantai",
    "collection",
    "girls",
    "frontline",
    "umamusume",
    "love",
    "live",
    "idolmaster",
    "vocaloid",
    "touhou",
    "fire",
    "emblem",
    "nikke",
    "wuthering",
    "waves",
    "zenless",
    "zone",
    "zero",
    "league",
    "of",
    "legends",
    "valorant",
    "overwatch",
    "genshin_impact",
    "honkai_star_rail",
    "blue_archive",
    "punishing",
    "gray",
    "raven",
    "re:zero",
    "rezero",
    "konosuba",
    "kaguya",
    "sama",
    "spy",
    "x",
    "family",
    "jujutsu",
    "kaisen",
    "demon",
    "slayer",
    "kimetsu",
    "yaiba",
    "naruto",
    "boruto",
    "bleach",
    "one",
    "piece",
    "evangelion",
    "neon",
    "nge",
    "lycoris",
    "recoil",
    "frieren",
    "oshi",
    "no",
    "ko",
    "hololive",
    "nijisanji",
    "vshojo",
    "indie",
    "vtuber",
}


def _trim_franchise_tail(fran: str) -> str:
    """Trim scene-description tokens from the end of a captured franchise.

    The regex greedily grabs up to 5 words, but real franchise names
    rarely exceed 3-4. Cut at the first token that doesn't look like
    part of a proper-noun franchise name.
    """
    tokens = fran.split()
    if not tokens:
        return ""
    keep: list[str] = []
    for tok in tokens:
        tl = tok.lower().strip(".,;:!?")
        # Keep capitalised tokens, or known franchise vocabulary, or
        # short ALL-CAPS abbreviations (HSR, GI, FGO).
        if (
            tok[:1].isupper()
            or tl in _KNOWN_FRANCHISE_HEADS
            or (tok.isupper() and 2 <= len(tok) <= 5)
        ):
            keep.append(tok)
            continue
        break
    return " ".join(keep) if keep else tokens[0]
