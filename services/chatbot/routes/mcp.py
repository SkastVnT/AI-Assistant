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
    logger.info("âœ… MCP integration loaded in routes")
except ImportError as e:
    logger.warning(f"âš ï¸ MCP integration not available: {e}")
    
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


@mcp_bp.route('/grep', methods=['GET'])
def mcp_grep_route():
    """Search file content by pattern (grep) via MCP blueprint."""
    check = _check_mcp_available()
    if check:
        return check
    try:
        pattern = request.args.get('pattern', '')
        file_type = request.args.get('type', 'all')
        max_results = int(request.args.get('max_results', 30))
        case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'
        regex = request.args.get('regex', 'false').lower() == 'true'

        if not pattern:
            return jsonify({
                'success': False,
                'error': 'Pattern is required'
            }), 400

        results = mcp_client.grep_content(
            pattern=pattern,
            file_type=file_type,
            max_results=max_results,
            case_sensitive=case_sensitive,
            regex=regex,
        )

        return jsonify({
            'success': True,
            'pattern': pattern,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        logger.error(f"MCP grep error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to grep files'
        }), 500


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


@mcp_bp.route('/ocr-extract', methods=['POST'])
def mcp_ocr_extract():
    """Extract text from image/document file via OCR through MCP client."""
    check = _check_mcp_available()
    if check:
        return check
    try:
        data = request.get_json() or {}
        file_path = (data.get('path') or '').strip()
        max_chars = int(data.get('max_chars', 6000))

        if not file_path:
            return jsonify({'success': False, 'error': 'File path is required'}), 400

        result = mcp_client.extract_file_with_ocr(
            file_path=file_path,
            max_chars=max(500, min(max_chars, 50000))
        )

        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid max_chars'}), 400
    except Exception as e:
        logger.error(f"MCP OCR extract error: {e}")
        return jsonify({'success': False, 'error': 'Failed to extract OCR text'}), 500


@mcp_bp.route('/grep', methods=['GET'])
def mcp_grep():
    """Search file content by pattern (grep)"""
    check = _check_mcp_available()
    if check:
        return check
    try:
        pattern = request.args.get('pattern', '')
        file_type = request.args.get('type', 'all')
        max_results = int(request.args.get('max_results', 30))
        case_sensitive = request.args.get('case_sensitive', 'false').lower() == 'true'

        if not pattern:
            return jsonify({'success': False, 'error': 'Pattern is required'}), 400

        results = mcp_client.grep_content(
            pattern=pattern,
            file_type=file_type,
            max_results=max_results,
            case_sensitive=case_sensitive
        )

        return jsonify({
            'success': True,
            'pattern': pattern,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        logger.error(f"MCP grep error: {e}")
        return jsonify({'success': False, 'error': 'Failed to grep files'}), 500


@mcp_bp.route('/warm-cache', methods=['POST'])
def mcp_warm_cache():
    """
    Trigger memory cache warmup based on user question domain before chat.
    """
    check = _check_mcp_available()
    if check:
        return check

    try:
        data = request.get_json() or {}
        question = (data.get('question') or '').strip()
        domain = data.get('domain')
        extra_queries = data.get('extra_queries') if isinstance(data.get('extra_queries'), list) else None
        force_refresh = bool(data.get('force_refresh', False))
        cache_ttl_seconds = int(data.get('cache_ttl_seconds', 900))
        limit = int(data.get('limit', 20))
        min_importance = int(data.get('min_importance', 4))
        max_chars = int(data.get('max_chars', 12000))

        if not question:
            return jsonify({'success': False, 'error': 'question is required'}), 400

        result = mcp_client.warm_memory_cache_by_question(
            question=question,
            domain=domain,
            extra_queries=extra_queries,
            force_refresh=force_refresh,
            cache_ttl_seconds=cache_ttl_seconds,
            limit=limit,
            min_importance=min_importance,
            max_chars=max_chars,
        )

        status = 200 if result.get('success') else 503
        return jsonify(result), status
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid numeric parameters'}), 400
    except Exception as e:
        logger.error(f"MCP warm cache error: {e}")
        return jsonify({'success': False, 'error': 'Failed to warm memory cache'}), 500


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
