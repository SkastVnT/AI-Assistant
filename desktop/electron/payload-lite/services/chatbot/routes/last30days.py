"""
Flask blueprint — last30days social media research tool route.

Provides:
  POST /api/tools/last30days — standalone API endpoint (JSON response)

The SSE streaming path uses the tool dispatch in routes/stream.py instead.
"""
import logging
import time

from flask import Blueprint, jsonify, request

last30days_bp = Blueprint('last30days', __name__)
logger = logging.getLogger(__name__)


@last30days_bp.route('/api/tools/last30days', methods=['POST'])
def last30days_research():
    """Run a last30days social-media research query.

    Request JSON:
        topic (str, required): Research topic
        depth (str, optional): quick | default | deep — default: "default"
        days (int, optional): Lookback window 1-90 — default: 30
        sources (str, optional): Comma-separated source filter
        timeout (int, optional): Override timeout in seconds

    Response JSON:
        success (bool): Whether research completed
        result (str): Markdown research report
        metadata (dict): topic, depth, days, elapsed_s
        error (str | null): Error message if any
    """
    data = request.get_json(silent=True) or {}

    topic = (data.get('topic') or '').strip()
    if not topic:
        return jsonify({
            'success': False,
            'result': '',
            'metadata': {},
            'error': 'Missing required field: topic',
        }), 400

    depth = data.get('depth', 'default')
    if depth not in ('quick', 'default', 'deep'):
        depth = 'default'

    days = data.get('days', 30)
    try:
        days = max(1, min(90, int(days)))
    except (TypeError, ValueError):
        days = 30

    sources = data.get('sources') or None
    if sources and not isinstance(sources, str):
        sources = None

    logger.info(
        "[LAST30DAYS-ROUTE] Request: topic=%r depth=%s days=%d sources=%s",
        topic, depth, days, sources,
    )

    start = time.time()
    try:
        from core.last30days_tool import run_last30days_research
        result = run_last30days_research(
            topic,
            depth=depth,
            days=days,
            sources=sources,
        )
    except Exception as e:
        logger.error("[LAST30DAYS-ROUTE] Unhandled error: %s", e)
        return jsonify({
            'success': False,
            'result': '',
            'metadata': {'topic': topic},
            'error': f'Internal error: {e}',
        }), 500

    elapsed = round(time.time() - start, 2)
    is_error = result.startswith("❌") if result else True

    logger.info(
        "[LAST30DAYS-ROUTE] Completed: success=%s elapsed=%.2fs len=%d",
        not is_error, elapsed, len(result or ''),
    )

    return jsonify({
        'success': not is_error,
        'result': result or '',
        'metadata': {
            'topic': topic,
            'depth': depth,
            'days': days,
            'elapsed_s': elapsed,
        },
        'error': result if is_error else None,
    }), 200 if not is_error else 422
