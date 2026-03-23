"""
Chatbot Application Entry Point

Modes (set via environment variables):
  USE_FASTAPI=true        -> FastAPI + Uvicorn  (recommended, native async)
  USE_NEW_STRUCTURE=true  -> Flask modular app factory
  (default)               -> Legacy Flask monolith (chatbot_main.py)
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

USE_FASTAPI = os.getenv('USE_FASTAPI', 'false').lower() == 'true'
USE_NEW_STRUCTURE = os.getenv('USE_NEW_STRUCTURE', 'false').lower() == 'true'

if USE_FASTAPI:
    # -- FastAPI mode (recommended) --
    from fastapi_app import create_app as _create_fastapi_app

    app = _create_fastapi_app()

    if __name__ == '__main__':
        import uvicorn

        port = int(os.getenv('FLASK_PORT', 5000))
        reload = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'

        print(f">> Starting Chatbot (FastAPI) on port {port}")
        uvicorn.run(
            "run:app",
            host='0.0.0.0',
            port=port,
            reload=reload,
            log_level='info',
        )

elif USE_NEW_STRUCTURE:
    # -- Flask modular app factory --
    import importlib.util

    app_init_path = service_dir / 'app' / '__init__.py'
    spec = importlib.util.spec_from_file_location("chatbot_app", app_init_path)
    chatbot_app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chatbot_app_module)

    create_app = chatbot_app_module.create_app
    app = create_app(os.getenv('FLASK_ENV', 'development'))

    if __name__ == '__main__':
        port = int(os.getenv('FLASK_PORT', 5000))
        debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'

        print(f"\U0001f680 Starting Chatbot (Flask New Structure) on port {port}")
        app.run(host='0.0.0.0', port=port, debug=debug)

else:
    # -- Legacy Flask monolith --
    print("\u2139\ufe0f  Using legacy application structure")
    print("\U0001f4a1 Set USE_FASTAPI=true for async FastAPI mode")

    if __name__ == '__main__':
        app_py_path = service_dir / 'chatbot_main.py'
        with open(app_py_path, 'r', encoding='utf-8') as f:
            code = compile(f.read(), app_py_path, 'exec')
            exec(code, {'__name__': '__main__', '__file__': str(app_py_path)})
