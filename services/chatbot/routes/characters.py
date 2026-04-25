"""Routes for the local character registry."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file, abort

from core.character_registry import get_registry

logger = logging.getLogger(__name__)

characters_bp = Blueprint("characters", __name__, url_prefix="/api/characters")


@characters_bp.get("")
@characters_bp.get("/")
def list_characters():
    """List/search characters.

    Query params:
        q: free-text search across display_name, aliases, character_tag.
        series: filter by series_key or series alias (GI, HSR, ...).
        limit: max results (default 50, capped at 200).
        extended: when "1"/"true" (default), augment local registry with SAA
                  WAI database matches (5149 verified characters) so the
                  picker can surface long-tail characters. Each record
                  carries ``source: "local"`` or ``source: "saa"``.
    """
    q = request.args.get("q", "", type=str)
    series = request.args.get("series", "", type=str) or None
    limit = min(max(request.args.get("limit", 50, type=int), 1), 200)
    extended = (request.args.get("extended", "1", type=str) or "1").strip().lower() not in ("0", "false", "no", "off")

    reg = get_registry()
    local = reg.find(query=q, series_filter=series, limit=limit)
    out = [{**r.to_dict(), "source": "local"} for r in local]

    # Augment with SAA WAI matches when there is room and a query was provided.
    # Series filter is honored only for local results — SAA series_hint is a
    # free-form parenthetical and not aligned with our local series_key vocabulary.
    if extended and q and not series and len(out) < limit:
        try:
            from image_pipeline.anime_pipeline.saa_character_db import (
                lookup_character, _load_wai, _wai_index,
            )
            _load_wai()
            seen_keys = {r["key"] for r in out}
            seen_tags = {r.get("character_tag", "").lower() for r in out}
            qn = q.strip().lower()
            # Walk the WAI index for substring matches; cap scan to keep <50ms.
            saa_hits: list[dict] = []
            from image_pipeline.anime_pipeline import saa_character_db as _saa_mod
            wai_index = _saa_mod._wai_index or {}
            for k, (display, tag) in wai_index.items():
                if qn in k or qn in tag.lower() or qn in display.lower():
                    if tag.lower() in seen_tags:
                        continue
                    # Use the underscored danbooru tag as the picker key — it
                    # round-trips cleanly through ``_enrich_with_character``
                    # via the SAA fallback path.
                    char_key = tag.replace(" ", "_")
                    if char_key in seen_keys:
                        continue
                    # Strip parenthesized series suffix to derive a series name.
                    import re as _re
                    m = _re.search(r"\(([^)]+)\)\s*$", tag)
                    series_name = m.group(1).strip() if m else ""
                    series_key = series_name.lower().replace(" ", "_") if series_name else ""
                    saa_hits.append({
                        "key": char_key,
                        "display_name": display or tag,
                        "series": series_name,
                        "series_key": series_key,
                        "character_tag": tag,
                        "series_tag": series_name,
                        "aliases": [],
                        "thumbnail": None,
                        "lora_hint": None,
                        "solo_recommended": True,
                        "category": "character",
                        "source": "saa",
                    })
                    seen_keys.add(char_key)
                    seen_tags.add(tag.lower())
                    if len(saa_hits) >= (limit - len(out)):
                        break
            out.extend(saa_hits)
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning("[characters] SAA augment failed: %s", exc)

    return jsonify({
        "characters": out,
        "count": len(out),
        "query": q,
        "series_filter": series,
        "extended": extended,
    })


@characters_bp.get("/series")
def list_series():
    reg = get_registry()
    return jsonify({"series": reg.list_series()})


@characters_bp.get("/<key>")
def get_character(key: str):
    reg = get_registry()
    rec = reg.get(key)
    if rec is None:
        return jsonify({"error": "not_found", "key": key}), 404
    collisions = reg.detect_collisions(rec.display_name)
    return jsonify({
        "character": rec.to_dict(),
        "collisions": [c.to_dict() for c in collisions if c.key != rec.key],
    })


@characters_bp.get("/<key>/thumbnail")
def get_thumbnail(key: str):
    reg = get_registry()
    rec = reg.get(key)
    if rec is None:
        # SAA fallback — thumbs are stored as data URLs in
        # wai_character_thumbs.json keyed by the SDXL tag (with spaces).
        try:
            from image_pipeline.anime_pipeline.saa_character_db import get_character_thumbnail
            tag = key.replace("_", " ")
            data_url = get_character_thumbnail(tag)
            if data_url and data_url.startswith("data:"):
                # data:image/png;base64,XXXX
                try:
                    header, payload = data_url.split(",", 1)
                    mime = header.split(":", 1)[1].split(";", 1)[0] or "image/png"
                    import base64 as _b64
                    raw = _b64.b64decode(payload)
                    from io import BytesIO as _BIO
                    return send_file(_BIO(raw), mimetype=mime)
                except Exception:
                    pass
        except Exception:
            pass
        abort(404)
    if not rec.thumbnail:
        abort(404)
    # Resolve relative to repo root (4 levels up from this file)
    repo_root = Path(__file__).resolve().parents[3]
    thumb_path = (repo_root / rec.thumbnail).resolve()
    # Security: ensure path stays under repo root
    try:
        thumb_path.relative_to(repo_root)
    except ValueError:
        abort(403)
    if not thumb_path.exists() or not thumb_path.is_file():
        abort(404)
    return send_file(str(thumb_path))


@characters_bp.post("/reload")
def reload_registry():
    """Force-reload the registry from disk (admin/dev convenience)."""
    reg = get_registry()
    reg.reload()
    return jsonify({"reloaded": True, "count": len(reg.list_all())})


@characters_bp.post("/resolve")
def resolve_query():
    """Resolve a free-form query to a single character record."""
    payload = request.get_json(silent=True) or {}
    q = (payload.get("query") or "").strip()
    if not q:
        return jsonify({"error": "query_required"}), 400
    reg = get_registry()
    rec = reg.resolve_query(q)
    if rec is None:
        return jsonify({"resolved": False, "query": q})
    return jsonify({"resolved": True, "query": q, "character": rec.to_dict()})
