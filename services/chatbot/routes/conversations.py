"""
Conversation CRUD routes
"""
import sys
from pathlib import Path
from flask import Blueprint, request, jsonify, session
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.extensions import MONGODB_ENABLED, ConversationDB, logger
from core.db_helpers import get_user_id_from_session, set_active_conversation
from core.chatbot import chatbots

conversations_bp = Blueprint('conversations', __name__)


@conversations_bp.route('/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations for current user"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        user_id = get_user_id_from_session()
        conversations = ConversationDB.get_user_conversations(user_id, include_archived=False, limit=50)
        
        for conv in conversations:
            conv['_id'] = str(conv['_id'])
        
        return jsonify({
            'conversations': conversations,
            'count': len(conversations)
        })
        
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return jsonify({'error': str(e)}), 500


@conversations_bp.route('/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get specific conversation with messages"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        conv = ConversationDB.get_conversation_with_messages(conversation_id)
        
        if not conv:
            return jsonify({'error': 'Conversation not found'}), 404
        
        conv['_id'] = str(conv['_id'])
        for msg in conv.get('messages', []):
            msg['_id'] = str(msg['_id'])
            msg['conversation_id'] = str(msg['conversation_id'])
        
        return jsonify(conv)
        
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return jsonify({'error': str(e)}), 500


@conversations_bp.route('/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        success = ConversationDB.delete_conversation(conversation_id)
        
        if success:
            if session.get('conversation_id') == conversation_id:
                session.pop('conversation_id', None)
            
            return jsonify({'message': 'Conversation deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete conversation'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        return jsonify({'error': str(e)}), 500


@conversations_bp.route('/conversations/<conversation_id>/archive', methods=['POST'])
def archive_conversation(conversation_id):
    """Archive a conversation"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        success = ConversationDB.archive_conversation(conversation_id)
        
        if success:
            return jsonify({'message': 'Conversation archived successfully'})
        else:
            return jsonify({'error': 'Failed to archive conversation'}), 500
        
    except Exception as e:
        logger.error(f"Error archiving conversation: {e}")
        return jsonify({'error': str(e)}), 500


@conversations_bp.route('/conversations/new', methods=['POST'])
def create_new_conversation():
    """Create a new conversation"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        data = request.json or {}
        user_id = get_user_id_from_session()
        
        conv = ConversationDB.create_conversation(
            user_id=user_id,
            model=data.get('model', 'grok'),
            title=data.get('title', 'New Chat')
        )
        
        set_active_conversation(conv['_id'])
        
        session_id = session.get('session_id')
        if session_id in chatbots:
            chatbots[session_id].conversation_id = conv['_id']
            chatbots[session_id].conversation_history = []
        
        conv['_id'] = str(conv['_id'])
        
        return jsonify(conv)
        
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        return jsonify({'error': str(e)}), 500


@conversations_bp.route('/conversations/<conversation_id>/switch', methods=['POST'])
def switch_conversation(conversation_id):
    """Switch to a different conversation"""
    try:
        if not MONGODB_ENABLED:
            return jsonify({'error': 'MongoDB not enabled'}), 503
        
        conv = ConversationDB.get_conversation_with_messages(conversation_id)
        
        if not conv:
            return jsonify({'error': 'Conversation not found'}), 404
        
        set_active_conversation(conversation_id)
        
        session_id = session.get('session_id')
        if session_id in chatbots:
            chatbots[session_id].conversation_id = conversation_id
            # Load history from conversation
            from core.db_helpers import load_conversation_history
            chatbots[session_id].conversation_history = load_conversation_history(conversation_id)
        
        conv['_id'] = str(conv['_id'])
        
        return jsonify({
            'message': 'Switched conversation',
            'conversation': conv
        })
        
    except Exception as e:
        logger.error(f"Error switching conversation: {e}")
        return jsonify({'error': str(e)}), 500
