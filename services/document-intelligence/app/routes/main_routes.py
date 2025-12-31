"""
Main Routes
Home page and basic endpoints
"""

from flask import Blueprint, render_template
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page - Document Intelligence interface."""
    logger.info("Serving Document Intelligence homepage")
    return render_template('index.html')


@main_bp.route('/about')
def about():
    """About page."""
    return {
        'name': 'Document Intelligence Service',
        'version': '2.0.0',
        'description': 'OCR and AI-powered document analysis',
        'features': ['OCR', 'Classification', 'Extraction', 'Summarization', 'Translation', 'Q&A']
    }
