"""
Pretrain Routes
Pre-training and configuration endpoints
"""

from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

pretrain_bp = Blueprint('pretrain', __name__)


@pretrain_bp.route('/pretrain', methods=['POST'])
def pretrain():
    """
    Run pre-training with uploaded data.
    """
    from ..controllers.pretrain_controller import PretrainController
    controller = PretrainController()
    
    data = request.get_json() or {}
    result = controller.run_pretrain(data)
    return jsonify(result)


@pretrain_bp.route('/pretrain-file', methods=['GET'])
def get_pretrain_files():
    """Get list of pretrain files."""
    from ..controllers.pretrain_controller import PretrainController
    controller = PretrainController()
    
    result = controller.get_pretrain_files()
    return jsonify(result)


@pretrain_bp.route('/pretrain-config', methods=['GET'])
def get_pretrain_config():
    """Get pretrain configuration."""
    from ..controllers.pretrain_controller import PretrainController
    controller = PretrainController()
    
    result = controller.get_config()
    return jsonify(result)


@pretrain_bp.route('/pretrain-report', methods=['GET'])
def get_pretrain_report():
    """Get pre-training report."""
    from ..controllers.pretrain_controller import PretrainController
    controller = PretrainController()
    
    result = controller.get_report()
    return jsonify(result)
