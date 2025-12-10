"""
AI Assistant Hub - Entry Point
Main entry point for the Hub Gateway application
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path so 'src' and 'config' can be imported
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.hub import app, print_banner

if __name__ == '__main__':
    print_banner()
    from config.model_config import HubConfig
    app.run(
        debug=HubConfig.DEBUG,
        host=HubConfig.HOST,
        port=HubConfig.PORT
    )
