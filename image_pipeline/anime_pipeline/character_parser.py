"""
character_parser.py - Preposition-aware character identity parser.

Converts free-form user prompts ("Raiden Shogun trong Genshin Impact",
"Kafka from Honkai Star Rail", "Rem of Re:Zero", "Hu Tao của Genshin")
into a structured ``ParsedIdentity`` with:

  * character_name / series_name / character_tag / series_tag
  * alias_source   (explicit_pattern | series_hint | alias_only | none)
  * solo_intent    (bool — user asked for exactly one character)
  * collision_blocks (negative-prompt fragments to suppress homonyms)

The parser is the single source of truth for character identification in
the anime pipeline. ``character_research.detect_character`` delegates to
``parse_character_identity`` so every caller sees the same answer.

Deterministic. No network calls. Safe to use in hot paths.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# Reuse the alias/series tables already maintained in character_research.
# Private imports are intentional — the parser is the dictionaries'
# authoritative consumer and keeps ownership in character_research.
from .character_research import _CHARACTER_ALIASES, _SERIES_HINTS


# ── Preposition tokens ──────────────────────────────────────────────────
# Vietnamese + English. Order matters only for regex compile determinism.
# Word prepositions: require \b boundaries. Slash separator handled
# separately because it has no word boundary semantics.
_PREP_WORDS: tuple[str, ...] = (
    "from", "of", "in", "at",            # English
    "trong", "của", "tại",               # Vietnamese
)
_PREP_PATTERN = re.compile(
    r"(?:\b(?:" + "|".join(re.escape(p) for p in _PREP_WORDS) + r")\b|\s*/\s*)",
    re.IGNORECASE,
)

# Max characters between preposition and series hint for "explicit pair"
# to count. Keeps "Kafka from Honkai Star Rail at the station" matching,
# but rejects matches where the hint is much later in a long prompt.
_EXPLICIT_PAIR_WINDOW = 96

# ── Solo-intent signals ────────────────────────────────────────────────
_SOLO_POSITIVE: tuple[str, ...] = (
    "solo",
    "1girl",
    "1boy",
    "alone",
    "by herself",
    "by himself",
    "only one character",
    "a single character",
    "one character",
    "một nhân vật",
    "một cô gái",
    "một chàng trai",
    "chỉ một",
)
_SOLO_NEGATIVE: tuple[str, ...] = (
    "2girls",
    "2boys",
    "3girls",
    "3boys",
    "multiple girls",
    "multiple boys",
    "group of",
    "duo",
    "trio",
    "pair of",
    "crowd",
    "cùng với",
    "và cùng",
    "nhóm ",
)

# ── Off-domain homonym suppressors ─────────────────────────────────────
# When the user types just a bare name that collides with a well-known
# non-anime referent, add targeted negatives to suppress it. Keep this
# table conservative and deterministic — no internet fetch.
_OFF_DOMAIN_HOMONYMS: dict[str, tuple[str, ...]] = {
    "kafka": ("franz kafka", "realistic photograph", "monochrome photograph"),
}


# ══════════════════════════════════════════════════════════════════════
# Public contract
# ══════════════════════════════════════════════════════════════════════

@dataclass
class ParsedIdentity:
    """Structured character identity parsed from a user prompt."""

    character_name: str = ""
    series_name: str = ""
    character_tag: str = ""
    series_tag: str = ""
    # How the identity was resolved:
    #   explicit_pattern — user wrote "X {from|of|in|trong|của} Y"
    #   series_hint      — series keyword appeared elsewhere in the prompt
    #   alias_only       — only a character alias matched (lowest confidence)
    #   none             — nothing matched
    alias_source: str = "none"
    solo_intent: bool = False
    # Negative-prompt fragments to block collisions (homonyms + multi-char
    # bleed when solo_intent is set).
    collision_blocks: list[str] = field(default_factory=list)
    # True when the user-supplied alias maps to multiple distinct
    # characters in our registry and no series hint was provided.
    homonym_collision: bool = False
    # All candidate (tag, series_tag, display_name, series_name) tuples
    # that matched, for audit/debug. Order: longest alias first.
    candidates: list[tuple[str, str, str, str]] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return bool(self.character_tag)

    def to_dict(self) -> dict:
        return {
            "character_name": self.character_name,
            "series_name": self.series_name,
            "character_tag": self.character_tag,
            "series_tag": self.series_tag,
            "alias_source": self.alias_source,
            "solo_intent": self.solo_intent,
            "collision_blocks": list(self.collision_blocks),
            "homonym_collision": self.homonym_collision,
            "candidates": list(self.candidates),
        }


def parse_character_identity(user_prompt: str) -> ParsedIdentity:
    """Parse ``user_prompt`` into a structured :class:`ParsedIdentity`.

    Resolution order:
      1. Explicit preposition pair ("X from/of/in/trong/của Y").
      2. Series-hint disambiguation (series keyword anywhere in prompt).
      3. Longest-alias single match.

    Always returns an object. ``resolved`` is False when no alias matched.
    Always populates ``solo_intent``, independent of character resolution.
    """
    result = ParsedIdentity()
    if not user_prompt:
        return result

    lower = user_prompt.lower()
    result.solo_intent = _detect_solo_intent(lower)

    alias_matches = _find_alias_matches(lower)
    if not alias_matches:
        # Fallback to the SAA 5149-char verified database before giving up.
        # This covers the long tail (Lynx, Castorice, Anaxa, ...) that the
        # hand-maintained _CHARACTER_ALIASES table does not list.
        saa_hit = _resolve_via_saa(user_prompt)
        if saa_hit is not None:
            _assign(result, saa_hit, source="saa_wai_db")
        # No character found — still emit solo-based negatives so that a
        # prompt like "one anime girl" still suppresses crowds.
        _fill_collision_blocks(result, alias_matches)
        return result

    # Record candidates (unique by character tag).
    seen_tags: set[str] = set()
    for _alias, info in alias_matches:
        if info[0] not in seen_tags:
            result.candidates.append(info)
            seen_tags.add(info[0])

    # ── Step 1: explicit preposition pair ─────────────────────────────
    explicit = _find_explicit_pair(lower, alias_matches)
    if explicit is not None:
        _assign(result, explicit, source="explicit_pattern")
        _fill_collision_blocks(result, alias_matches)
        return result

    # ── Step 2: series hint disambiguation ────────────────────────────
    series_hint = _detect_series_hint(lower)
    if series_hint:
        for _alias, info in alias_matches:
            if info[1] == series_hint:
                _assign(result, info, source="series_hint")
                _fill_collision_blocks(result, alias_matches)
                return result

    # ── Step 3: fallback to first (longest alias) match ───────────────
    _alias, info = alias_matches[0]
    _assign(result, info, source="alias_only")

    # Homonym detection — if multiple *distinct* character tags matched
    # without a series hint, flag collision and let downstream decide.
    distinct_tags = {m_info[0] for _a, m_info in alias_matches}
    if len(distinct_tags) > 1:
        result.homonym_collision = True

    _fill_collision_blocks(result, alias_matches)
    return result


# ══════════════════════════════════════════════════════════════════════
# Internals
# ══════════════════════════════════════════════════════════════════════

def _assign(
    result: ParsedIdentity,
    info: tuple[str, str, str, str],
    *,
    source: str,
) -> None:
    result.character_tag = info[0]
    result.series_tag = info[1]
    result.character_name = info[2]
    result.series_name = info[3]
    result.alias_source = source


def _boundary_pattern(needle: str) -> re.Pattern:
    """Build a word-boundary-ish regex that tolerates spaces inside the
    alias (e.g. "hu tao", "raiden shogun") but refuses hits that sit
    inside a larger alphanumeric token (e.g. "ram" inside "framework").
    """
    escaped = re.escape(needle)
    return re.compile(r"(?<![a-z0-9])" + escaped + r"(?![a-z0-9])")


def _find_alias_matches(
    lower: str,
) -> list[tuple[str, tuple[str, str, str, str]]]:
    """Return character alias hits ordered by alias length desc."""
    out: list[tuple[str, tuple[str, str, str, str]]] = []
    for alias in sorted(_CHARACTER_ALIASES.keys(), key=len, reverse=True):
        if _boundary_pattern(alias).search(lower):
            out.append((alias, _CHARACTER_ALIASES[alias]))
    return out


def _detect_series_hint(lower: str) -> Optional[str]:
    """Return the canonical series_tag for the longest matching hint."""
    for hint in sorted(_SERIES_HINTS.keys(), key=len, reverse=True):
        if _boundary_pattern(hint).search(lower):
            return _SERIES_HINTS[hint]
    return None


def _find_explicit_pair(
    lower: str,
    alias_matches: list[tuple[str, tuple[str, str, str, str]]],
) -> Optional[tuple[str, str, str, str]]:
    """Look for ``<alias> <prep> <series-hint>`` within a small window.

    Returns the matching character-info tuple only when both the alias
    and a series hint belonging to the *same* series appear in order
    with a preposition between them.
    """
    if not _PREP_PATTERN.search(lower):
        return None

    for alias, info in alias_matches:
        alias_match = _boundary_pattern(alias).search(lower)
        if not alias_match:
            continue
        tail = lower[alias_match.end():]
        prep_match = _PREP_PATTERN.search(tail)
        if not prep_match:
            continue
        window = tail[prep_match.end(): prep_match.end() + _EXPLICIT_PAIR_WINDOW]
        # Look for any series hint inside the window.
        for hint in sorted(_SERIES_HINTS.keys(), key=len, reverse=True):
            if _SERIES_HINTS[hint] != info[1]:
                continue
            if _boundary_pattern(hint).search(window):
                return info
    return None


def _detect_solo_intent(lower: str) -> bool:
    """Return True when the user asked for exactly one character."""
    for neg in _SOLO_NEGATIVE:
        if neg in lower:
            return False
    for pos in _SOLO_POSITIVE:
        # pos may contain spaces — use substring check with trimmed edges.
        if pos in lower:
            return True
    return False


def _fill_collision_blocks(
    result: ParsedIdentity,
    alias_matches: list[tuple[str, tuple[str, str, str, str]]],
) -> None:
    """Populate ``result.collision_blocks`` from:
      * off-domain homonyms (Kafka → writer, ...)
      * other alias matches that resolve to different characters
      * solo-intent multi-subject negatives
    """
    blocks: list[str] = []

    # Off-domain homonyms — keyed by alias that matched. Only the aliases
    # that literally map to the resolved character deserve suppression.
    for alias, info in alias_matches:
        if info[0] == result.character_tag and alias in _OFF_DOMAIN_HOMONYMS:
            blocks.extend(_OFF_DOMAIN_HOMONYMS[alias])

    # On-domain homonyms — when multiple distinct characters matched the
    # prompt, suppress the LOSING candidates by display name.
    if result.character_tag:
        for _alias, info in alias_matches:
            if info[0] != result.character_tag:
                blocks.append(info[2])  # losing character's display name

    # Solo-intent multi-subject negatives.
    if result.solo_intent:
        blocks.extend([
            "2girls",
            "2boys",
            "multiple girls",
            "multiple boys",
            "group of people",
            "crowd",
            "duo",
        ])

    # Deduplicate, case-insensitive, preserving first-seen order.
    seen: set[str] = set()
    unique: list[str] = []
    for raw in blocks:
        if not raw:
            continue
        key = raw.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(raw.strip())
    result.collision_blocks = unique


__all__ = ["ParsedIdentity", "parse_character_identity"]


# ══════════════════════════════════════════════════════════════════════
# SAA (Character Select Stand-Alone App) fallback
# ══════════════════════════════════════════════════════════════════════

def _resolve_via_saa(user_prompt: str) -> Optional[tuple[str, str, str, str]]:
    """Resolve a character via the SAA wai_characters.csv database.

    Returns ``(danbooru_tag, series_tag, display_name, series_name)`` or
    ``None``. The SAA DB holds 5149 characters verified against
    waiIllustriousSDXL, which is much larger than the hand-curated
    ``_CHARACTER_ALIASES`` table. Kept as a last-resort fallback because
    the hand-curated table also knows about series hints and display
    aliases that the CSV does not encode.

    Fails closed on any import / lookup error so the main parser never
    regresses to a crash when the SAA folder is missing.
    """
    try:
        from .saa_character_db import lookup_character
    except Exception:
        return None

    # Strip common prompt noise ("tạo ảnh", "draw", "make a picture of") so
    # the CSV lookup sees just the likely subject phrase.
    cleaned = user_prompt
    for junk in ("tạo ảnh", "vẽ", "draw", "generate", "make a picture of",
                 "picture of", "image of"):
        cleaned = re.sub(rf"\b{re.escape(junk)}\b", " ", cleaned, flags=re.I)

    try:
        hit = lookup_character(cleaned)
    except Exception:
        return None
    if hit is None or hit.match_score < 0.5:
        return None

    # Map SAA fields to the (tag, series_tag, display, series_name) tuple
    # shape the pipeline expects.
    series_tag = (hit.series_hint or "").replace(" ", "_").lower() or "unknown"
    series_name = hit.series_hint or "Unknown"
    display = hit.display_name or hit.tag.title()
    return (hit.danbooru_tag, series_tag, display, series_name)
