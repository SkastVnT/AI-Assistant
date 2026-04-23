"""
Flask blueprint — Character Select SAA sidecar status route.

Endpoints:
  GET /api/character-select/status — feature flag + reachability
  GET /api/character-select/url    — URL the frontend should open
  GET /api/local-image-gen/recent  — list new ComfyUI output files since `since`
  GET /api/local-image-gen/file/<name> — serve one file from the ComfyUI output dir
"""
import logging

from flask import Blueprint, abort, jsonify, request, send_file

character_select_bp = Blueprint('character_select', __name__)
logger = logging.getLogger(__name__)


@character_select_bp.route('/api/character-select/status', methods=['GET'])
def character_select_status_route():
    """Return enable flag + sidecar reachability status."""
    try:
        from core.character_select_adapter import get_status, install_path_exists
        result = get_status()
        result['installed'] = install_path_exists()
    except Exception as exc:
        logger.error("[CHARACTER-SELECT-ROUTE] Status error: %s", exc)
        return jsonify({
            'enabled': False, 'reachable': False, 'running': False,
            'error': f'Internal error: {exc}',
        }), 500

    return jsonify(result), 200


@character_select_bp.route('/api/character-select/url', methods=['GET'])
def character_select_url_route():
    """Return the URL the frontend should open to access the SAA picker."""
    from core.config import (
        CHARACTER_SELECT_ENABLED,
        CHARACTER_SELECT_URL,
    )
    return jsonify({
        'enabled': bool(CHARACTER_SELECT_ENABLED),
        'url': CHARACTER_SELECT_URL,
    }), 200


# ── Local image gen bridge (ComfyUI output watcher) ──────────────────


@character_select_bp.route('/api/local-image-gen/recent', methods=['GET'])
def local_image_gen_recent():
    """Return ComfyUI output files newer than ``since`` (epoch seconds)."""
    try:
        since = float(request.args.get('since', '0') or 0)
    except (TypeError, ValueError):
        since = 0.0
    try:
        limit = max(1, min(int(request.args.get('limit', '12') or 12), 48))
    except (TypeError, ValueError):
        limit = 12

    from core.local_image_gen_watch import list_recent
    payload = list_recent(since=since, limit=limit)
    status = 200 if payload.get('ok') else 503
    return jsonify(payload), status


@character_select_bp.route('/api/local-image-gen/file/<path:name>', methods=['GET'])
def local_image_gen_file(name: str):
    """Serve a single file from the ComfyUI output directory."""
    from core.local_image_gen_watch import resolve_file
    path, mime = resolve_file(name)
    if path is None:
        abort(404)
    return send_file(str(path), mimetype=mime, conditional=True)

