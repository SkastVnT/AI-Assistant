"""
Test script for all upscale models
Tests 7 Real-ESRGAN models + 4 Chinese models
"""
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from src.upscale_tool.multi_upscaler import MultiArchUpscaler

def create_test_image(size=(64, 64)):
    """Create a simple test image"""
    img = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
    return img

def test_model(model_name, device='cuda'):
    """Test a single model"""
    print(f"\n{'='*60}")
    print(f"Testing: {model_name}")
    print(f"{'='*60}")
    
    try:
        # Create test image
        test_img = create_test_image()
        print(f"[OK] Created test image: {test_img.shape}")
        
        # Initialize upscaler
        upscaler = MultiArchUpscaler(model=model_name, device=device)
        print(f"[OK] Loaded model: {model_name}")
        print(f"  Architecture: {upscaler.arch_type}")
        
        # Upscale
        output = upscaler.upscale_array(test_img, scale=2)
        print(f"[OK] Upscale successful!")
        print(f"  Input: {test_img.shape}")
        print(f"  Output: {output.shape}")
        
        # Verify output size
        expected_h = test_img.shape[0] * 2
        expected_w = test_img.shape[1] * 2
        
        # ScuNET is denoise-only, doesn't upscale
        if 'ScuNET' in model_name:
            if output.shape[0] == test_img.shape[0] and output.shape[1] == test_img.shape[1]:
                print(f"[OK] ScuNET denoise output valid (no upscaling expected)")
                return True
            else:
                print(f"[WARN] ScuNET output unexpected")
                return False
        
        if output.shape[0] >= expected_h * 0.9 and output.shape[1] >= expected_w * 0.9:
            print(f"[OK] Output size valid (expected ~{expected_h}x{expected_w})")
            return True
        else:
            print(f"[WARN] Output size unexpected (expected ~{expected_h}x{expected_w})")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Test all models"""
    print("="*60)
    print("UPSCALE TOOL - MODEL TEST")
    print("="*60)
    
    # Check CUDA
    if torch.cuda.is_available():
        print(f"[OK] CUDA Available: {torch.cuda.get_device_name(0)}")
        print(f"  CUDA Version: {torch.version.cuda}")
        print(f"  PyTorch Version: {torch.__version__}")
        device = 'cuda'
    else:
        print("[WARN] CUDA not available, using CPU")
        device = 'cpu'
    
    # All models to test
    models = [
        # Real-ESRGAN models (RRDBNet)
        'RealESRGAN_x4plus',
        'RealESRGAN_x2plus',
        'RealESRGAN_x4plus_anime_6B',
        'RealESRGAN_animevideov3',
        'RealESRNet_x4plus',
        'realesr-general-x4v3',
        'realesr-general-wdn-x4v3',
        # Chinese models (Swin Transformer, U-Net)
        'SwinIR_realSR_x4',
        'Swin2SR_realSR_x4',
        'ScuNET_GAN',
        'ScuNET_PSNR',
    ]
    
    results = {}
    for model in models:
        success = test_model(model, device=device)
        results[model] = success
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}\n")
    
    for model, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status:8} - {model}")
    
    print("\n" + "="*60)
    
    if passed == total:
        print("[OK] All models working!")
    else:
        print(f"[WARN] {total - passed} model(s) failed")
    
    print("="*60)

if __name__ == '__main__':
    main()
