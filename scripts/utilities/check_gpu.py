#!/usr/bin/env python3
"""
GPU Detection and Verification Utility
Checks NVIDIA GPU availability, CUDA version, and PyTorch CUDA support
"""

import sys
import subprocess
import platform


def check_nvidia_smi():
    """Check if nvidia-smi is available and get GPU info."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=name,driver_version,memory.total', '--format=csv,noheader'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            gpu_info = result.stdout.strip().split('\n')
            return True, gpu_info
        return False, []
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, []


def check_cuda_version():
    """Check CUDA toolkit version."""
    try:
        result = subprocess.run(
            ['nvcc', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Parse CUDA version from output
            for line in result.stdout.split('\n'):
                if 'release' in line.lower():
                    # Extract version like "11.8"
                    parts = line.split('release')
                    if len(parts) > 1:
                        version = parts[1].strip().split(',')[0].strip()
                        return True, version
        return False, None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, None


def check_pytorch_cuda():
    """Check if PyTorch is installed and has CUDA support."""
    try:
        import torch
        
        pytorch_version = torch.__version__
        cuda_available = torch.cuda.is_available()
        
        if cuda_available:
            cuda_version = torch.version.cuda
            device_count = torch.cuda.device_count()
            current_device = torch.cuda.current_device()
            device_name = torch.cuda.get_device_name(current_device)
            
            return True, {
                'pytorch_version': pytorch_version,
                'cuda_available': True,
                'cuda_version': cuda_version,
                'device_count': device_count,
                'current_device': current_device,
                'device_name': device_name
            }
        else:
            return True, {
                'pytorch_version': pytorch_version,
                'cuda_available': False,
                'cuda_version': None
            }
    except ImportError:
        return False, None


def print_separator():
    """Print a separator line."""
    print("=" * 80)


def main():
    """Main function to check GPU capabilities."""
    print_separator()
    print("GPU Detection and Verification Utility")
    print_separator()
    print()
    
    # System info
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version.split()[0]}")
    print()
    
    # Check NVIDIA GPU
    print("[1/3] Checking NVIDIA GPU...")
    has_gpu, gpu_info = check_nvidia_smi()
    
    if has_gpu:
        print("✓ NVIDIA GPU detected:")
        for idx, info in enumerate(gpu_info):
            parts = [p.strip() for p in info.split(',')]
            if len(parts) >= 3:
                print(f"  GPU {idx}: {parts[0]}")
                print(f"    Driver: {parts[1]}")
                print(f"    Memory: {parts[2]}")
    else:
        print("✗ No NVIDIA GPU detected")
        print("  Note: CPU-only PyTorch will be used (slower for AI tasks)")
    print()
    
    # Check CUDA toolkit
    print("[2/3] Checking CUDA Toolkit...")
    has_cuda, cuda_version = check_cuda_version()
    
    if has_cuda:
        print(f"✓ CUDA Toolkit installed: {cuda_version}")
    else:
        print("✗ CUDA Toolkit not found (nvcc not in PATH)")
        if has_gpu:
            print("  Note: GPU detected but CUDA toolkit not installed")
            print("  PyTorch can still use GPU if compatible version is installed")
    print()
    
    # Check PyTorch
    print("[3/3] Checking PyTorch Installation...")
    has_pytorch, pytorch_info = check_pytorch_cuda()
    
    if has_pytorch:
        print(f"✓ PyTorch installed: {pytorch_info['pytorch_version']}")
        
        if pytorch_info['cuda_available']:
            print(f"✓ CUDA support: ENABLED (CUDA {pytorch_info['cuda_version']})")
            print(f"  Devices available: {pytorch_info['device_count']}")
            print(f"  Current device: {pytorch_info['device_name']}")
            print()
            print("✓✓✓ GPU ACCELERATION READY! ✓✓✓")
            print("  All AI services will run with GPU acceleration")
        else:
            print("✗ CUDA support: DISABLED (CPU-only version)")
            if has_gpu:
                print()
                print("⚠ WARNING: GPU detected but PyTorch has no CUDA support!")
                print("  To enable GPU acceleration, reinstall PyTorch:")
                print("  pip uninstall torch torchvision torchaudio -y")
                print("  pip install torch==2.6.0 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118")
    else:
        print("✗ PyTorch not installed")
        print("  Run setup-venv.bat or setup-all.bat to install")
    
    print()
    print_separator()
    
    # Summary and recommendations
    print("Summary:")
    print_separator()
    
    if has_gpu and has_pytorch and pytorch_info['cuda_available']:
        print("✓ Status: OPTIMAL - GPU acceleration enabled")
        print("  Your system is ready for all AI services!")
        return 0
    elif has_gpu and (not has_pytorch or not pytorch_info['cuda_available']):
        print("⚠ Status: SUBOPTIMAL - GPU detected but not utilized")
        print("  Action required: Install CUDA-enabled PyTorch")
        return 1
    else:
        print("ℹ Status: CPU-ONLY MODE")
        print("  AI services will work but may be slower")
        print("  Recommended: Get a system with NVIDIA GPU for better performance")
        return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nError: {e}")
        sys.exit(1)
