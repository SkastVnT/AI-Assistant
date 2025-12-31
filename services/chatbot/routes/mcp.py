"""
MCP (Model Context Protocol) integration routes
"""
import sys
from pathlib import Path
from flask import Blueprint, request, jsonify
import logging

# Setup path
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.extensions import logger

mcp_bp = Blueprint('mcp', __name__)

# Try to import MCP integration (optional module)
MCP_AVAILABLE = False
mcp_client = None

try:
    from src.utils.mcp_integration import get_mcp_client, inject_code_context
    mcp_client = get_mcp_client()
    MCP_AVAILABLE = True
    logger.info("✅ MCP integration loaded in routes")
except ImportError as e:
    logger.warning(f"⚠️ MCP integration not available: {e}")
    
    def inject_code_context(message, context_data, selected_files=None):
        return message


def _check_mcp_available():
    """Check if MCP is available"""
    if not MCP_AVAILABLE or mcp_client is None:
        return jsonify({
            'success': False,
            'error': 'MCP integration is not available'
        }), 503
    return None


@mcp_bp.route('/enable', methods=['POST'])
def mcp_enable():
    """Enable MCP integration"""
    check = _check_mcp_available()
    if check:
        return check
    try:
        success = mcp_client.enable()
        return jsonify({
            'success': success,
            'status': mcp_client.get_status()
        })
    except Exception as e:
        logger.error(f"MCP enable error: {e}")
        return jsonify({'success': False, 'error': 'Failed to enable MCP'}), 500


@mcp_bp.route('/disable', methods=['POST'])
def mcp_disable():
    """Disable MCP integration"""
    check = _check_mcp_available()
    if check:
        return check
    try:
        mcp_client.disable()
        return jsonify({
            'success': True,
            'status': mcp_client.get_status()
        })
    except Exception as e:
        logger.error(f"MCP disable error: {e}")
        return jsonify({'success': False, 'error': 'Failed to disable MCP'}), 500


@mcp_bp.route('/add-folder', methods=['POST'])
def mcp_add_folder():
    """Add folder to MCP access list"""
    check = _check_mcp_available()
    if check:
        return check
    try:
        data = request.get_json()
        folder_path = data.get('folder_path')
        
        if not folder_path:
            return jsonify({'success': False, 'error': 'Folder path is required'}), 400
        
        success = mcp_client.add_folder(folder_path)
        
        return jsonify({
            'success': success,
            'status': mcp_client.get_status()
        })
    except Exception as e:
        logger.error(f"MCP add folder error: {e}")
        return jsonify({'success': False, 'error': 'Failed to add folder'}), 500


@mcp_bp.route('/remove-folder', methods=['POST'])
def mcp_remove_folder():
    """Remove folder from MCP access list"""
    check = _check_mcp_available()
    if check:
        return check
    try:
        data = request.get_json()
        folder_path = data.get('folder_path')
        
        if not folder_path:
            return jsonify({'success': False, 'error': 'Folder path is required'}), 400
        
        mcp_client.remove_folder(folder_path)
        
        return jsonify({
            'success': True,
            'status': mcp_client.get_status()
        })
    except Exception as e:
        logger.error(f"MCP remove folder error: {e}")
        return jsonify({'success': False, 'error': 'Failed to remove folder'}), 500


@mcp_bp.route('/list-files', methods=['GET'])
def mcp_list_files():
    """List files in selected folders"""
    check = _check_mcp_available()
    if check:
        return check
    try:
        folder_path = request.args.get('folder')
        files = mcp_client.list_files_in_folder(folder_path)
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        logger.error(f"MCP list files error: {e}")
        return jsonify({'success': False, 'error': 'Failed to list files'}), 500


@mcp_bp.route('/search-files', methods=['GET'])
def mcp_search_files():
    """Search files in selected folders"""
    check = _check_mcp_available()
    if check:
        return check
    try:
        query = request.args.get('query', '')
        file_type = request.args.get('type', 'all')
        
        files = mcp_client.search_files(query, file_type)
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })
    except Exception as e:
        logger.error(f"MCP search files error: {e}")
        return jsonify({'success': False, 'error': 'Failed to search files'}), 500


@mcp_bp.route('/read-file', methods=['GET'])
def mcp_read_file():
    """Read file content"""
    check = _check_mcp_available()
    if check:
        return check
    try:
        file_path = request.args.get('path')
        max_lines = int(request.args.get('max_lines', 500))
        
        if not file_path:
            return jsonify({'success': False, 'error': 'File path is required'}), 400
        
        content = mcp_client.read_file(file_path, max_lines)
        
        if content and 'error' in content:
            return jsonify({'success': False, 'error': content['error']}), 400
        
        return jsonify({
            'success': True,
            'content': content
        })
    except Exception as e:
        logger.error(f"MCP read file error: {e}")
        return jsonify({'success': False, 'error': 'Failed to read file'}), 500


@mcp_bp.route('/status', methods=['GET'])
def mcp_status():
    """Get MCP client status"""
    try:
        if not MCP_AVAILABLE or mcp_client is None:
            return jsonify({
                'success': True,
                'status': {
                    'available': False,
                    'enabled': False,
                    'message': 'MCP integration module not installed'
                }
            })
        return jsonify({
            'success': True,
            'status': mcp_client.get_status()
        })
    except Exception as e:
        logger.error(f"MCP status error: {e}")
        return jsonify({'success': False, 'error': 'Failed to get MCP status'}), 500
