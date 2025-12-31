"""
Core package for chatbot
"""
import sys
from pathlib import Path

# Setup path for imports
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
ROOT_DIR = CHATBOT_DIR.parent.parent

if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))