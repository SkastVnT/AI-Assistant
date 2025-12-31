"""
Learning Routes

API endpoints for AI self-learning capabilities.
"""

from flask import Blueprint, request, jsonify, current_app
from ..controllers.learning_controller import LearningController

learning_bp = Blueprint('learning', __name__)
controller = LearningController()


@learning_bp.route('/data', methods=['GET'])
def list_learning_data():
    """
    Get all learning data entries
    
    Query Parameters:
        - category: str (optional) - Filter by category
        - is_approved: bool (optional) - Filter by approval status
        - min_quality: float (optional) - Minimum quality score
        - limit: int (optional) - Maximum to return
    """
    try:
        category = request.args.get('category')
        is_approved = request.args.get('is_approved')
        min_quality = float(request.args.get('min_quality', 0))
        limit = int(request.args.get('limit', 100))
        
        if is_approved is not None:
            is_approved = is_approved.lower() == 'true'
        
        result = controller.list_learning_data(
            category=category,
            is_approved=is_approved,
            min_quality=min_quality,
            limit=limit
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@learning_bp.route('/data', methods=['POST'])
def submit_learning_data():
    """
    Submit new data for AI learning
    
    Request Body:
        - source: str (required) - Data source (conversation, manual, feedback)
        - category: str (required) - Category (qa, knowledge, preference)
        - data: dict (required) - The learning data
        - quality_score: float (optional) - Initial quality score
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body is required'}), 400
        
        required = ['source', 'category', 'data']
        for field in required:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        result = controller.submit_learning_data(
            source=data['source'],
            category=data['category'],
            data=data['data'],
            quality_score=data.get('quality_score', 0.5)
        )
        
        return jsonify(result), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@learning_bp.route('/data/<data_id>/approve', methods=['POST'])
def approve_learning_data(data_id: str):
    """Approve learning data for use"""
    try:
        result = controller.approve_learning_data(data_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@learning_bp.route('/data/<data_id>/reject', methods=['POST'])
def reject_learning_data(data_id: str):
    """
    Reject learning data
    
    Request Body:
        - reason: str (optional) - Rejection reason
    """
    try:
        data = request.get_json() or {}
        result = controller.reject_learning_data(
            data_id=data_id,
            reason=data.get('reason', 'Manual rejection')
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@learning_bp.route('/extract', methods=['POST'])
def extract_from_conversation():
    """
    Extract learning data from a conversation
    
    Request Body:
        - conversation_id: str (required)
        - auto_approve: bool (optional) - Auto-approve high quality data
    """
    try:
        data = request.get_json()
        
        if not data or 'conversation_id' not in data:
            return jsonify({'error': 'conversation_id is required'}), 400
        
        result = controller.extract_from_conversation(
            conversation_id=data['conversation_id'],
            auto_approve=data.get('auto_approve', False)
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@learning_bp.route('/stats', methods=['GET'])
def get_learning_stats():
    """Get learning system statistics"""
    try:
        result = controller.get_stats()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@learning_bp.route('/deleted-conversations', methods=['GET'])
def list_deleted_conversations():
    """
    Get archived deleted conversations (for learning review)
    
    Query Parameters:
        - should_learn: bool (optional) - Filter by learning flag
    """
    try:
        should_learn = request.args.get('should_learn')
        if should_learn is not None:
            should_learn = should_learn.lower() == 'true'
        
        result = controller.list_deleted_conversations(should_learn=should_learn)
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
