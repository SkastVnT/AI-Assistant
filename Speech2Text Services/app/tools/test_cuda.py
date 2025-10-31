# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# Test script to verify CUDA functionality

import torch
print("=== PyTorch CUDA Test ===")
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU count: {torch.cuda.device_count()}")
    print(f"GPU name: {torch.cuda.get_device_name(0)}")
    print(f"GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

print("\n=== faster-whisper CUDA Test ===")
try:
    from faster_whisper import WhisperModel
    print("Loading tiny model with CUDA...")
    model = WhisperModel('tiny', device='cuda', compute_type='float16')
    print("[OK] faster-whisper can use CUDA successfully!")
    del model  # Free memory
except Exception as e:
    print(f"[?] faster-whisper CUDA error: {e}")
    print("Trying CPU fallback...")
    try:
        model = WhisperModel('tiny', device='cpu')
        print("[OK] faster-whisper works with CPU")
        del model
    except Exception as e2:
        print(f"[?] faster-whisper CPU error: {e2}")

print("\n=== Transformers CUDA Test ===")
try:
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Testing transformers with device: {device}")
    
    # Test with a small model first
    processor = WhisperProcessor.from_pretrained("openai/whisper-tiny")
    print("[OK] WhisperProcessor loaded")
    
    model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-tiny")
    if device == "cuda":
        model = model.half().to(device)
        print("[OK] Whisper model loaded to CUDA with half precision")
    else:
        model = model.to(device)
        print("[OK] Whisper model loaded to CPU")
    
    del model, processor
    print("[OK] transformers works successfully!")
    
except Exception as e:
    print(f"[?] transformers error: {e}")

print("\n=== Summary ===")
if torch.cuda.is_available():
    print("[SUCCESS] CUDA setup is working! Your dual model script should now run with GPU acceleration.")
else:
    print("[WARN] CUDA not available, but CPU fallback should work.")