"""
Run Grok-like Simple UI
=======================

Chạy: python run_grok_ui.py
Mở: http://localhost:7860
"""

import asyncio
import logging
import os
import sys

# Add path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env file
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

from app.ui.grok_ui import create_grok_ui

if __name__ == "__main__":
    ui = create_grok_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )
