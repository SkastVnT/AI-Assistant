#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
System Check - Verify installation after clone
"""

import sys
import os

def check_python():
    print("✓ Python version:", sys.version.split()[0])
    if sys.version_info < (3, 10):
        print("  ⚠️  Warning: Python 3.10+ recommended")
    return True

def check_venv():
    venv_path = os.path.join('app', 's2t', 'Scripts', 'python.exe')
    if os.path.exists(venv_path):
        print("✓ Virtual environment found")
        return True
    else:
        print("✗ Virtual environment NOT found")
        print("  → Run: python -m venv app/s2t")
        return False

def check_cuda():
    try:
        import torch
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            total_mem = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"✓ CUDA available: {device_name}")
            print(f"  VRAM: {total_mem:.1f}GB")
            
            # Check if enough VRAM
            if total_mem < 6:
                print(f"  ⚠️  Warning: Less than 6GB VRAM (recommended)")
            
            # Test CUDA
            try:
                x = torch.tensor([1.0]).cuda()
                print(f"  ✓ CUDA test passed")
            except Exception as e:
                print(f"  ✗ CUDA test failed: {e}")
            
            return True
        else:
            print("⚠️  CUDA not available (CPU mode - will be slow)")
            return False
    except ImportError:
        print("✗ PyTorch not installed")
        print("  → Run: pip install torch torchvision torchaudio")
        return False

def check_config():
    env_path = os.path.join('app', 'config', '.env')
    if os.path.exists(env_path):
        print("✓ Config file found")
        with open(env_path, 'r') as f:
            content = f.read()
            if 'HF_API_TOKEN' in content:
                print("  ✓ HF_API_TOKEN configured")
            else:
                print("  ⚠️  HF_API_TOKEN not set")
        return True
    else:
        print("✗ Config file NOT found")
        print("  → Copy app/config/.env.example to app/config/.env")
        return False

def check_folders():
    folders = ['app/output', 'app/audio', 'app/logs']
    missing = [f for f in folders if not os.path.exists(f)]
    if not missing:
        print("✓ Output folders ready")
        return True
    else:
        print("⚠️  Creating missing folders...")
        for folder in missing:
            os.makedirs(folder, exist_ok=True)
        print("✓ Folders created")
        return True

def check_dependencies():
    """Check if key dependencies are installed"""
    required = {
        'torch': 'PyTorch',
        'transformers': 'Transformers',
        'faster_whisper': 'Faster Whisper',
        'librosa': 'Librosa',
        'soundfile': 'SoundFile',
    }
    
    missing = []
    for module, name in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(name)
    
    if not missing:
        print("✓ All key dependencies installed")
        return True
    else:
        print(f"✗ Missing dependencies: {', '.join(missing)}")
        print("  → Run: pip install -r requirements.txt")
        return False

def check_models():
    """Check if models are cached"""
    cache_dir = os.path.join(os.path.expanduser('~'), '.cache', 'huggingface', 'hub')
    if os.path.exists(cache_dir):
        models = os.listdir(cache_dir)
        if len(models) > 0:
            print(f"✓ Found {len(models)} cached models")
            # Check for key models
            key_models = ['whisper', 'phowhisper', 'qwen']
            found = [m for m in key_models if any(m.lower() in cached.lower() for cached in models)]
            if found:
                print(f"  Including: {', '.join(found)}")
            return True
        else:
            print("⚠️  No models cached (will download on first run)")
            return True
    else:
        print("⚠️  Model cache not found (will download on first run)")
        return True

if __name__ == "__main__":
    print("=" * 60)
    print("SPEECH-TO-TEXT SYSTEM - INSTALLATION CHECK")
    print("=" * 60)
    print()
    
    checks = [
        ("Python", check_python),
        ("Virtual Environment", check_venv),
        ("Dependencies", check_dependencies),
        ("CUDA/GPU", check_cuda),
        ("Configuration", check_config),
        ("Folders", check_folders),
        ("Model Cache", check_models),
    ]
    
    results = []
    for name, check in checks:
        print(f"\n[{name}]")
        results.append(check())
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    # Check critical components
    critical_ok = all(results[:2])  # Python + venv
    deps_ok = results[2] if len(results) > 2 else False
    cuda_ok = results[3] if len(results) > 3 else False
    
    if critical_ok and deps_ok:
        print("✅ SYSTEM READY!")
        print()
        print("Next steps:")
        print("  1. Configure: notepad app\\config\\.env")
        print("  2. Run: run.bat")
        if not cuda_ok:
            print()
            print("⚠️  Note: Running on CPU (will be slow)")
            print("   Install CUDA for GPU acceleration")
    else:
        print("❌ SETUP INCOMPLETE")
        print()
        print("Fix the issues above, then:")
        print("  - Run: rebuild_project.bat (complete rebuild)")
        print("  - Or: setup.bat (quick setup)")
    
    print("=" * 60)
