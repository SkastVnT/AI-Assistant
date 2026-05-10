"""Character registry — searchable, alias-aware character database.

Loads JSON seed data from ``storage/character_db/`` and exposes a thread-safe
singleton with search, series filtering, and alias resolution.

Additive layer on top of ``image_pipeline/anime_pipeline/character_parser`` —
does not replace the existing parser. When the registry resolves a query
explicitly (by key or alias), it returns a fully-qualified identity that the
anime pipeline can use directly, bypassing the heuristic parser.
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Repo root is 3 levels up from this file: services/chatbot/core/character_registry.py
_REPO_ROOT = Path(__file__).resolve().parents[3]
_CHAR_DB_DIR = _REPO_ROOT / "storage" / "character_db"
_CHARACTERS_FILE = _CHAR_DB_DIR / "characters.json"
_SERIES_ALIASES_FILE = _CHAR_DB_DIR / "series_aliases.json"


@dataclass
class CharacterRecord:
    key: str
    display_name: str
    series: str
    series_key: str
    character_tag: str
    series_tag: str
    aliases: list[str] = field(default_factory=list)
    thumbnail: Optional[str] = None
    lora_hint: Optional[str] = None
    solo_recommended: bool = True
    category: str = "character"

    def to_dict(self) -> dict:
        return asdict(self)


class CharacterRegistry:
    """Thread-safe singleton character registry.

    Use ``CharacterRegistry.get_instance()`` to access the shared registry.
    """

    _instance: Optional["CharacterRegistry"] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._records: dict[str, CharacterRecord] = {}
        self._series_aliases: dict[str, str] = {}
        self._load_lock = threading.Lock()
        self._loaded = False

    @classmethod
    def get_instance(cls) -> "CharacterRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
                cls._instance.load()
            return cls._instance

    def load(self) -> None:
        """Load JSON data from disk. Safe to call multiple times."""
        with self._load_lock:
            self._records = {}
            self._series_aliases = {}
            if _CHARACTERS_FILE.exists():
                try:
                    raw = json.loads(_CHARACTERS_FILE.read_text(encoding="utf-8"))
                    for key, payload in raw.items():
                        try:
                            payload.setdefault("key", key)
                            self._records[key] = CharacterRecord(**payload)
                        except TypeError as exc:
                            logger.warning("character_registry: skip %s — %s", key, exc)
                except Exception as exc:
                    logger.error("character_registry: failed to load characters.json: %s", exc)
            else:
                logger.warning("character_registry: %s missing", _CHARACTERS_FILE)
            if _SERIES_ALIASES_FILE.exists():
                try:
                    self._series_aliases = json.loads(_SERIES_ALIASES_FILE.read_text(encoding="utf-8"))
                except Exception as exc:
                    logger.error("character_registry: failed to load series_aliases.json: %s", exc)
            self._loaded = True
            logger.info("character_registry: loaded %d characters, %d series aliases",
                        len(self._records), len(self._series_aliases))

    def reload(self) -> None:
        self.load()

    # --- queries -------------------------------------------------------

    def get(self, key: str) -> Optional[CharacterRecord]:
        return self._records.get(key)

    def list_all(self) -> list[CharacterRecord]:
        return list(self._records.values())

    def list_series(self) -> list[dict]:
        seen: dict[str, str] = {}
        for rec in self._records.values():
            seen.setdefault(rec.series_key, rec.series)
        return [{"key": k, "name": v} for k, v in sorted(seen.items())]

    def normalize_series(self, raw: str) -> Optional[str]:
        """Resolve a series alias (e.g. ``GI``) to canonical series_key."""
        if not raw:
            return None
        raw_strip = raw.strip()
        if raw_strip in self._series_aliases:
            return self._series_aliases[raw_strip]
        # Case-insensitive fallback
        raw_lower = raw_strip.lower()
        for alias, canonical in self._series_aliases.items():
            if alias.lower() == raw_lower:
                return canonical
        # Maybe already a canonical key
        for rec in self._records.values():
            if rec.series_key == raw_lower:
                return rec.series_key
        return None

    def find(
        self,
        query: str = "",
        series_filter: Optional[str] = None,
        limit: int = 50,
    ) -> list[CharacterRecord]:
        """Search by display_name / aliases / character_tag.

        ``series_filter`` accepts a canonical series_key OR a known alias
        (resolved via ``normalize_series``).
        """
        q = (query or "").strip().lower()
        series_key = None
        if series_filter:
            series_key = self.normalize_series(series_filter) or series_filter.strip().lower()

        results: list[CharacterRecord] = []
        for rec in self._records.values():
            if series_key and rec.series_key != series_key:
                continue
            if q:
                hay = [rec.display_name.lower(), rec.character_tag.lower(),
                       rec.series.lower(), rec.key.lower()]
                hay.extend(a.lower() for a in rec.aliases)
                if not any(q in h for h in hay):
                    continue
            results.append(rec)
            if len(results) >= limit:
                break
        return results

    def resolve_query(self, query: str) -> Optional[CharacterRecord]:
        """Best-effort single-record resolution for an explicit query.

        Tries: exact key → exact display_name (case-insensitive) → alias →
        partial display_name match. Returns the first hit.
        """
        if not query:
            return None
        q = query.strip()
        if q in self._records:
            return self._records[q]
        q_lower = q.lower()
        for rec in self._records.values():
            if rec.display_name.lower() == q_lower:
                return rec
            if any(a.lower() == q_lower for a in rec.aliases):
                return rec
            if rec.character_tag.lower() == q_lower:
                return rec
        # Partial fallback
        for rec in self._records.values():
            if q_lower in rec.display_name.lower():
                return rec
        return None

    def detect_collisions(self, display_name: str) -> list[CharacterRecord]:
        """Return all records sharing the same display_name across series.

        Useful for the picker UI to warn the user when a name like ``Rem``
        exists in multiple games. Empty list = no collision.
        """
        if not display_name:
            return []
        target = display_name.strip().lower()
        return [r for r in self._records.values() if r.display_name.lower() == target]


def get_registry() -> CharacterRegistry:
    """Module-level convenience accessor."""
    return CharacterRegistry.get_instance()


# ── Thumbnail resolution ────────────────────────────────────────────────
_CHAR_REFS_DIR = _REPO_ROOT / "storage" / "character_refs"
_IMAGE_EXTS = {".webp", ".png", ".jpg", ".jpeg", ".gif"}


def _normalize_token(s: str) -> str:
    """Lowercase + strip punctuation so dirnames and tags can be compared
    loosely (``hu_tao_(genshin_impact)`` ↔ ``hu_tao_genshin_impact``)."""
    out = []
    for ch in (s or "").lower():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "_", "-"):
            out.append("_")
        # drop everything else (parens, colons, etc.)
    return "".join(out).strip("_")


def resolve_thumbnail_data_url(rec: CharacterRecord) -> Optional[str]:
    """Try the SAA WAI character DB for a base64 data-URL thumbnail.

    Used as a fallback when no on-disk image is found in
    ``storage/character_refs/``. The WAI DB ships ~5000 SDXL character
    thumbnails keyed by their tag (with spaces). We try several spellings
    derived from the registry record: the SDXL ``character_tag``, a
    ``"name (series)"`` form built from the tags, and the lowercase
    display name. Returns ``None`` when SAA is unavailable or no match.
    """
    if rec is None:
        return None
    try:
        from image_pipeline.anime_pipeline.saa_character_db import (
            get_character_thumbnail,
        )
    except Exception:
        return None
    candidates: list[str] = []
    if rec.character_tag:
        candidates.append(rec.character_tag.replace("_", " "))
    if rec.character_tag and rec.series_tag:
        candidates.append(
            f"{rec.character_tag} ({rec.series_tag})".replace("_", " ")
        )
    if rec.display_name and rec.series:
        candidates.append(f"{rec.display_name} ({rec.series})".lower())
    if rec.display_name:
        candidates.append(rec.display_name.lower())
    seen: set[str] = set()
    for tag in candidates:
        norm = tag.strip()
        if not norm or norm in seen:
            continue
        seen.add(norm)
        try:
            data_url = get_character_thumbnail(norm)
        except Exception:
            continue
        if data_url and data_url.startswith("data:"):
            return data_url
    return None


def resolve_thumbnail_path(rec: CharacterRecord) -> Optional[Path]:
    """Resolve a usable on-disk thumbnail for ``rec``.

    Priority:
        1. ``rec.thumbnail`` if the file exists.
        2. First image found inside any ``storage/character_refs/<dir>``
           whose normalized name matches ``character_tag`` or ``key``.

    Returns an absolute :class:`Path` under the repo root, or ``None`` when
    no candidate is found. Caller is responsible for serving the file.
    """
    if rec is None:
        return None
    # 1) Direct path from registry data.
    if rec.thumbnail:
        direct = (_REPO_ROOT / rec.thumbnail).resolve()
        try:
            direct.relative_to(_REPO_ROOT)
        except ValueError:
            return None
        if direct.is_file():
            return direct
    # 2) Fallback — scan storage/character_refs for a matching dir.
    if not _CHAR_REFS_DIR.is_dir():
        return None
    candidates = {_normalize_token(rec.character_tag), _normalize_token(rec.key)}
    candidates.discard("")
    for sub in _CHAR_REFS_DIR.iterdir():
        if not sub.is_dir():
            continue
        norm = _normalize_token(sub.name)
        if norm in candidates or any(norm.startswith(c) for c in candidates):
            for f in sorted(sub.iterdir()):
                if f.is_file() and f.suffix.lower() in _IMAGE_EXTS:
                    return f.resolve()
    return None


__all__ = [
    "CharacterRegistry",
    "CharacterRecord",
    "get_registry",
    "resolve_thumbnail_path",
    "resolve_thumbnail_data_url",
]
