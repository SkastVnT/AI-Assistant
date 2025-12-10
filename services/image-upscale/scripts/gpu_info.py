"""
GPU Information and CUDA Detection Script
Shows detailed GPU info and optimal settings for upscaling
"""
import sys

def print_separator(char='=', length=70):
    print(char * length)

def check_cuda_installation():
    """Check CUDA and PyTorch installation"""
    print_separator()
    print("CUDA & PyTorch Detection")
    print_separator()
    
    # Check PyTorch
    try:
        import torch
        print(f"✓ PyTorch installed: {torch.__version__}")
    except ImportError:
        print("✗ PyTorch not installed")
        print("  Install: pip install torch torchvision")
        return False
    
    # Check CUDA availability
    if torch.cuda.is_available():
        print(f"✓ CUDA available: {torch.version.cuda}")
        print(f"✓ cuDNN version: {torch.backends.cudnn.version()}")
        return True
    else:
        print("✗ CUDA not available")
        print("  Your PyTorch installation may be CPU-only")
        print("  Install CUDA PyTorch: pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
        return False

def show_gpu_details():
    """Show detailed GPU information"""
    try:
        import torch
        if not torch.cuda.is_available():
            return
        
        print_separator()
        print("GPU Information")
        print_separator()
        
        num_gpus = torch.cuda.device_count()
        print(f"Number of GPUs: {num_gpus}\n")
        
        for i in range(num_gpus):
            props = torch.cuda.get_device_properties(i)
            
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"  Compute Capability: {props.major}.{props.minor}")
            print(f"  Total Memory: {props.total_memory / 1024**3:.2f} GB")
            print(f"  Multi-processors: {props.multi_processor_count}")
            
            # Memory info
            torch.cuda.synchronize(i)
            allocated = torch.cuda.memory_allocated(i) / 1024**2
            reserved = torch.cuda.memory_reserved(i) / 1024**2
            free = (props.total_memory - torch.cuda.memory_reserved(i)) / 1024**2
            
            print(f"  Memory Allocated: {allocated:.2f} MB")
            print(f"  Memory Reserved: {reserved:.2f} MB")
            print(f"  Memory Free: {free:.2f} MB")
            
            # Features
            print(f"  FP16 Support: {'Yes' if props.major >= 7 else 'Limited'}")
            print(f"  TF32 Support: {'Yes (Ampere)' if props.major >= 8 else 'No'}")
            print()
        
    except Exception as e:
        print(f"Error getting GPU details: {e}")

def show_optimization_settings():
    """Show recommended optimization settings"""
    try:
        import torch
        if not torch.cuda.is_available():
            print_separator()
            print("Recommended Settings (CPU Mode)")
            print_separator()
            print("device = 'cpu'")
            print("tile_size = 256")
            print("half_precision = False")
            return
        
        print_separator()
        print("Recommended Settings for Upscaling")
        print_separator()
        
        props = torch.cuda.get_device_properties(0)
        free_mem = (props.total_memory - torch.cuda.memory_reserved(0)) / 1024**3
        
        # Determine optimal settings
        device = 'cuda'
        tile_size = 256
        half_precision = props.major >= 7
        
        if free_mem >= 12:
            tile_size = 1024
        elif free_mem >= 8:
            tile_size = 768
        elif free_mem >= 6:
            tile_size = 512
        elif free_mem >= 4:
            tile_size = 384
        elif free_mem >= 2:
            tile_size = 256
        else:
            tile_size = 128
        
        print(f"Device: {device}")
        print(f"Tile Size: {tile_size}")
        print(f"Half Precision (FP16): {half_precision}")
        print(f"Free Memory: {free_mem:.2f} GB")
        
        print("\nPython Code:")
        print(f"from upscale_tool.upscaler import ImageUpscaler")
        print(f"upscaler = ImageUpscaler(")
        print(f"    model='RealESRGAN_x4plus',")
        print(f"    device='{device}',")
        print(f"    tile_size={tile_size},")
        print(f"    half_precision={half_precision}")
        print(f")")
        
    except Exception as e:
        print(f"Error: {e}")

def run_benchmark():
    """Run quick performance benchmark"""
    try:
        import torch
        if not torch.cuda.is_available():
            print("\nSkipping benchmark (no CUDA)")
            return
        
        print_separator()
        print("Running Quick Benchmark...")
        print_separator()
        
        from upscale_tool.utils import benchmark_gpu
        
        results = benchmark_gpu(test_size=(256, 256))
        
        if 'error' in results:
            print(f"Benchmark failed: {results['error']}")
            return
        
        print(f"Device: {results['device']}")
        print(f"Test Size: {results['test_size']}")
        
        if results['fp32_time']:
            print(f"FP32 Time: {results['fp32_time']:.3f}s")
        
        if results['fp16_time']:
            print(f"FP16 Time: {results['fp16_time']:.3f}s")
            print(f"Speedup: {results['speedup']:.2f}x")
        
    except ImportError:
        print("\nSkipping benchmark (upscale_tool not fully installed)")
    except Exception as e:
        print(f"\nBenchmark error: {e}")

def main():
    """Main function"""
    print("\n🔍 GPU Detection & Optimization Tool")
    print("=" * 70)
    
    # Check CUDA installation
    cuda_available = check_cuda_installation()
    
    # Show GPU details
    if cuda_available:
        show_gpu_details()
        show_optimization_settings()
    
    # Ask for benchmark
    if cuda_available:
        print_separator()
        response = input("\nRun performance benchmark? (y/n): ").strip().lower()
        if response == 'y':
            run_benchmark()
    
    print_separator()
    print("\n✓ GPU check complete!")
    print()

if __name__ == "__main__":
    main()
