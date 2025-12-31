"""
History Routes
Processing history endpoints
"""

from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

history_bp = Blueprint('history', __name__)


@history_bp.route('/history', methods=['GET'])
def get_history():
    """Get processing history."""
    from ..extensions import get_processing_history
    
    history = get_processing_history()
    limit = request.args.get('limit', 50, type=int)
    
    if history:
        entries = history.get_recent(limit)
        return jsonify({
            'history': entries,
            'count': len(entries)
        })
    
    return jsonify({'history': [], 'count': 0})


@history_bp.route('/history/search', methods=['GET'])
def search_history():
    """Search processing history."""
    from ..extensions import get_processing_history
    
    history = get_processing_history()
    query = request.args.get('q', '')
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    if history:
        results = history.search(query)
        return jsonify({
            'results': results,
            'count': len(results)
        })
    
    return jsonify({'results': [], 'count': 0})


@history_bp.route('/history/clear', methods=['POST'])
def clear_history():
    """Clear processing history."""
    from ..extensions import get_processing_history
    
    history = get_processing_history()
    
    if history:
        history.clear()
        return jsonify({'message': 'History cleared'})
    
    return jsonify({'error': 'History not available'}), 500
