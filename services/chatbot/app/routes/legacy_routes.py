"""
Legacy Routes

Backward-compatible routes for existing frontend.
Maps old endpoints to new API structure.
"""

from flask import Blueprint, request, jsonify, session, render_template
from ..controllers.chat_controller import ChatController
from ..controllers.conversation_controller import ConversationController

legacy_bp = Blueprint('legacy', __name__)
chat_controller = ChatController()
conversation_controller = ConversationController()


# ============================================================================
# PAGE ROUTES
# ============================================================================

@legacy_bp.route('/')
def index():
    """Main chatbot page"""
    return render_template('index.html')


@legacy_bp.route('/monitor')
def monitor():
    """System monitor page"""
    return render_template('monitor.html')


# ============================================================================
# LEGACY CHAT ROUTES
# ============================================================================

@legacy_bp.route('/chat', methods=['POST'])
def legacy_chat():
    """Legacy chat endpoint - redirects to new API"""
    try:
        data = request.get_json()
        
        result = chat_controller.process_message(
            message=data.get('message', ''),
            model=data.get('model', 'grok'),
            context=data.get('context', 'casual'),
            deep_thinking=data.get('deep_thinking', False),
            language=data.get('language', 'vi'),
            conversation_id=data.get('conversation_id'),
            user_id=session.get('user_id', 'anonymous'),
            # Legacy parameters
            custom_prompt=data.get('custom_prompt'),
            history=data.get('history')
        )
        
        # Map to legacy response format
        return jsonify({
            'response': result.get('response', ''),
            'model': result.get('model_used', 'grok'),
            'conversation_id': result.get('conversation_id')
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@legacy_bp.route('/conversations', methods=['GET'])
def legacy_list_conversations():
    """Legacy list conversations"""
    try:
        user_id = session.get('user_id', 'anonymous')
        result = conversation_controller.list_conversations(user_id=user_id)
        return jsonify({'conversations': result.get('conversations', [])}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@legacy_bp.route('/new_conversation', methods=['POST'])
def legacy_new_conversation():
    """Legacy create conversation"""
    try:
        user_id = session.get('user_id', 'anonymous')
        data = request.get_json() or {}
        
        result = conversation_controller.create_conversation(
            user_id=user_id,
            title=data.get('title', 'New Chat'),
            model=data.get('model', 'grok')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@legacy_bp.route('/delete_conversation/<conversation_id>', methods=['DELETE'])
def legacy_delete_conversation(conversation_id: str):
    """Legacy delete conversation"""
    try:
        result = conversation_controller.delete_conversation(
            conversation_id=conversation_id,
            save_for_learning=True
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# LEGACY MEMORY ROUTES
# ============================================================================

@legacy_bp.route('/memories', methods=['GET'])
def legacy_list_memories():
    """Legacy list memories"""
    from ..controllers.memory_controller import MemoryController
    controller = MemoryController()
    
    try:
        user_id = session.get('user_id', 'anonymous')
        result = controller.list_memories(user_id=user_id)
        return jsonify({'memories': result.get('memories', [])}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@legacy_bp.route('/save_memory', methods=['POST'])
def legacy_save_memory():
    """Legacy save memory"""
    from ..controllers.memory_controller import MemoryController
    controller = MemoryController()
    
    try:
        data = request.get_json()
        user_id = session.get('user_id', 'anonymous')
        
        result = controller.create_memory(
            user_id=user_id,
            title=data.get('title', 'Untitled'),
            content=data.get('content', ''),
            category=data.get('category', 'general')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# HEALTH & STATUS
# ============================================================================

@legacy_bp.route('/health')
def health():
    """Health check"""
    return jsonify({'status': 'healthy', 'service': 'chatbot'}), 200


@legacy_bp.route('/status')
def status():
    """Service status with model availability"""
    models = chat_controller.get_available_models()
    return jsonify({
        'status': 'running',
        'models': models
    }), 200
