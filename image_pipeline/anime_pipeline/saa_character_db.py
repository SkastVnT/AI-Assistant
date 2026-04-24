"""
saa_character_db.py - Offline lookup over the Character Select SAA dataset.

Backs the anime pipeline with the ``wai_characters.csv`` (5149 entries, verified
on ``waiIllustriousSDXL_v160``) and ``danbooru_e621_merged.csv`` shipped with
the Character Select Stand-Alone App. All I/O happens once per process: the
CSVs are memory-mapped at module import and then served by in-memory indexes.

Public API
----------
* ``lookup_character(query)`` — match a free-text fragment (e.g. "yae miko",
  "Tokisaki Kurumi") against the 5149 verified WAI characters. Returns a
  :class:`WaiCharacterMatch` or ``None``.
* ``autocomplete_tag(prefix, limit=20)`` — prefix search against the
  danbooru/e621 tag vocabulary for the prompt-input autocomplete UI.
* ``get_character_thumbnail(tag)`` — returns the base64-encoded thumbnail URL
  for a WAI character tag, or ``None`` if unknown.

The module is tolerant: if the SAA folder is missing, every function
returns an empty result and the rest of the pipeline keeps working.
"""

from __future__ import annotations

import csv
import json
import logging
import random
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────
# character_research.py lives two levels below the repo root, same as us.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SAA_DATA = _REPO_ROOT / "character_select_stand_alone_app-main" / "data"
_WAI_CSV = _SAA_DATA / "wai_characters.csv"
_WAI_THUMBS = _SAA_DATA / "wai_character_thumbs.json"
_TAG_CSV = _SAA_DATA / "danbooru_e621_merged.csv"


# ── Data classes ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class WaiCharacterMatch:
    """A character hit from the SAA 5149-char verified database."""
    display_name: str           # Chinese/localized display
    tag: str                    # SDXL prompt tag (spaces, e.g. "yae miko")
    danbooru_tag: str           # underscore form for danbooru/web lookup
    series_hint: Optional[str]  # parenthesized series if present
    match_score: float          # 0-1 (1 = exact)


@dataclass(frozen=True)
class TagAutocomplete:
    tag: str                    # canonical tag
    category: int               # 0=general 1=artist 3=copyright 4=character 5=meta
    post_count: int
    aliases: tuple[str, ...]


# ── Lazy state ───────────────────────────────────────────────────────
_lock = threading.Lock()
_wai_index: Optional[dict[str, tuple[str, str]]] = None   # lookup_key -> (display, tag)
_wai_tags: list[tuple[str, str]] = []                      # (lookup_key, tag)
_thumbs: Optional[dict[str, str]] = None
_tag_list: Optional[list[TagAutocomplete]] = None
_tag_prefix_index: Optional[dict[str, list[int]]] = None   # first3char -> indices

# Regex for series-in-parentheses extraction
_PAREN_RE = re.compile(r"\s*\(([^)]+)\)\s*$")


# ── WAI character loader ─────────────────────────────────────────────

def _normalise_key(s: str) -> str:
    """Lowercase, strip punctuation/underscores, collapse whitespace."""
    s = s.lower().strip()
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"[()',:.!?]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _load_wai() -> None:
    global _wai_index, _wai_tags, _thumbs
    if _wai_index is not None:
        return
    with _lock:
        if _wai_index is not None:
            return
        index: dict[str, tuple[str, str]] = {}
        all_tags: list[tuple[str, str]] = []
        if not _WAI_CSV.exists():
            logger.info("[SAA-DB] wai_characters.csv not found at %s — offline lookup disabled.", _WAI_CSV)
            _wai_index = index
            _wai_tags = all_tags
            _thumbs = {}
            return
        try:
            with _WAI_CSV.open("r", encoding="utf-8", newline="") as f:
                rdr = csv.reader(f)
                for row in rdr:
                    if len(row) < 2:
                        continue
                    display = row[0].strip()
                    tag = row[1].strip()
                    if not tag:
                        continue
                    key_tag = _normalise_key(tag)
                    key_disp = _normalise_key(display)
                    # Also stash a variant without the (series) suffix
                    bare = _PAREN_RE.sub("", tag).strip()
                    key_bare = _normalise_key(bare)
                    entry = (display, tag)
                    for k in {key_tag, key_disp, key_bare}:
                        if k and k not in index:
                            index[k] = entry
                    all_tags.append((key_tag, tag))
        except Exception as e:
            logger.warning("[SAA-DB] failed to parse wai_characters.csv: %s", e)
        logger.info("[SAA-DB] loaded %d WAI character entries (%d index keys).",
                    len(all_tags), len(index))
        _wai_index = index
        _wai_tags = all_tags

        # Thumbnails (optional, large JSON)
        thumbs: dict[str, str] = {}
        if _WAI_THUMBS.exists():
            try:
                thumbs = json.loads(_WAI_THUMBS.read_text(encoding="utf-8")) or {}
                logger.info("[SAA-DB] loaded %d character thumbnails.", len(thumbs))
            except Exception as e:
                logger.warning("[SAA-DB] failed to read thumbnails: %s", e)
        _thumbs = thumbs


def lookup_character(query: str) -> Optional[WaiCharacterMatch]:
    """Resolve ``query`` against the 5149-char WAI verified database.

    Tries an exact-key match first, then substring, then longest-alias match.
    Returns ``None`` when nothing plausible is found. Guaranteed to never
    raise and to be fast enough (<5 ms for typical prompts) to call on every
    character-research request.
    """
    if not query:
        return None
    _load_wai()
    assert _wai_index is not None
    key = _normalise_key(query)
    if not key:
        return None

    # 1) exact
    hit = _wai_index.get(key)
    if hit:
        return _to_match(hit, score=1.0)

    # 2) containment — prefer longer keys (more specific)
    candidates: list[tuple[int, tuple[str, str]]] = []
    for k, v in _wai_index.items():
        if k in key or key in k:
            candidates.append((len(k), v))
    if candidates:
        candidates.sort(key=lambda x: -x[0])
        best_len, best = candidates[0]
        # Score shrinks as the overlap shrinks.
        score = min(1.0, best_len / max(len(key), best_len))
        return _to_match(best, score=score * 0.9)

    return None


def _to_match(entry: tuple[str, str], score: float) -> WaiCharacterMatch:
    display, tag = entry
    m = _PAREN_RE.search(tag)
    series = m.group(1).strip() if m else None
    danbooru = tag.replace(" ", "_")
    return WaiCharacterMatch(
        display_name=display,
        tag=tag,
        danbooru_tag=danbooru,
        series_hint=series,
        match_score=round(score, 3),
    )


def get_character_thumbnail(tag: str) -> Optional[str]:
    """Return the base64 data URL for a WAI character thumbnail, if any."""
    _load_wai()
    if not _thumbs:
        return None
    return _thumbs.get(tag) or _thumbs.get(tag.replace("_", " "))


# ── Tag autocomplete ─────────────────────────────────────────────────

def _load_tags() -> None:
    global _tag_list, _tag_prefix_index
    if _tag_list is not None:
        return
    with _lock:
        if _tag_list is not None:
            return
        tags: list[TagAutocomplete] = []
        if not _TAG_CSV.exists():
            logger.info("[SAA-DB] danbooru_e621_merged.csv not found — autocomplete disabled.")
            _tag_list = tags
            _tag_prefix_index = {}
            return
        try:
            with _TAG_CSV.open("r", encoding="utf-8", newline="") as f:
                rdr = csv.reader(f)
                for row in rdr:
                    if len(row) < 3:
                        continue
                    tag = row[0].strip()
                    if not tag:
                        continue
                    try:
                        category = int(row[1] or "0")
                    except ValueError:
                        category = 0
                    try:
                        post_count = int(row[2] or "0")
                    except ValueError:
                        post_count = 0
                    aliases_raw = row[3] if len(row) > 3 else ""
                    aliases = tuple(a.strip() for a in aliases_raw.split(",") if a.strip())
                    tags.append(TagAutocomplete(
                        tag=tag, category=category,
                        post_count=post_count, aliases=aliases,
                    ))
        except Exception as e:
            logger.warning("[SAA-DB] failed to parse tag csv: %s", e)

        # Sort by post_count desc so autocomplete returns popular tags first.
        tags.sort(key=lambda t: -t.post_count)

        # Build prefix index: first 3 chars of tag + each alias -> list of tag indices.
        prefix_index: dict[str, list[int]] = {}
        for i, t in enumerate(tags):
            seen_keys: set[str] = set()
            for s in (t.tag, *t.aliases):
                k = _prefix_key(s)
                if k and k not in seen_keys:
                    prefix_index.setdefault(k, []).append(i)
                    seen_keys.add(k)
        _tag_list = tags
        _tag_prefix_index = prefix_index
        logger.info("[SAA-DB] loaded %d tags (%d prefix buckets).",
                    len(tags), len(prefix_index))


def _prefix_key(s: str) -> str:
    s = s.lower().strip().replace(" ", "_")
    return s[:3]


def autocomplete_tag(prefix: str, limit: int = 20) -> list[TagAutocomplete]:
    """Return up to ``limit`` tag suggestions whose canonical name or any
    alias starts with ``prefix`` (case-insensitive). Results are sorted
    by danbooru post_count (descending) because popular tags are almost
    always what the user wants first.
    """
    if not prefix or len(prefix) < 1:
        return []
    _load_tags()
    assert _tag_list is not None and _tag_prefix_index is not None
    norm = prefix.lower().strip().replace(" ", "_")
    if not norm:
        return []

    # Narrow via prefix bucket.
    bucket_key = norm[:3] if len(norm) >= 3 else None
    if bucket_key is None:
        # Very short prefix — scan the top-N most-used tags only to stay fast.
        candidates = _tag_list[:5000]
    else:
        idxs = _tag_prefix_index.get(bucket_key, [])
        candidates = [_tag_list[i] for i in idxs]

    out: list[TagAutocomplete] = []
    for t in candidates:
        if t.tag.lower().startswith(norm):
            out.append(t)
            if len(out) >= limit:
                return out

    # Alias fallback
    if len(out) < limit:
        for t in candidates:
            if t in out:
                continue
            for a in t.aliases:
                if a.lower().startswith(norm):
                    out.append(t)
                    break
            if len(out) >= limit:
                break
    return out[:limit]


def db_stats() -> dict[str, int]:
    """Diagnostic helper for the /api/tags/stats endpoint."""
    _load_wai()
    _load_tags()
    return {
        "wai_characters": len(_wai_tags),
        "wai_thumbs": len(_thumbs or {}),
        "tag_vocabulary": len(_tag_list or []),
    }


# ── Random pick (continuous-generation feature) ──────────────────────


def random_character(
    exclude_tags: Optional[list[str]] = None,
    max_retries: int = 24,
) -> Optional[WaiCharacterMatch]:
    """Pick a random WAI character, avoiding any tag in ``exclude_tags``.

    Used by the chatbot's "Tạo liên tục" loop to rotate the female
    character on every iteration while keeping the rest of the prompt
    intact. Returns ``None`` only when the DB is empty.
    """
    _load_wai()
    if not _wai_tags:
        return None
    excludes = {(t or "").strip().lower() for t in (exclude_tags or [])}
    # Try a few random picks before falling back to a full scan.
    for _ in range(max(1, int(max_retries))):
        key, tag = random.choice(_wai_tags)
        if tag.strip().lower() in excludes:
            continue
        entry = _wai_index.get(key) if _wai_index else None
        if not entry:
            entry = (tag, tag)
        return _to_match(entry, score=1.0)
    # All recent picks collided — scan once for any non-excluded entry.
    for key, tag in _wai_tags:
        if tag.strip().lower() in excludes:
            continue
        entry = (_wai_index or {}).get(key) or (tag, tag)
        return _to_match(entry, score=1.0)
    # Excludes covered the whole DB; just return any character.
    key, tag = random.choice(_wai_tags)
    entry = (_wai_index or {}).get(key) or (tag, tag)
    return _to_match(entry, score=1.0)


def swap_character_in_prompt(
    prompt: str,
    new_match: WaiCharacterMatch,
) -> tuple[str, dict]:
    """Rewrite ``prompt`` so the leading character reference is replaced
    by ``new_match``.

    Heuristic, intentionally simple — the ``character_parser`` module is
    where the production identity resolution lives. This helper exists
    purely to support the continuous-generation loop, which only needs
    "swap the obvious character mention(s) with the new pick".

    Strategy:
      1. If a known WAI character resolves from the prompt, replace every
         occurrence of its tag (and the underscore variant) with the new
         tag.
      2. Always strip a leading ``character: <name>,`` / ``character:
         <name>\n`` prefix and re-insert ``character: <new_tag>,`` so the
         downstream prompt enhancer keeps recognising the lead character.
      3. Return ``(new_prompt, info)`` where ``info`` tells the caller
         what was swapped (useful for the UI banner).
    """
    if not prompt or not new_match:
        return prompt or "", {"replaced": False}

    info: dict = {
        "replaced": False,
        "old_tag": None,
        "new_tag": new_match.tag,
        "new_display": new_match.display_name,
        "new_danbooru": new_match.danbooru_tag,
    }

    text = prompt

    # 1) Resolve the existing character (if any) and swap inline mentions.
    try:
        prev = lookup_character(prompt)
    except Exception:
        prev = None

    if prev and prev.tag:
        info["old_tag"] = prev.tag
        info["old_display"] = prev.display_name
        for variant in {prev.tag, prev.danbooru_tag, prev.tag.replace(" ", "_")}:
            if not variant:
                continue
            pattern = re.compile(re.escape(variant), re.IGNORECASE)
            text = pattern.sub(new_match.tag, text)
        info["replaced"] = True

    # 2) Normalise / inject the leading ``character:`` directive so the
    #    rest of the prompt keeps its structure.
    lead_re = re.compile(r"^\s*character\s*:\s*[^,\n]+\s*([,\n])", re.IGNORECASE)
    if lead_re.search(text):
        text = lead_re.sub(f"character: {new_match.tag}\\1", text, count=1)
        info["replaced"] = True
    else:
        # Prepend a fresh character directive so the new pick actually
        # influences the generation even when the original prompt did
        # not mention any character.
        text = f"character: {new_match.tag}, " + text.lstrip()
        info["replaced"] = True

    return text, info


__all__ = [
    "WaiCharacterMatch",
    "TagAutocomplete",
    "lookup_character",
    "autocomplete_tag",
    "get_character_thumbnail",
    "db_stats",
    "random_character",
    "swap_character_in_prompt",
]
