"""
Chatbot Application Entry Point

This file provides backward compatibility and runs the new modular application.
"""

import os
import sys
from pathlib import Path

# Ensure the app package is in path
sys.path.insert(0, str(Path(__file__).parent))

# Check if using new structure or legacy
USE_NEW_STRUCTURE = os.getenv('USE_NEW_STRUCTURE', 'false').lower() == 'true'

if USE_NEW_STRUCTURE:
    # Use new modular structure
    from app import create_app
    
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    if __name__ == '__main__':
        port = int(os.getenv('FLASK_PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
        
        print(f"🚀 Starting Chatbot (New Structure) on port {port}")
        app.run(host='0.0.0.0', port=port, debug=debug)
else:
    # Use legacy app.py
    # Import everything from the original app.py
    # This maintains backward compatibility
    
    print("ℹ️ Using legacy application structure")
    print("💡 Set USE_NEW_STRUCTURE=true to use the new modular structure")
    
    # The original app.py is too large to import directly
    # We'll just run it as the main module
    if __name__ == '__main__':
        exec(open('app.py', encoding='utf-8').read())
