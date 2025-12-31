"""
ChatBot Flask Application - Modular Version
============================================

Main entry point for the ChatBot service.
All routes are organized in separate blueprints under the routes/ folder.

Structure:
- core/config.py        - Configuration (API keys, paths)
- core/extensions.py    - Extensions (MongoDB, cache, logger)
- core/chatbot.py       - ChatbotAgent class
- core/db_helpers.py    - Database helper functions
- core/tools.py         - Tool functions (search)
- routes/main.py        - Main routes (/, /chat, /clear, /history)
- routes/conversations.py - Conversation CRUD
- routes/stable_diffusion.py - Stable Diffusion routes
- routes/memory.py      - AI Memory routes
- routes/images.py      - Image storage routes
- routes/mcp.py         - MCP integration routes
"""
import os
import sys
from pathlib import Path
from flask import Flask, send_from_directory

# Add paths for imports
CHATBOT_DIR = Path(__file__).parent.resolve()
ROOT_DIR = CHATBOT_DIR.parent.parent
sys.path.insert(0, str(CHATBOT_DIR))
sys.path.insert(0, str(ROOT_DIR))

# Create Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Configure static folder for Storage
app.static_folder = str(CHATBOT_DIR / 'static')

# Import and register extensions
from core.extensions import logger, register_monitor

# Register monitor for health checks
register_monitor(app)

# Register blueprints
from routes import register_blueprints
register_blueprints(app)

# Additional route for serving stored images
@app.route('/static/Storage/Image_Gen/<filename>')
def serve_storage_image(filename):
    """Serve images from Storage/Image_Gen folder"""
    storage_dir = CHATBOT_DIR / 'Storage' / 'Image_Gen'
    return send_from_directory(storage_dir, filename)


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return {'error': 'Not found'}, 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}")
    return {'error': 'Internal server error'}, 500


# Main entry point
if __name__ == '__main__':
    debug_mode = os.getenv('DEBUG', '0') == '1'
    host = os.getenv('HOST', '127.0.0.1')
    port = int(os.getenv('CHATBOT_PORT', '5000'))
    
    logger.info(f"🚀 Starting ChatBot on {host}:{port} (debug={debug_mode})")
    app.run(debug=debug_mode, host=host, port=port)
