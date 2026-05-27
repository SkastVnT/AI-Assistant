"""
Core package for chatbot
"""

import sys
from pathlib import Path

# Setup path for imports
CHATBOT_DIR = Path(__file__).parent.parent.resolve()
ROOT_DIR = CHATBOT_DIR.parent.parent
APP_ROOT = ROOT_DIR / "app"

if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))
if str(APP_ROOT) not in sys.path:
    sys.path.insert(1, str(APP_ROOT))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(2, str(ROOT_DIR))
