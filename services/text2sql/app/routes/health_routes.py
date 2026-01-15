"""
Health Routes
Health check and debug endpoints
"""

from flask import Blueprint, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health_check():
    """Basic health check."""
    return jsonify({
        'status': 'healthy',
        'service': 'text2sql',
        'version': '2.0.0'
    })


@health_bp.route('/health/db')
def db_health():
    """Database health check."""
    from ..controllers.health_controller import HealthController
    controller = HealthController()
    
    result = controller.check_database()
    return jsonify(result)


@health_bp.route('/debug/table/<name>')
def debug_table(name: str):
    """Get table debug information."""
    from ..controllers.health_controller import HealthController
    controller = HealthController()
    
    result = controller.get_table_info(name)
    return jsonify(result)


@health_bp.route('/stats')
def get_stats():
    """Get service statistics."""
    from ..controllers.health_controller import HealthController
    controller = HealthController()
    
    result = controller.get_stats()
    return jsonify(result)
