"""
File Routes

API endpoints for file upload and management.
"""

from flask import Blueprint, request, jsonify, session, send_file
from ..controllers.file_controller import FileController

file_bp = Blueprint('files', __name__)
controller = FileController()


@file_bp.route('/', methods=['GET'])
def list_files():
    """List all files for current user"""
    try:
        user_id = session.get('user_id', 'anonymous')
        result = controller.list_files(user_id=user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@file_bp.route('/', methods=['POST'])
def upload_file():
    """Upload a new file"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        conversation_id = request.form.get('conversation_id')
        user_id = session.get('user_id', 'anonymous')
        
        result = controller.upload_file(
            file=file,
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        return jsonify(result), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@file_bp.route('/<file_id>', methods=['GET'])
def get_file(file_id: str):
    """Download a file"""
    try:
        file_path = controller.get_file_path(file_id)
        
        if not file_path:
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@file_bp.route('/<file_id>', methods=['DELETE'])
def delete_file(file_id: str):
    """Delete a file"""
    try:
        result = controller.delete_file(file_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
