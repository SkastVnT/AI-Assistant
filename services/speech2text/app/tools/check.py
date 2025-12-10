#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
VistralS2T System Health Check
Verifies all dependencies and system requirements
"""

import sys
import os

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def check_python():
    """Check Python version"""
    print("\n[1/8] Python Version")
    print(f"  ✓ Python {sys.version.split()[0]}")
    if sys.version_info >= (3, 10) and sys.version_info < (3, 11):
        print("  ✓ Version OK (3.10.x required)")
        return True
    else:
        print("  ✗ Version mismatch (3.10.x recommended)")
        return False

def check_pytorch():
    """Check PyTorch and CUDA"""
    print("\n[2/8] PyTorch & CUDA")
    try:
        import torch
        print(f"  ✓ PyTorch {torch.__version__}")
        
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            print(f"  ✓ CUDA Available: {torch.cuda.get_device_name(0)}")
            print(f"  ✓ CUDA Version: {torch.version.cuda}")
            return True
        else:
            print("  ⚠ CUDA not available (CPU mode)")
            return True
    except ImportError as e:
        print(f"  ✗ PyTorch not found: {e}")
        return False

def check_transformers():
    """Check Transformers library"""
    print("\n[3/8] Transformers & HuggingFace")
    try:
        import transformers
        print(f"  ✓ Transformers {transformers.__version__}")
        
        import huggingface_hub
        print(f"  ✓ HuggingFace Hub installed")
        return True
    except ImportError as e:
        print(f"  ✗ Transformers/HF Hub not found: {e}")
        return False

def check_whisper():
    """Check Faster-Whisper"""
    print("\n[4/8] Faster-Whisper")
    try:
        import faster_whisper
        print(f"  ✓ Faster-Whisper installed")
        return True
    except ImportError as e:
        print(f"  ✗ Faster-Whisper not found: {e}")
        return False

def check_audio_libs():
    """Check audio processing libraries"""
    print("\n[5/8] Audio Processing")
    libs = {
        'librosa': 'Librosa',
        'soundfile': 'SoundFile',
        'scipy': 'SciPy',
        'pydub': 'PyDub',
        'av': 'PyAV'
    }
    
    all_ok = True
    for module, name in libs.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} not found")
            all_ok = False
    
    return all_ok

def check_diarization():
    """Check speaker diarization"""
    print("\n[6/8] Speaker Diarization")
    try:
        import pyannote.audio
        print(f"  ✓ Pyannote.audio installed")
        
        # Check for HF token
        env_path = os.path.join('app', 'config', '.env')
        if os.path.exists(env_path):
            with open(env_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'HF_TOKEN' in content and 'your_token_here' not in content:
                    print(f"  ✓ HuggingFace token configured")
                else:
                    print(f"  ⚠ HF_TOKEN not set in .env (required for diarization)")
        else:
            print(f"  ⚠ .env file not found (create from .env.example)")
        
        return True
    except ImportError as e:
        print(f"  ✗ Pyannote.audio not found: {e}")
        return False
    except Exception as e:
        print(f"  ⚠ Error checking diarization: {e}")
        return True

def check_web_ui():
    """Check Web UI dependencies"""
    print("\n[7/8] Web UI Dependencies")
    libs = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'flask_socketio': 'Flask-SocketIO',
        'eventlet': 'Eventlet'
    }
    
    all_ok = True
    for module, name in libs.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} not found")
            all_ok = False
    
    return all_ok

def check_dev_tools():
    """Check development tools"""
    print("\n[8/8] Development Tools")
    tools = {
        'black': 'Black (formatter)',
        'flake8': 'Flake8 (linter)',
        'pytest': 'Pytest (testing)',
        'mypy': 'MyPy (type checker)'
    }
    
    for module, name in tools.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ⚠ {name} not found (optional)")
    
    return True

def check_directories():
    """Check project structure"""
    print("\n[Bonus] Project Structure")
    required_dirs = [
        'app',
        'app/core',
        'app/api',
        'app/config',
        'app/data',
        'app/scripts'
    ]
    
    all_ok = True
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            print(f"  ✓ {dir_path}/")
        else:
            print(f"  ✗ {dir_path}/ not found")
            all_ok = False
    
    return all_ok

def main():
    """Run all health checks"""
    print_header("VistralS2T v3.1.0 - System Health Check")
    
    checks = [
        check_python,
        check_pytorch,
        check_transformers,
        check_whisper,
        check_audio_libs,
        check_diarization,
        check_web_ui,
        check_dev_tools,
        check_directories
    ]
    
    results = []
    for check in checks:
        try:
            result = check()
            results.append(result)
        except Exception as e:
            print(f"  ✗ Check failed: {e}")
            results.append(False)
    
    # Summary
    print_header("Summary")
    passed = sum(results)
    total = len(results)
    
    print(f"\n  Passed: {passed}/{total} checks")
    
    if passed == total:
        print("  ✅ System is fully operational!")
        print("\n  Next steps:")
        print("    1. Configure .env: notepad app\\config\\.env")
        print("    2. Run transcription: run.bat")
        print("    3. Or launch Web UI: start_webui.bat")
    elif passed >= total - 2:
        print("  ⚠ System is mostly operational with minor issues")
        print("  ✓ You can proceed but some features may be limited")
    else:
        print("  ✗ System has critical issues")
        print("  ⚠ Please run: rebuild_project.bat")
    
    print("\n" + "="*70 + "\n")
    
    return 0 if passed >= total - 2 else 1

if __name__ == "__main__":
    sys.exit(main())
