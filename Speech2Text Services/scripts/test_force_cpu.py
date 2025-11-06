"""
Test script để kiểm tra FORCE_CPU setting
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

# Load environment
load_dotenv("app/config/.env")

print("=" * 60)
print("FORCE_CPU TEST")
print("=" * 60)

force_cpu = os.getenv("FORCE_CPU", "false")
print(f"FORCE_CPU environment variable: '{force_cpu}'")
print(f"Should force CPU: {force_cpu.lower() in ['true', '1', 'yes']}")

print("\nTesting PyTorch import...")
try:
    import torch
    print(f"✅ PyTorch imported successfully: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU count: {torch.cuda.device_count()}")
        try:
            # Test simple CUDA operation
            test_tensor = torch.randn(1).cuda()
            result = test_tensor + 1
            print("✅ CUDA test passed")
        except Exception as e:
            print(f"❌ CUDA test failed: {e}")
    
except Exception as e:
    print(f"❌ PyTorch import failed: {e}")

print("\nTesting device utils...")
try:
    from app.core.utils.device_utils import get_device, print_device_info
    print_device_info()
    recommended_device = get_device()
    print(f"Recommended device: {recommended_device}")
except Exception as e:
    print(f"❌ Device utils failed: {e}")

print("=" * 60)