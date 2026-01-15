"""
Main Routes
Home page and basic endpoints
"""

from flask import Blueprint, render_template, current_app
import logging

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page - Text2SQL interface."""
    logger.info("Serving Text2SQL homepage")
    return render_template('index.html')


@main_bp.route('/about')
def about():
    """About page."""
    return {
        'name': 'Text2SQL Service',
        'version': '2.0.0',
        'description': 'Natural language to SQL query generator',
        'models': ['gemini', 'grok', 'openai', 'deepseek']
    }
