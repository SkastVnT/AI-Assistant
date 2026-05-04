"""Minimal manual-profile preview/save for characters missing from
SAA / local registry / alias table.

Pure helpers — no web, no vision, no GPU, no ComfyUI imports.
Reuses existing slug + identity-block builders from
``core.character_understanding`` so the preview matches what the runtime
resolver would produce.

Public API:
    preview_manual_profile(payload)        -> dict
    save_manual_profile(payload, force=False) -> dict
    OVERRIDES_PATH                          -> Path
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.character_understanding import (
    _build_identity_block,
    _load_manual_overrides,
    _slugify,
    make_canonical_id,
)
from core.character_registry import get_registry

logger = logging.getLogger(__name__)

OVERRIDES_PATH = (
    Path(__file__).resolve().parent.parent / "config" / "character_overrides.json"
)

_ALLOWED_FIELDS = {
    "display_name",
    "series_name",
    "series_slug",
    "character_slug",
    "aliases",
    "visual_traits",
    "outfit_traits",
    "personality_traits",
    "negative_identity_guard",
    "scene_hints",
    "reference_images",
    "notes",
}


# ── Validation ─────────────────────────────────────────────────────────────

def _norm_list(val: Any) -> list[str]:
    if not val:
        return []
    if isinstance(val, str):
        # Tolerate newline / comma separated input from textareas.
        parts = [p.strip() for p in val.replace(",", "\n").split("\n")]
        return [p for p in parts if p]
    if isinstance(val, list):
        return [str(p).strip() for p in val if str(p).strip()]
    return []


def _normalize(payload: dict) -> dict:
    """Trim and coerce a raw manual_profile payload into the canonical shape.

    Drops keys not in :data:`_ALLOWED_FIELDS`. Returns ``{}`` for falsy
    input. Never raises.
    """
    if not isinstance(payload, dict):
        return {}
    out: dict = {}
    for k in _ALLOWED_FIELDS:
        if k not in payload:
            continue
        v = payload.get(k)
        if k in {
            "aliases",
            "visual_traits",
            "outfit_traits",
            "personality_traits",
            "negative_identity_guard",
            "scene_hints",
            "reference_images",
        }:
            lst = _norm_list(v)
            if lst:
                out[k] = lst
        else:
            sv = ("" if v is None else str(v)).strip()
            if sv:
                out[k] = sv
    return out


def _validate(profile: dict) -> list[str]:
    """Return human-readable warnings for a normalized profile."""
    warnings: list[str] = []
    if not profile.get("display_name"):
        warnings.append("display_name is required")
    if not profile.get("series_slug") and not profile.get("series_name"):
        warnings.append(
            "series_name or series_slug is recommended — without it the "
            "canonical_id collides with same-named characters from other series"
        )
    if not profile.get("visual_traits"):
        warnings.append(
            "visual_traits is empty — the identity block will be very thin "
            "and renders may drift"
        )
    refs = profile.get("reference_images") or []
    bad_refs = [
        r for r in refs
        if not (r.startswith("http://") or r.startswith("https://") or r.startswith("/"))
    ]
    if bad_refs:
        warnings.append(
            f"reference_images contains {len(bad_refs)} non-URL entries "
            "(must start with http://, https://, or /)"
        )
    return warnings


# ── Preview ────────────────────────────────────────────────────────────────

def preview_manual_profile(payload: dict) -> dict:
    """Build a preview of how the runtime would treat this manual profile.

    Always returns ``safe_to_attach_lora=False`` and ``needs_review=True``
    — manual profiles never auto-attach LoRA. ``needs_review`` stays True
    until a curator promotes the entry into the persistent override file.

    Output keys:
        canonical_id, provisional_id, character_slug, series_slug,
        display_name, series_name, character_identity_block,
        safe_to_attach_lora, needs_review, mode, warnings, duplicates,
        normalized.
    """
    profile = _normalize(payload)
    warnings = _validate(profile)

    display = profile.get("display_name", "")
    series_name = profile.get("series_name", "")
    series_slug = _slugify(profile.get("series_slug", "") or series_name)
    char_slug = _slugify(profile.get("character_slug", "") or display)
    canonical_id = make_canonical_id(char_slug, series_slug) if char_slug else ""
    provisional_id = canonical_id or f"unknown:{_slugify(display) or 'unspecified'}@"

    identity_block = _build_identity_block(
        raw_name=display,
        possible_series=series_slug,
        visual_traits=profile.get("visual_traits", []),
        outfit_traits=profile.get("outfit_traits", []),
        negative_identity_guard=profile.get("negative_identity_guard", []),
    )

    duplicates = _find_duplicates(canonical_id, char_slug, profile.get("aliases", []))
    if duplicates:
        warnings.append(
            "duplicate detected: "
            + ", ".join(f"{d['source']}:{d['where']}" for d in duplicates)
        )

    return {
        "canonical_id": canonical_id,
        "provisional_id": provisional_id,
        "character_slug": char_slug,
        "series_slug": series_slug,
        "display_name": display,
        "series_name": series_name,
        "character_identity_block": identity_block,
        "safe_to_attach_lora": False,  # always False for manual profiles
        "needs_review": True,
        "mode": "low_data_profile",
        "warnings": warnings,
        "duplicates": duplicates,
        "normalized": profile,
    }


def _find_duplicates(canonical_id: str, char_slug: str, aliases: list[str]) -> list[dict]:
    """Look for collisions in the existing override file and registry.

    Returns a list of ``{"source", "where"}`` dicts. ``source`` is one of
    ``"override"`` or ``"registry"``. ``where`` describes the matching field.
    """
    out: list[dict] = []
    alias_set = {_slugify(a) for a in (aliases or []) if a}

    # Override file
    for entry in _load_manual_overrides():
        if not isinstance(entry, dict):
            continue
        if canonical_id and entry.get("canonical_id") == canonical_id:
            out.append({"source": "override", "where": f"canonical_id={canonical_id}"})
            continue
        entry_aliases = {_slugify(a) for a in (entry.get("aliases", []) or ())}
        entry_aliases.add(_slugify(entry.get("display_name", "")))
        if char_slug and char_slug in entry_aliases:
            out.append({"source": "override", "where": f"alias={char_slug}"})
            continue
        if alias_set & entry_aliases:
            out.append({
                "source": "override",
                "where": "alias=" + next(iter(alias_set & entry_aliases)),
            })

    # Local registry
    try:
        reg = get_registry()
        if char_slug:
            for r in reg.find(query=char_slug, limit=5):
                out.append({"source": "registry", "where": f"key={r.key}"})
    except Exception as exc:  # noqa: BLE001
        logger.debug("manual_profile: registry duplicate-check skipped (%s)", exc)

    return out


# ── Save ───────────────────────────────────────────────────────────────────

def save_manual_profile(payload: dict, *, force: bool = False) -> dict:
    """Append a manual profile to ``character_overrides.json`` if safe.

    "Safe" means: no validation errors, no duplicates, and the profile
    has at least display_name + (series_slug or series_name) + one
    visual_trait.

    When unsafe (or when the file is missing and we don't want to create
    it implicitly), returns ``{"saved": False, "reason", "preview",
    "suggested_json", "target_path"}`` so the caller can paste it into
    the file manually. Existing entries are NEVER silently overwritten.

    ``force=True`` only bypasses the duplicate check; it does NOT bypass
    validation errors.
    """
    preview = preview_manual_profile(payload)
    profile = preview["normalized"]
    warnings = list(preview["warnings"])

    # Hard validation errors (everything except the duplicate warning).
    hard_errors = [
        w for w in warnings
        if w.startswith("display_name is required")
        or w.startswith("series_name or series_slug")
        or w.startswith("visual_traits is empty")
        or w.startswith("reference_images contains")
    ]
    has_dupes = bool(preview["duplicates"])

    suggested = {
        "canonical_id": preview["canonical_id"],
        "display_name": preview["display_name"],
        "character_slug": preview["character_slug"],
        "series_name": preview["series_name"],
        "series_slug": preview["series_slug"],
        "data_status": "manual_override",
        "needs_review": True,
        **{k: v for k, v in profile.items() if k not in {
            "display_name", "series_name", "series_slug", "character_slug",
        }},
    }

    if hard_errors or (has_dupes and not force):
        return {
            "saved": False,
            "reason": (
                "validation failed: " + "; ".join(hard_errors)
                if hard_errors else
                "duplicate canonical_id or alias — pass force=true to override "
                "after manually editing the existing entry"
            ),
            "preview": preview,
            "suggested_json": suggested,
            "target_path": str(OVERRIDES_PATH),
        }

    # Safe path — append (or create file). Never silently overwrite.
    try:
        if OVERRIDES_PATH.exists():
            data = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("character_overrides.json is not a JSON object")
            chars = data.get("characters")
            if not isinstance(chars, list):
                chars = []
                data["characters"] = chars
        else:
            data = {"characters": []}
            chars = data["characters"]

        # Final overwrite guard — even with force=True, refuse to clobber an
        # entry with the SAME canonical_id. The user must edit-in-place.
        cid = preview["canonical_id"]
        if cid:
            for entry in chars:
                if isinstance(entry, dict) and entry.get("canonical_id") == cid:
                    return {
                        "saved": False,
                        "reason": (
                            f"canonical_id {cid!r} already exists — refusing to "
                            "silently overwrite. Edit the existing entry in "
                            f"{OVERRIDES_PATH.name} manually."
                        ),
                        "preview": preview,
                        "suggested_json": suggested,
                        "target_path": str(OVERRIDES_PATH),
                    }

        chars.append(suggested)
        OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
        OVERRIDES_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return {
            "saved": True,
            "preview": preview,
            "target_path": str(OVERRIDES_PATH),
            "warnings": warnings,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("manual_profile: save failed (%s)", exc)
        return {
            "saved": False,
            "reason": f"write failed: {exc}",
            "preview": preview,
            "suggested_json": suggested,
            "target_path": str(OVERRIDES_PATH),
        }


__all__ = ["preview_manual_profile", "save_manual_profile", "OVERRIDES_PATH"]
