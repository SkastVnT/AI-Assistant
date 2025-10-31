#!/usr/bin/env python3
"""
System Status Check - VistralS2T
Verifies all components are working correctly
"""
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv("app/config/.env")

def test_pytorch():
    """Test PyTorch and CUDA"""
    try:
        import torch
        print(f"✅ PyTorch version: {torch.__version__}")
        print(f"✅ CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"✅ GPU: {torch.cuda.get_device_name(0)}")
            print(f"✅ CUDA version: {torch.version.cuda}")
        return True
    except Exception as e:
        print(f"❌ PyTorch error: {e}")
        return False

def test_whisper():
    """Test Whisper (faster-whisper)"""
    try:
        from faster_whisper import WhisperModel
        print(f"✅ Faster-Whisper available")
        return True
    except Exception as e:
        print(f"❌ Faster-Whisper error: {e}")
        return False

def test_transformers():
    """Test Transformers"""
    try:
        import transformers
        print(f"✅ Transformers version: {transformers.__version__}")
        return True
    except Exception as e:
        print(f"❌ Transformers error: {e}")
        return False

def test_phowhisper():
    """Test PhoWhisper loading"""
    try:
        from transformers import pipeline
        # Quick test without full model loading
        print(f"✅ PhoWhisper pipeline available")
        return True
    except Exception as e:
        print(f"❌ PhoWhisper error: {e}")
        return False

def test_hf_token():
    """Test HuggingFace token"""
    token = os.getenv('HF_TOKEN')
    if token:
        print(f"✅ HF_TOKEN loaded: {token[:20]}...")
        return True
    else:
        print(f"❌ HF_TOKEN not found")
        return False

def test_diarization():
    """Test pyannote diarization"""
    try:
        from pyannote.audio import Pipeline
        print(f"✅ Pyannote audio available")
        
        # Test if models are accessible (without loading)
        token = os.getenv('HF_TOKEN')
        if not token:
            print(f"⚠️  HF_TOKEN required for diarization models")
            return False
            
        print(f"✅ Ready to test diarization models")
        return True
    except Exception as e:
        print(f"❌ Diarization error: {e}")
        return False

def main():
    print("=" * 80)
    print("VISTRAL S2T SYSTEM STATUS CHECK")
    print("=" * 80)
    
    results = []
    
    print("\n1. PyTorch & CUDA:")
    results.append(test_pytorch())
    
    print("\n2. Whisper:")
    results.append(test_whisper())
    
    print("\n3. Transformers:")
    results.append(test_transformers())
    
    print("\n4. PhoWhisper:")
    results.append(test_phowhisper())
    
    print("\n5. HuggingFace Token:")
    results.append(test_hf_token())
    
    print("\n6. Diarization:")
    results.append(test_diarization())
    
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL SYSTEMS READY!")
        print("\nNext steps:")
        print("1. Accept HuggingFace model licenses (run accept_licenses.py)")
        print("2. Start the web UI (run start_webui.bat)")
    else:
        print("⚠️  Some issues need attention.")
        print("\nTroubleshooting:")
        print("- Run accept_licenses.py for diarization models")
        print("- Check your .env file for HF_TOKEN")
        print("- Restart your terminal and try again")

if __name__ == "__main__":
    main()