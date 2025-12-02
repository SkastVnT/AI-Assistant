"""
Configuration for upscale tool
"""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class UpscaleConfig:
    """Configuration for upscaling"""
    
    # Model settings
    default_model: str = 'RealESRGAN_x4plus'
    default_scale: int = 4
    device: str = 'auto'  # 'auto', 'cuda', 'cpu', 'cuda:0', 'cuda:1', etc.
    
    # Model paths
    model_dir: str = './models'
    download_auto: bool = True
    
    # CUDA/GPU settings
    gpu_id: int = 0  # GPU device ID for multi-GPU systems
    tile_size: int = 400  # Larger = faster but more VRAM
    tile_pad: int = 10
    pre_pad: int = 0
    half_precision: bool = True  # FP16 for faster inference (requires GPU compute >= 7.0)
    
    # CUDA optimization flags
    cudnn_benchmark: bool = True  # Enable cuDNN auto-tuner
    tf32_matmul: bool = True  # Enable TF32 on Ampere GPUs (RTX 30xx+)
    
    # Memory management
    auto_tile_size: bool = True  # Automatically adjust tile size based on GPU memory
    clear_cache: bool = True  # Clear GPU cache between batches
    
    # Output settings
    output_format: str = 'png'  # 'png', 'jpg', 'webp'
    output_quality: int = 95     # For jpg
    
    # Advanced settings
    denoise_strength: Optional[int] = None  # -1 to disable, 0-255
    face_enhance: bool = False
    
    # Model URLs
    model_urls: Dict[str, str] = field(default_factory=lambda: {
        # Real-ESRGAN models (Tencent ARC)
        'RealESRGAN_x4plus': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth',
        'RealESRGAN_x2plus': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
        'RealESRGAN_x4plus_anime_6B': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth',
        'RealESRGAN_animevideov3': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth',
        'RealESRNet_x4plus': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRNet_x4plus.pth',
        'realesr-general-x4v3': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth',
        'realesr-general-wdn-x4v3': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth',
        
        # Chinese models (require different architectures)
        'SwinIR_realSR_x4': 'https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth',
        'Swin2SR_realSR_x4': 'https://github.com/mv-lab/swin2sr/releases/download/v0.0.1/Swin2SR_RealworldSR_X4_64_BSRGAN_PSNR.pth',
        'ScuNET_GAN': 'https://github.com/cszn/KAIR/releases/download/v1.0/scunet_color_real_gan.pth',
        'ScuNET_PSNR': 'https://github.com/cszn/KAIR/releases/download/v1.0/scunet_color_real_psnr.pth',
    })


def load_config(config_path: str = None) -> UpscaleConfig:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to config file. If None, use default config.
        
    Returns:
        UpscaleConfig object
    """
    if config_path is None or not Path(config_path).exists():
        return UpscaleConfig()
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config_dict = yaml.safe_load(f)
    
    # Flatten nested dict
    flat_config = {}
    if 'upscaler' in config_dict:
        flat_config.update(config_dict['upscaler'])
    if 'models' in config_dict:
        flat_config.update(config_dict['models'])
    if 'processing' in config_dict:
        flat_config.update(config_dict['processing'])
    if 'output' in config_dict:
        flat_config['output_format'] = config_dict['output'].get('format', 'png')
        flat_config['output_quality'] = config_dict['output'].get('quality', 95)
    
    return UpscaleConfig(**flat_config)


def save_config(config: UpscaleConfig, output_path: str):
    """
    Save configuration to YAML file
    
    Args:
        config: UpscaleConfig object
        output_path: Path to save config
    """
    config_dict = {
        'upscaler': {
            'default_model': config.default_model,
            'default_scale': config.default_scale,
            'device': config.device,
        },
        'models': {
            'download_auto': config.download_auto,
            'model_dir': config.model_dir,
        },
        'processing': {
            'tile_size': config.tile_size,
            'tile_pad': config.tile_pad,
            'pre_pad': config.pre_pad,
            'half_precision': config.half_precision,
        },
        'output': {
            'format': config.output_format,
            'quality': config.output_quality,
        }
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.dump(config_dict, f, default_flow_style=False)


# Constants for backward compatibility
MODELS_DIR = Path('./models')

# Supported models configuration
SUPPORTED_MODELS = {
    # Real-ESRGAN models (Tencent ARC) - RRDBNet architecture
    'RealESRGAN_x4plus': {
        'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth',
        'num_block': 23,
        'scale': 4,
        'description': '[Tencent] Best for general photos'
    },
    'RealESRGAN_x2plus': {
        'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth',
        'num_block': 23,
        'scale': 2,
        'description': '[Tencent] 2x upscale, faster, less VRAM'
    },
    'RealESRGAN_x4plus_anime_6B': {
        'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth',
        'num_block': 6,
        'scale': 4,
        'description': '[Tencent] Best for anime/manga'
    },
    'RealESRGAN_animevideov3': {
        'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth',
        'num_block': 6,
        'scale': 4,
        'description': '[Tencent] Temporal consistency for anime videos'
    },
    'RealESRNet_x4plus': {
        'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.1/RealESRNet_x4plus.pth',
        'num_block': 23,
        'scale': 4,
        'description': '[Tencent] No GAN, less artifacts'
    },
    'realesr-general-x4v3': {
        'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth',
        'num_block': 6,
        'scale': 4,
        'description': '[Tencent] Small model, fast'
    },
    'realesr-general-wdn-x4v3': {
        'url': 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-wdn-x4v3.pth',
        'num_block': 6,
        'scale': 4,
        'description': '[Tencent] With denoise, good for old/degraded photos'
    },
    # Chinese models (SwinIR, Swin2SR, ScuNET - different architectures)
    'SwinIR_realSR_x4': {
        'url': 'https://github.com/JingyunLiang/SwinIR/releases/download/v0.0/003_realSR_BSRGAN_DFOWMFC_s64w8_SwinIR-L_x4_GAN.pth',
        'num_block': None,
        'scale': 4,
        'description': '👑 [CUHK] Highest quality, Swin Transformer, slow, high VRAM'
    },
    'Swin2SR_realSR_x4': {
        'url': 'https://github.com/mv-lab/swin2sr/releases/download/v0.0.1/Swin2SR_RealworldSR_X4_64_BSRGAN_PSNR.pth',
        'num_block': None,
        'scale': 4,
        'description': '[ETH Zurich] Swin v2, faster than SwinIR, good quality'
    },
    'ScuNET_GAN': {
        'url': 'https://github.com/cszn/KAIR/releases/download/v1.0/scunet_color_real_gan.pth',
        'num_block': None,
        'scale': 1,
        'description': '[CUHK] Strong denoise + upscale, with GAN, for noisy images'
    },
    'ScuNET_PSNR': {
        'url': 'https://github.com/cszn/KAIR/releases/download/v1.0/scunet_color_real_psnr.pth',
        'num_block': None,
        'scale': 1,
        'description': '[CUHK] Less artifacts, no GAN, good for old photos'
    }
}
