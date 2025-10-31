#!/usr/bin/env python3
"""
HuggingFace Model License Acceptance Script
Accepts licenses for required pyannote models
"""
import webbrowser
import time
from dotenv import load_dotenv
import os

# Load environment
load_dotenv("app/config/.env")

def main():
    print("=" * 80)
    print("HUGGINGFACE MODEL LICENSE ACCEPTANCE")
    print("=" * 80)
    
    # Check HF token
    hf_token = os.getenv('HF_TOKEN')
    if not hf_token:
        print("❌ HF_TOKEN not found in app/config/.env")
        print("Please add your HuggingFace token to the .env file.")
        return
    
    print(f"✅ HF_TOKEN found: {hf_token[:20]}...")
    
    # Models that need license acceptance
    models_to_accept = [
        "pyannote/speaker-diarization-3.1",
        "pyannote/segmentation-3.0",
        "speechbrain/spkrec-ecapa-voxceleb"
    ]
    
    print("\n" + "=" * 80)
    print("MODELS REQUIRING LICENSE ACCEPTANCE:")
    print("=" * 80)
    
    for i, model in enumerate(models_to_accept, 1):
        print(f"\n{i}. {model}")
        print(f"   URL: https://huggingface.co/{model}")
    
    print("\n" + "=" * 80)
    print("INSTRUCTIONS:")
    print("=" * 80)
    print("1. Visit each URL above")
    print("2. Log in to HuggingFace with your account")
    print("3. Accept the license agreement for each model")
    print("4. Come back and run the web UI again")
    
    print("\n" + "=" * 80)
    print("AUTO-OPENING BROWSER WINDOWS...")
    print("=" * 80)
    
    # Auto-open browser windows
    for model in models_to_accept:
        url = f"https://huggingface.co/{model}"
        print(f"\nOpening: {url}")
        webbrowser.open(url)
        time.sleep(2)  # Small delay between opening tabs
    
    print("\n" + "=" * 80)
    print("✅ BROWSER WINDOWS OPENED!")
    print("=" * 80)
    print("\nPlease:")
    print("1. Accept licenses in the opened browser tabs")
    print("2. Run the web UI again after accepting licenses")
    print("3. Diarization should now work correctly!")
    
    input("\nPress Enter when you've accepted all licenses...")

if __name__ == "__main__":
    main()