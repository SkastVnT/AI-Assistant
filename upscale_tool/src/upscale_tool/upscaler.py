"""
Main upscaler class
Wrapper for Real-ESRGAN and other models
"""
import os
import numpy as np
from pathlib import Path
from typing import Optional, List, Union
from PIL import Image
import logging

from .config import UpscaleConfig, load_config
from .utils import (
    ensure_model_exists, 
    get_image_files, 
    check_gpu_memory,
    estimate_tile_size,
    validate_image
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImageUpscaler:
    """
    Image upscaler using Real-ESRGAN and other models
    
    Examples:
        >>> upscaler = ImageUpscaler(model='RealESRGAN_x4plus')
        >>> upscaler.upscale_image('input.jpg', 'output.png', scale=4)
        
        >>> # With config file
        >>> config = load_config('config.yaml')
        >>> upscaler = ImageUpscaler.from_config(config)
    """
    
    SUPPORTED_MODELS = {
        'RealESRGAN_x4plus': {
            'num_block': 23,
            'scale': 4,
            'description': '🌟 [Tencent ARC] Best for real photos, high quality, slower'
        },
        'RealESRGAN_x2plus': {
            'num_block': 23,
            'scale': 2,
            'description': '[Tencent] 2x upscale, faster, less VRAM (good for large images)'
        },
        'RealESRGAN_x4plus_anime_6B': {
            'num_block': 6,
            'scale': 4,
            'description': '🎌 [Tencent] Best for anime/manga, small model, fast'
        },
        'RealESRGAN_animevideov3': {
            'num_block': 6,
            'scale': 4,
            'description': '[Tencent] For anime videos, temporal consistency'
        },
        'RealESRNet_x4plus': {
            'num_block': 23,
            'scale': 4,
            'description': '[Tencent] Without GAN, less artifacts, more conservative'
        },
        'realesr-general-x4v3': {
            'num_block': 6,
            'scale': 4,
            'description': '[Tencent] General purpose, small size, fast inference'
        },
        'realesr-general-wdn-x4v3': {
            'num_block': 6,
            'scale': 4,
            'description': '[Tencent] With denoise, good for old/degraded photos'
        },
        # Chinese models (SwinIR, Swin2SR, ScuNET - different architectures)
        'SwinIR_realSR_x4': {
            'num_block': None,
            'scale': 4,
            'description': '👑 [CUHK] Highest quality, Swin Transformer, slow, high VRAM'
        },
        'Swin2SR_realSR_x4': {
            'num_block': None,
            'scale': 4,
            'description': '[ETH Zurich] Swin v2, faster than SwinIR, good quality'
        },
        'ScuNET_GAN': {
            'num_block': None,
            'scale': 1,
            'description': '[CUHK] Strong denoise + upscale, with GAN, for noisy images'
        },
        'ScuNET_PSNR': {
            'num_block': None,
            'scale': 1,
            'description': '[CUHK] Less artifacts, no GAN, good for old photos'
        }
    }
    
    def __init__(
        self,
        model: str = 'RealESRGAN_x4plus',
        device: str = 'cuda',
        config: Optional[UpscaleConfig] = None,
        **kwargs
    ):
        """
        Initialize upscaler
        
        Args:
            model: Model name (see SUPPORTED_MODELS)
            device: Device to use ('cuda' or 'cpu')
            config: UpscaleConfig object (optional)
            **kwargs: Additional config options
        """
        if config is None:
            config = UpscaleConfig()
            # Update with kwargs
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        self.config = config
        self.model_name = model
        self.device = device
        self.upsampler = None
        
        # Validate model
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Unsupported model: {model}. "
                f"Choose from: {list(self.SUPPORTED_MODELS.keys())}"
            )
        
        # Check device
        self._check_device()
        
        # Load model
        self._load_model()
        
        logger.info(f"Initialized {model} on {device}")
    
    @classmethod
    def from_config(cls, config: Union[UpscaleConfig, str], **kwargs):
        """
        Create upscaler from config
        
        Args:
            config: UpscaleConfig object or path to config file
            **kwargs: Override config options
            
        Returns:
            ImageUpscaler instance
        """
        if isinstance(config, str):
            config = load_config(config)
        
        # Override with kwargs
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return cls(
            model=config.default_model,
            device=config.device,
            config=config
        )
    
    def _check_device(self):
        """Check if device is available and configure CUDA"""
        try:
            import torch
            
            # Auto-detect best device
            if self.device == 'auto':
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            
            if self.device == 'cuda' and not torch.cuda.is_available():
                logger.warning("CUDA not available, falling back to CPU")
                self.device = 'cpu'
            
            if self.device == 'cuda':
                # Enable CUDA optimizations
                torch.backends.cudnn.benchmark = True
                torch.backends.cudnn.enabled = True
                
                # Check CUDA version
                logger.info(f"CUDA Version: {torch.version.cuda}")
                logger.info(f"cuDNN Version: {torch.backends.cudnn.version()}")
                
                # Print GPU info for each available GPU
                num_gpus = torch.cuda.device_count()
                logger.info(f"Available GPUs: {num_gpus}")
                
                for i in range(num_gpus):
                    gpu_name = torch.cuda.get_device_name(i)
                    gpu_props = torch.cuda.get_device_properties(i)
                    gpu_mem = check_gpu_memory(i)
                    
                    logger.info(
                        f"GPU {i}: {gpu_name} - "
                        f"Compute {gpu_props.major}.{gpu_props.minor} - "
                        f"Total: {gpu_props.total_memory / 1024**3:.1f}GB"
                    )
                    if gpu_mem:
                        logger.info(
                            f"  Memory: Total={gpu_mem['total_str']}, "
                            f"Free={gpu_mem['free_str']}, "
                            f"Used={gpu_mem['used_str']}"
                        )
                
                # Set default GPU device
                torch.cuda.set_device(0)
                
                # Enable TF32 for Ampere GPUs (RTX 30xx+) for better performance
                if torch.cuda.get_device_capability()[0] >= 8:
                    torch.backends.cuda.matmul.allow_tf32 = True
                    torch.backends.cudnn.allow_tf32 = True
                    logger.info("TF32 enabled for Ampere GPU")
                
        except ImportError:
            logger.warning("PyTorch not installed, using CPU")
            self.device = 'cpu'
    
    def _load_model(self):
        """Load upscaling model"""
        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
        except ImportError as e:
            raise ImportError(
                "Please install required packages: "
                "pip install basicsr realesrgan\n"
                f"Error: {e}"
            )
        
        # Get model info
        model_info = self.SUPPORTED_MODELS[self.model_name]
        num_block = model_info['num_block']
        
        # Ensure model exists
        if self.model_name not in self.config.model_urls:
            raise ValueError(f"No download URL for model: {self.model_name}")
        
        model_url = self.config.model_urls[self.model_name]
        model_path = ensure_model_exists(
            self.model_name,
            self.config.model_dir,
            model_url
        )
        
        logger.info(f"Loading model from: {model_path}")
        
        # Create model
        model = RRDBNet(
            num_in_ch=3,
            num_out_ch=3,
            num_feat=64,
            num_block=num_block,
            num_grow_ch=32,
            scale=4
        )
        
        # Determine optimal tile size based on GPU memory
        tile_size = self.config.tile_size
        if self.device == 'cuda':
            import torch
            gpu_mem = check_gpu_memory()
            if gpu_mem:
                # Estimate optimal tile size (conservative)
                free_mem_gb = gpu_mem['free'] / 1024**3
                if free_mem_gb < 4:
                    tile_size = min(tile_size, 256)
                    logger.warning(f"Low GPU memory ({free_mem_gb:.1f}GB), using tile_size={tile_size}")
                elif free_mem_gb > 8:
                    tile_size = max(tile_size, 512)
                    logger.info(f"High GPU memory ({free_mem_gb:.1f}GB), using tile_size={tile_size}")
        
        # Enable FP16 for CUDA (significant speedup with minimal quality loss)
        use_half = self.config.half_precision and self.device == 'cuda'
        if use_half:
            logger.info("Using FP16 mixed precision (faster inference)")
        
        # Create upsampler with optimized settings
        self.upsampler = RealESRGANer(
            scale=4,
            model_path=model_path,
            model=model,
            tile=tile_size,
            tile_pad=self.config.tile_pad,
            pre_pad=self.config.pre_pad,
            half=use_half,
            device=self.device,
            gpu_id=0  # Use first GPU by default
        )
        
        # Move model to GPU and set to eval mode
        if self.device == 'cuda':
            import torch
            self.upsampler.model.eval()
            if use_half:
                self.upsampler.model.half()
            
            # Clear cache to free memory
            torch.cuda.empty_cache()
        
        logger.info(f"Model loaded successfully (tile_size={tile_size}, fp16={use_half})")
    
    def upscale_image(
        self,
        input_path: str,
        output_path: str = None,
        scale: int = None,
        **kwargs
    ) -> str:
        """
        Upscale single image
        
        Args:
            input_path: Path to input image
            output_path: Path to save output (optional)
            scale: Upscale ratio (default: use model's scale)
            **kwargs: Additional options (tile_size, etc.)
            
        Returns:
            Path to output image
        """
        if not validate_image(input_path):
            raise ValueError(f"Invalid image: {input_path}")
        
        # Load image
        img = Image.open(input_path)
        img_array = np.array(img)
        
        # Upscale
        output_array = self.upscale_array(img_array, scale=scale, **kwargs)
        
        # Convert back to PIL Image
        output_img = Image.fromarray(output_array)
        
        # Determine output path
        if output_path is None:
            input_path = Path(input_path)
            output_path = input_path.parent / f"{input_path.stem}_upscaled{input_path.suffix}"
        
        # Save
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.config.output_format.lower() == 'jpg':
            output_img.save(output_path, quality=self.config.output_quality)
        else:
            output_img.save(output_path)
        
        logger.info(f"Saved upscaled image to: {output_path}")
        
        return str(output_path)
    
    def upscale_array(
        self,
        img: np.ndarray,
        scale: int = None,
        **kwargs
    ) -> np.ndarray:
        """
        Upscale numpy array with GPU memory optimization
        
        Args:
            img: Input image array (H, W, C) RGB or BGR
            scale: Upscale ratio
            **kwargs: Additional options
            
        Returns:
            Upscaled image array
        """
        if scale is None:
            scale = self.config.default_scale
        
        # Update upsampler options if provided
        if 'tile_size' in kwargs:
            self.upsampler.tile = kwargs['tile_size']
        
        # Convert RGB to BGR (Real-ESRGAN expects BGR)
        if len(img.shape) == 3 and img.shape[2] == 3:
            img = img[:, :, ::-1]
        
        # Clear GPU cache before processing
        if self.device == 'cuda':
            import torch
            torch.cuda.empty_cache()
        
        # Upscale with automatic retry and memory management
        try:
            with self._inference_context():
                output, _ = self.upsampler.enhance(img, outscale=scale)
        except RuntimeError as e:
            if 'out of memory' in str(e).lower():
                logger.error(f"GPU OOM error: {e}")
                # Clear cache and retry with smaller tile size
                if self.device == 'cuda':
                    import torch
                    torch.cuda.empty_cache()
                
                logger.warning("Retrying with smaller tile size...")
                original_tile = self.upsampler.tile
                self.upsampler.tile = max(128, original_tile // 2)
                
                try:
                    with self._inference_context():
                        output, _ = self.upsampler.enhance(img, outscale=scale)
                finally:
                    self.upsampler.tile = original_tile
            else:
                raise
        except Exception as e:
            logger.error(f"Upscaling failed: {e}")
            raise
        finally:
            # Clean up GPU memory
            if self.device == 'cuda':
                import torch
                torch.cuda.empty_cache()
        
        # Convert BGR back to RGB
        if len(output.shape) == 3 and output.shape[2] == 3:
            output = output[:, :, ::-1]
        
        return output
    
    def upscale_folder(
        self,
        input_folder: str,
        output_folder: str = None,
        scale: int = None,
        extensions: tuple = ('.jpg', '.jpeg', '.png', '.webp'),
        **kwargs
    ) -> List[str]:
        """
        Upscale all images in folder
        
        Args:
            input_folder: Path to input folder
            output_folder: Path to output folder
            scale: Upscale ratio
            extensions: Valid image extensions
            **kwargs: Additional options
            
        Returns:
            List of output image paths
        """
        input_folder = Path(input_folder)
        
        if output_folder is None:
            output_folder = input_folder.parent / f"{input_folder.name}_upscaled"
        
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # Get all images
        image_files = get_image_files(input_folder, extensions)
        
        if not image_files:
            logger.warning(f"No images found in: {input_folder}")
            return []
        
        logger.info(f"Found {len(image_files)} images to upscale")
        
        # Upscale each image
        output_paths = []
        from tqdm import tqdm
        
        for img_path in tqdm(image_files, desc="Upscaling"):
            try:
                output_path = output_folder / img_path.name
                self.upscale_image(img_path, output_path, scale=scale, **kwargs)
                output_paths.append(str(output_path))
            except Exception as e:
                logger.error(f"Failed to upscale {img_path}: {e}")
        
        logger.info(f"Upscaled {len(output_paths)}/{len(image_files)} images")
        
        return output_paths
    
    @staticmethod
    def list_models() -> dict:
        """
        List all supported models
        
        Returns:
            Dict of model names and descriptions
        """
        return {
            name: info['description']
            for name, info in ImageUpscaler.SUPPORTED_MODELS.items()
        }
    
    def _inference_context(self):
        """Context manager for inference with optimal settings"""
        if self.device == 'cuda':
            import torch
            return torch.inference_mode()  # Faster than torch.no_grad()
        else:
            from contextlib import nullcontext
            return nullcontext()
    
    def cleanup(self):
        """Clean up GPU memory"""
        if self.device == 'cuda':
            import torch
            if self.upsampler:
                del self.upsampler
                self.upsampler = None
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            logger.info("GPU memory cleaned up")
    
    def get_gpu_stats(self) -> dict:
        """Get current GPU memory statistics"""
        if self.device == 'cuda':
            import torch
            return {
                'allocated': torch.cuda.memory_allocated() / 1024**2,  # MB
                'reserved': torch.cuda.memory_reserved() / 1024**2,  # MB
                'max_allocated': torch.cuda.max_memory_allocated() / 1024**2,  # MB
            }
        return {}
    
    def __repr__(self):
        return (
            f"ImageUpscaler(model='{self.model_name}', "
            f"device='{self.device}')"
        )
    
    def __del__(self):
        """Cleanup on deletion"""
        self.cleanup()


# Convenience function
def upscale(
    input_path: str,
    output_path: str = None,
    model: str = 'RealESRGAN_x4plus',
    scale: int = 4,
    device: str = 'cuda',
    **kwargs
) -> str:
    """
    Quick upscale function
    
    Args:
        input_path: Input image or folder path
        output_path: Output image or folder path
        model: Model name
        scale: Upscale ratio
        device: Device to use
        **kwargs: Additional options
        
    Returns:
        Output path
    """
    upscaler = ImageUpscaler(model=model, device=device, **kwargs)
    
    input_path = Path(input_path)
    
    if input_path.is_dir():
        # Upscale folder
        results = upscaler.upscale_folder(
            input_folder=input_path,
            output_folder=output_path,
            scale=scale,
            **kwargs
        )
        return output_path if output_path else f"{input_path}_upscaled"
    else:
        # Upscale single image
        return upscaler.upscale_image(
            input_path=input_path,
            output_path=output_path,
            scale=scale,
            **kwargs
        )
