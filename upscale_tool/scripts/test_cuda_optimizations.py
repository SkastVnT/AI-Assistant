"""
Comprehensive test for CUDA GPU optimizations
Tests all new features and optimizations
"""
import sys
import time
import numpy as np
from pathlib import Path

def print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)

def test_imports():
    """Test basic imports"""
    print_section("1. Testing Imports")
    
    try:
        import torch
        print(f"✓ PyTorch: {torch.__version__}")
        
        from upscale_tool import ImageUpscaler
        print("✓ ImageUpscaler imported")
        
        from upscale_tool.utils import (
            get_optimal_device,
            optimize_for_gpu,
            check_gpu_memory,
            benchmark_gpu
        )
        print("✓ Utility functions imported")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_device_detection():
    """Test device detection"""
    print_section("2. Testing Device Detection")
    
    try:
        import torch
        from upscale_tool.utils import get_optimal_device
        
        # Test auto detection
        device = get_optimal_device()
        print(f"✓ Optimal device: {device}")
        
        # Test CUDA availability
        cuda_available = torch.cuda.is_available()
        print(f"✓ CUDA available: {cuda_available}")
        
        if cuda_available:
            print(f"  CUDA version: {torch.version.cuda}")
            print(f"  GPU count: {torch.cuda.device_count()}")
            print(f"  GPU 0: {torch.cuda.get_device_name(0)}")
        
        return True
    except Exception as e:
        print(f"✗ Device detection failed: {e}")
        return False

def test_gpu_memory():
    """Test GPU memory functions"""
    print_section("3. Testing GPU Memory Functions")
    
    try:
        import torch
        from upscale_tool.utils import check_gpu_memory
        
        if not torch.cuda.is_available():
            print("⊘ Skipped (no CUDA)")
            return True
        
        mem_info = check_gpu_memory(0)
        
        if mem_info:
            print(f"✓ GPU memory check successful")
            print(f"  Device: {mem_info.get('device_name', 'Unknown')}")
            print(f"  Total: {mem_info.get('total_str', 'Unknown')}")
            print(f"  Free: {mem_info.get('free_str', 'Unknown')}")
            print(f"  Used: {mem_info.get('used_str', 'Unknown')}")
        else:
            print("✗ Failed to get GPU memory info")
            return False
        
        return True
    except Exception as e:
        print(f"✗ GPU memory test failed: {e}")
        return False

def test_optimization_settings():
    """Test optimize_for_gpu function"""
    print_section("4. Testing Optimization Settings")
    
    try:
        from upscale_tool.utils import optimize_for_gpu
        
        settings = optimize_for_gpu()
        
        print(f"✓ Optimization settings generated")
        print(f"  Device: {settings['device']}")
        print(f"  Tile size: {settings['tile_size']}")
        print(f"  Half precision: {settings['half_precision']}")
        
        return True
    except Exception as e:
        print(f"✗ Optimization settings failed: {e}")
        return False

def test_upscaler_init():
    """Test ImageUpscaler initialization with different configs"""
    print_section("5. Testing ImageUpscaler Initialization")
    
    try:
        from upscale_tool import ImageUpscaler
        
        # Test auto device
        print("  Testing device='auto'...")
        upscaler = ImageUpscaler(device='auto', model='RealESRGAN_x4plus')
        print(f"  ✓ Auto device: {upscaler.device}")
        
        # Test with optimization
        print("  Testing with optimize_for_gpu()...")
        from upscale_tool.utils import optimize_for_gpu
        settings = optimize_for_gpu()
        upscaler2 = ImageUpscaler(model='RealESRGAN_x4plus', **settings)
        print(f"  ✓ Optimized init successful")
        
        # Test cleanup
        print("  Testing cleanup()...")
        upscaler.cleanup()
        print("  ✓ Cleanup successful")
        
        return True
    except Exception as e:
        print(f"✗ Upscaler init failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gpu_stats():
    """Test get_gpu_stats method"""
    print_section("6. Testing GPU Stats")
    
    try:
        import torch
        from upscale_tool import ImageUpscaler
        
        if not torch.cuda.is_available():
            print("⊘ Skipped (no CUDA)")
            return True
        
        upscaler = ImageUpscaler(device='cuda', model='RealESRGAN_x4plus')
        stats = upscaler.get_gpu_stats()
        
        if stats:
            print(f"✓ GPU stats retrieved")
            print(f"  Allocated: {stats.get('allocated', 0):.2f} MB")
            print(f"  Reserved: {stats.get('reserved', 0):.2f} MB")
            print(f"  Max allocated: {stats.get('max_allocated', 0):.2f} MB")
        else:
            print("  ⊘ No stats (CPU mode)")
        
        upscaler.cleanup()
        return True
    except Exception as e:
        print(f"✗ GPU stats failed: {e}")
        return False

def test_inference():
    """Test actual inference with small image"""
    print_section("7. Testing Inference")
    
    try:
        from upscale_tool import ImageUpscaler
        from PIL import Image
        
        # Create small test image
        print("  Creating test image (256x256)...")
        test_img = Image.new('RGB', (256, 256), color='blue')
        test_img.save('test_small.png')
        
        # Test inference
        print("  Running inference...")
        upscaler = ImageUpscaler(device='auto', model='RealESRGAN_x4plus')
        
        start = time.time()
        result = upscaler.upscale_image('test_small.png', 'test_small_upscaled.png', scale=2)
        elapsed = time.time() - start
        
        # Verify output
        output_img = Image.open(result)
        expected_size = (512, 512)
        
        if output_img.size == expected_size:
            print(f"✓ Inference successful")
            print(f"  Input: 256x256")
            print(f"  Output: {output_img.size}")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Device: {upscaler.device}")
        else:
            print(f"✗ Wrong output size: {output_img.size} (expected {expected_size})")
            return False
        
        # Cleanup
        upscaler.cleanup()
        Path('test_small.png').unlink(missing_ok=True)
        Path('test_small_upscaled.png').unlink(missing_ok=True)
        
        return True
    except Exception as e:
        print(f"✗ Inference failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fp16_vs_fp32():
    """Test FP16 vs FP32 performance (CUDA only)"""
    print_section("8. Testing FP16 vs FP32 (if CUDA available)")
    
    try:
        import torch
        
        if not torch.cuda.is_available():
            print("⊘ Skipped (no CUDA)")
            return True
        
        from upscale_tool import ImageUpscaler
        from PIL import Image
        
        # Create test image
        test_img = Image.new('RGB', (256, 256), color='red')
        test_arr = np.array(test_img)
        
        # Test FP32
        print("  Testing FP32...")
        upscaler_fp32 = ImageUpscaler(device='cuda', half_precision=False)
        start = time.time()
        _ = upscaler_fp32.upscale_array(test_arr, scale=2)
        fp32_time = time.time() - start
        print(f"  FP32 time: {fp32_time:.3f}s")
        upscaler_fp32.cleanup()
        
        # Test FP16
        print("  Testing FP16...")
        upscaler_fp16 = ImageUpscaler(device='cuda', half_precision=True)
        start = time.time()
        _ = upscaler_fp16.upscale_array(test_arr, scale=2)
        fp16_time = time.time() - start
        print(f"  FP16 time: {fp16_time:.3f}s")
        upscaler_fp16.cleanup()
        
        speedup = fp32_time / fp16_time if fp16_time > 0 else 0
        print(f"✓ FP16 speedup: {speedup:.2f}x")
        
        return True
    except Exception as e:
        print(f"✗ FP16/FP32 test failed: {e}")
        return False

def test_dynamic_tile_size():
    """Test dynamic tile size adjustment"""
    print_section("9. Testing Dynamic Tile Size")
    
    try:
        from upscale_tool import ImageUpscaler
        import torch
        
        if not torch.cuda.is_available():
            print("⊘ Skipped (no CUDA)")
            return True
        
        # Test with auto_tile_size
        upscaler = ImageUpscaler(
            device='cuda',
            model='RealESRGAN_x4plus',
            auto_tile_size=True
        )
        
        print(f"✓ Dynamic tile size enabled")
        print(f"  Tile size: {upscaler.upsampler.tile}")
        
        upscaler.cleanup()
        return True
    except Exception as e:
        print(f"✗ Dynamic tile size test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("  CUDA GPU OPTIMIZATION TEST SUITE")
    print("="*70)
    
    tests = [
        ("Imports", test_imports),
        ("Device Detection", test_device_detection),
        ("GPU Memory", test_gpu_memory),
        ("Optimization Settings", test_optimization_settings),
        ("Upscaler Init", test_upscaler_init),
        ("GPU Stats", test_gpu_stats),
        ("Inference", test_inference),
        ("FP16 vs FP32", test_fp16_vs_fp32),
        ("Dynamic Tile Size", test_dynamic_tile_size),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
