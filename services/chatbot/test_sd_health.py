#!/usr/bin/env python
"""Test SD health check"""

import sys
import os
from pathlib import Path

# Add chatbot dir to path
CHATBOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CHATBOT_DIR))

print(f"CHATBOT_DIR: {CHATBOT_DIR}")
print(f"sys.path[0]: {sys.path[0]}")

try:
    print("\n1. Testing import...")
    from src.utils.sd_client import get_sd_client
    print("✅ Import successful")
    
    print("\n2. Creating client...")
    sd_api_url = 'http://127.0.0.1:7861'
    sd_client = get_sd_client(sd_api_url)
    print(f"✅ Client created: {sd_client}")
    
    print("\n3. Checking health...")
    is_running = sd_client.check_health()
    print(f"✅ Health check result: {is_running}")
    
    if is_running:
        print("\n4. Getting current model...")
        current_model = sd_client.get_current_model()
        print(f"✅ Current model: {current_model}")
    else:
        print("⚠️ SD is offline")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
