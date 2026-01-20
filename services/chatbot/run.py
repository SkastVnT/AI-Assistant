"""
Chatbot Application Entry Point

This file provides backward compatibility and runs the new modular application.
Handles the naming conflict between app.py and app/ directory.
"""

import os
import sys
from pathlib import Path

# Ensure the chatbot service directory is in path
service_dir = Path(__file__).parent
sys.path.insert(0, str(service_dir))

# Add project root for shared configs
project_root = service_dir.parent.parent
sys.path.insert(0, str(project_root))

# Check if using new structure or legacy
USE_NEW_STRUCTURE = os.getenv('USE_NEW_STRUCTURE', 'false').lower() == 'true'

if USE_NEW_STRUCTURE:
    # Use new modular structure - import from app package
    # We need to be careful about the naming conflict
    import importlib.util
    
    # Load the app package's __init__.py directly
    app_init_path = service_dir / 'app' / '__init__.py'
    spec = importlib.util.spec_from_file_location("chatbot_app", app_init_path)
    chatbot_app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chatbot_app_module)
    
    create_app = chatbot_app_module.create_app
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    if __name__ == '__main__':
        port = int(os.getenv('FLASK_PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
        
        print(f"🚀 Starting Chatbot (New Structure) on port {port}")
        app.run(host='0.0.0.0', port=port, debug=debug)
else:
    # Use legacy chatbot_main.py (renamed from app.py to avoid conflict)
    print("ℹ️ Using legacy application structure")
    print("💡 Set USE_NEW_STRUCTURE=true to use the new modular structure")
    
    if __name__ == '__main__':
        # Load and execute chatbot_main.py as a script to avoid import conflicts
        app_py_path = service_dir / 'chatbot_main.py'
        with open(app_py_path, 'r', encoding='utf-8') as f:
            code = compile(f.read(), app_py_path, 'exec')
            exec(code, {'__name__': '__main__', '__file__': str(app_py_path)})
