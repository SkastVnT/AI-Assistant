"""
Health Routes
Health check and status endpoints
"""

from flask import Blueprint, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    from ..extensions import get_ocr_processor, get_document_analyzer
    
    ocr_status = 'ready' if get_ocr_processor() else 'not initialized'
    ai_status = 'ready' if get_document_analyzer() else 'disabled'
    
    return jsonify({
        'status': 'healthy',
        'service': 'document-intelligence',
        'version': '2.0.0',
        'components': {
            'ocr': ocr_status,
            'ai': ai_status
        }
    })


@health_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    from ..extensions import get_processing_history
    
    history = get_processing_history()
    history_count = len(history.get_recent(1000)) if history else 0
    
    return jsonify({
        'service': 'document-intelligence',
        'version': '2.0.0',
        'config': {
            'ai_enabled': current_app.config.get('ENABLE_AI_ENHANCEMENT', True),
            'ai_model': current_app.config.get('AI_MODEL', 'grok-3'),
            'ocr_language': current_app.config.get('OCR_LANGUAGE', 'vi'),
            'use_gpu': current_app.config.get('OCR_USE_GPU', False)
        },
        'stats': {
            'processed_documents': history_count
        }
    })
