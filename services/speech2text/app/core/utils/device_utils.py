"""
Device utilities for VistralS2T
Handles CPU/GPU device selection with FORCE_CPU support
"""

import os
import torch
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'config', '.env'))

def get_device(force_cpu_env_var="FORCE_CPU"):
    """
    Get the appropriate device for PyTorch operations
    
    Args:
        force_cpu_env_var (str): Environment variable name to check for forcing CPU
        
    Returns:
        str: Device string ("cuda", "cuda:0", or "cpu")
    """
    # Check if CPU is forced via environment variable
    force_cpu = os.getenv(force_cpu_env_var, "false").lower() in ["true", "1", "yes", "on"]
    
    if force_cpu:
        print("[DEVICE] CPU mode forced via environment variable")
        return "cpu"
    
    # Check CUDA availability
    if torch.cuda.is_available():
        try:
            # Test CUDA with a simple operation
            test_tensor = torch.randn(1).cuda()
            _ = test_tensor + 1  # Simple operation to test CUDA libraries
            print(f"[DEVICE] CUDA available - GPU: {torch.cuda.get_device_name()}")
            return "cuda"
        except Exception as e:
            print(f"[DEVICE] CUDA test failed: {e}")
            print("[DEVICE] Falling back to CPU mode")
            return "cpu"
    else:
        print("[DEVICE] CUDA not available, using CPU")
        return "cpu"

def get_compute_type(device):
    """
    Get appropriate compute type based on device
    
    Args:
        device (str): Device string from get_device()
        
    Returns:
        str: Compute type for faster-whisper ("float16", "int8", etc.)
    """
    if device == "cuda":
        return "float16"
    else:
        return "int8"

def get_torch_dtype(device):
    """
    Get appropriate torch dtype based on device
    
    Args:
        device (str): Device string from get_device()
        
    Returns:
        torch.dtype: PyTorch data type
    """
    if device == "cuda":
        return torch.float16
    else:
        return torch.float32

def is_cuda_available():
    """
    Check if CUDA is available and working (respects FORCE_CPU)
    
    Returns:
        bool: True if CUDA should be used, False otherwise
    """
    device = get_device()
    return device.startswith("cuda")

def clear_gpu_memory():
    """
    Clear GPU memory if CUDA is available
    """
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        import gc
        gc.collect()
        print("[GPU] Memory cleared")

def print_device_info():
    """
    Print detailed device information
    """
    print("=" * 60)
    print("DEVICE INFORMATION")
    print("=" * 60)
    
    force_cpu = os.getenv("FORCE_CPU", "false").lower() in ["true", "1", "yes", "on"]
    print(f"FORCE_CPU setting: {force_cpu}")
    
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
    
    selected_device = get_device()
    print(f"Selected device: {selected_device}")
    print("=" * 60)

# Example usage
if __name__ == "__main__":
    print_device_info()
    device = get_device()
    print(f"\nRecommended device: {device}")
    print(f"Compute type: {get_compute_type(device)}")
    print(f"Torch dtype: {get_torch_dtype(device)}")