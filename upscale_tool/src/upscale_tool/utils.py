"""
Utility functions for upscale tool
"""
import os
import requests
from pathlib import Path
from typing import Optional
from tqdm import tqdm


def download_file(url: str, output_path: str, chunk_size: int = 8192) -> str:
    """
    Download file with progress bar
    
    Args:
        url: URL to download from
        output_path: Path to save file
        chunk_size: Download chunk size
        
    Returns:
        Path to downloaded file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if already exists
    if output_path.exists():
        print(f"File already exists: {output_path}")
        return str(output_path)
    
    print(f"Downloading {url} to {output_path}")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    
    with open(output_path, 'wb') as f, tqdm(
        desc=output_path.name,
        total=total_size,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))
    
    return str(output_path)


def get_model_path(model_name: str, model_dir: str = './models') -> Optional[str]:
    """
    Get path to model file
    
    Args:
        model_name: Name of model
        model_dir: Directory containing models
        
    Returns:
        Path to model file, or None if not found
    """
    model_dir = Path(model_dir)
    
    # Try exact match
    model_path = model_dir / f"{model_name}.pth"
    if model_path.exists():
        return str(model_path)
    
    # Try case-insensitive search
    for file in model_dir.glob('*.pth'):
        if file.stem.lower() == model_name.lower():
            return str(file)
    
    return None


def ensure_model_exists(model_name: str, model_dir: str, model_url: str) -> str:
    """
    Ensure model exists, download if needed
    
    Args:
        model_name: Name of model
        model_dir: Directory to save model
        model_url: URL to download model
        
    Returns:
        Path to model file
    """
    model_path = get_model_path(model_name, model_dir)
    
    if model_path is None:
        # Download model
        output_path = Path(model_dir) / f"{model_name}.pth"
        model_path = download_file(model_url, str(output_path))
    
    return model_path


def get_image_files(directory: str, extensions: tuple = ('.jpg', '.jpeg', '.png', '.webp')) -> list:
    """
    Get all image files in directory
    
    Args:
        directory: Directory to search
        extensions: Valid image extensions
        
    Returns:
        List of image file paths
    """
    directory = Path(directory)
    image_files = []
    
    for ext in extensions:
        image_files.extend(directory.glob(f'*{ext}'))
        image_files.extend(directory.glob(f'*{ext.upper()}'))
    
    return sorted(image_files)


def format_bytes(bytes_size: int) -> str:
    """
    Format bytes to human readable string
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted string (e.g., '1.5 GB')
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


def check_gpu_memory(device_id: int = 0) -> dict:
    """
    Check available GPU memory for specific device
    
    Args:
        device_id: GPU device ID (default: 0)
    
    Returns:
        Dict with total, used, and free memory in bytes
    """
    try:
        import torch
        if torch.cuda.is_available() and device_id < torch.cuda.device_count():
            torch.cuda.synchronize(device_id)
            total = torch.cuda.get_device_properties(device_id).total_memory
            reserved = torch.cuda.memory_reserved(device_id)
            allocated = torch.cuda.memory_allocated(device_id)
            free = total - reserved
            
            return {
                'device_id': device_id,
                'device_name': torch.cuda.get_device_name(device_id),
                'total': total,
                'used': reserved,
                'allocated': allocated,
                'free': free,
                'total_str': format_bytes(total),
                'used_str': format_bytes(reserved),
                'allocated_str': format_bytes(allocated),
                'free_str': format_bytes(free),
            }
    except Exception as e:
        print(f"Warning: Could not check GPU memory: {e}")
    
    return {}


def estimate_tile_size(image_size: tuple, available_vram: int) -> int:
    """
    Estimate optimal tile size based on available VRAM
    
    Args:
        image_size: (width, height)
        available_vram: Available VRAM in bytes
        
    Returns:
        Recommended tile size
    """
    # Rough estimation: 
    # 400x400 tile uses ~2GB VRAM for RealESRGAN_x4plus
    # Scale linearly
    
    base_tile = 400
    base_vram = 2 * 1024 * 1024 * 1024  # 2GB
    
    if available_vram >= base_vram:
        max_tile = int(base_tile * (available_vram / base_vram) ** 0.5)
        # Cap at image size
        max_dim = max(image_size)
        return min(max_tile, max_dim)
    else:
        # Use smaller tiles
        return int(base_tile * (available_vram / base_vram) ** 0.5)


def validate_image(image_path: str) -> bool:
    """
    Validate if file is a valid image
    
    Args:
        image_path: Path to image file
        
    Returns:
        True if valid, False otherwise
    """
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def get_optimal_device() -> str:
    """
    Get optimal device for inference
    
    Returns:
        Device string ('cuda', 'cpu')
    """
    try:
        import torch
        if torch.cuda.is_available():
            # Check if GPU has enough memory (at least 2GB free)
            gpu_mem = check_gpu_memory(0)
            if gpu_mem and gpu_mem.get('free', 0) > 2 * 1024**3:
                return 'cuda'
    except Exception:
        pass
    return 'cpu'


def benchmark_gpu(model_name: str = 'RealESRGAN_x4plus', test_size: tuple = (512, 512)) -> dict:
    """
    Benchmark GPU performance for upscaling
    
    Args:
        model_name: Model to benchmark
        test_size: Test image size (width, height)
    
    Returns:
        Dict with benchmark results
    """
    import time
    import numpy as np
    try:
        import torch
        
        results = {
            'device': 'unknown',
            'model': model_name,
            'test_size': test_size,
            'fp32_time': None,
            'fp16_time': None,
            'speedup': None,
        }
        
        if not torch.cuda.is_available():
            results['device'] = 'cpu'
            return results
        
        results['device'] = torch.cuda.get_device_name(0)
        
        # Import upscaler
        from .upscaler import ImageUpscaler
        
        # Create test image
        test_img = np.random.randint(0, 255, (*test_size, 3), dtype=np.uint8)
        
        # Benchmark FP32
        print("Benchmarking FP32...")
        upscaler_fp32 = ImageUpscaler(model=model_name, device='cuda', half_precision=False)
        torch.cuda.synchronize()
        start = time.time()
        _ = upscaler_fp32.upscale_array(test_img, scale=2)
        torch.cuda.synchronize()
        fp32_time = time.time() - start
        results['fp32_time'] = fp32_time
        upscaler_fp32.cleanup()
        
        # Benchmark FP16
        print("Benchmarking FP16...")
        upscaler_fp16 = ImageUpscaler(model=model_name, device='cuda', half_precision=True)
        torch.cuda.synchronize()
        start = time.time()
        _ = upscaler_fp16.upscale_array(test_img, scale=2)
        torch.cuda.synchronize()
        fp16_time = time.time() - start
        results['fp16_time'] = fp16_time
        results['speedup'] = fp32_time / fp16_time if fp16_time > 0 else 0
        upscaler_fp16.cleanup()
        
        return results
        
    except Exception as e:
        print(f"Benchmark failed: {e}")
        return {'error': str(e)}


def optimize_for_gpu(tile_size: int = None, gpu_id: int = 0) -> dict:
    """
    Get optimal settings for current GPU
    
    Args:
        tile_size: Preferred tile size (None for auto)
        gpu_id: GPU device ID
    
    Returns:
        Dict with optimal settings
    """
    settings = {
        'device': 'cpu',
        'tile_size': 256,
        'half_precision': False,
        'batch_size': 1,
    }
    
    try:
        import torch
        if not torch.cuda.is_available():
            return settings
        
        settings['device'] = 'cuda'
        gpu_mem = check_gpu_memory(gpu_id)
        
        if not gpu_mem:
            return settings
        
        free_gb = gpu_mem['free'] / 1024**3
        
        # Determine tile size based on available memory
        if tile_size is None:
            if free_gb >= 12:
                tile_size = 1024
            elif free_gb >= 8:
                tile_size = 768
            elif free_gb >= 6:
                tile_size = 512
            elif free_gb >= 4:
                tile_size = 384
            elif free_gb >= 2:
                tile_size = 256
            else:
                tile_size = 128
        
        settings['tile_size'] = tile_size
        
        # Enable FP16 for better performance
        # Check if GPU supports FP16 (compute capability >= 7.0)
        compute_cap = torch.cuda.get_device_capability(gpu_id)
        if compute_cap[0] >= 7:
            settings['half_precision'] = True
        
        return settings
        
    except Exception as e:
        print(f"Optimization failed: {e}")
        return settings

