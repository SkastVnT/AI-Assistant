"""Character Understanding Layer (Phase 1).

A small resolver that turns free-text or UI-payload character references
into a stable canonical identity. Designed to disambiguate duplicate
names, cross-franchise collisions, and short aliases before any
downstream system (LoRA resolver, prompt builder, image gen route)
attaches model weights.

This module is intentionally **not wired into image generation** in
phase 1. It is a pure, testable core layer:

    >>> from core.character_understanding import resolve_character
    >>> r = resolve_character("hutao")
    >>> r.canonical_id
    'hu_tao@genshin_impact'

Resolver priority
-----------------
1. ``selected_character`` payload from the UI (if provided).
2. Local :class:`CharacterRegistry` (``storage/character_db/``).
3. SAA standalone-app DB (``image_pipeline.anime_pipeline.saa_character_db``)
   via lazy import — fail-safe if SAA data is absent.
4. Built-in alias table (small, hard-coded, for common short aliases).
5. Unresolved.

Canonical ID format
-------------------
``<character_slug>@<series_slug>`` (e.g. ``hu_tao@genshin_impact``).
A future variant suffix ``:<variant_slug>`` is reserved but unused.

Ambiguity handling
------------------
When two or more high-confidence candidates exist (e.g. ``Rem`` →
re:zero / generic ``rem_sleep``), the result is marked
``ambiguous=True`` and **all** candidates are returned. Callers MUST
NOT auto-attach LoRA in that case — they should ask the user.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Public dataclasses ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class CharacterCandidate:
    """A single resolved (or partially-resolved) character identity."""
    canonical_id: str            # "<character_slug>@<series_slug>"
    character_slug: str          # "hu_tao"
    series_slug: str             # "genshin_impact" — "" if unknown
    display_name: str            # "Hu Tao"
    series_name: str             # "Genshin Impact" — "" if unknown
    source: str                  # "selected" | "registry" | "saa" | "alias_table"
    confidence: float            # 0.0–1.0
    aliases: tuple[str, ...] = ()
    lora_hint: Optional[str] = None
    variant_slug: Optional[str] = None  # reserved for phase 2


@dataclass
class CharacterUnderstandingResult:
    """Outcome of one resolve call. See :func:`resolve_character`."""
    query: str
    resolved: bool
    ambiguous: bool
    candidates: list[CharacterCandidate] = field(default_factory=list)
    reason: str = ""
    # Phase 2 — unknown / low-data fallback support. All optional, all
    # backward-compatible: legacy callers reading the original fields
    # continue to work unchanged.
    mode: str = ""                 # "resolved_known" | "ambiguous" |
                                   # "low_data_profile" | "unresolved_unknown" | ""
    unknown_profile: Optional["UnknownCharacterProfile"] = None
    safe_to_attach_lora: bool = False
    character_identity_block: str = ""

    @property
    def best(self) -> Optional[CharacterCandidate]:
        """The single best candidate, or ``None`` if unresolved/ambiguous."""
        if self.ambiguous or not self.candidates:
            return None
        return self.candidates[0]

    def to_dict(self) -> dict:
        """JSON-serializable view of the result."""
        return {
            "query": self.query,
            "resolved": self.resolved,
            "ambiguous": self.ambiguous,
            "mode": self.mode,
            "reason": self.reason,
            "safe_to_attach_lora": self.safe_to_attach_lora,
            "character_identity_block": self.character_identity_block,
            "candidates": [
                {
                    "canonical_id": c.canonical_id,
                    "character_slug": c.character_slug,
                    "series_slug": c.series_slug,
                    "display_name": c.display_name,
                    "series_name": c.series_name,
                    "source": c.source,
                    "confidence": round(c.confidence, 4),
                    "aliases": list(c.aliases),
                    "lora_hint": c.lora_hint,
                }
                for c in self.candidates
            ],
            "unknown_profile": (
                self.unknown_profile.to_dict()
                if self.unknown_profile is not None else None
            ),
        }


@dataclass
class UnknownCharacterProfile:
    """Provisional descriptor for an unknown / low-data character.

    Created when a user references a character that none of the local
    sources (``selected_character`` payload, registry, SAA, alias table)
    can identify, OR when a manual override is the only source of
    metadata. NEVER drives LoRA selection — the resolver flips
    ``safe_to_attach_lora`` to ``False`` whenever this is set.
    """
    provisional_id: str            # "unknown:<char>@<series>" or canonical_id (override)
    raw_name: str                  # what the user actually typed
    possible_series: str = ""      # canonical series_slug, or "" if unknown
    profile_source: str = "unknown"  # "prompt" | "manual_override" | "payload" | "unknown"
    visual_traits: list[str] = field(default_factory=list)
    outfit_traits: list[str] = field(default_factory=list)
    personality_traits: list[str] = field(default_factory=list)
    scene_hints: list[str] = field(default_factory=list)
    negative_identity_guard: list[str] = field(default_factory=list)
    confidence: float = 0.0
    needs_user_confirmation: bool = True
    reason: str = ""
    # Phase 4 — generic profile metadata. ``data_status`` mirrors the
    # parent result's ``mode`` for self-contained JSON ("unknown" |
    # "manual_override" | "low_data" | "ambiguous"). ``needs_review`` is
    # an alias of ``needs_user_confirmation`` exposed under the spec name.
    data_status: str = "unknown"
    needs_review: bool = True

    def to_dict(self) -> dict:
        return {
            "provisional_id": self.provisional_id,
            "raw_name": self.raw_name,
            "possible_series": self.possible_series,
            "profile_source": self.profile_source,
            "data_status": self.data_status,
            "visual_traits": list(self.visual_traits),
            "outfit_traits": list(self.outfit_traits),
            "personality_traits": list(self.personality_traits),
            "scene_hints": list(self.scene_hints),
            "negative_identity_guard": list(self.negative_identity_guard),
            "confidence": round(self.confidence, 4),
            "needs_user_confirmation": self.needs_user_confirmation,
            "needs_review": self.needs_review,
            "reason": self.reason,
        }


# ── Slug helpers ─────────────────────────────────────────────────────────────

_SLUG_NON_WORD = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    """Lowercase, strip diacritics, collapse to ``[a-z0-9_]+``."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKD", text)
    norm = norm.encode("ascii", "ignore").decode("ascii")
    norm = norm.lower().strip()
    norm = _SLUG_NON_WORD.sub("_", norm).strip("_")
    return norm


def make_canonical_id(character_slug: str, series_slug: str) -> str:
    """Build the canonical ``<char>@<series>`` id. Series may be empty."""
    c = _slugify(character_slug)
    s = _slugify(series_slug)
    return f"{c}@{s}" if s else f"{c}@"


# ── Built-in alias table ─────────────────────────────────────────────────────
# Maps a normalized short alias to one or more candidate descriptors.
# Multiple entries → ambiguity → caller must ask.
#
# Format: alias_key -> tuple of (character_slug, series_slug, display_name,
#                                series_name, lora_hint_or_none)
_ALIAS_TABLE: dict[str, tuple[tuple[str, str, str, str, Optional[str]], ...]] = {
    # Genshin Impact — Hu Tao
    "hutao": (("hu_tao", "genshin_impact", "Hu Tao", "Genshin Impact", None),),
    "hu_tao": (("hu_tao", "genshin_impact", "Hu Tao", "Genshin Impact", None),),

    # Genshin Impact — Yae Miko (collides with generic shrine_miko if "miko")
    "yae": (("yae_miko", "genshin_impact", "Yae Miko", "Genshin Impact", None),),
    "yae_miko": (("yae_miko", "genshin_impact", "Yae Miko", "Genshin Impact", None),),
    "miko": (
        ("yae_miko", "genshin_impact", "Yae Miko", "Genshin Impact", None),
        ("shrine_miko", "generic", "Shrine Miko", "Generic", None),
    ),

    # Honkai Star Rail — Sparkle (collides with generic sparkle effect)
    "sparkle": (
        ("sparkle", "honkai_star_rail", "Sparkle", "Honkai: Star Rail", None),
        ("sparkle_effect", "generic", "Sparkle Effect", "Generic", None),
    ),

    # Re:Zero — Rem (collides with generic rem_sleep)
    "rem": (
        ("rem", "rezero", "Rem", "Re:Zero", None),
        ("rem_sleep", "generic", "REM Sleep", "Generic", None),
    ),

    # Fate — Saber (highly ambiguous, lots of Sabers; treat as ambiguous
    # between two of the most common references).
    "saber": (
        ("artoria_pendragon", "fate_stay_night", "Artoria Pendragon",
         "Fate/stay night", None),
        ("saber_alter", "fate_stay_night", "Saber Alter",
         "Fate/stay night", None),
    ),
}


# ── Resolver entry points ────────────────────────────────────────────────────

def _from_selected(payload: dict) -> Optional[CharacterCandidate]:
    """Build a candidate from a UI payload. Trusts the UI fully."""
    if not isinstance(payload, dict):
        return None
    char = payload.get("character_slug") or payload.get("character") or ""
    series = payload.get("series_slug") or payload.get("series") or ""
    char_slug = _slugify(char)
    if not char_slug:
        return None
    series_slug = _slugify(series)
    return CharacterCandidate(
        canonical_id=make_canonical_id(char_slug, series_slug),
        character_slug=char_slug,
        series_slug=series_slug,
        display_name=payload.get("display_name") or char or char_slug,
        series_name=payload.get("series_name") or series or "",
        source="selected",
        confidence=1.0,
        aliases=tuple(payload.get("aliases") or ()),
        lora_hint=payload.get("lora_hint"),
    )


def _from_registry(query: str) -> list[CharacterCandidate]:
    """Look up via :class:`CharacterRegistry`. Empty list on any failure."""
    try:
        from core.character_registry import get_registry  # noqa: PLC0415
        registry = get_registry()
    except Exception as exc:
        logger.debug("character_understanding: registry unavailable (%s)", exc)
        return []

    out: list[CharacterCandidate] = []
    seen: set[str] = set()

    # Direct resolve (alias-aware) → highest confidence single hit.
    try:
        rec = registry.resolve_query(query)
    except Exception as exc:
        logger.debug("character_understanding: registry.resolve_query failed (%s)", exc)
        rec = None
    if rec is not None:
        cid = make_canonical_id(rec.character_tag or rec.key, rec.series_key)
        out.append(_record_to_candidate(rec, confidence=0.95))
        seen.add(cid)

    # Collision detection — same display name in multiple series.
    try:
        collisions = registry.detect_collisions(query)
    except Exception:
        collisions = []
    for crec in collisions:
        cid = make_canonical_id(crec.character_tag or crec.key, crec.series_key)
        if cid in seen:
            continue
        out.append(_record_to_candidate(crec, confidence=0.9))
        seen.add(cid)

    return out


def _record_to_candidate(rec, confidence: float) -> CharacterCandidate:
    char_slug = _slugify(rec.character_tag or rec.key)
    series_slug = _slugify(rec.series_key)
    return CharacterCandidate(
        canonical_id=make_canonical_id(char_slug, series_slug),
        character_slug=char_slug,
        series_slug=series_slug,
        display_name=rec.display_name,
        series_name=rec.series,
        source="registry",
        confidence=confidence,
        aliases=tuple(rec.aliases or ()),
        lora_hint=rec.lora_hint,
    )


def _from_saa(query: str) -> Optional[CharacterCandidate]:
    """Lazy SAA lookup. Returns ``None`` if SAA is unavailable or no hit."""
    try:
        from image_pipeline.anime_pipeline.saa_character_db import (  # noqa: PLC0415
            lookup_character,
        )
    except Exception as exc:
        logger.debug("character_understanding: SAA module unavailable (%s)", exc)
        return None

    try:
        match = lookup_character(query)
    except Exception as exc:
        logger.debug("character_understanding: SAA lookup error (%s)", exc)
        return None

    if match is None:
        return None

    char_slug = _slugify(match.danbooru_tag or match.tag)
    series_slug = _slugify(match.series_hint or "")
    # SAA's match_score is 0..1 already; clamp & dampen lightly because
    # SAA matches by substring and can over-trigger.
    final_conf = max(0.0, min(1.0, float(match.match_score) * 0.85))
    # Confidence floor — below this, SAA is more likely substring noise
    # than a real identity. The route-level auto-attach gate is 0.8, so
    # keeping low-confidence SAA hits would just produce ambiguous /
    # never-attached candidates that confuse callers. Drop them.
    if final_conf < 0.6:
        logger.debug(
            "character_understanding: SAA confidence %.2f below floor — discarded", final_conf,
        )
        return None
    return CharacterCandidate(
        canonical_id=make_canonical_id(char_slug, series_slug),
        character_slug=char_slug,
        series_slug=series_slug,
        display_name=match.display_name or match.tag,
        series_name=match.series_hint or "",
        source="saa",
        confidence=final_conf,
    )


def _from_alias_table(query: str) -> list[CharacterCandidate]:
    """Look up the built-in alias table. Returns 0+ candidates."""
    key = _slugify(query)
    if not key or key not in _ALIAS_TABLE:
        return []
    entries = _ALIAS_TABLE[key]
    out: list[CharacterCandidate] = []
    for char_slug, series_slug, display, series, lora_hint in entries:
        out.append(CharacterCandidate(
            canonical_id=make_canonical_id(char_slug, series_slug),
            character_slug=_slugify(char_slug),
            series_slug=_slugify(series_slug),
            display_name=display,
            series_name=series,
            source="alias_table",
            confidence=0.8 if len(entries) == 1 else 0.6,
            lora_hint=lora_hint,
        ))
    return out


# ── Sentence-aware helpers ───────────────────────────────────────────────────

# Words ignored when deciding whether the query is a "sentence" vs a bare
# name. Conservative: only the most common Vietnamese/English filler words
# that frame an image request.
_PROMPT_NOISE = frozenset({
    "anh", "tranh", "hinh", "ve", "cho", "mot", "bucanh", "mac",
    "trong", "voi", "cua", "den", "cai", "buc",
    # Vietnamese generic noun-prefix "nhân vật" ("character"). Both tokens
    # are filtered so prompts like "nhân vật Sparkle trong HSR" reduce to
    # candidate "sparkle". Protagonist phrases ("nhan vat main nu") are
    # detected on the pre-noise token slice, so this filter is safe.
    "nhan", "vat",
    "draw", "paint", "sketch", "render", "make", "create", "generate",
    "image", "picture", "of", "a", "an", "the", "in", "with", "and", "for",
    "wearing", "at", "on",
})


def _query_tokens(query: str) -> list[str]:
    """Return slugified word tokens of the query (order preserved)."""
    return [t for t in _slugify(query).split("_") if t]


def _is_sentence_query(tokens: list[str]) -> bool:
    """A query is "sentence-like" when more than 2 non-noise tokens remain."""
    significant = [t for t in tokens if t not in _PROMPT_NOISE]
    return len(significant) > 2


def _series_hints_in_tokens(tokens: set[str]) -> set[str]:
    """Return registry series_slugs whose own tokens are a subset of ``tokens``.

    Lets us disambiguate "Sparkle Honkai Star Rail" against the bare
    "Sparkle" entry in the alias table.
    """
    try:
        from core.character_registry import get_registry  # noqa: PLC0415
        registry = get_registry()
        all_series = registry.list_series()
    except Exception:
        all_series = []

    hints: set[str] = set()
    for entry in all_series:
        skey = entry.get("key", "")
        if not skey:
            continue
        sk_tokens = {t for t in skey.split("_") if t}
        if sk_tokens and sk_tokens.issubset(tokens):
            hints.add(skey)
    # Always include slugs that are visible in the alias table too.
    for entries in _ALIAS_TABLE.values():
        for _c, series_slug, _d, _s, _lh in entries:
            sk_tokens = {t for t in series_slug.split("_") if t}
            if series_slug and sk_tokens.issubset(tokens):
                hints.add(series_slug)
    return hints


def _scan_alias_table_in_sentence(tokens: list[str]) -> list[CharacterCandidate]:
    """Find alias-table hits whose key appears as a token in the sentence."""
    token_set = set(tokens)
    out: list[CharacterCandidate] = []
    for alias_key in _ALIAS_TABLE:
        if alias_key in token_set:
            out.extend(_from_alias_table(alias_key))
    return out


def _resolve_sentence(query: str) -> Optional[CharacterUnderstandingResult]:
    """Sentence-aware path. Returns a result when at least one name token
    matches the alias table or registry; ``None`` otherwise (caller may
    fall back to short-query handling)."""
    tokens = _query_tokens(query)
    if not tokens:
        return None
    token_set = set(tokens)
    series_hints = _series_hints_in_tokens(token_set)

    candidates: dict[str, CharacterCandidate] = {}

    # 1. Alias-table tokens hit.
    for c in _scan_alias_table_in_sentence(tokens):
        existing = candidates.get(c.canonical_id)
        if existing is None or c.confidence > existing.confidence:
            candidates[c.canonical_id] = c

    # 2. Registry: any record whose display_name / aliases / character_tag
    # appear as a contiguous slug-token in the sentence.
    try:
        from core.character_registry import get_registry  # noqa: PLC0415
        registry = get_registry()
        for rec in registry.list_all():
            haystacks: list[str] = [rec.display_name, rec.character_tag, rec.key]
            haystacks.extend(rec.aliases or ())
            for h in haystacks:
                h_tokens = [t for t in _slugify(h).split("_") if t]
                if not h_tokens:
                    continue
                # Must match as a contiguous sub-sequence of tokens.
                if _is_subseq(h_tokens, tokens):
                    cand = _record_to_candidate(rec, confidence=0.9)
                    existing = candidates.get(cand.canonical_id)
                    if existing is None or cand.confidence > existing.confidence:
                        candidates[cand.canonical_id] = cand
                    break
    except Exception as exc:
        logger.debug("character_understanding: sentence registry scan failed (%s)", exc)

    if not candidates:
        return None

    # 3. Series-hint disambiguation. If the sentence pins a series, drop
    # candidates whose series doesn't match.
    if series_hints:
        filtered = {
            cid: c for cid, c in candidates.items()
            if not c.series_slug or c.series_slug in series_hints
        }
        if filtered:
            # Boost confidence of survivors — series match is strong signal.
            for cid in list(filtered):
                c = filtered[cid]
                if c.series_slug in series_hints:
                    filtered[cid] = replace(c, confidence=min(1.0, c.confidence + 0.15))
            candidates = filtered

    cands = sorted(candidates.values(), key=lambda x: -x.confidence)
    if len(cands) == 1:
        return CharacterUnderstandingResult(
            query=query, resolved=True, ambiguous=False,
            candidates=cands, reason=f"sentence: single {cands[0].source} hit",
        )

    top, second = cands[0], cands[1]
    if top.confidence >= 0.8 and (top.confidence - second.confidence) >= 0.2:
        return CharacterUnderstandingResult(
            query=query, resolved=True, ambiguous=False,
            candidates=[top],
            reason=f"sentence: top dominates ({top.confidence:.2f} vs {second.confidence:.2f})",
        )
    return CharacterUnderstandingResult(
        query=query, resolved=False, ambiguous=True,
        candidates=cands,
        reason=f"sentence: {len(cands)} candidates within band",
    )


def _is_subseq(needle: list[str], haystack: list[str]) -> bool:
    """True iff ``needle`` appears as a contiguous slice of ``haystack``."""
    if not needle:
        return False
    n = len(needle)
    return any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


# ── Unknown / low-data fallback ──────────────────────────────────────────────

# Series alias map (slugified phrase → canonical series_slug). Small &
# extensible; extend as more series are seen in the wild. Multi-token keys
# win over single-token keys via longest-match scanning.
_SERIES_ALIAS_MAP: dict[str, str] = {
    "genshin": "genshin_impact",
    "genshin_impact": "genshin_impact",
    "gi": "genshin_impact",
    "hsr": "honkai_star_rail",
    "honkai_star_rail": "honkai_star_rail",
    "honkai": "honkai_star_rail",
    "wuwa": "wuthering_waves",
    "wuthering_waves": "wuthering_waves",
    "zzz": "zenless_zone_zero",
    "zenless_zone_zero": "zenless_zone_zero",
    "bocchi_the_rock": "bocchi_the_rock",
    "kaguya_cosmic_princess": "cosmic_princess_kaguya",
    "cosmic_princess_kaguya": "cosmic_princess_kaguya",
    "fate_stay_night": "fate_stay_night",
    "rezero": "rezero",
    "re_zero": "rezero",
    "blue_archive": "blue_archive",
    "ba": "blue_archive",
}

# Connector words that introduce a series phrase: "X trong Y", "X from Y".
_CONNECTOR_TOKENS = frozenset({
    "trong", "tu", "cua",      # Vietnamese: trong / từ / của
    "from", "in", "of",        # English
})

# Action / outfit / scene tokens — anything after one of these is residual,
# not character identity. Used both for residual extraction and as a
# secondary stop boundary for the candidate-name span.
_ACTION_TOKENS = frozenset({
    # Vietnamese
    "mac", "dung", "ngoi", "choi", "cam", "cau", "chay", "bay",
    "tren", "duoi", "ben", "voi", "o", "den",
    # English
    "wearing", "standing", "sitting", "playing", "holding", "fishing",
    "flying", "on", "beside", "with", "at",
})


def _looks_named(original: str, candidate_slug: str) -> bool:
    """Heuristic: does ``candidate_slug`` correspond to a capitalized word
    in ``original``? Pure rule, no LLM."""
    if not candidate_slug:
        return False
    cand_tokens = set(candidate_slug.split("_"))
    # Match Latin + extended Latin (Vietnamese diacritics included).
    for raw_word in re.findall(r"[A-Za-zÀ-ỹ]+", original):
        if not raw_word:
            continue
        if _slugify(raw_word) in cand_tokens and raw_word[0].isupper():
            return True
    return False


# Negation patterns — "không phải X" / "not X" / "khong phai X". Captured X
# is appended to the unknown profile's negative_identity_guard so the
# downstream prompt explicitly avoids that identity.
_NEGATION_PATTERNS = (
    re.compile(r"kh[oô]ng\s+ph[aả]i\s+([A-Za-zÀ-ỹ][A-Za-zÀ-ỹ\s]*?)(?:[,.;!?]|$)",
               re.IGNORECASE),
    re.compile(r"\bnot\s+([A-Za-z][A-Za-z\s]*?)(?:[,.;!?]|$)", re.IGNORECASE),
)


def _extract_negation_targets(text: str) -> list[str]:
    """Return the list of identities the user explicitly excluded."""
    out: list[str] = []
    if not text:
        return out
    for pat in _NEGATION_PATTERNS:
        for m in pat.finditer(text):
            target = (m.group(1) or "").strip()
            if target:
                out.append(target)
    return out


# Protagonist phrase canonicalization. Maps Vietnamese / English
# protagonist references to a stable slug so the same character category
# resolves identically across languages.
def _normalize_protagonist_phrase(slug: str) -> str:
    if not slug:
        return slug
    toks = set(slug.split("_"))
    is_protag = bool(toks & {"main", "protagonist"}) or {"nhan", "vat"}.issubset(toks)
    if not is_protag:
        return slug
    if toks & {"nu", "female"}:
        return "main_female_protagonist"
    if toks & {"nam", "male"}:
        return "main_male_protagonist"
    return slug


# Style markers — when present, the series alias should be treated as a
# *style* reference rather than a character/series identity (unless an
# explicit known character was named).
_STYLE_TOKENS = frozenset({"style", "kieu"})  # "phong cach" handled as phrase
_OC_TOKENS = frozenset({"oc"})

# Multi-character connector — a capitalized name + "và"/"and" + capitalized
# name signals the prompt references multiple characters.
_MULTI_CHAR_RE = re.compile(
    r"\b[A-ZÀ-Ỹ][A-Za-zÀ-ỹ]+\s+(?:v[aà]|and)\s+[A-ZÀ-Ỹ][A-Za-zÀ-ỹ]+\b"
)


def _has_phrase(tokens: list[str], phrase: tuple[str, ...]) -> bool:
    """True iff ``phrase`` appears as a contiguous slice of ``tokens``."""
    n = len(phrase)
    if n == 0 or n > len(tokens):
        return False
    target = list(phrase)
    return any(tokens[i:i + n] == target for i in range(len(tokens) - n + 1))


def _word_spans(text: str) -> list[str]:
    """Whitespace-split the original prompt, preserving case and diacritics."""
    return re.findall(r"\S+", text)


def _raw_name_from_words(words: list[str], name_tokens: list[str]) -> str:
    """Reconstruct the original-cased character name by walking ``words``
    and emitting those whose slug matches ``name_tokens`` (in order).

    Used so prompts like ``"Iroha trong Kaguya..."`` produce
    ``raw_character_query == "Iroha"`` (preserving capitalization), while
    ``"klee câu cá bằng bom"`` produces ``"klee"`` (lowercase preserved).
    """
    if not name_tokens:
        return ""
    remaining = list(name_tokens)
    out: list[str] = []
    for w in words:
        # Strip trailing punctuation but keep the lexical content.
        cleaned = w.strip(".,;:!?\"'()[]")
        s = _slugify(cleaned)
        if not s:
            continue
        if s in remaining:
            out.append(cleaned)
            remaining.remove(s)
            if not remaining:
                break
    return " ".join(out)


def _raw_residual_from_words(words: list[str]) -> str:
    """Return original-cased prompt tail starting at the first action token.

    Preserves Vietnamese diacritics so prompt-builders downstream see
    ``"câu cá bằng bom"`` instead of slug-form ``"cau ca bang bom"``.
    """
    out: list[str] = []
    collecting = False
    for w in words:
        s = _slugify(w.strip(".,;:!?\"'()[]"))
        if not collecting and s in _ACTION_TOKENS:
            collecting = True
        if collecting:
            out.append(w)
    return " ".join(out)


def extract_prompt_entities(prompt: str) -> dict:
    """Rule-based prompt entity extraction.

    Pure heuristic — never raises, no network, no model. The return dict
    is JSON-serializable and contains both the spec-required keys and a
    set of legacy keys preserved for backward compatibility.

    Spec fields
    -----------
    - ``raw_character_query``     — original-cased character name
      (e.g. ``"Iroha"``, ``"klee"``, ``""``).
    - ``series_hint``             — canonical series slug
      (e.g. ``"cosmic_princess_kaguya"``); also exposed as ``series_slug``.
    - ``series_slug``             — alias of ``series_hint``.
    - ``residual_prompt``         — original-cased outfit/action/scene tail
      starting at the first action token (e.g. ``"câu cá bằng bom"``).
    - ``style_hint``              — series slug repurposed as a style ref
      when the prompt says "phong cách"/"kiểu"/"style" and no explicit
      character is named (e.g. ``"bocchi_the_rock"``).
    - ``negative_identity_guard`` — list of identities the user explicitly
      excluded via "không phải X"/"not X".
    - ``multiple_characters``     — True iff two capitalized names are
      connected by "và"/"and".
    - ``extraction_confidence``   — 0.0–0.9 heuristic score.
    - ``extraction_reason``       — short human-readable trace.

    Legacy fields (preserved)
    -------------------------
    - ``candidate_name``, ``candidate_name_slug``, ``series_hint_raw``,
      ``is_named``.
    """
    text = (prompt or "").strip()
    empty = {
        "raw_character_query": "",
        "candidate_name": "",
        "candidate_name_slug": "",
        "series_hint": "",
        "series_slug": "",
        "series_hint_raw": "",
        "residual_prompt": "",
        "style_hint": "",
        "negative_identity_guard": [],
        "multiple_characters": False,
        "extraction_confidence": 0.0,
        "extraction_reason": "empty prompt",
        "is_named": False,
    }
    if not text:
        return empty

    text_tokens = _query_tokens(text)
    if not text_tokens:
        return empty
    words = _word_spans(text)

    reason_parts: list[str] = []

    # 1. Series hint: longest-token-count alias key wins.
    series_hint = ""
    series_hint_raw = ""
    series_span: Optional[tuple[int, int]] = None
    for alias_key in sorted(_SERIES_ALIAS_MAP, key=lambda k: -len(k.split("_"))):
        ak_tokens = alias_key.split("_")
        n = len(ak_tokens)
        if n > len(text_tokens):
            continue
        for i in range(len(text_tokens) - n + 1):
            if text_tokens[i:i + n] == ak_tokens:
                series_hint = _SERIES_ALIAS_MAP[alias_key]
                series_hint_raw = " ".join(ak_tokens)
                series_span = (i, i + n)
                break
        if series_span is not None:
            break
    if series_hint:
        reason_parts.append(f"series={series_hint}")

    # 2. Candidate name span — tokens up to the first connector / action /
    # series / style boundary, minus prompt-noise words.
    end_idx = len(text_tokens)
    boundary_kind = ""
    for i, tok in enumerate(text_tokens):
        if tok in _CONNECTOR_TOKENS:
            end_idx = i
            boundary_kind = f"connector '{tok}'"
            break
        if tok in _ACTION_TOKENS:
            end_idx = i
            boundary_kind = f"action '{tok}'"
            break
        if tok in _STYLE_TOKENS:
            end_idx = i
            boundary_kind = f"style '{tok}'"
            break
        # Multi-token style phrase "phong cach".
        if tok == "phong" and i + 1 < len(text_tokens) and text_tokens[i + 1] == "cach":
            end_idx = i
            boundary_kind = "style 'phong cach'"
            break
        if series_span is not None and i == series_span[0]:
            end_idx = i
            boundary_kind = "series-alias"
            break
    # Run protagonist normalization on the PRE-noise token slice so phrases
    # like "nhân vật main nữ" — where "nhan"/"vat" are filtered as generic
    # noise — still canonicalize to "main_female_protagonist".
    raw_pre_noise = "_".join(text_tokens[:end_idx])
    canonical_slug = _normalize_protagonist_phrase(raw_pre_noise)
    if canonical_slug != raw_pre_noise and canonical_slug:
        reason_parts.append("protagonist-phrase normalized")
        candidate_name_slug = canonical_slug
        name_tokens = [t for t in candidate_name_slug.split("_") if t]
    else:
        name_tokens = [t for t in text_tokens[:end_idx] if t not in _PROMPT_NOISE]
        candidate_name_slug = "_".join(name_tokens)
    candidate_name = " ".join(t.capitalize() for t in name_tokens)
    if boundary_kind:
        reason_parts.append(f"boundary={boundary_kind}")

    # 3. Residual = everything from first action token onward, original-cased.
    residual_prompt = _raw_residual_from_words(words)

    # 4. Negative identity guard — "không phải X" / "not X".
    negative_identity_guard = _extract_negation_targets(text)
    if negative_identity_guard:
        reason_parts.append(f"negation={len(negative_identity_guard)}")

    # 5. Multi-character — "Furina và Nahida" / "Hu Tao and Yae".
    multiple_characters = bool(_MULTI_CHAR_RE.search(text))
    if multiple_characters:
        reason_parts.append("multi-character")
        # When multi-char detected, narrow candidate to FIRST capitalized
        # proper noun so resolver doesn't try to merge both into one slug.
        m = re.search(r"\b([A-ZÀ-Ỹ][A-Za-zÀ-ỹ]+)\b", text)
        if m:
            candidate_name = m.group(1)
            candidate_name_slug = _slugify(candidate_name)
            name_tokens = [t for t in candidate_name_slug.split("_") if t]

    # 6. raw_character_query — original-cased name from input words.
    raw_character_query = _raw_name_from_words(words, name_tokens)
    if not raw_character_query:
        raw_character_query = candidate_name  # fallback (e.g. protagonist phrase)

    # 7. Style mode — "phong cách"/"style"/"kiểu". When active and no
    # explicit character is named (alias-table hit), the series alias is
    # demoted to ``style_hint`` and character fields are cleared.
    style_marker = (
        _has_phrase(text_tokens, ("phong", "cach"))
        or bool(_STYLE_TOKENS & set(text_tokens))
        or _has_phrase(text_tokens, ("in", "the", "style", "of"))
    )
    style_hint = ""
    if style_marker:
        explicit_char = candidate_name_slug in _ALIAS_TABLE
        if not explicit_char and series_hint:
            style_hint = series_hint
            series_hint = ""
            series_hint_raw = ""
            candidate_name = ""
            candidate_name_slug = ""
            name_tokens = []
            raw_character_query = ""
            reason_parts.append(f"style={style_hint}")

    # 8. OC mode — "OC" / "original character" / "nhân vật tự tạo".
    oc_marker = (
        bool(_OC_TOKENS & set(text_tokens))
        or _has_phrase(text_tokens, ("original", "character"))
        or _has_phrase(text_tokens, ("nhan", "vat", "tu", "tao"))
        or _has_phrase(text_tokens, ("nhan", "vat", "tu", "ta"))
    )
    if oc_marker:
        reason_parts.append("OC marker")

    # 9. is_named — capitalised in original prompt OR series hint present
    # OR candidate is itself a known alias key. OC marker forces False to
    # prevent silent resolution to a known character by name alone.
    is_named = bool(candidate_name_slug) and (
        bool(series_hint)
        or _looks_named(text, candidate_name_slug)
        or candidate_name_slug in _ALIAS_TABLE
    )
    if oc_marker:
        is_named = False

    # 10. Extraction confidence — coarse heuristic.
    if not candidate_name_slug and not style_hint:
        confidence = 0.0
    elif series_hint and is_named:
        confidence = 0.9
    elif is_named:
        confidence = 0.7
    elif series_hint or style_hint:
        confidence = 0.5
    elif candidate_name_slug:
        confidence = 0.3
    else:
        confidence = 0.0

    extraction_reason = "; ".join(reason_parts) if reason_parts else "no signal"

    return {
        "raw_character_query": raw_character_query,
        "candidate_name": candidate_name,
        "candidate_name_slug": candidate_name_slug,
        "series_hint": series_hint,
        "series_slug": series_hint,
        "series_hint_raw": series_hint_raw,
        "residual_prompt": residual_prompt,
        "style_hint": style_hint,
        "negative_identity_guard": list(negative_identity_guard),
        "multiple_characters": multiple_characters,
        "extraction_confidence": confidence,
        "extraction_reason": extraction_reason,
        "is_named": is_named,
    }


# ── Manual overrides ─────────────────────────────────────────────────────────

# Cached at module level. Tests can monkeypatch ``_load_manual_overrides``
# directly. The on-disk file is OPTIONAL — missing/unreadable file is
# treated as "no overrides".
_OVERRIDES_PATH_DEFAULT = (
    Path(__file__).resolve().parent.parent / "config" / "character_overrides.json"
)


def _load_manual_overrides(path: Optional[Path] = None) -> list[dict]:
    """Lazy + fail-safe loader. Returns ``[]`` on any error."""
    p = path or _OVERRIDES_PATH_DEFAULT
    try:
        if not p.exists():
            return []
        import json  # noqa: PLC0415
        data = json.loads(p.read_text(encoding="utf-8"))
        chars = data.get("characters", []) if isinstance(data, dict) else []
        return [c for c in chars if isinstance(c, dict)]
    except Exception as exc:
        logger.debug("character_understanding: override load failed (%s)", exc)
        return []


def _match_override(
    name_slug: str,
    series_slug: str,
    overrides: list[dict],
) -> Optional[dict]:
    """First override whose aliases / display_name match ``name_slug``.

    If ``series_slug`` is non-empty, the override's ``series_slug`` (when
    present) must match — this prevents a same-named override entry from
    hijacking a different franchise.
    """
    if not name_slug:
        return None
    for entry in overrides:
        candidates: set[str] = set()
        for a in entry.get("aliases", []) or ():
            candidates.add(_slugify(a))
        if entry.get("display_name"):
            candidates.add(_slugify(entry["display_name"]))
        if entry.get("canonical_id"):
            # canonical_id format "<char>@<series>" — extract char part.
            cid = entry["canonical_id"]
            if "@" in cid:
                candidates.add(_slugify(cid.split("@", 1)[0]))
            else:
                candidates.add(_slugify(cid))
        if name_slug not in candidates:
            continue
        entry_series = _slugify(entry.get("series_slug", ""))
        if series_slug and entry_series and entry_series != series_slug:
            continue
        return entry
    return None


def _build_identity_block(
    raw_name: str,
    possible_series: str,
    visual_traits: list[str],
    outfit_traits: list[str],
    negative_identity_guard: list[str],
) -> str:
    """Build a prompt-normalization block describing an unknown / low-data
    character. Explicitly instructs downstream NOT to map to a known LoRA.
    """
    lines = [
        f"Character (unknown / low-data, no LoRA): {raw_name or 'unspecified'}",
    ]
    if possible_series:
        lines.append(f"Possible series: {possible_series}")
    if visual_traits:
        lines.append("Visual traits: " + ", ".join(visual_traits))
    if outfit_traits:
        lines.append("Outfit traits: " + ", ".join(outfit_traits))
    if negative_identity_guard:
        lines.append("Identity guard (avoid): " + "; ".join(negative_identity_guard))
    lines.append(
        "Do not substitute with a known character. Do not attach LoRA. "
        "Render from the textual description only."
    )
    return "\n".join(lines)


def _make_override_result(
    hit: dict,
    ents: dict,
    query: str,
) -> CharacterUnderstandingResult:
    """Build a ``low_data_profile`` result from a matched override entry.

    LoRA safety: ``safe_to_attach_lora`` is ``True`` only when the
    override explicitly carries a non-empty ``lora_hint`` AND its own
    ``safe_to_attach_lora`` field is not literally ``False``. This is
    the single override-driven path allowed to attach LoRA, and the
    UI / route still applies the 0.8 confidence gate on top of it.
    """
    name_slug = _slugify(ents["candidate_name_slug"])
    series_slug = ents["series_hint"]
    char_slug = _slugify(
        hit.get("canonical_id", "").split("@", 1)[0]
        or hit.get("character_slug", "")
        or hit.get("display_name", "")
        or name_slug
    )
    s_slug = _slugify(hit.get("series_slug", "") or series_slug)
    canonical_id = hit.get("canonical_id") or make_canonical_id(char_slug, s_slug)

    raw_lora = hit.get("lora_hint")
    explicit_safe = hit.get("safe_to_attach_lora", False)
    safe_lora = bool(raw_lora) and bool(explicit_safe)
    candidate_lora = raw_lora if safe_lora else None

    cand = CharacterCandidate(
        canonical_id=canonical_id,
        character_slug=char_slug,
        series_slug=s_slug,
        display_name=hit.get("display_name", "") or ents["candidate_name"],
        series_name=hit.get("series_name", "") or hit.get("series", "")
                    or s_slug.replace("_", " ").title(),
        source="manual_override",
        confidence=float(hit.get("confidence", 0.7)),
        aliases=tuple(hit.get("aliases", []) or ()),
        lora_hint=candidate_lora,
    )
    profile = UnknownCharacterProfile(
        provisional_id=canonical_id,
        raw_name=ents["candidate_name"] or hit.get("display_name", ""),
        possible_series=s_slug,
        profile_source="manual_override",
        visual_traits=list(hit.get("visual_traits", []) or []),
        outfit_traits=list(hit.get("outfit_traits", []) or []),
        personality_traits=list(hit.get("personality_traits", []) or []),
        scene_hints=list(hit.get("scene_hints", []) or []),
        negative_identity_guard=list(hit.get("negative_identity_guard", []) or []),
        confidence=float(hit.get("confidence", 0.7)),
        needs_user_confirmation=False,
        data_status=hit.get("data_status", "manual_override"),
        needs_review=bool(hit.get("needs_review", True)),
        reason="manual override matched",
    )
    block = _build_identity_block(
        profile.raw_name,
        profile.possible_series,
        profile.visual_traits,
        profile.outfit_traits,
        profile.negative_identity_guard,
    )
    return CharacterUnderstandingResult(
        query=query, resolved=True, ambiguous=False,
        candidates=[cand],
        reason="manual override → low_data_profile",
        mode="low_data_profile",
        unknown_profile=profile,
        safe_to_attach_lora=safe_lora,
        character_identity_block=block,
    )


def _try_manual_override(
    query: str,
    *,
    overrides: Optional[list[dict]] = None,
) -> Optional[CharacterUnderstandingResult]:
    """Run the override matcher early (before registry/SAA). Returns
    ``None`` when no entity could be extracted or no override matches.
    """
    if not query:
        return None
    ents = extract_prompt_entities(query)
    if not ents["candidate_name_slug"]:
        return None
    overrides = _load_manual_overrides() if overrides is None else overrides
    if not overrides:
        return None
    hit = _match_override(ents["candidate_name_slug"], ents["series_hint"], overrides)
    if hit is None:
        return None
    return _make_override_result(hit, ents, query)


def _unknown_or_low_data_result(
    query: str,
    *,
    overrides: Optional[list[dict]] = None,
) -> Optional[CharacterUnderstandingResult]:
    """Build a low_data_profile / unresolved_unknown result for ``query``.

    Returns ``None`` when the prompt does not look character-named
    (``is_named=False``) — in that case the caller keeps the original
    "fully unresolved" outcome unchanged.
    """
    ents = extract_prompt_entities(query)
    if not ents["is_named"] or not ents["candidate_name_slug"]:
        return None

    name_slug = _slugify(ents["candidate_name_slug"])
    series_slug = ents["series_hint"]
    overrides = _load_manual_overrides() if overrides is None else overrides
    hit = _match_override(name_slug, series_slug, overrides)

    if hit is not None:
        # Late-path safety net — normally already handled by the early
        # ``_try_manual_override`` hook in ``resolve_character``.
        return _make_override_result(hit, ents, query)

    # ── unresolved_unknown ──────────────────────────────────────────────
    series_for_id = series_slug or "unknown_series"
    provisional_id = f"unknown:{name_slug}@{series_for_id}"
    guard = [
        "do not substitute with another known anime/game character",
        "do not use a similar popular character as identity",
        "do not attach LoRA",
    ]
    # User-supplied "không phải X" / "not X" — append explicit negative
    # targets so the prompt block tells the model what NOT to draw.
    for target in _extract_negation_targets(query):
        guard.append(f"do not draw {target}")
    profile = UnknownCharacterProfile(
        provisional_id=provisional_id,
        raw_name=ents["candidate_name"],
        possible_series=series_slug,
        profile_source="prompt",
        visual_traits=[],
        outfit_traits=[ents["residual_prompt"]] if ents["residual_prompt"] else [],
        negative_identity_guard=guard,
        confidence=0.3,
        needs_user_confirmation=True,
        data_status="unknown",
        needs_review=True,
        reason="no registry/SAA/alias/manual override hit; using unknown character profile fallback",
    )
    block = _build_identity_block(
        profile.raw_name,
        profile.possible_series,
        profile.visual_traits,
        profile.outfit_traits,
        profile.negative_identity_guard,
    )
    return CharacterUnderstandingResult(
        query=query, resolved=False, ambiguous=False,
        candidates=[],
        reason=profile.reason,
        mode="unresolved_unknown",
        unknown_profile=profile,
        safe_to_attach_lora=False,
        character_identity_block=block,
    )


def _annotate_resolved_known(
    result: CharacterUnderstandingResult,
) -> CharacterUnderstandingResult:
    """Stamp ``mode`` / ``safe_to_attach_lora`` on a successful resolution."""
    if result.ambiguous:
        result.mode = "ambiguous"
        result.safe_to_attach_lora = False
    elif result.resolved and result.candidates:
        result.mode = "resolved_known"
        # All known sources (selected/registry/saa/alias_table) are
        # considered safe — the existing confidence gate in route handlers
        # still applies the 0.8 threshold for actual hint auto-fill.
        result.safe_to_attach_lora = True
    return result


def resolve_character(
    query: str = "",
    *,
    selected_character: Optional[dict] = None,
) -> CharacterUnderstandingResult:
    """Resolve ``query`` to a canonical character identity.

    Parameters
    ----------
    query:
        Free-text character reference (e.g. ``"hutao"``, ``"Rem"``).
    selected_character:
        Optional UI payload that bypasses all heuristics. Shape::

            {"character_slug": "hu_tao", "series_slug": "genshin_impact",
             "display_name": "Hu Tao", "series_name": "Genshin Impact",
             "lora_hint": "...", "aliases": [...]}

    Returns
    -------
    :class:`CharacterUnderstandingResult` — never raises. ``best`` is
    ``None`` when unresolved or ambiguous.

    The result is post-processed to set ``mode`` (``resolved_known`` /
    ``ambiguous`` / ``low_data_profile`` / ``unresolved_unknown`` / ``""``)
    and ``safe_to_attach_lora``. When the known-source pipeline returns
    no candidate AND the prompt looks character-named, the unknown /
    low-data fallback runs (manual override → ``low_data_profile``,
    otherwise ``unresolved_unknown``).
    """
    original_query = (query or "").strip()
    original_was_sentence = (
        _is_sentence_query(_query_tokens(original_query))
        if original_query else False
    )

    # Priority 1 — selected_character payload short-circuits everything.
    if selected_character:
        sel_result = _resolve_known(
            original_query, selected_character=selected_character,
        )
        if sel_result.candidates:
            return _annotate_resolved_known(sel_result)

    # Priority 2 — manual overrides win over registry/SAA/alias. This is
    # how new / niche / low-data characters become resolvable without
    # touching code: drop a JSON entry into character_overrides.json.
    override_result = _try_manual_override(original_query)
    if override_result is not None:
        return override_result

    result = _resolve_known(original_query, selected_character=selected_character)

    # Sentence-mode safety: SAA-only matches without a confirming series
    # hint are too noisy (substring matching). Drop them so the prompt
    # flows into the unknown / low-data fallback. Registry, alias_table,
    # and selected_character matches are still trusted.
    if (
        original_was_sentence
        and result.candidates
        and not result.ambiguous
        and result.best is not None
        and result.best.source == "saa"
    ):
        ents = extract_prompt_entities(original_query)
        series_hint = ents["series_hint"]
        if not series_hint or result.best.series_slug != series_hint:
            logger.debug(
                "character_understanding: dropping SAA sentence match "
                "(series_hint=%r, candidate=%s/%s)",
                series_hint, result.best.canonical_id, result.best.series_slug,
            )
            result = CharacterUnderstandingResult(
                query=original_query, resolved=False, ambiguous=False,
                reason="SAA sentence match dropped — no confirming series hint",
            )

    # Successful or ambiguous: stamp mode + LoRA-attach safety. Done.
    if result.candidates or result.ambiguous:
        return _annotate_resolved_known(result)

    # Truly unresolved with no candidates → try the unknown / low-data
    # fallback. ``selected_character`` already wins above; here we only
    # reach this branch when no source produced a candidate.
    fallback = _unknown_or_low_data_result(original_query)
    if fallback is not None:
        # Preserve the original "no known character" reason for debugging.
        if result.reason and "unknown" not in result.reason:
            fallback.reason = f"{result.reason}; {fallback.reason}"
        return fallback

    # Still nothing — leave mode empty for backward compat (callers that
    # check ``resolved is False`` keep working).
    return result


def _resolve_known(
    query: str = "",
    *,
    selected_character: Optional[dict] = None,
) -> CharacterUnderstandingResult:
    """Inner resolver — returns a known-source result, ambiguous result,
    or an empty unresolved result. Never builds an unknown profile.
    """
    query = (query or "").strip()

    # Priority 1 — UI selection wins outright.
    if selected_character:
        cand = _from_selected(selected_character)
        if cand is not None:
            return CharacterUnderstandingResult(
                query=query,
                resolved=True,
                ambiguous=False,
                candidates=[cand],
                reason="selected_character payload",
            )

    if not query:
        return CharacterUnderstandingResult(
            query="", resolved=False, ambiguous=False,
            reason="empty query and no selected_character",
        )

    # Sentence-aware path — when the user types a full prompt instead of a
    # bare name, dispatch to a token-based scanner that handles series
    # disambiguation (e.g. "Sparkle Honkai Star Rail") and avoids SAA
    # substring noise.
    tokens = _query_tokens(query)
    if _is_sentence_query(tokens):
        sentence_result = _resolve_sentence(query)
        if sentence_result is not None:
            return sentence_result
        # Sentence had no alias / registry hit. Use rule-based entity
        # extraction to pick the actual character-name token, NOT a
        # random longest leftover (which used to feed words like
        # "princess" or "cosmic" into SAA and produce wrong matches).
        ents = extract_prompt_entities(query)
        if ents["candidate_name_slug"] and ents["is_named"]:
            query = ents["candidate_name_slug"]
        else:
            return CharacterUnderstandingResult(
                query=query, resolved=False, ambiguous=False,
                reason="no character token found in sentence",
            )

    # Priority 2 — local registry (highest-quality local data).
    reg_candidates = _from_registry(query)
    if reg_candidates:
        # Dedupe by canonical_id (resolve_query + collisions can overlap).
        unique: dict[str, CharacterCandidate] = {}
        for c in reg_candidates:
            unique.setdefault(c.canonical_id, c)
        cands = list(unique.values())
        if len(cands) > 1:
            return CharacterUnderstandingResult(
                query=query, resolved=False, ambiguous=True,
                candidates=cands,
                reason=f"registry: {len(cands)} candidates share display name",
            )
        return CharacterUnderstandingResult(
            query=query, resolved=True, ambiguous=False,
            candidates=cands, reason="registry exact / alias hit",
        )

    # Priority 3 — SAA (large but noisier).
    saa = _from_saa(query)
    saa_list = [saa] if saa is not None else []

    # Priority 4 — built-in alias table.
    alias_candidates = _from_alias_table(query)

    # Combine SAA + alias table for ambiguity assessment.
    combined: dict[str, CharacterCandidate] = {}
    for c in saa_list + alias_candidates:
        existing = combined.get(c.canonical_id)
        if existing is None or c.confidence > existing.confidence:
            combined[c.canonical_id] = c

    cands = sorted(combined.values(), key=lambda x: -x.confidence)

    if not cands:
        return CharacterUnderstandingResult(
            query=query, resolved=False, ambiguous=False,
            reason="no candidate from registry / SAA / alias table",
        )

    if len(cands) > 1:
        # Ambiguity rule: only resolve outright if the top candidate is
        # clearly higher-confidence than the runner-up.
        top, second = cands[0], cands[1]
        if top.confidence >= 0.8 and (top.confidence - second.confidence) >= 0.2:
            return CharacterUnderstandingResult(
                query=query, resolved=True, ambiguous=False,
                candidates=[top],
                reason=f"top candidate dominates ({top.confidence:.2f} vs {second.confidence:.2f})",
            )
        return CharacterUnderstandingResult(
            query=query, resolved=False, ambiguous=True,
            candidates=cands,
            reason=f"{len(cands)} candidates within confidence band",
        )

    return CharacterUnderstandingResult(
        query=query, resolved=True, ambiguous=False,
        candidates=cands, reason=f"single {cands[0].source} hit",
    )


# ── LoRA attach safety gate ──────────────────────────────────────────────────

def can_attach_character_lora(
    character_result: Optional["CharacterUnderstandingResult"],
    lora_candidate: Optional[dict] = None,
) -> tuple[bool, str]:
    """Decide whether it is safe to attach a character LoRA / reference.

    Returns ``(safe, reason)``. ``reason`` is a short machine-readable
    tag suitable for logging or surfacing as ``lora_blocked_reason`` in
    a route response. Generation must NOT fail when this returns
    ``False`` — the caller should fall back to prompt-only / profile-
    based rendering.

    Safe is granted only when ALL of:
      * ``character_result`` is non-null and ``resolved`` is true.
      * ``ambiguous`` is false.
      * ``safe_to_attach_lora`` is true on the result.
      * ``mode`` is ``resolved_known`` OR (``low_data_profile`` with the
        manual-override carrying an explicit ``lora_hint``).
      * The single best candidate has a non-empty ``canonical_id`` AND
        non-empty ``series_slug``.
      * If ``lora_candidate`` is supplied, its ``canonical_id`` /
        ``character_slug``+``series_slug`` exactly matches the resolved
        candidate. A mere display-name match across different series is
        treated as a collision, not a match.

    Blocked for: unresolved/unknown, ambiguous, OC, style-only prompts
    (those reach this gate with no ``best`` candidate), low-data profiles
    that lack an explicit ``lora_hint``, and any series-mismatch.
    """
    if character_result is None:
        return False, "no_character_result"
    if not character_result.resolved:
        # Unknown / unresolved — covers OC, style-only, missing-name.
        if character_result.mode == "unresolved_unknown":
            return False, "unresolved_unknown"
        return False, "not_resolved"
    if character_result.ambiguous:
        return False, "ambiguous"
    if not character_result.safe_to_attach_lora:
        return False, "safe_to_attach_lora_false"

    best = character_result.best
    if best is None:
        return False, "no_best_candidate"
    if not best.canonical_id or not best.series_slug:
        return False, "incomplete_canonical_id"

    mode = character_result.mode
    if mode == "low_data_profile":
        # Only allowed via explicit override-supplied lora_hint.
        if not best.lora_hint:
            return False, "low_data_profile_no_lora_hint"
    elif mode != "resolved_known":
        return False, f"unsafe_mode:{mode or 'unknown'}"

    if lora_candidate is not None:
        cid = (lora_candidate.get("canonical_id") or "").strip()
        if cid:
            if cid != best.canonical_id:
                return False, "canonical_id_mismatch"
        else:
            cand_char = _slugify(lora_candidate.get("character_slug", ""))
            cand_series = _slugify(lora_candidate.get("series_slug", ""))
            if cand_char and cand_char != best.character_slug:
                return False, "character_slug_mismatch"
            if cand_series and cand_series != best.series_slug:
                # Same display name across different franchises — refuse.
                return False, "series_mismatch"
            if not cand_char and not cid:
                # Unverifiable LoRA candidate metadata — refuse rather
                # than silently trust it.
                return False, "unverifiable_lora_candidate"

    return True, "ok"


__all__ = [
    "CharacterCandidate",
    "CharacterUnderstandingResult",
    "UnknownCharacterProfile",
    "can_attach_character_lora",
    "extract_prompt_entities",
    "make_canonical_id",
    "resolve_character",
    "resolve_character_intent",
]


# Public alias — preferred name when called from request handlers, where
# "intent" reads more naturally alongside other intent helpers.
resolve_character_intent = resolve_character
