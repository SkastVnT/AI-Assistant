"""
Legacy Routes

Backward-compatible routes for existing frontend.
Maps old endpoints to new API structure.
"""

from flask import Blueprint, request, jsonify, session, render_template
from ..controllers.chat_controller import ChatController
from ..controllers.conversation_controller import ConversationController
import logging

legacy_bp = Blueprint('legacy', __name__)
chat_controller = ChatController()
conversation_controller = ConversationController()
logger = logging.getLogger(__name__)


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
        logger.error(f"Error in legacy chat: {str(e)}")
        return jsonify({'error': 'Failed to process chat message'}), 500


@legacy_bp.route('/conversations', methods=['GET'])
def legacy_list_conversations():
    """Legacy list conversations"""
    try:
        user_id = session.get('user_id', 'anonymous')
        result = conversation_controller.list_conversations(user_id=user_id)
        return jsonify({'conversations': result.get('conversations', [])}), 200
    except Exception as e:
        logger.error(f"Error listing conversations: {str(e)}")
        return jsonify({'error': 'Failed to list conversations'}), 500


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
        logger.error(f"Error creating memory: {str(e)}")
        return jsonify({'error': 'Failed to create memory'}), 500


# ============================================================================
# HEALTH & STATUS
# ============================================================================

@legacy_bp.route('/clear', methods=['POST'])
def legacy_clear():
    """Legacy clear conversation history"""
    try:
        data = request.get_json() or {}
        conversation_id = data.get('conversation_id')
        if conversation_id:
            try:
                conversation_controller.delete_conversation(
                    conversation_id=conversation_id,
                    save_for_learning=False
                )
            except Exception as e:
                logger.debug(f"Clear conversation best-effort failed: {str(e)}")
        return jsonify({'message': 'Conversation cleared'}), 200
    except Exception as e:
        logger.error(f"Error clearing conversation: {str(e)}")
        return jsonify({'error': 'Failed to clear conversation'}), 500


@legacy_bp.route('/history', methods=['GET'])
def legacy_history():
    """Legacy get conversation history"""
    try:
        user_id = session.get('user_id', 'anonymous')
        result = conversation_controller.list_conversations(user_id=user_id)
        return jsonify({
            'history': result.get('conversations', [])
        }), 200
    except Exception as e:
        logger.error(f"Error getting history: {str(e)}")
        return jsonify({'error': 'Failed to retrieve history'}), 500


# ============================================================================
# LEGACY IMAGE GENERATION ROUTES
# ============================================================================

@legacy_bp.route('/api/generate-image', methods=['POST'])
def legacy_generate_image():
    """Legacy generate image endpoint"""
    try:
        data = request.get_json() or {}
        prompt = data.get('prompt', '')

        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400

        from src.utils.comfyui_client import get_comfyui_client
        import os

        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:8189')
        sd_client = get_comfyui_client(sd_api_url)

        import base64
        image_bytes = sd_client.generate_image(
            prompt=prompt,
            negative_prompt=data.get('negative_prompt', 'bad quality, blurry'),
            width=int(data.get('width') or 1024),
            height=int(data.get('height') or 1024),
            steps=int(data.get('steps') or 20),
            cfg_scale=float(data.get('cfg_scale') or 7.0),
            seed=int(data.get('seed') or -1),
        )
        if not image_bytes:
            return jsonify({'error': 'Failed to generate image'}), 500

        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        return jsonify({'images': [base64_image]}), 200

    except ImportError:
        return jsonify({'error': 'Image generation service not available'}), 503
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        return jsonify({'error': 'Image generation failed'}), 500


@legacy_bp.route('/api/img2img', methods=['POST'])
def legacy_img2img():
    """Legacy img2img endpoint"""
    try:
        data = request.get_json() or {}
        image = data.get('image') or data.get('init_image', '')
        prompt = data.get('prompt', '')

        if not image:
            return jsonify({'error': 'Image is required'}), 400
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400

        from src.utils.comfyui_client import get_comfyui_client
        import os

        sd_api_url = os.getenv('SD_API_URL', os.getenv('COMFYUI_URL', 'http://127.0.0.1:8189'))
        sd_client = get_comfyui_client(sd_api_url)

        result = sd_client.img2img(
            init_images=[image],
            prompt=prompt,
            negative_prompt=data.get('negative_prompt', ''),
            denoising_strength=float(data.get('denoising_strength') or 0.8),
            width=int(data.get('width') or 512),
            height=int(data.get('height') or 512),
            steps=int(data.get('steps') or 30),
            cfg_scale=float(data.get('cfg_scale') or 7.0),
            seed=int(data.get('seed') or -1),
        )
        if 'error' in result:
            # Log internal error details but return a generic message to the client
            logger.error(f"ComfyUI img2img error: {result.get('error')}")
            return jsonify({'error': 'Image generation failed'}), 500

        return jsonify({'images': result.get('images', [])}), 200

    except ImportError:
        return jsonify({'error': 'Image generation service not available'}), 503
    except Exception as e:
        logger.error(f"Error in img2img: {str(e)}")
        return jsonify({'error': 'img2img failed'}), 500


@legacy_bp.route('/api/sd-models', methods=['GET'])
def legacy_sd_models():
    """Legacy get SD models endpoint"""
    try:
        from src.utils.comfyui_client import get_comfyui_client
        import os

        sd_api_url = os.getenv('SD_API_URL', 'http://127.0.0.1:8189')
        sd_client = get_comfyui_client(sd_api_url)

        models = sd_client.get_models()
        current = sd_client.get_current_model()

        return jsonify({'models': models, 'current_model': current}), 200

    except ImportError:
        return jsonify({'error': 'Image generation service not available'}), 503
    except Exception as e:
        logger.error(f"Error getting SD models: {str(e)}")
        return jsonify({'error': 'Failed to retrieve SD models'}), 500


# ============================================================================
# LEGACY MEMORY API ROUTES
# ============================================================================

@legacy_bp.route('/api/memory/save', methods=['POST'])
def legacy_api_save_memory():
    """Legacy save memory via API path"""
    from ..controllers.memory_controller import MemoryController
    controller = MemoryController()

    try:
        data = request.get_json() or {}
        user_id = session.get('user_id', 'anonymous')

        result = controller.create_memory(
            user_id=user_id,
            title=data.get('title', 'Untitled'),
            content=data.get('summary', data.get('content', '')),
            category=data.get('category', 'general')
        )

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error saving memory: {str(e)}")
        return jsonify({'error': 'Failed to save memory'}), 500


@legacy_bp.route('/api/memory/list', methods=['GET'])
def legacy_api_list_memories():
    """Legacy list memories via API path"""
    from ..controllers.memory_controller import MemoryController
    controller = MemoryController()

    try:
        user_id = session.get('user_id', 'anonymous')
        result = controller.list_memories(user_id=user_id)
        return jsonify({'memories': result.get('memories', [])}), 200
    except Exception as e:
        logger.error(f"Error listing memories: {str(e)}")
        return jsonify({'error': 'Failed to list memories'}), 500


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
