"""
Memory Routes

API endpoints for AI memory/knowledge base management.
"""

from flask import Blueprint, request, jsonify, session
from ..controllers.memory_controller import MemoryController
import logging

memory_bp = Blueprint('memory', __name__)
controller = MemoryController()
logger = logging.getLogger(__name__)


@memory_bp.route('/', methods=['GET'])
def list_memories():
    """
    Get all memories for current user
    
    Query Parameters:
        - category: str (optional) - Filter by category
        - limit: int (optional) - Maximum to return
    """
    try:
        user_id = session.get('user_id', 'anonymous')
        category = request.args.get('category')
        limit = int(request.args.get('limit', 100))
        
        result = controller.list_memories(
            user_id=user_id,
            category=category,
            limit=limit
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@memory_bp.route('/', methods=['POST'])
def create_memory():
    """
    Create a new memory entry
    
    Request Body:
        - title: str (required) - Memory title
        - content: str (required) - Memory content
        - category: str (optional) - Category (default: general)
        - tags: list (optional) - Tags for searching
        - importance: float (optional) - Importance score 0-1
    """
    try:
        data = request.get_json()
        
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'title and content are required'}), 400
        
        user_id = session.get('user_id', 'anonymous')
        
        result = controller.create_memory(
            user_id=user_id,
            title=data['title'],
            content=data['content'],
            category=data.get('category', 'general'),
            tags=data.get('tags', []),
            importance=data.get('importance', 0.5)
        )
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Error creating memory: {str(e)}")
        return jsonify({'error': 'Failed to create memory'}), 500


@memory_bp.route('/<memory_id>', methods=['GET'])
def get_memory(memory_id: str):
    """Get a specific memory"""
    try:
        result = controller.get_memory(memory_id)
        
        if not result:
            return jsonify({'error': 'Memory not found'}), 404
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting memory: {str(e)}")
        return jsonify({'error': 'Failed to get memory'}), 500


@memory_bp.route('/<memory_id>', methods=['PUT'])
def update_memory(memory_id: str):
    """Update a memory entry"""
    try:
        data = request.get_json() or {}
        
        result = controller.update_memory(
            memory_id=memory_id,
            title=data.get('title'),
            content=data.get('content'),
            category=data.get('category'),
            tags=data.get('tags'),
            importance=data.get('importance')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error updating memory: {str(e)}")
        return jsonify({'error': 'Failed to update memory'}), 500


@memory_bp.route('/<memory_id>', methods=['DELETE'])
def delete_memory(memory_id: str):
    """Delete a memory entry"""
    try:
        result = controller.delete_memory(memory_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error deleting memory: {str(e)}")
        return jsonify({'error': 'Failed to delete memory'}), 500


@memory_bp.route('/search', methods=['GET'])
def search_memories():
    """
    Search memories by text or tags
    
    Query Parameters:
        - q: str - Search query
        - tags: str - Comma-separated tags
    """
    try:
        user_id = session.get('user_id', 'anonymous')
        query = request.args.get('q', '')
        tags = request.args.get('tags', '').split(',') if request.args.get('tags') else []
        
        result = controller.search_memories(
            user_id=user_id,
            query=query,
            tags=tags
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error searching memories: {str(e)}")
        return jsonify({'error': 'Failed to search memories'}), 500
