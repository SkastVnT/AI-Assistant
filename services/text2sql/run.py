"""
Text2SQL Service Entry Point
Run with: python run.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Run the Text2SQL service."""
    from app import create_app
    from app.config import get_config
    
    config = get_config()
    app = create_app()
    
    # Print startup banner
    print("=" * 60)
    print("ðŸ” TEXT2SQL SERVICE v2.0")
    print("=" * 60)
    print(f"ðŸ“ URL: http://{config.HOST}:{config.PORT}")
    print(f"ðŸ› Debug: {config.DEBUG}")
    print(f"ðŸ¤– Default Model: {config.DEFAULT_SQL_MODEL}")
    print(f"ðŸ”§ Refine Strategy: {config.REFINE_STRATEGY}")
    print("=" * 60)
    
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )


if __name__ == '__main__':
    main()
