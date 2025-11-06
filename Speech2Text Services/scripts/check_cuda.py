"""
Quick Check: CUDA & Dependencies
Kiểm tra nhanh CUDA và các thư viện
"""
import sys

print("=" * 80)
print("🔍 QUICK CHECK - CUDA & DEPENDENCIES")
print("=" * 80)
print()

# 1. Check PyTorch
print("[1/5] Checking PyTorch...")
try:
    import torch
    print(f"  ✓ PyTorch version: {torch.__version__}")
    print(f"  ✓ CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  ✓ CUDA version: {torch.version.cuda}")
        print(f"  ✓ Device: {torch.cuda.get_device_name(0)}")
        print(f"  ✓ Device count: {torch.cuda.device_count()}")
    else:
        print(f"  ⚠️ CUDA NOT available - Running on CPU (slower)")
        print(f"  💡 Fix: pip uninstall torch torchaudio")
        print(f"         pip install torch==2.2.0+cu118 torchaudio==2.2.0+cu118 --index-url https://download.pytorch.org/whl/cu118")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()

# 2. Check Transformers
print("[2/5] Checking Transformers...")
try:
    import transformers
    print(f"  ✓ Transformers version: {transformers.__version__}")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()

# 3. Check Pyannote
print("[3/5] Checking Pyannote...")
try:
    import pyannote.audio
    print(f"  ✓ Pyannote.audio installed")
    
    # Check if can load pipeline (needs token)
    from pyannote.audio import Pipeline
    import os
    token = os.getenv("HF_TOKEN") or os.getenv("HF_API_TOKEN")
    if token:
        print(f"  ✓ HF_TOKEN found: {token[:20]}...")
        # Quick test (don't actually load model)
        print(f"  ℹ️ Token configured (model loading not tested)")
    else:
        print(f"  ⚠️ HF_TOKEN not found in environment")
        print(f"  💡 Set HF_TOKEN in app/config/.env")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()

# 4. Check Faster Whisper
print("[4/5] Checking Faster Whisper...")
try:
    import faster_whisper
    print(f"  ✓ Faster-whisper installed")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()

# 5. Check Audio Libraries
print("[5/5] Checking Audio Libraries...")
try:
    import librosa
    print(f"  ✓ Librosa installed")
except Exception as e:
    print(f"  ✗ Librosa: {e}")

try:
    import soundfile
    print(f"  ✓ Soundfile installed")
except Exception as e:
    print(f"  ✗ Soundfile: {e}")

try:
    import torchcodec
    print(f"  ⚠️ Torchcodec installed (may have FFmpeg issues)")
except Exception as e:
    print(f"  ℹ️ Torchcodec: Not installed (non-critical)")

print()
print("=" * 80)
print("📊 SUMMARY")
print("=" * 80)

# Summary
has_cuda = False
try:
    import torch
    has_cuda = torch.cuda.is_available()
except:
    pass

if has_cuda:
    print("✅ CUDA is available - GPU acceleration enabled!")
    print("🚀 Processing will be FAST")
else:
    print("⚠️ CUDA not available - Running on CPU")
    print("🐌 Processing will be SLOW but functional")
    print()
    print("💡 To enable CUDA:")
    print("   1. Uninstall current PyTorch:")
    print("      pip uninstall torch torchaudio torchvision")
    print()
    print("   2. Install PyTorch with CUDA:")
    print("      pip install torch==2.2.0+cu118 torchaudio==2.2.0+cu118 --index-url https://download.pytorch.org/whl/cu118")

print()
print("=" * 80)
print("✅ Check complete! Press Enter to exit...")
input()
