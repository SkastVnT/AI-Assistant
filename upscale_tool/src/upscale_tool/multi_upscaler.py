"""
Multi-architecture upscaler supporting RealESRGAN, SwinIR, ScuNET
"""
import torch
import numpy as np
from pathlib import Path
import logging
from PIL import Image

logger = logging.getLogger(__name__)


class MultiArchUpscaler:
    """Upscaler that supports multiple architectures"""
    
    ARCH_INFO = {
        # Real-ESRGAN models (RRDBNet architecture)
        'RealESRGAN_x4plus': {'arch': 'rrdb', 'num_block': 23, 'scale': 4},
        'RealESRGAN_x2plus': {'arch': 'rrdb', 'num_block': 23, 'scale': 2},
        'RealESRGAN_x4plus_anime_6B': {'arch': 'rrdb', 'num_block': 6, 'scale': 4},
        'RealESRGAN_animevideov3': {'arch': 'rrdb', 'num_block': 6, 'scale': 4},
        'RealESRNet_x4plus': {'arch': 'rrdb', 'num_block': 23, 'scale': 4},
        'realesr-general-x4v3': {'arch': 'rrdb', 'num_block': 6, 'scale': 4},
        'realesr-general-wdn-x4v3': {'arch': 'rrdb', 'num_block': 6, 'scale': 4},
        
        # SwinIR models (Swin Transformer)
        'SwinIR_realSR_x4': {'arch': 'swinir', 'scale': 4},
        'Swin2SR_realSR_x4': {'arch': 'swin2sr', 'scale': 4},
        
        # ScuNET models (U-Net) - denoise only, no upscaling
        'ScuNET_GAN': {'arch': 'scunet', 'scale': 1},  # Denoise only
        'ScuNET_PSNR': {'arch': 'scunet', 'scale': 1},  # Denoise only
    }
    
    def __init__(self, model, device='auto', tile_size=400):
        """
        Initialize multi-architecture upscaler
        
        Args:
            model: Model name (e.g., 'RealESRGAN_x4plus', 'SwinIR_realSR_x4')
            device: 'auto', 'cuda', or 'cpu'
            tile_size: Tile size for processing large images
        """
        from .config import MODELS_DIR, SUPPORTED_MODELS
        from .utils import download_file
        
        self.model_name = model
        self.tile_size = tile_size
        
        # Auto device selection
        if device == 'auto':
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device if torch.cuda.is_available() and device == 'cuda' else 'cpu'
        
        # Get model info
        if model not in self.ARCH_INFO:
            raise ValueError(f"Unsupported model: {model}. Supported: {list(self.ARCH_INFO.keys())}")
        
        arch_info = self.ARCH_INFO[model]
        self.arch_type = arch_info['arch']
        self.scale = arch_info.get('scale', 4)
        
        # Download model if needed
        model_info = SUPPORTED_MODELS.get(model)
        if model_info is None:
            raise ValueError(f"Model {model} not found in SUPPORTED_MODELS")
        
        # Ensure models directory exists
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Download model if not exists
        model_path = MODELS_DIR / f"{model}.pth"
        if not model_path.exists():
            logger.info(f"Downloading model {model}...")
            download_file(model_info['url'], str(model_path))
            logger.info(f"Model downloaded to {model_path}")
        
        self.model_path = model_path
        
        # Load model based on architecture
        logger.info(f"Loading {model} with {self.arch_type} architecture...")
        self.upsampler = self._load_model()
        logger.info(f"Model loaded successfully on {self.device}")
    
    def _load_model(self):
        """Load model based on architecture type"""
        if self.arch_type == 'rrdb':
            return self._load_rrdb_model()
        elif self.arch_type == 'swinir':
            return self._load_swinir_model()
        elif self.arch_type == 'swin2sr':
            return self._load_swin2sr_model()
        elif self.arch_type == 'scunet':
            return self._load_scunet_model()
        else:
            raise ValueError(f"Unsupported architecture: {self.arch_type}")
    
    def _load_rrdb_model(self):
        """Load RRDBNet model (Real-ESRGAN)"""
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer
        from realesrgan.archs.srvgg_arch import SRVGGNetCompact
        
        arch_info = self.ARCH_INFO[self.model_name]
        
        # Load weights first to check structure
        loadnet = torch.load(self.model_path, map_location=self.device)
        if 'params_ema' in loadnet:
            keyname = 'params_ema'
        elif 'params' in loadnet:
            keyname = 'params'
        else:
            keyname = list(loadnet.keys())[0] if isinstance(loadnet, dict) else None
        
        state_dict = loadnet[keyname] if keyname and keyname in loadnet else loadnet
        
        # Check if it's SRVGG architecture (general models use this)
        # SRVGG uses simple Sequential layers (body.0.weight, body.1.weight...)
        # RRDB uses nested structure (body.0.rdb1.conv1.weight...)
        is_srvgg = False
        if 'body.0.weight' in state_dict and 'body.0.bias' in state_dict:
            # Check if it's truly SRVGG by looking for RRDB-specific keys
            if 'body.0.rdb1.conv1.weight' not in state_dict and 'conv_first.weight' not in state_dict:
                is_srvgg = True
        
        if is_srvgg:
            # SRVGG architecture (realesr-general models)
            # Detect num_feat from weights
            if 'body.0.weight' in state_dict:
                num_feat = state_dict['body.0.weight'].shape[0]
            else:
                num_feat = 64
            
            # Hardcode num_conv for known models
            if self.model_name == 'RealESRGAN_animevideov3':
                num_conv = 16  # animevideov3 uses 16 conv blocks
            elif self.model_name in ['realesr-general-x4v3', 'realesr-general-wdn-x4v3']:
                num_conv = 32  # general models use 32 conv blocks
            else:
                # Auto-detect from body layers
                body_keys = [k for k in state_dict.keys() if k.startswith('body.') and '.weight' in k]
                if body_keys:
                    max_idx = max([int(k.split('.')[1]) for k in body_keys if k.split('.')[1].isdigit()])
                    num_conv = (max_idx // 2) + 1
                else:
                    num_conv = 32
            
            model = SRVGGNetCompact(
                num_in_ch=3,
                num_out_ch=3,
                num_feat=num_feat,
                num_conv=num_conv,
                upscale=arch_info['scale'],
                act_type='prelu'
            )
        else:
            # RRDBNet architecture - detect num_feat from weights
            # Default is 64, but animevideov3 uses 48
            if 'conv_up1.weight' in state_dict:
                num_feat = state_dict['conv_up1.weight'].shape[1]  # Get feature channels
            else:
                num_feat = 64
            
            model = RRDBNet(
                num_in_ch=3,
                num_out_ch=3,
                num_feat=num_feat,
                num_block=arch_info['num_block'],
                num_grow_ch=32,
                scale=arch_info['scale']
            )
        
        model.load_state_dict(state_dict, strict=True)
        model.eval()
        model = model.to(self.device)
        
        # Enable FP16 if on CUDA
        if self.device == 'cuda':
            model = model.half()
        
        return model
    
    def _load_swinir_model(self):
        """Load SwinIR model (Swin Transformer)"""
        from .archs.swinir_model_arch import SwinIR
        
        # SwinIR config for Real-SR x4 - larger model
        model = SwinIR(
            upscale=4,
            in_chans=3,
            img_size=64,
            window_size=8,
            img_range=1.,
            depths=[6, 6, 6, 6, 6, 6, 6, 6, 6],
            embed_dim=240,
            num_heads=[8, 8, 8, 8, 8, 8, 8, 8, 8],
            mlp_ratio=2,
            upsampler='nearest+conv',
            resi_connection='3conv'
        )
        
        # Load weights
        loadnet = torch.load(self.model_path, map_location=self.device)
        if 'params_ema' in loadnet:
            keyname = 'params_ema'
        elif 'params' in loadnet:
            keyname = 'params'
        elif 'params-ema' in loadnet:
            keyname = 'params-ema'
        else:
            keyname = list(loadnet.keys())[0] if isinstance(loadnet, dict) and loadnet else 'params'
        
        state_dict = loadnet[keyname] if keyname and keyname in loadnet else loadnet
        model.load_state_dict(state_dict, strict=True)
        model.eval()
        model = model.to(self.device)
        
        # Keep SwinIR in FP32 to avoid dtype issues
        # if self.device == 'cuda':
        #     model = model.half()
        
        return model
    
    def _load_swin2sr_model(self):
        """Load Swin2SR model (Swin Transformer v2)"""
        from .archs.swinir_model_arch_v2 import Swin2SR
        
        # Load weights first to get params_ema
        loadnet = torch.load(self.model_path, map_location=self.device)
        
        # Swin2SR config for Real-SR x4
        model = Swin2SR(
            upscale=4,
            in_chans=3,
            img_size=64,
            window_size=8,
            img_range=1.,
            depths=[6, 6, 6, 6, 6, 6],
            embed_dim=180,
            num_heads=[6, 6, 6, 6, 6, 6],
            mlp_ratio=2,
            upsampler='nearest+conv',
            resi_connection='1conv'
        )
        
        # Get state dict
        if 'params_ema' in loadnet:
            state_dict = loadnet['params_ema']
        elif 'params' in loadnet:
            state_dict = loadnet['params']
        elif isinstance(loadnet, dict) and len(loadnet) > 0:
            state_dict = loadnet
        else:
            state_dict = loadnet
        
        model.load_state_dict(state_dict, strict=True)
        model.eval()
        model = model.to(self.device)
        
        # Keep Swin2SR in FP32 to avoid dtype issues
        # if self.device == 'cuda':
        #     model = model.half()
        
        return model
    
    def _load_scunet_model(self):
        """Load ScuNET model (U-Net for denoise)"""
        from .archs.scunet_model_arch import SCUNet
        
        # ScuNET config
        model = SCUNet(
            in_nc=3,
            config=[4, 4, 4, 4, 4, 4, 4],
            dim=64
        )
        
        # Load weights - ScuNET saves weights directly as tensor dict, not wrapped
        loadnet = torch.load(self.model_path, map_location=self.device)
        
        # Handle different weight formats
        if isinstance(loadnet, dict):
            if 'params_ema' in loadnet:
                state_dict = loadnet['params_ema']
            elif 'params' in loadnet:
                state_dict = loadnet['params']
            else:
                state_dict = loadnet
        else:
            # Weights saved directly without wrapper
            state_dict = loadnet
        
        model.load_state_dict(state_dict, strict=True)
        model.eval()
        model = model.to(self.device)
        
        if self.device == 'cuda':
            model = model.half()
        
        return model
    
    def upscale_array(self, img_array: np.ndarray, scale: int = None) -> np.ndarray:
        """
        Upscale a numpy image array
        
        Args:
            img_array: Input image as numpy array (H, W, C) or (H, W)
            scale: Upscale factor (optional, uses model default if None)
        
        Returns:
            Upscaled image as numpy array
        """
        if scale is None:
            scale = self.scale
        
        # Convert to tensor
        if img_array.ndim == 2:
            img_array = img_array[:, :, None]
        
        img_tensor = torch.from_numpy(img_array).permute(2, 0, 1).float().unsqueeze(0)
        img_tensor = img_tensor / 255.0
        
        # Move to device and match model dtype
        img_tensor = img_tensor.to(self.device)
        # Match the dtype of the model (half or float)
        model_dtype = next(self.upsampler.parameters()).dtype
        img_tensor = img_tensor.to(dtype=model_dtype)
        
        # Inference based on architecture
        with torch.no_grad():
            if self.arch_type in ['swinir', 'swin2sr']:
                output = self._swin_inference(img_tensor)
            else:
                output = self.upsampler(img_tensor)
        
        # Convert back to numpy
        output = output.squeeze(0).permute(1, 2, 0).cpu().float().numpy()
        output = np.clip(output * 255.0, 0, 255).astype(np.uint8)
        
        return output
    
    def _swin_inference(self, img_tensor):
        """Special inference for Swin-based models with window padding"""
        _, _, h, w = img_tensor.size()
        
        # Swin requires specific window size padding
        window_size = 8
        mod_pad_h = (window_size - h % window_size) % window_size
        mod_pad_w = (window_size - w % window_size) % window_size
        
        if mod_pad_h > 0 or mod_pad_w > 0:
            img_tensor = torch.nn.functional.pad(img_tensor, (0, mod_pad_w, 0, mod_pad_h), 'reflect')
        
        output = self.upsampler(img_tensor)
        
        # Remove padding from output
        if mod_pad_h > 0 or mod_pad_w > 0:
            _, _, h_out, w_out = output.size()
            output = output[:, :, :h_out - mod_pad_h * self.scale, :w_out - mod_pad_w * self.scale]
        
        return output
    
    def upscale_image(self, image_path: str, output_path: str = None, scale: int = None):
        """
        Upscale an image file
        
        Args:
            image_path: Path to input image
            output_path: Path to save output (optional)
            scale: Upscale factor (optional)
        
        Returns:
            Upscaled image as numpy array
        """
        # Load image
        img = Image.open(image_path).convert('RGB')
        img_array = np.array(img)
        
        # Upscale
        output_array = self.upscale_array(img_array, scale)
        
        # Save if output path provided
        if output_path:
            output_img = Image.fromarray(output_array)
            output_img.save(output_path)
        
        return output_array
