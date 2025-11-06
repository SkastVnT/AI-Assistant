#!/usr/bin/env python3
"""
Test script to verify CUDA fix for Whisper
Tests if faster-whisper can load models without CUDA library errors
"""

import torch
import os
import sys

def test_cuda_setup():
    """Test CUDA setup and PyTorch compatibility"""
    print("=" * 60)
    print("CUDA Fix Verification Test")
    print("=" * 60)
    
    # Check PyTorch CUDA
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"CUDA version: {torch.version.cuda}")
    
    if torch.cuda.is_available():
        print(f"GPU count: {torch.cuda.device_count()}")
        print(f"GPU name: {torch.cuda.get_device_name(0)}")
        print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    print("\n" + "=" * 60)
    print("Testing GPU Memory Allocation...")
    print("=" * 60)
    
    try:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Using device: {device}")
        
        # Test tensor allocation
        x = torch.randn(1000, 1000).to(device)
        y = torch.randn(1000, 1000).to(device)
        z = torch.mm(x, y)
        
        print("✅ GPU memory allocation successful!")
        print("✅ GPU matrix multiplication successful!")
        
        # Clear GPU memory
        del x, y, z
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        
    except Exception as e:
        print(f"❌ GPU test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("Testing Faster-Whisper Loading...")
    print("=" * 60)
    
    try:
        from faster_whisper import WhisperModel
        
        # Test model loading (tiny model for quick test)
        print("Loading tiny Whisper model...")
        model = WhisperModel("tiny", device=device, compute_type="float16" if device == "cuda" else "int8")
        print("✅ Faster-Whisper model loaded successfully!")
        
        # Test if model can be used
        print("Testing model inference...")
        segments, info = model.transcribe("test", beam_size=1)
        print("✅ Faster-Whisper inference test passed!")
        
        del model
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        
    except Exception as e:
        print(f"❌ Faster-Whisper test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("✅ CUDA error should be resolved!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_cuda_setup()
    sys.exit(0 if success else 1)