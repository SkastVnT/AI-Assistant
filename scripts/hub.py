"""
AI Assistant Hub - Entry Point
Main entry point for the Hub Gateway application
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.hub import app, print_banner

if __name__ == '__main__':
    print_banner()
    from config.model_config import HubConfig
    app.run(
        debug=HubConfig.DEBUG,
        host=HubConfig.HOST,
        port=HubConfig.PORT
    )
