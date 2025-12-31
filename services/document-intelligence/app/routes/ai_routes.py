"""
AI Routes
AI-powered document analysis endpoints
"""

from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/classify', methods=['POST'])
def classify_document():
    """Classify document type using AI."""
    from ..extensions import get_document_analyzer
    
    analyzer = get_document_analyzer()
    if not analyzer:
        return jsonify({'error': 'AI not available'}), 503
    
    data = request.get_json() or {}
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        result = analyzer.classify(text)
        return jsonify({
            'success': True,
            'classification': result
        })
    except Exception as e:
        logger.error(f"Classification error: {e}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/extract', methods=['POST'])
def extract_entities():
    """Extract entities from document text."""
    from ..extensions import get_document_analyzer
    
    analyzer = get_document_analyzer()
    if not analyzer:
        return jsonify({'error': 'AI not available'}), 503
    
    data = request.get_json() or {}
    text = data.get('text', '')
    entity_types = data.get('entity_types', [])
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        result = analyzer.extract_entities(text, entity_types)
        return jsonify({
            'success': True,
            'entities': result
        })
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/summarize', methods=['POST'])
def summarize_document():
    """Summarize document content."""
    from ..extensions import get_document_analyzer
    
    analyzer = get_document_analyzer()
    if not analyzer:
        return jsonify({'error': 'AI not available'}), 503
    
    data = request.get_json() or {}
    text = data.get('text', '')
    max_length = data.get('max_length', 200)
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        result = analyzer.summarize(text, max_length)
        return jsonify({
            'success': True,
            'summary': result
        })
    except Exception as e:
        logger.error(f"Summarization error: {e}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/qa', methods=['POST'])
def question_answer():
    """Answer questions about document."""
    from ..extensions import get_document_analyzer
    
    analyzer = get_document_analyzer()
    if not analyzer:
        return jsonify({'error': 'AI not available'}), 503
    
    data = request.get_json() or {}
    text = data.get('text', '')
    question = data.get('question', '')
    
    if not text or not question:
        return jsonify({'error': 'Text and question are required'}), 400
    
    try:
        result = analyzer.answer_question(text, question)
        return jsonify({
            'success': True,
            'answer': result
        })
    except Exception as e:
        logger.error(f"Q&A error: {e}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/translate', methods=['POST'])
def translate_text():
    """Translate document text."""
    from ..extensions import get_document_analyzer
    
    analyzer = get_document_analyzer()
    if not analyzer:
        return jsonify({'error': 'AI not available'}), 503
    
    data = request.get_json() or {}
    text = data.get('text', '')
    target_lang = data.get('target_lang', 'en')
    source_lang = data.get('source_lang', 'auto')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        result = analyzer.translate(text, target_lang, source_lang)
        return jsonify({
            'success': True,
            'translation': result
        })
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return jsonify({'error': str(e)}), 500


@ai_bp.route('/insights', methods=['POST'])
def get_insights():
    """Get comprehensive insights from document."""
    from ..extensions import get_document_analyzer
    
    analyzer = get_document_analyzer()
    if not analyzer:
        return jsonify({'error': 'AI not available'}), 503
    
    data = request.get_json() or {}
    text = data.get('text', '')
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    try:
        result = analyzer.get_insights(text)
        return jsonify({
            'success': True,
            'insights': result
        })
    except Exception as e:
        logger.error(f"Insights error: {e}")
        return jsonify({'error': str(e)}), 500
