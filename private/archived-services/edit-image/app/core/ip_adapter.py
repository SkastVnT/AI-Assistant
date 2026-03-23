"""
IP-Adapter Integration for Edit Image Service.

IP-Adapter allows using images as prompts for Stable Diffusion,
enabling style transfer, face preservation, and reference-based generation.

Supports:
- IP-Adapter: General image prompts
- IP-Adapter Plus: Enhanced image understanding
- IP-Adapter FaceID: Face identity preservation
- IP-Adapter FaceID Plus: Combined face + style

References:
- https://github.com/tencent-ailab/IP-Adapter
- https://huggingface.co/h94/IP-Adapter
"""

import logging
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple
from functools import lru_cache

import torch
from PIL import Image

logger = logging.getLogger(__name__)


# ==============================================================================
# IP-Adapter Model Registry
# ==============================================================================

IP_ADAPTER_MODELS = {
    # SD 1.5 Models
    "sd15": {
        "ip_adapter": "h94/IP-Adapter/models/ip-adapter_sd15.bin",
        "ip_adapter_light": "h94/IP-Adapter/models/ip-adapter_sd15_light.bin",
        "ip_adapter_plus": "h94/IP-Adapter/models/ip-adapter-plus_sd15.bin",
        "ip_adapter_plus_face": "h94/IP-Adapter/models/ip-adapter-plus-face_sd15.bin",
        "ip_adapter_full_face": "h94/IP-Adapter/models/ip-adapter-full-face_sd15.bin",
    },
    # SDXL Models
    "sdxl": {
        "ip_adapter": "h94/IP-Adapter/sdxl_models/ip-adapter_sdxl.bin",
        "ip_adapter_plus": "h94/IP-Adapter/sdxl_models/ip-adapter-plus_sdxl_vit-h.bin",
        "ip_adapter_plus_face": "h94/IP-Adapter/sdxl_models/ip-adapter-plus-face_sdxl_vit-h.bin",
    },
    # FaceID Models (require InsightFace)
    "faceid": {
        "ip_adapter_faceid": "h94/IP-Adapter-FaceID/ip-adapter-faceid_sd15.bin",
        "ip_adapter_faceid_plus": "h94/IP-Adapter-FaceID/ip-adapter-faceid-plus_sd15.bin",
        "ip_adapter_faceid_plusv2": "h94/IP-Adapter-FaceID/ip-adapter-faceid-plusv2_sd15.bin",
        "ip_adapter_faceid_sdxl": "h94/IP-Adapter-FaceID/ip-adapter-faceid_sdxl.bin",
    },
}

# Image Encoder Models
IMAGE_ENCODERS = {
    "clip_vit_h": "laion/CLIP-ViT-H-14-laion2B-s32B-b79K",
    "clip_vit_g": "laion/CLIP-ViT-bigG-14-laion2B-39B-b160k",
    "openclip_vit_h": "h94/IP-Adapter/models/image_encoder",
    "openclip_vit_h_sdxl": "h94/IP-Adapter/sdxl_models/image_encoder",
}


# ==============================================================================
# IP-Adapter Manager
# ==============================================================================

class IPAdapterManager:
    """
    Manages IP-Adapter models for image-to-image prompting.
    
    Usage:
        manager = IPAdapterManager(device="cuda")
        
        # Load IP-Adapter for a pipeline
        pipe = manager.load_ip_adapter(
            pipeline=sdxl_pipeline,
            model_name="ip_adapter_plus",
            base_model="sdxl"
        )
        
        # Generate with image prompt
        image = manager.generate_with_image_prompt(
            pipeline=pipe,
            prompt="a beautiful woman",
            image_prompt=reference_image,
            scale=0.7
        )
    """
    
    def __init__(
        self,
        device: str = "cuda",
        dtype: torch.dtype = torch.float16,
        models_dir: str = "./models/ip_adapter",
    ):
        self.device = device
        self.dtype = dtype
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._image_encoder = None
        self._face_analyzer = None
        self._loaded_adapters: Dict[str, Any] = {}
        
        logger.info(f"IPAdapterManager initialized on {device}")
    
    def _get_image_encoder(self, encoder_type: str = "openclip_vit_h"):
        """Load CLIP image encoder for IP-Adapter."""
        if self._image_encoder is not None:
            return self._image_encoder
        
        try:
            from transformers import CLIPVisionModelWithProjection, CLIPImageProcessor
            
            encoder_path = IMAGE_ENCODERS.get(encoder_type, encoder_type)
            
            logger.info(f"Loading image encoder: {encoder_path}")
            
            self._image_processor = CLIPImageProcessor.from_pretrained(encoder_path)
            self._image_encoder = CLIPVisionModelWithProjection.from_pretrained(
                encoder_path,
                torch_dtype=self.dtype,
            ).to(self.device)
            
            return self._image_encoder
            
        except Exception as e:
            logger.error(f"Failed to load image encoder: {e}")
            raise
    
    def _get_face_analyzer(self):
        """Load InsightFace analyzer for FaceID."""
        if self._face_analyzer is not None:
            return self._face_analyzer
        
        try:
            from insightface.app import FaceAnalysis
            
            logger.info("Loading InsightFace face analyzer...")
            
            self._face_analyzer = FaceAnalysis(
                name="buffalo_l",
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
            )
            self._face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
            
            return self._face_analyzer
            
        except ImportError:
            logger.warning("InsightFace not installed. FaceID features unavailable.")
            return None
        except Exception as e:
            logger.error(f"Failed to load face analyzer: {e}")
            return None
    
    def load_ip_adapter(
        self,
        pipeline: Any,
        model_name: str = "ip_adapter_plus",
        base_model: str = "sdxl",
        scale: float = 1.0,
    ) -> Any:
        """
        Load IP-Adapter into a diffusion pipeline.
        
        Args:
            pipeline: StableDiffusion pipeline
            model_name: IP-Adapter model name
            base_model: Base model type (sd15, sdxl)
            scale: IP-Adapter conditioning scale
            
        Returns:
            Pipeline with IP-Adapter loaded
        """
        try:
            # Get model path
            if base_model in IP_ADAPTER_MODELS:
                model_paths = IP_ADAPTER_MODELS[base_model]
                if model_name in model_paths:
                    adapter_path = model_paths[model_name]
                else:
                    raise ValueError(f"Unknown IP-Adapter: {model_name}")
            else:
                raise ValueError(f"Unknown base model: {base_model}")
            
            # Load image encoder
            encoder_key = "openclip_vit_h_sdxl" if base_model == "sdxl" else "openclip_vit_h"
            image_encoder = self._get_image_encoder(encoder_key)
            
            # Load IP-Adapter weights
            logger.info(f"Loading IP-Adapter: {adapter_path}")
            
            # Use diffusers' built-in IP-Adapter loading
            pipeline.load_ip_adapter(
                "h94/IP-Adapter",
                subfolder="sdxl_models" if base_model == "sdxl" else "models",
                weight_name=adapter_path.split("/")[-1],
            )
            
            pipeline.set_ip_adapter_scale(scale)
            
            self._loaded_adapters[model_name] = {
                "pipeline": pipeline,
                "scale": scale,
            }
            
            logger.info(f"IP-Adapter {model_name} loaded successfully")
            return pipeline
            
        except Exception as e:
            logger.error(f"Failed to load IP-Adapter: {e}")
            raise
    
    def prepare_image_prompt(
        self,
        image: Union[Image.Image, List[Image.Image]],
        mode: str = "full",
    ) -> Dict[str, Any]:
        """
        Prepare image(s) for IP-Adapter input.
        
        Args:
            image: Single image or list of images
            mode: Preparation mode:
                - "full": Use full image
                - "face": Extract and use face only
                - "style": Focus on style features
                
        Returns:
            Prepared inputs for IP-Adapter
        """
        if isinstance(image, Image.Image):
            images = [image]
        else:
            images = image
        
        # Convert to RGB
        images = [img.convert("RGB") for img in images]
        
        if mode == "face":
            # Extract faces using InsightFace
            face_analyzer = self._get_face_analyzer()
            if face_analyzer is None:
                logger.warning("Face analyzer unavailable, using full image")
                mode = "full"
            else:
                face_images = []
                for img in images:
                    import numpy as np
                    img_array = np.array(img)
                    faces = face_analyzer.get(img_array)
                    
                    if faces:
                        # Get the largest face
                        face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
                        bbox = face.bbox.astype(int)
                        
                        # Crop face with padding
                        x1, y1, x2, y2 = bbox
                        w, h = x2 - x1, y2 - y1
                        pad = int(max(w, h) * 0.3)
                        
                        x1 = max(0, x1 - pad)
                        y1 = max(0, y1 - pad)
                        x2 = min(img.width, x2 + pad)
                        y2 = min(img.height, y2 + pad)
                        
                        face_img = img.crop((x1, y1, x2, y2))
                        face_images.append(face_img)
                    else:
                        face_images.append(img)  # Use original if no face found
                
                images = face_images
        
        # Process images
        processed = self._image_processor(
            images=images,
            return_tensors="pt"
        )
        
        return {
            "images": images,
            "pixel_values": processed.pixel_values.to(self.device, dtype=self.dtype),
            "mode": mode,
        }
    
    def generate_with_image_prompt(
        self,
        pipeline: Any,
        prompt: str,
        image_prompt: Union[Image.Image, List[Image.Image]],
        negative_prompt: Optional[str] = None,
        scale: float = 0.7,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        **kwargs,
    ) -> Image.Image:
        """
        Generate image using both text and image prompts.
        
        Args:
            pipeline: Pipeline with IP-Adapter loaded
            prompt: Text prompt
            image_prompt: Reference image(s) for style/content
            negative_prompt: Negative text prompt
            scale: IP-Adapter scale (0-1)
            num_inference_steps: Number of denoising steps
            guidance_scale: CFG scale
            width: Output width
            height: Output height
            seed: Random seed
            
        Returns:
            Generated image
        """
        # Set scale
        pipeline.set_ip_adapter_scale(scale)
        
        # Prepare generator
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        # Prepare image prompt
        if isinstance(image_prompt, list):
            ip_adapter_image = image_prompt
        else:
            ip_adapter_image = [image_prompt]
        
        # Generate
        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            ip_adapter_image=ip_adapter_image,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            generator=generator,
            **kwargs,
        )
        
        return result.images[0]
    
    def extract_face_embedding(
        self,
        image: Image.Image,
    ) -> Optional[torch.Tensor]:
        """
        Extract face embedding for FaceID IP-Adapter.
        
        Args:
            image: Image containing a face
            
        Returns:
            Face embedding tensor or None if no face found
        """
        face_analyzer = self._get_face_analyzer()
        if face_analyzer is None:
            return None
        
        import numpy as np
        img_array = np.array(image.convert("RGB"))
        faces = face_analyzer.get(img_array)
        
        if not faces:
            logger.warning("No face detected in image")
            return None
        
        # Get the largest face
        face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
        
        # Return embedding
        embedding = torch.from_numpy(face.normed_embedding).unsqueeze(0)
        return embedding.to(self.device, dtype=self.dtype)
    
    def generate_with_face(
        self,
        pipeline: Any,
        prompt: str,
        face_image: Image.Image,
        negative_prompt: Optional[str] = None,
        face_scale: float = 0.6,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        **kwargs,
    ) -> Optional[Image.Image]:
        """
        Generate image while preserving face identity.
        
        Uses IP-Adapter FaceID for face preservation.
        
        Args:
            pipeline: Pipeline with FaceID IP-Adapter loaded
            prompt: Text prompt
            face_image: Reference face image
            negative_prompt: Negative text prompt
            face_scale: Face preservation strength
            
        Returns:
            Generated image with preserved face, or None if face extraction fails
        """
        # Extract face embedding
        face_embedding = self.extract_face_embedding(face_image)
        if face_embedding is None:
            logger.error("Could not extract face embedding")
            return None
        
        # Set scale
        pipeline.set_ip_adapter_scale(face_scale)
        
        # Prepare generator
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        # Generate with face embedding
        result = pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            ip_adapter_image_embeds=face_embedding,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            generator=generator,
            **kwargs,
        )
        
        return result.images[0]
    
    def style_transfer(
        self,
        pipeline: Any,
        content_image: Image.Image,
        style_image: Image.Image,
        prompt: str = "",
        style_scale: float = 0.8,
        content_scale: float = 0.4,
        strength: float = 0.6,
        num_inference_steps: int = 30,
        seed: Optional[int] = None,
    ) -> Image.Image:
        """
        Transfer style from one image to another.
        
        Args:
            pipeline: Pipeline with IP-Adapter loaded
            content_image: Content source image
            style_image: Style reference image
            prompt: Optional text prompt
            style_scale: Style transfer strength
            content_scale: Content preservation strength
            strength: Denoising strength for img2img
            
        Returns:
            Style-transferred image
        """
        # Use style image as IP-Adapter input
        pipeline.set_ip_adapter_scale(style_scale)
        
        # Prepare generator
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        # Generate
        result = pipeline(
            prompt=prompt if prompt else "masterpiece, best quality",
            image=content_image,
            ip_adapter_image=style_image,
            strength=strength,
            num_inference_steps=num_inference_steps,
            generator=generator,
        )
        
        return result.images[0]
    
    def unload(self, pipeline: Any = None):
        """Unload IP-Adapter from pipeline."""
        if pipeline is not None:
            try:
                pipeline.unload_ip_adapter()
            except Exception as e:
                logger.warning(f"Failed to unload IP-Adapter: {e}")
        
        self._loaded_adapters.clear()
        logger.info("IP-Adapter unloaded")


# ==============================================================================
# Convenience Functions
# ==============================================================================

_manager: Optional[IPAdapterManager] = None

def get_ip_adapter_manager() -> IPAdapterManager:
    """Get singleton IP-Adapter manager instance."""
    global _manager
    if _manager is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _manager = IPAdapterManager(device=device)
    return _manager


def apply_image_prompt(
    pipeline: Any,
    reference_image: Image.Image,
    prompt: str,
    scale: float = 0.7,
    **kwargs,
) -> Image.Image:
    """
    Convenience function to apply image prompt to generation.
    
    Args:
        pipeline: Diffusion pipeline
        reference_image: Reference image for style/content
        prompt: Text prompt
        scale: IP-Adapter influence strength
        
    Returns:
        Generated image
    """
    manager = get_ip_adapter_manager()
    
    # Load IP-Adapter if not already loaded
    pipeline = manager.load_ip_adapter(pipeline, model_name="ip_adapter_plus")
    
    return manager.generate_with_image_prompt(
        pipeline=pipeline,
        prompt=prompt,
        image_prompt=reference_image,
        scale=scale,
        **kwargs,
    )


def preserve_face(
    pipeline: Any,
    face_image: Image.Image,
    prompt: str,
    scale: float = 0.6,
    **kwargs,
) -> Optional[Image.Image]:
    """
    Convenience function to preserve face identity in generation.
    
    Args:
        pipeline: Diffusion pipeline
        face_image: Face reference image
        prompt: Text prompt
        scale: Face preservation strength
        
    Returns:
        Generated image with preserved face
    """
    manager = get_ip_adapter_manager()
    
    # Load FaceID IP-Adapter
    pipeline = manager.load_ip_adapter(
        pipeline,
        model_name="ip_adapter_faceid_plus",
        base_model="faceid"
    )
    
    return manager.generate_with_face(
        pipeline=pipeline,
        prompt=prompt,
        face_image=face_image,
        face_scale=scale,
        **kwargs,
    )
