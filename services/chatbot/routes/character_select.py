"""
Flask blueprint â€” Character Select SAA sidecar status route.

Endpoints:
  GET /api/character-select/status â€” feature flag + reachability
  GET /api/character-select/url    â€” URL the frontend should open
  GET /api/local-image-gen/recent  â€” list new ComfyUI output files since `since`
  GET /api/local-image-gen/file/<name> â€” serve one file from the ComfyUI output dir
"""

import logging

from flask import Blueprint, abort, jsonify, request, send_file

character_select_bp = Blueprint("character_select", __name__)
logger = logging.getLogger(__name__)


@character_select_bp.route("/api/character-select/status", methods=["GET"])
def character_select_status_route():
    """Return enable flag + sidecar reachability status."""
    try:
        from core.character_select_adapter import get_status, install_path_exists

        result = get_status()
        result["installed"] = install_path_exists()
    except Exception as exc:
        logger.error("[CHARACTER-SELECT-ROUTE] Status error: %s", exc)
        return (
            jsonify(
                {
                    "enabled": False,
                    "reachable": False,
                    "running": False,
                    "error": f"Internal error: {exc}",
                }
            ),
            500,
        )

    return jsonify(result), 200


@character_select_bp.route("/api/character-select/url", methods=["GET"])
def character_select_url_route():
    """Return the URL the frontend should open to access the SAA picker."""
    from core.config import (
        CHARACTER_SELECT_ENABLED,
        CHARACTER_SELECT_URL,
    )

    return (
        jsonify(
            {
                "enabled": bool(CHARACTER_SELECT_ENABLED),
                "url": CHARACTER_SELECT_URL,
            }
        ),
        200,
    )


# â”€â”€ Local image gen bridge (ComfyUI output watcher) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@character_select_bp.route("/api/local-image-gen/recent", methods=["GET"])
def local_image_gen_recent():
    """Return ComfyUI output files newer than ``since`` (epoch seconds)."""
    try:
        since = float(request.args.get("since", "0") or 0)
    except (TypeError, ValueError):
        since = 0.0
    try:
        limit = max(1, min(int(request.args.get("limit", "12") or 12), 48))
    except (TypeError, ValueError):
        limit = 12

    from core.local_image_gen_watch import list_recent

    payload = list_recent(since=since, limit=limit)
    status = 200 if payload.get("ok") else 503
    return jsonify(payload), status


@character_select_bp.route("/api/local-image-gen/file/<path:name>", methods=["GET"])
def local_image_gen_file(name: str):
    """Serve a single file from the ComfyUI output directory."""
    from core.local_image_gen_watch import resolve_file

    path, mime = resolve_file(name)
    if path is None:
        abort(404)
    return send_file(str(path), mimetype=mime, conditional=True)


# â”€â”€ SAA offline DB endpoints (tag autocomplete + character lookup) â”€â”€â”€
# Powered by app/image_pipeline/anime_pipeline/saa_character_db.py which
# reads app/character_select_stand_alone_app-main/data/{wai_characters.csv,
# danbooru_e621_merged.csv, wai_character_thumbs.json}. All lookups are
# in-memory after the first call, so these endpoints are safe to call
# from the chat input on every keystroke.


@character_select_bp.route("/api/tags/autocomplete", methods=["GET"])
def tags_autocomplete_route():
    """Return up to ``limit`` tag suggestions for the given ``q`` prefix.

    Response shape::
        {"ok": true, "tags": [
            {"tag": "...", "category": 0, "post_count": 42,
             "aliases": ["..."]}, ...
        ]}
    """
    q = (request.args.get("q") or "").strip()
    try:
        limit = max(1, min(int(request.args.get("limit", "20") or 20), 50))
    except (TypeError, ValueError):
        limit = 20
    if len(q) < 1:
        return jsonify({"ok": True, "tags": []}), 200

    try:
        from image_pipeline.anime_pipeline.saa_character_db import autocomplete_tag
    except Exception as exc:
        logger.warning("[SAA-DB] autocomplete unavailable: %s", exc)
        return jsonify({"ok": False, "tags": [], "error": str(exc)}), 200

    try:
        hits = autocomplete_tag(q, limit=limit)
    except Exception as exc:
        logger.exception("[SAA-DB] autocomplete lookup failed")
        return jsonify({"ok": False, "tags": [], "error": str(exc)}), 500

    return (
        jsonify(
            {
                "ok": True,
                "tags": [
                    {
                        "tag": t.tag,
                        "category": t.category,
                        "post_count": t.post_count,
                        "aliases": list(t.aliases)[:5],
                    }
                    for t in hits
                ],
            }
        ),
        200,
    )


@character_select_bp.route("/api/characters/lookup", methods=["GET"])
def character_lookup_route():
    """Resolve a free-text query against the WAI 5149-character DB.

    Response shape::
        {"ok": true, "match": {
            "display_name": "...", "tag": "...", "danbooru_tag": "...",
            "series_hint": "...", "match_score": 0.87, "thumbnail": "..."
        }}
        or {"ok": true, "match": null} when nothing resolves.
    """
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"ok": True, "match": None}), 200

    try:
        from image_pipeline.anime_pipeline.saa_character_db import (
            get_character_thumbnail,
            lookup_character,
        )
    except Exception as exc:
        return jsonify({"ok": False, "match": None, "error": str(exc)}), 200

    try:
        hit = lookup_character(q)
    except Exception as exc:
        logger.exception("[SAA-DB] character lookup failed")
        return jsonify({"ok": False, "match": None, "error": str(exc)}), 500

    if hit is None:
        return jsonify({"ok": True, "match": None}), 200

    return (
        jsonify(
            {
                "ok": True,
                "match": {
                    "display_name": hit.display_name,
                    "tag": hit.tag,
                    "danbooru_tag": hit.danbooru_tag,
                    "series_hint": hit.series_hint,
                    "match_score": hit.match_score,
                    "thumbnail": get_character_thumbnail(hit.tag),
                },
            }
        ),
        200,
    )


@character_select_bp.route("/api/saa-db/stats", methods=["GET"])
def saa_db_stats_route():
    """Diagnostic endpoint â€” returns counts for the three DB files."""
    try:
        from image_pipeline.anime_pipeline.saa_character_db import db_stats

        return jsonify({"ok": True, **db_stats()}), 200
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 200


# â”€â”€ Continuous-generation helpers (random pick + prompt swap) â”€â”€â”€â”€â”€â”€â”€â”€


@character_select_bp.route("/api/characters/random", methods=["GET"])
def character_random_route():
    """Pick a random WAI character, optionally avoiding a comma-separated
    ``exclude`` list of tags. Powers the chatbot's "Táº¡o liÃªn tá»¥c" loop
    so every iteration uses a fresh female character.

    Response shape::
        {"ok": true, "character": {
            "display_name": "...", "tag": "...", "danbooru_tag": "...",
            "series_hint": "...", "thumbnail": "..."
        }}
    """
    raw_excl = (request.args.get("exclude") or "").strip()
    excludes = [t.strip() for t in raw_excl.split(",") if t.strip()] if raw_excl else []

    try:
        from image_pipeline.anime_pipeline.saa_character_db import (
            get_character_thumbnail,
            random_character,
        )
    except Exception as exc:
        return jsonify({"ok": False, "character": None, "error": str(exc)}), 200

    try:
        hit = random_character(exclude_tags=excludes)
    except Exception as exc:
        logger.exception("[SAA-DB] random character failed")
        return jsonify({"ok": False, "character": None, "error": str(exc)}), 500

    if hit is None:
        return jsonify({"ok": True, "character": None}), 200

    return (
        jsonify(
            {
                "ok": True,
                "character": {
                    "display_name": hit.display_name,
                    "tag": hit.tag,
                    "danbooru_tag": hit.danbooru_tag,
                    "series_hint": hit.series_hint,
                    "thumbnail": get_character_thumbnail(hit.tag),
                },
            }
        ),
        200,
    )


@character_select_bp.route("/api/characters/swap-in-prompt", methods=["POST"])
def character_swap_in_prompt_route():
    """Rewrite a prompt so its lead character is replaced by a fresh
    random pick. Used by the "Táº¡o liÃªn tá»¥c" loop on every iteration.

    Request body::
        {"prompt": "...", "exclude": ["tag1", "tag2", ...]}

    Response shape::
        {"ok": true, "prompt": "<rewritten>", "character": {...},
         "swap": {"old_tag": "...", "new_tag": "...", "replaced": true}}
    """
    payload = request.get_json(silent=True) or {}
    prompt = (payload.get("prompt") or "").strip()
    excludes_raw = payload.get("exclude") or []
    excludes = [str(t).strip() for t in excludes_raw if str(t).strip()]

    if not prompt:
        return jsonify({"ok": False, "error": "prompt required"}), 400

    try:
        from image_pipeline.anime_pipeline.saa_character_db import (
            get_character_thumbnail,
            random_character,
            swap_character_in_prompt,
        )
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 200

    try:
        pick = random_character(exclude_tags=excludes)
    except Exception as exc:
        logger.exception("[SAA-DB] random pick failed")
        return jsonify({"ok": False, "error": str(exc)}), 500
    if pick is None:
        return jsonify({"ok": False, "error": "character DB empty"}), 200

    try:
        new_prompt, swap_info = swap_character_in_prompt(prompt, pick)
    except Exception as exc:
        logger.exception("[SAA-DB] swap failed")
        return jsonify({"ok": False, "error": str(exc)}), 500

    return (
        jsonify(
            {
                "ok": True,
                "prompt": new_prompt,
                "character": {
                    "display_name": pick.display_name,
                    "tag": pick.tag,
                    "danbooru_tag": pick.danbooru_tag,
                    "series_hint": pick.series_hint,
                    "thumbnail": get_character_thumbnail(pick.tag),
                },
                "swap": swap_info,
            }
        ),
        200,
    )
