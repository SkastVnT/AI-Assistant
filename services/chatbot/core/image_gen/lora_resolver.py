"""Text-driven LoRA resolver.

Lets the chatbot turn plain natural-language text into a usable
`<lora:...>` stack without requiring the user to know LoRA syntax.

Pipeline:
1. Build a *runtime catalog* by merging the curated `LORA_CATALOG`
   (model_presets) with auto-derived entries from
   `app/storage/lora_inventory.json` so all 328 files become reachable
   via plain-text triggers.
2. Word-boundary scan of the prompt for every trigger phrase. Avoids
   false positives where short triggers used to substring-match
   unrelated words (e.g. `ei` inside "their").
3. Return a ranked, de-duplicated `list[LoraSpec]` ready to feed into
   `ComfyUIFastProvider`.

Side-effect free, dependency-light. Importable from both image-gen
routes and chat router.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from config.model_presets import LORA_CATALOG  # type: ignore

try:
    from core.project_paths import STORAGE_DIR
except ImportError:  # pragma: no cover - package import fallback
    from core.project_paths import STORAGE_DIR

from .providers.base import LoraSpec

logger = logging.getLogger(__name__)

_INVENTORY_PATH = STORAGE_DIR / "lora_inventory.json"

# Trigger phrases shorter than this are dropped entirely.
_MIN_TRIGGER_LEN = 4
# Hard cap on auto-injected LoRAs per request.
_MAX_AUTO_LORAS = 4

# Tokens that are noise-only when extracted from a filename.
_FILENAME_NOISE = {
    "lora",
    "lycoris",
    "lyco",
    "loha",
    "ckpt",
    "model",
    "merge",
    "il",
    "ilxl",
    "illustrious",
    "illust",
    "sdxl",
    "sd15",
    "sd",
    "xl",
    "pony",
    "pdxl",
    "ponyxl",
    "anime",
    "style",
    "test",
    "final",
    "epoch",
    "epochs",
    "rank",
    "alpha",
    "att",
    "attn",
    "noxattn",
    "fp16",
    "fp32",
    "bf16",
    "safetensors",
    "fix",
    "fixed",
    "by",
    "for",
    "the",
    "and",
    "with",
    "from",
    "copy",
}
# Patterns dropped from filenames before tokenization.
_VERSION_RE = re.compile(
    r"(?:[-_ ]?v?\d+(?:\.\d+)*[a-z]?)|"
    r"(?:[-_]?\d{2,5}(?:steps|step|epoch|ep)?)|"
    r"(?:\(\d+\))",
    re.IGNORECASE,
)
_NON_WORD_SPLIT_RE = re.compile(r"[^a-z0-9]+", re.IGNORECASE)
_BIDI_CHARS_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e]")


@dataclass
class ResolvedLora:
    spec: LoraSpec
    matched_phrase: str
    catalog_key: str
    category: str
    base: str
    auto_derived: bool = False


_RUNTIME_CATALOG: dict[str, dict] | None = None
_INVENTORY_MTIME: float = 0.0
_COMPILED_PATTERNS: list[tuple[re.Pattern, str, str, dict]] | None = None


def _strip_diacritics(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _derive_triggers_from_filename(fname: str) -> list[str]:
    stem = re.sub(r"\.safetensors$", "", fname, flags=re.IGNORECASE)
    stem = _BIDI_CHARS_RE.sub("", stem)
    cleaned = _VERSION_RE.sub(" ", stem)
    raw_tokens = [t.lower() for t in _NON_WORD_SPLIT_RE.split(cleaned) if t]
    tokens = [t for t in raw_tokens if t not in _FILENAME_NOISE and not t.isdigit()]
    if not tokens:
        return []

    triggers: list[str] = []
    full = " ".join(tokens)
    if len(full) >= _MIN_TRIGGER_LEN and full not in _FILENAME_NOISE:
        triggers.append(full)
    for t in tokens:
        if (
            len(t) >= _MIN_TRIGGER_LEN
            and t not in _FILENAME_NOISE
            and t not in triggers
        ):
            triggers.append(t)
    return triggers[:4]


def _detect_base_from_filename(fname: str) -> str:
    f = fname.lower()
    if "ilxl" in f or "illust" in f or "_il" in f or "-il" in f:
        return "ilxl"
    if "pony" in f or "pdxl" in f:
        return "ponyxl"
    if "sdxl" in f or "_xl" in f:
        return "sdxl"
    if "flux" in f:
        return "flux"
    return "sdxl"


def _detect_category_from_filename(fname: str) -> str:
    f = fname.lower()
    nsfw_hints = (
        "nsfw",
        "xray",
        "x-ray",
        "x_ray",
        "cervix",
        "cameltoe",
        "cum",
        "speculum",
        "vibrator",
        "spread",
        "anal",
        "pussy",
        "nude",
        "creampie",
        "tape_gape",
        "tapegape",
        "armpit_hair",
    )
    if any(h in f for h in nsfw_hints):
        return "nsfw"
    style_hints = ("style", "outline", "detail", "anatomy", "pose", "concept")
    if any(h in f for h in style_hints):
        return "style"
    return "character"


def _load_inventory() -> dict:
    if not _INVENTORY_PATH.exists():
        return {"items": []}
    try:
        return json.loads(_INVENTORY_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("[lora_resolver] inventory load failed: %s", e)
        return {"items": []}


def _build_runtime_catalog() -> dict[str, dict]:
    out: dict[str, dict] = {}

    # 1) Curated catalog â€” also expand triggers with diacritic-stripped variants.
    for key, entry in LORA_CATALOG.items():
        triggers = list(entry.get("trigger") or [])
        extra = []
        for t in triggers:
            stripped = _strip_diacritics(t)
            if stripped != t.lower() and stripped not in extra:
                extra.append(stripped)
        merged = dict(entry)
        merged["trigger"] = triggers + extra
        merged["_source"] = "curated"
        out[key] = merged

    # 2) Inventory-derived entries.
    curated_files = {(e.get("file") or "").lower() for e in LORA_CATALOG.values()}
    inv = _load_inventory()
    derived = 0
    for item in inv.get("items", []):
        fname = item.get("name") or ""
        if not fname or fname.lower() in curated_files:
            continue
        triggers = _derive_triggers_from_filename(fname)
        if not triggers:
            continue
        key = "inv:" + re.sub(r"\s+", "_", triggers[0])[:48]
        if key in out:
            continue
        out[key] = {
            "file": fname,
            "trigger": triggers,
            "category": _detect_category_from_filename(fname),
            "base": _detect_base_from_filename(fname),
            "weight": 0.75,
            "_source": "inventory",
        }
        derived += 1

    logger.info(
        "[lora_resolver] runtime catalog built: %d curated + %d derived = %d",
        len(LORA_CATALOG),
        derived,
        len(out),
    )
    return out


def _get_catalog(force_reload: bool = False) -> dict[str, dict]:
    global _RUNTIME_CATALOG, _INVENTORY_MTIME
    mtime = _INVENTORY_PATH.stat().st_mtime if _INVENTORY_PATH.exists() else 0.0
    if force_reload or _RUNTIME_CATALOG is None or mtime != _INVENTORY_MTIME:
        _RUNTIME_CATALOG = _build_runtime_catalog()
        _INVENTORY_MTIME = mtime
    return _RUNTIME_CATALOG


def _compile_patterns(
    catalog: dict[str, dict],
) -> list[tuple[re.Pattern, str, str, dict]]:
    """Compile word-boundary anchored patterns per trigger.

    Patterns match against ASCII-folded text so 'huohuo' fires on
    'há»a há»a' too. Boundaries use lookarounds instead of `\\b` to
    keep behavior identical for ASCII and non-ASCII contexts.
    """
    patterns: list[tuple[re.Pattern, str, str, dict]] = []
    for key, entry in catalog.items():
        seen_phrase: set[str] = set()
        for phrase in entry.get("trigger") or []:
            if not phrase or len(phrase) < _MIN_TRIGGER_LEN:
                continue
            folded = _strip_diacritics(phrase)
            if not folded or folded in seen_phrase:
                continue
            seen_phrase.add(folded)
            try:
                pat = re.compile(
                    rf"(?<![A-Za-z0-9]){re.escape(folded)}(?![A-Za-z0-9])",
                    re.IGNORECASE,
                )
            except re.error as e:
                logger.warning("[lora_resolver] bad pattern %r: %s", phrase, e)
                continue
            patterns.append((pat, key, phrase, entry))
    return patterns


def _get_patterns(
    force_reload: bool = False,
) -> list[tuple[re.Pattern, str, str, dict]]:
    global _COMPILED_PATTERNS
    if force_reload or _COMPILED_PATTERNS is None:
        _COMPILED_PATTERNS = _compile_patterns(_get_catalog(force_reload=force_reload))
    return _COMPILED_PATTERNS


def reload_catalog() -> dict:
    """Force-rebuild the runtime catalog (e.g. after inventory rescan)."""
    cat = _get_catalog(force_reload=True)
    _get_patterns(force_reload=True)
    return {
        "total": len(cat),
        "curated": sum(1 for v in cat.values() if v.get("_source") == "curated"),
        "derived": sum(1 for v in cat.values() if v.get("_source") == "inventory"),
    }


def resolve_loras_from_text(
    prompt: str,
    *,
    exclude_keys: Iterable[str] = (),
    max_loras: int = _MAX_AUTO_LORAS,
    include_categories: tuple[str, ...] = ("character", "style", "nsfw"),
    include_derived: bool = True,
) -> list[ResolvedLora]:
    """Return LoRAs whose triggers appear in `prompt`."""
    if not prompt:
        return []

    folded = _strip_diacritics(prompt)
    excluded = {k.lower() for k in exclude_keys}

    out: list[ResolvedLora] = []
    seen_files: set[str] = set()
    seen_keys: set[str] = set()

    for pat, key, phrase, entry in _get_patterns():
        if key.lower() in excluded or key in seen_keys:
            continue
        if entry.get("category") not in include_categories:
            continue
        is_derived = entry.get("_source") == "inventory"
        if is_derived and not include_derived:
            continue
        if not pat.search(folded):
            continue

        fname = entry.get("file", "")
        if not fname or fname in seen_files:
            continue
        seen_files.add(fname)
        seen_keys.add(key)

        weight = float(entry.get("weight", 0.8))
        clip_w = float(entry.get("clip_weight", weight))
        out.append(
            ResolvedLora(
                spec=LoraSpec(
                    name=fname,
                    weight=weight,
                    clip_weight=clip_w,
                    trigger_words=list(entry.get("trigger") or []),
                ),
                matched_phrase=phrase,
                catalog_key=key,
                category=entry.get("category", ""),
                base=entry.get("base", ""),
                auto_derived=is_derived,
            )
        )

    # Rank: curated first; within source, characters > styles > nsfw.
    cat_rank = {"character": 0, "style": 1, "anatomy": 2, "quality": 3, "nsfw": 4}
    out.sort(
        key=lambda r: (
            1 if r.auto_derived else 0,
            cat_rank.get(r.category, 9),
        )
    )
    return out[:max_loras]


def suggest_for_chat(prompt: str) -> dict:
    resolved = resolve_loras_from_text(prompt)
    return {
        "prompt": prompt,
        "count": len(resolved),
        "loras": [
            {
                "key": r.catalog_key,
                "file": r.spec.name,
                "weight": r.spec.weight,
                "category": r.category,
                "base": r.base,
                "matched": r.matched_phrase,
                "auto_derived": r.auto_derived,
                "trigger_words": r.spec.trigger_words[:6],
            }
            for r in resolved
        ],
    }


def catalog_stats() -> dict:
    cat = _get_catalog()
    return {
        "total": len(cat),
        "curated": sum(1 for v in cat.values() if v.get("_source") == "curated"),
        "derived": sum(1 for v in cat.values() if v.get("_source") == "inventory"),
        "patterns": len(_get_patterns()),
    }


__all__ = [
    "ResolvedLora",
    "resolve_loras_from_text",
    "suggest_for_chat",
    "reload_catalog",
    "catalog_stats",
]
