"""
Upscaler module for Edit Image Service.
Provides image upscaling using Real-ESRGAN and face restoration using GFPGAN/CodeFormer.
"""

import logging
from pathlib import Path
from typing import Optional, Union, Tuple
import gc

import numpy as np
from PIL import Image
import torch

logger = logging.getLogger(__name__)


class RealESRGAN:
    """
    Real-ESRGAN upscaler for high-quality image upscaling.
    
    Supports:
    - RealESRGAN_x4plus (general images)
    - RealESRGAN_x4plus_anime_6B (anime/illustration)
    - RealESRGAN_x2plus (2x upscale)
    """
    
    MODELS = {
        "x4plus": {
            "name": "RealESRGAN_x4plus",
            "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
            "scale": 4,
            "model_type": "RRDBNet",
        },
        "x4plus_anime": {
            "name": "RealESRGAN_x4plus_anime_6B",
            "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
            "scale": 4,
            "model_type": "RRDBNet_anime",
        },
        "x2plus": {
            "name": "RealESRGAN_x2plus",
            "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
            "scale": 2,
            "model_type": "RRDBNet",
        },
    }
    
    def __init__(
        self,
        model_name: str = "x4plus",
        model_path: Optional[str] = None,
        device: str = "cuda",
        half: bool = True,
    ):
        """
        Initialize Real-ESRGAN upscaler.
        
        Args:
            model_name: Model variant name
            model_path: Custom model path
            device: Device to run on (cuda/cpu)
            half: Use FP16 for faster inference
        """
        self.model_name = model_name
        self.model_path = model_path
        self.device = device if torch.cuda.is_available() else "cpu"
        self.half = half and self.device == "cuda"
        
        self.model = None
        self.upsampler = None
        
        self._load_model()
    
    def _load_model(self):
        """Load the Real-ESRGAN model."""
        try:
            from basicsr.archs.rrdbnet_arch import RRDBNet
            from realesrgan import RealESRGANer
        except ImportError:
            raise ImportError(
                "Real-ESRGAN requires basicsr and realesrgan. "
                "Install with: pip install basicsr realesrgan"
            )
        
        model_info = self.MODELS.get(self.model_name)
        if model_info is None:
            raise ValueError(f"Unknown model: {self.model_name}")
        
        # Create model architecture
        if "anime" in self.model_name:
            self.model = RRDBNet(
                num_in_ch=3,
                num_out_ch=3,
                num_feat=64,
                num_block=6,
                num_grow_ch=32,
                scale=model_info["scale"],
            )
        else:
            self.model = RRDBNet(
                num_in_ch=3,
                num_out_ch=3,
                num_feat=64,
                num_block=23,
                num_grow_ch=32,
                scale=model_info["scale"],
            )
        
        # Determine model path
        if self.model_path:
            model_file = self.model_path
        else:
            model_file = Path("./models/realesrgan") / f"{model_info['name']}.pth"
            if not model_file.exists():
                logger.info(f"Downloading {model_info['name']}...")
                model_file.parent.mkdir(parents=True, exist_ok=True)
                
                import requests
                response = requests.get(model_info["url"], stream=True)
                response.raise_for_status()
                
                with open(model_file, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
        
        # Create upsampler
        self.upsampler = RealESRGANer(
            scale=model_info["scale"],
            model_path=str(model_file),
            model=self.model,
            tile=400,  # Tile size for memory efficiency
            tile_pad=10,
            pre_pad=0,
            half=self.half,
            device=self.device,
        )
        
        logger.info(f"Loaded Real-ESRGAN model: {model_info['name']}")
    
    def upscale(
        self,
        image: Union[str, Path, Image.Image],
        outscale: Optional[float] = None,
    ) -> Image.Image:
        """
        Upscale an image.
        
        Args:
            image: Input image
            outscale: Output scale factor (default: model's scale)
            
        Returns:
            Upscaled PIL Image
        """
        # Load image
        if isinstance(image, (str, Path)):
            img = Image.open(image).convert("RGB")
        else:
            img = image.convert("RGB")
        
        # Convert to numpy BGR
        img_np = np.array(img)[:, :, ::-1]
        
        # Upscale
        output, _ = self.upsampler.enhance(img_np, outscale=outscale)
        
        # Convert back to PIL RGB
        output_rgb = output[:, :, ::-1]
        return Image.fromarray(output_rgb)
    
    def __del__(self):
        """Cleanup."""
        del self.model
        del self.upsampler
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class GFPGAN:
    """
    GFPGAN for face restoration and enhancement.
    """
    
    MODEL_URL = "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth"
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        upscale: int = 2,
        device: str = "cuda",
    ):
        """
        Initialize GFPGAN.
        
        Args:
            model_path: Path to model file
            upscale: Upscale factor
            device: Device to run on
        """
        self.model_path = model_path
        self.upscale = upscale
        self.device = device if torch.cuda.is_available() else "cpu"
        
        self.restorer = None
        self._load_model()
    
    def _load_model(self):
        """Load the GFPGAN model."""
        try:
            from gfpgan import GFPGANer
        except ImportError:
            raise ImportError(
                "GFPGAN is required. Install with: pip install gfpgan"
            )
        
        # Determine model path
        if self.model_path:
            model_file = Path(self.model_path)
        else:
            model_file = Path("./models/gfpgan/GFPGANv1.4.pth")
            if not model_file.exists():
                logger.info("Downloading GFPGANv1.4...")
                model_file.parent.mkdir(parents=True, exist_ok=True)
                
                import requests
                response = requests.get(self.MODEL_URL, stream=True)
                response.raise_for_status()
                
                with open(model_file, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
        
        self.restorer = GFPGANer(
            model_path=str(model_file),
            upscale=self.upscale,
            arch="clean",
            channel_multiplier=2,
            device=self.device,
        )
        
        logger.info("Loaded GFPGAN model")
    
    def restore(
        self,
        image: Union[str, Path, Image.Image],
        only_center_face: bool = False,
        paste_back: bool = True,
    ) -> Tuple[Image.Image, list]:
        """
        Restore faces in an image.
        
        Args:
            image: Input image
            only_center_face: Only process center face
            paste_back: Paste restored faces back
            
        Returns:
            Tuple of (restored image, list of face crops)
        """
        # Load image
        if isinstance(image, (str, Path)):
            img = Image.open(image).convert("RGB")
        else:
            img = image.convert("RGB")
        
        # Convert to numpy BGR
        img_np = np.array(img)[:, :, ::-1]
        
        # Restore
        _, restored_faces, restored_img = self.restorer.enhance(
            img_np,
            has_aligned=False,
            only_center_face=only_center_face,
            paste_back=paste_back,
        )
        
        # Convert faces
        face_images = []
        for face in restored_faces:
            face_rgb = face[:, :, ::-1]
            face_images.append(Image.fromarray(face_rgb))
        
        # Convert main output
        if restored_img is not None:
            output_rgb = restored_img[:, :, ::-1]
            output_img = Image.fromarray(output_rgb)
        else:
            output_img = img
        
        return output_img, face_images


class CodeFormer:
    """
    CodeFormer for high-quality face restoration.
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        fidelity_weight: float = 0.5,
        device: str = "cuda",
    ):
        """
        Initialize CodeFormer.
        
        Args:
            model_path: Path to model file
            fidelity_weight: Balance between quality and fidelity (0-1)
            device: Device to run on
        """
        self.model_path = model_path
        self.fidelity_weight = fidelity_weight
        self.device = device if torch.cuda.is_available() else "cpu"
        
        self.restorer = None
        self._available = self._check_availability()
    
    def _check_availability(self) -> bool:
        """Check if CodeFormer is available."""
        try:
            from codeformer import CodeFormerEnhancer
            return True
        except ImportError:
            logger.warning(
                "CodeFormer not available. Install from: "
                "https://github.com/sczhou/CodeFormer"
            )
            return False
    
    def restore(
        self,
        image: Union[str, Path, Image.Image],
    ) -> Image.Image:
        """
        Restore faces in an image using CodeFormer.
        
        Args:
            image: Input image
            
        Returns:
            Restored image
        """
        if not self._available:
            logger.warning("CodeFormer not available, returning original image")
            if isinstance(image, (str, Path)):
                return Image.open(image).convert("RGB")
            return image.convert("RGB")
        
        # Implementation would depend on CodeFormer setup
        raise NotImplementedError("CodeFormer integration pending")


class PostProcessor:
    """
    Unified post-processor combining upscaling and face restoration.
    """
    
    def __init__(
        self,
        upscaler: str = "x4plus",
        face_restore: str = "gfpgan",
        device: str = "cuda",
    ):
        """
        Initialize post-processor.
        
        Args:
            upscaler: Upscaler model name
            face_restore: Face restoration model
            device: Device to run on
        """
        self.device = device if torch.cuda.is_available() else "cpu"
        
        self._upscaler = None
        self._face_restorer = None
        
        self.upscaler_name = upscaler
        self.face_restore_name = face_restore
    
    @property
    def upscaler(self) -> RealESRGAN:
        """Lazy-load upscaler."""
        if self._upscaler is None:
            self._upscaler = RealESRGAN(
                model_name=self.upscaler_name,
                device=self.device,
            )
        return self._upscaler
    
    @property
    def face_restorer(self) -> GFPGAN:
        """Lazy-load face restorer."""
        if self._face_restorer is None:
            self._face_restorer = GFPGAN(device=self.device)
        return self._face_restorer
    
    def process(
        self,
        image: Union[str, Path, Image.Image],
        upscale: bool = True,
        restore_faces: bool = True,
        upscale_first: bool = False,
    ) -> Image.Image:
        """
        Process an image with upscaling and face restoration.
        
        Args:
            image: Input image
            upscale: Apply upscaling
            restore_faces: Apply face restoration
            upscale_first: Upscale before face restoration
            
        Returns:
            Processed image
        """
        # Load image
        if isinstance(image, (str, Path)):
            img = Image.open(image).convert("RGB")
        else:
            img = image.convert("RGB")
        
        if upscale_first and upscale:
            img = self.upscaler.upscale(img)
        
        if restore_faces:
            img, _ = self.face_restorer.restore(img)
        
        if not upscale_first and upscale:
            img = self.upscaler.upscale(img)
        
        return img
    
    def upscale_only(
        self,
        image: Union[str, Path, Image.Image],
        model: Optional[str] = None,
    ) -> Image.Image:
        """
        Only upscale an image.
        
        Args:
            image: Input image
            model: Upscaler model to use
            
        Returns:
            Upscaled image
        """
        if model and model != self.upscaler_name:
            upscaler = RealESRGAN(model_name=model, device=self.device)
            return upscaler.upscale(image)
        return self.upscaler.upscale(image)
    
    def restore_faces_only(
        self,
        image: Union[str, Path, Image.Image],
    ) -> Image.Image:
        """
        Only restore faces in an image.
        
        Args:
            image: Input image
            
        Returns:
            Image with restored faces
        """
        result, _ = self.face_restorer.restore(image)
        return result
    
    def clear_cache(self):
        """Clear model cache and free memory."""
        self._upscaler = None
        self._face_restorer = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# Global post-processor
_processor: Optional[PostProcessor] = None


def get_post_processor(device: str = "cuda") -> PostProcessor:
    """Get or create the global post-processor."""
    global _processor
    if _processor is None:
        _processor = PostProcessor(device=device)
    return _processor


def upscale_image(
    image: Union[str, Path, Image.Image],
    model: str = "x4plus",
) -> Image.Image:
    """
    Upscale an image using Real-ESRGAN.
    
    Args:
        image: Input image
        model: Upscaler model name
        
    Returns:
        Upscaled image
    """
    processor = get_post_processor()
    return processor.upscale_only(image, model=model)


def restore_faces(
    image: Union[str, Path, Image.Image],
) -> Image.Image:
    """
    Restore faces in an image using GFPGAN.
    
    Args:
        image: Input image
        
    Returns:
        Image with restored faces
    """
    processor = get_post_processor()
    return processor.restore_faces_only(image)


def enhance_image(
    image: Union[str, Path, Image.Image],
    upscale: bool = True,
    restore_faces: bool = True,
) -> Image.Image:
    """
    Enhance an image with upscaling and face restoration.
    
    Args:
        image: Input image
        upscale: Apply upscaling
        restore_faces: Apply face restoration
        
    Returns:
        Enhanced image
    """
    processor = get_post_processor()
    return processor.process(image, upscale=upscale, restore_faces=restore_faces)
