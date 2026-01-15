"""
Chat Routes

API endpoints for chat functionality.
"""

from flask import Blueprint, request, jsonify, session
from ..controllers.chat_controller import ChatController
import logging

chat_bp = Blueprint('chat', __name__)
controller = ChatController()
logger = logging.getLogger(__name__)


@chat_bp.route('/send', methods=['POST'])
def send_message():
    """
    Send a message and get AI response
    
    Request Body:
        - message: str (required) - User message
        - model: str (optional) - AI model to use (default: grok)
        - context: str (optional) - Conversation context type
        - deep_thinking: bool (optional) - Enable deep analysis
        - language: str (optional) - Response language (vi/en)
        - conversation_id: str (optional) - Existing conversation ID
    
    Returns:
        - response: str - AI response
        - conversation_id: str - Conversation ID
        - model_used: str - Model that was used
        - tokens: dict - Token usage info
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        result = controller.process_message(
            message=data['message'],
            model=data.get('model', 'grok'),
            context=data.get('context', 'casual'),
            deep_thinking=data.get('deep_thinking', False),
            language=data.get('language', 'vi'),
            conversation_id=data.get('conversation_id'),
            user_id=session.get('user_id', 'anonymous')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@chat_bp.route('/models', methods=['GET'])
def get_available_models():
    """
    Get list of available AI models
    
    Returns:
        - models: list - Available models with their status
    """
    models = controller.get_available_models()
    return jsonify({'models': models}), 200


@chat_bp.route('/stream', methods=['POST'])
def stream_message():
    """
    Send message with streaming response
    
    Uses Server-Sent Events for real-time streaming.
    """
    # TODO: Implement streaming
    return jsonify({'error': 'Streaming not yet implemented'}), 501


@chat_bp.route('/regenerate', methods=['POST'])
def regenerate_response():
    """
    Regenerate the last AI response
    
    Request Body:
        - conversation_id: str (required)
        - message_id: str (optional) - Specific message to regenerate
    """
    try:
        data = request.get_json()
        
        if not data or 'conversation_id' not in data:
            return jsonify({'error': 'conversation_id is required'}), 400
        
        result = controller.regenerate_response(
            conversation_id=data['conversation_id'],
            message_id=data.get('message_id')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error regenerating response: {str(e)}")
        return jsonify({'error': 'Failed to regenerate response'}), 500
