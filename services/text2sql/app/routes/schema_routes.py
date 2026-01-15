"""
Schema Routes
Schema upload and management endpoints
"""

from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

schema_bp = Blueprint('schema', __name__)


@schema_bp.route('/upload-schema', methods=['POST'])
def upload_schema():
    """
    Upload database schema file.
    Supports: txt, json, jsonl, csv, sql
    """
    from ..controllers.schema_controller import SchemaController
    controller = SchemaController()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    
    success, message, data = controller.upload_schema(file)
    
    if success:
        return jsonify({
            'message': message,
            **data
        })
    else:
        return jsonify({'error': message}), 400


@schema_bp.route('/schema', methods=['GET'])
def get_schema():
    """Get current schema information."""
    from ..controllers.schema_controller import SchemaController
    controller = SchemaController()
    
    result = controller.get_schema_info()
    return jsonify(result)


@schema_bp.route('/schema/clear', methods=['POST', 'DELETE'])
def clear_schema():
    """Clear all uploaded schemas."""
    from ..controllers.schema_controller import SchemaController
    controller = SchemaController()
    
    success = controller.clear_schemas()
    
    if success:
        return jsonify({'message': 'All schemas cleared'})
    else:
        return jsonify({'error': 'Failed to clear schemas'}), 500


@schema_bp.route('/tables', methods=['GET'])
def get_tables():
    """Get list of known tables."""
    from ..controllers.schema_controller import SchemaController
    controller = SchemaController()
    
    result = controller.get_tables()
    return jsonify(result)
