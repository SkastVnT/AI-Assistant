"""
Document Intelligence Service Entry Point
Run with: python run.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Run the Document Intelligence service."""
    from app import create_app
    from app.config import get_config
    
    config = get_config()
    app = create_app()
    
    # Print startup banner
    print("=" * 60)
    print("📄 DOCUMENT INTELLIGENCE SERVICE v2.0")
    print("=" * 60)
    print(f"📍 URL: http://{config.HOST}:{config.PORT}")
    print(f"🐛 Debug: {config.DEBUG}")
    print(f"🤖 AI Enabled: {config.ENABLE_AI_ENHANCEMENT}")
    print(f"📝 AI Model: {config.AI_MODEL}")
    print(f"🌐 OCR Language: {config.OCR_LANGUAGE}")
    print("=" * 60)
    
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )


if __name__ == '__main__':
    main()
