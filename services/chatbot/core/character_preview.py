"""Compact character preview builder.

Pure helper used by ``GET /api/characters/preview`` and the frontend
character chip. **No network calls, no file writes, no GPU.** The function
only reads the local registry, the SAA offline thumbnail map, the manual
override file, and the on-disk preview cache. Missing sources are silent.

Documented priority (see docs/CHARACTER_PROFILE_FALLBACK.md):
    1. ``selected_character.thumbnail``
    2. ``manual_profile.reference_images[0]``
    3. ``character_overrides.json`` ``reference_images[0]``
    4. SAA thumbnail (offline DB)
    5. Local cache (``services/chatbot/static/cache/character_previews/``)
    6. Inline SVG placeholder
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Inline SVG so no static asset is required.
PLACEHOLDER_URL = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='48' height='48'>"
    "<rect width='48' height='48' fill='%231f2128'/>"
    "<text x='24' y='31' text-anchor='middle' fill='%23999' "
    "font-size='22' font-family='sans-serif'>?</text></svg>"
)

_CHATBOT_DIR = Path(__file__).resolve().parent.parent
_LOCAL_CACHE_DIR = _CHATBOT_DIR / "static" / "cache" / "character_previews"
_OVERRIDES_PATH = _CHATBOT_DIR / "config" / "character_overrides.json"

# Only allow safe filename characters to prevent path traversal.
_SAFE_KEY_RE = re.compile(r"[^A-Za-z0-9_\-]")
_STRICT_SAFE_KEY_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def _sanitize_for_log(value: str) -> str:
    """Remove line breaks from untrusted strings before logging."""
    return (value or "").replace("\r", "").replace("\n", "")


def _safe_key(key: str) -> str:
    """Sanitize a registry key so it is safe to use as a filename component.

    Returns an empty string if the key is empty or becomes empty after
    sanitization (e.g. all-symbol input). Callers must guard against empty
    return values before constructing paths.
    """
    return _SAFE_KEY_RE.sub("_", key)


def _is_strict_safe_key(key: str) -> bool:
    """Return True only for canonical cache key filename components."""
    return bool(key and _STRICT_SAFE_KEY_RE.fullmatch(key))


@dataclass
class CharacterPreview:
    """Shape returned by ``build_preview`` and ``GET /api/characters/preview``."""

    preview_url: str = PLACEHOLDER_URL
    preview_source: str = "placeholder"  # saa_thumbnail | manual_profile | local_cache | external_cached | placeholder
    source_url: Optional[str] = None
    display_name: str = ""
    canonical_id: Optional[str] = None
    provisional_id: Optional[str] = None
    series_name: str = ""
    series_slug: str = ""
    source: str = ""  # registry | saa | manual_override | selected | unknown
    safe_to_attach_lora: bool = False
    needs_review: bool = False
    confidence: float = 0.0
    tooltip_lines: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def build_preview(
    *,
    key: str = "",
    query: str = "",
    selected_character: Optional[dict] = None,
    manual_profile: Optional[dict] = None,
) -> CharacterPreview:
    """Build a CharacterPreview using the documented priority chain.

    Pure: never raises, never writes, never blocks on network. A missing
    or malformed registry / overrides file degrades to a placeholder.
    """
    p = CharacterPreview()
    _fill_metadata(p, key=key, selected_character=selected_character)

    # Priority 1: selected_character.thumbnail
    if selected_character and selected_character.get("thumbnail"):
        url = str(selected_character["thumbnail"])
        p.preview_url = url
        p.preview_source = (
            "saa_thumbnail" if url.startswith("/api/") or "thumbnail" in url else "manual_profile"
        )
        return _finalize(p, query=query)

    # Priority 2: manual_profile.reference_images[0]
    if manual_profile and isinstance(manual_profile.get("reference_images"), list):
        refs = manual_profile["reference_images"]
        if refs:
            p.preview_url = str(refs[0])
            p.preview_source = "manual_profile"
            p.source = p.source or "manual_override"
            p.needs_review = bool(manual_profile.get("needs_review", True))
            return _finalize(p, query=query)

    # Priority 3: character_overrides reference_images[0] + metadata
    override = _lookup_override(key=key, query=query)
    if override:
        _merge_override(p, override)
        refs = override.get("reference_images") or []
        if isinstance(refs, list) and refs:
            p.preview_url = str(refs[0])
            p.preview_source = "manual_profile"
            return _finalize(p, query=query)

    # Priority 4: SAA thumbnail
    if key:
        saa_url = _saa_thumbnail_url(key)
        if saa_url:
            p.preview_url = saa_url
            p.preview_source = "saa_thumbnail"
            return _finalize(p, query=query)

    # Priority 5: local cached preview
    if key:
        cached = _local_cached_url(key)
        if cached:
            p.preview_url = cached
            p.preview_source = "local_cache"
            return _finalize(p, query=query)

    # Priority 6: placeholder
    if not p.display_name and query:
        p.display_name = query
    if not p.canonical_id:
        slug = (key or query or "unknown").strip().lower().replace(" ", "_")
        p.provisional_id = f"unknown:{slug}"
        p.source = p.source or "unknown"
        p.needs_review = True
        p.warnings.append(
            "No preview image. Add a manual override or pick a known character."
        )
    return _finalize(p, query=query)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fill_metadata(
    p: CharacterPreview,
    *,
    key: str,
    selected_character: Optional[dict],
) -> None:
    """Populate identity fields from the registry (if hit) or selected payload."""
    rec = None
    if key:
        try:
            from core.character_registry import get_registry  # local import — avoid load on import
            rec = get_registry().get(key)
        except Exception as exc:  # pragma: no cover — defensive
            logger.debug("[character_preview] registry lookup failed: %s", exc)

    if rec is not None:
        p.display_name = rec.display_name
        p.series_name = rec.series
        p.series_slug = rec.series_key or ""
        p.canonical_id = f"{rec.character_tag or rec.key}@{rec.series_key or 'unknown'}"
        p.source = "registry"
        p.confidence = 1.0
        p.safe_to_attach_lora = bool(rec.lora_hint)
        return

    if selected_character:
        p.display_name = (
            selected_character.get("display_name")
            or selected_character.get("name")
            or ""
        )
        p.series_name = selected_character.get("series", "") or ""
        p.series_slug = (
            selected_character.get("series_key")
            or selected_character.get("series_slug")
            or ""
        )
        p.canonical_id = selected_character.get("canonical_id") or (
            f"{selected_character.get('character_tag', selected_character.get('key', 'unknown'))}"
            f"@{p.series_slug or 'unknown'}"
        )
        p.source = "selected"
        p.confidence = 0.95
        p.safe_to_attach_lora = bool(selected_character.get("lora_hint"))


def _merge_override(p: CharacterPreview, entry: dict) -> None:
    p.display_name = p.display_name or entry.get("display_name", "")
    p.series_name = p.series_name or entry.get("series_name") or entry.get("series", "")
    p.series_slug = p.series_slug or entry.get("series_slug", "")
    p.canonical_id = p.canonical_id or entry.get("canonical_id")
    p.source = "manual_override"
    p.needs_review = bool(entry.get("needs_review", True))
    p.confidence = float(entry.get("confidence", 0.75) or 0.75)
    p.safe_to_attach_lora = bool(
        entry.get("lora_hint") and entry.get("safe_to_attach_lora", False)
    )


def _lookup_override(*, key: str = "", query: str = "") -> Optional[dict]:
    """Find a matching entry in character_overrides.json. Fail-safe."""
    if not _OVERRIDES_PATH.exists():
        return None
    try:
        import json
        data = json.loads(_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.debug("[character_preview] overrides load failed: %s", exc)
        return None
    chars = data.get("characters") if isinstance(data, dict) else None
    if not isinstance(chars, list):
        return None
    needle = (key or query or "").strip().lower()
    if not needle:
        return None
    for entry in chars:
        if not isinstance(entry, dict):
            continue
        cands = {
            (entry.get("canonical_id") or "").lower(),
            (entry.get("character_slug") or "").lower(),
            (entry.get("display_name") or "").lower(),
        }
        cands.update(str(a).lower() for a in (entry.get("aliases") or []) if a)
        cands.discard("")
        if needle in cands:
            return entry
    return None


def _saa_thumbnail_url(key: str) -> Optional[str]:
    """Return the chatbot-served thumbnail URL if SAA has data for this key."""
    safe = _safe_key(key)
    if not safe:
        return None
    try:
        from image_pipeline.anime_pipeline.saa_character_db import get_character_thumbnail
        tag = safe.replace("_", " ")
        data_url = get_character_thumbnail(tag)
        if data_url and data_url.startswith("data:"):
            # Reuse the existing thumbnail route which decodes the data URL.
            return f"/api/characters/{safe}/thumbnail"
    except Exception:  # pragma: no cover — image_pipeline optional
        return None
    return None


_ALLOWED_PREVIEW_EXTS = frozenset({".png", ".jpg", ".jpeg", ".webp"})


def _local_cached_url(key: str) -> Optional[str]:
    """Return a static URL if a manually-dropped preview exists on disk.

    Iterates the cache directory rather than constructing a path from user
    data, so no user-controlled value flows into a filesystem path expression.
    The directory is a hand-curated preview cache (expected O(hundreds) of
    files at most), so a linear scan is acceptable.
    """
    safe = _safe_key(key)
    if not _is_strict_safe_key(safe):
        return None
    try:
        for candidate in _LOCAL_CACHE_DIR.iterdir():
            if (candidate.suffix.lower() in _ALLOWED_PREVIEW_EXTS
                    and candidate.stem == safe):
                return f"/static/cache/character_previews/{safe}{candidate.suffix.lower()}"
    except Exception:  # pragma: no cover — defensive
        return None
    return None


def _finalize(p: CharacterPreview, *, query: str) -> CharacterPreview:
    if not p.display_name and query:
        p.display_name = query
    lines: list[str] = []
    if p.display_name:
        lines.append(p.display_name)
    if p.series_name:
        lines.append(f"Series: {p.series_name}")
    ident = p.canonical_id or p.provisional_id
    if ident:
        lines.append(f"ID: {ident}")
    if p.source:
        lines.append(f"Source: {p.source}")
    lines.append(f"Confidence: {p.confidence:.2f}")
    lines.append(f"safe_to_attach_lora: {str(p.safe_to_attach_lora).lower()}")
    if p.needs_review:
        lines.append("⚠ Needs review")
    p.tooltip_lines = lines
    return p


__all__ = ["CharacterPreview", "build_preview", "PLACEHOLDER_URL"]
