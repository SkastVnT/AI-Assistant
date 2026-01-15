"""
Settings Routes

API endpoints for user settings management.
"""

from flask import Blueprint, request, jsonify, session
from ..controllers.settings_controller import SettingsController

settings_bp = Blueprint('settings', __name__)
controller = SettingsController()


@settings_bp.route('/', methods=['GET'])
def get_settings():
    """Get user settings"""
    try:
        user_id = session.get('user_id', 'anonymous')
        result = controller.get_settings(user_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        return jsonify({'error': 'Failed to get settings'}), 500


@settings_bp.route('/', methods=['PUT'])
def update_settings():
    """
    Update user settings
    
    Request Body:
        - default_model: str (optional)
        - default_language: str (optional)
        - theme: str (optional)
        - custom_prompt: str (optional)
    """
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id', 'anonymous')
        
        result = controller.update_settings(
            user_id=user_id,
            settings=data
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        return jsonify({'error': 'Failed to update settings'}), 500


@settings_bp.route('/custom-prompts', methods=['GET'])
def list_custom_prompts():
    """Get user's custom prompts"""
    try:
        user_id = session.get('user_id', 'anonymous')
        result = controller.list_custom_prompts(user_id)
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error listing custom prompts: {str(e)}")
        return jsonify({'error': 'Failed to list custom prompts'}), 500


@settings_bp.route('/custom-prompts', methods=['POST'])
def create_custom_prompt():
    """Create a new custom prompt"""
    try:
        data = request.get_json()
        
        if not data or 'name' not in data or 'prompt' not in data:
            return jsonify({'error': 'name and prompt are required'}), 400
        
        user_id = session.get('user_id', 'anonymous')
        
        result = controller.create_custom_prompt(
            user_id=user_id,
            name=data['name'],
            prompt=data['prompt']
        )
        
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Error creating custom prompt: {str(e)}")
        return jsonify({'error': 'Failed to create custom prompt'}), 500
