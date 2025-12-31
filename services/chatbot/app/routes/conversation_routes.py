"""
Conversation Routes

API endpoints for managing conversations.
"""

from flask import Blueprint, request, jsonify, session
from ..controllers.conversation_controller import ConversationController

conversation_bp = Blueprint('conversations', __name__)
controller = ConversationController()


@conversation_bp.route('/', methods=['GET'])
def list_conversations():
    """
    Get all conversations for current user
    
    Query Parameters:
        - include_archived: bool (optional) - Include archived conversations
        - limit: int (optional) - Maximum number to return (default: 50)
        - offset: int (optional) - Pagination offset
    
    Returns:
        - conversations: list - List of conversation summaries
        - total: int - Total count
    """
    try:
        user_id = session.get('user_id', 'anonymous')
        include_archived = request.args.get('include_archived', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        result = controller.list_conversations(
            user_id=user_id,
            include_archived=include_archived,
            limit=limit,
            offset=offset
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id: str):
    """
    Get a specific conversation with messages
    
    Path Parameters:
        - conversation_id: str - Conversation ID
    
    Query Parameters:
        - message_limit: int (optional) - Max messages to return
    
    Returns:
        - conversation: dict - Full conversation with messages
    """
    try:
        message_limit = int(request.args.get('message_limit', 100))
        
        result = controller.get_conversation(
            conversation_id=conversation_id,
            message_limit=message_limit
        )
        
        if not result:
            return jsonify({'error': 'Conversation not found'}), 404
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/', methods=['POST'])
def create_conversation():
    """
    Create a new conversation
    
    Request Body:
        - title: str (optional) - Conversation title
        - model: str (optional) - Default AI model
    
    Returns:
        - conversation: dict - Created conversation
    """
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id', 'anonymous')
        
        result = controller.create_conversation(
            user_id=user_id,
            title=data.get('title', 'New Chat'),
            model=data.get('model', 'grok')
        )
        
        return jsonify(result), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/<conversation_id>', methods=['PUT'])
def update_conversation(conversation_id: str):
    """
    Update conversation metadata
    
    Request Body:
        - title: str (optional)
        - is_archived: bool (optional)
    """
    try:
        data = request.get_json() or {}
        
        result = controller.update_conversation(
            conversation_id=conversation_id,
            title=data.get('title'),
            is_archived=data.get('is_archived')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id: str):
    """
    Delete a conversation
    
    Note: Conversation is archived to local_data for AI learning before deletion.
    
    Query Parameters:
        - save_for_learning: bool (optional) - Save for AI learning (default: true)
    """
    try:
        save_for_learning = request.args.get('save_for_learning', 'true').lower() == 'true'
        
        result = controller.delete_conversation(
            conversation_id=conversation_id,
            save_for_learning=save_for_learning
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/<conversation_id>/archive', methods=['POST'])
def archive_conversation(conversation_id: str):
    """Archive a conversation"""
    try:
        result = controller.update_conversation(
            conversation_id=conversation_id,
            is_archived=True
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@conversation_bp.route('/<conversation_id>/unarchive', methods=['POST'])
def unarchive_conversation(conversation_id: str):
    """Unarchive a conversation"""
    try:
        result = controller.update_conversation(
            conversation_id=conversation_id,
            is_archived=False
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
