"""
Test Installation Script for LoRA Training Tool
Verifies all required packages are installed correctly
"""

import sys

def test_imports():
    """Test importing all required packages"""
    print("=" * 60)
    print("Testing LoRA Training Tool Installation")
    print("=" * 60)
    
    packages = {
        'Core ML': ['torch', 'torchvision', 'diffusers', 'transformers', 'accelerate', 'peft'],
        'Data Processing': ['numpy', 'pandas', 'PIL', 'cv2'],
        'Utilities': ['yaml', 'omegaconf', 'tqdm'],
        'Monitoring': ['tensorboard', 'wandb'],
        'Augmentation': ['albumentations'],
        'Optimization': ['xformers', 'bitsandbytes'],
        'Storage': ['safetensors', 'huggingface_hub']
    }
    
    all_success = True
    
    for category, modules in packages.items():
        print(f"\n📦 {category}:")
        for module in modules:
            try:
                if module == 'PIL':
                    __import__('PIL')
                elif module == 'cv2':
                    __import__('cv2')
                elif module == 'yaml':
                    __import__('yaml')
                else:
                    __import__(module)
                print(f"  ✅ {module}")
            except ImportError as e:
                print(f"  ❌ {module} - {str(e)}")
                all_success = False
    
    print("\n" + "=" * 60)
    
    if all_success:
        print("✅ All packages installed successfully!")
        
        # Print versions of key packages
        import torch
        import diffusers
        import transformers
        import accelerate
        
        print("\n📊 Key Package Versions:")
        print(f"  PyTorch: {torch.__version__}")
        print(f"  Diffusers: {diffusers.__version__}")
        print(f"  Transformers: {transformers.__version__}")
        print(f"  Accelerate: {accelerate.__version__}")
        
        print("\n🎮 GPU Information:")
        if torch.cuda.is_available():
            print(f"  ✅ CUDA Available: Yes")
            print(f"  GPU Count: {torch.cuda.device_count()}")
            print(f"  Current GPU: {torch.cuda.get_device_name(0)}")
            print(f"  CUDA Version: {torch.version.cuda}")
            
            # Memory info
            total_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"  GPU Memory: {total_mem:.2f} GB")
        else:
            print("  ⚠️  CUDA Available: No (CPU mode only)")
        
        print("\n" + "=" * 60)
        print("🎉 Installation test completed successfully!")
        print("You can now run the training scripts.")
        print("\nQuick Start:")
        print("  1. cd train_LoRA_tool")
        print("  2. .\\scripts\\setup\\quickstart.bat")
        print("=" * 60)
        
        return 0
    else:
        print("❌ Some packages failed to install.")
        print("Please run: pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(test_imports())
