"""
Batch Routes
Batch processing and quick actions endpoints
"""

from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

batch_bp = Blueprint('batch', __name__)


@batch_bp.route('/batch', methods=['POST'])
def batch_process():
    """Process multiple files in batch."""
    from ..extensions import get_batch_processor
    
    processor = get_batch_processor()
    data = request.get_json() or {}
    files = data.get('files', [])
    output_format = data.get('format', 'txt')
    
    if not files:
        return jsonify({'error': 'Files list is required'}), 400
    
    try:
        results = processor.process_batch(files, output_format)
        return jsonify({
            'success': True,
            'results': results,
            'processed': len(results)
        })
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        return jsonify({'error': str(e)}), 500


@batch_bp.route('/quick-actions/clean', methods=['POST'])
def quick_clean():
    """Quick action: Clean text."""
    from ..extensions import get_quick_actions
    
    actions = get_quick_actions()
    data = request.get_json() or {}
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        result = actions.clean_text(text)
        return jsonify({
            'success': True,
            'cleaned': result
        })
    except Exception as e:
        logger.error(f"Clean action error: {e}")
        return jsonify({'error': str(e)}), 500


@batch_bp.route('/quick-actions/extract', methods=['POST'])
def quick_extract():
    """Quick action: Extract patterns."""
    from ..extensions import get_quick_actions
    
    actions = get_quick_actions()
    data = request.get_json() or {}
    text = data.get('text', '')
    pattern_type = data.get('pattern', 'email')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        result = actions.extract_pattern(text, pattern_type)
        return jsonify({
            'success': True,
            'extracted': result
        })
    except Exception as e:
        logger.error(f"Extract action error: {e}")
        return jsonify({'error': str(e)}), 500


@batch_bp.route('/quick-actions/format', methods=['POST'])
def quick_format():
    """Quick action: Format text."""
    from ..extensions import get_quick_actions
    
    actions = get_quick_actions()
    data = request.get_json() or {}
    text = data.get('text', '')
    format_type = data.get('format', 'paragraph')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        result = actions.format_text(text, format_type)
        return jsonify({
            'success': True,
            'formatted': result
        })
    except Exception as e:
        logger.error(f"Format action error: {e}")
        return jsonify({'error': str(e)}), 500


@batch_bp.route('/templates', methods=['GET'])
def get_templates():
    """Get document templates."""
    from src.utils.advanced_features import DocumentTemplates
    
    templates = DocumentTemplates()
    return jsonify({
        'templates': templates.get_all()
    })


@batch_bp.route('/templates/match', methods=['POST'])
def match_template():
    """Match document to template."""
    from src.utils.advanced_features import DocumentTemplates
    
    templates = DocumentTemplates()
    data = request.get_json() or {}
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        result = templates.match(text)
        return jsonify({
            'success': True,
            'template': result
        })
    except Exception as e:
        logger.error(f"Template matching error: {e}")
        return jsonify({'error': str(e)}), 500
