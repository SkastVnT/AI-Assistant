"""
Anime ControlNet Models for Edit Image Service.

Specialized ControlNet models for anime/manga style generation:
- lineart_anime: Extract and generate from anime lineart
- style_anime: Anime style transfer
- openpose_anime: Anime-specific pose detection

Based on research from private docs on anime-specific models.

References:
- https://huggingface.co/lllyasviel/sd-controlnet-lineart-anime
- https://huggingface.co/thibaud/controlnet-sd21-lineart-anime
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union

import torch
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


# ==============================================================================
# Anime ControlNet Model Registry
# ==============================================================================

ANIME_CONTROLNET_MODELS = {
    # SD 1.5 Anime ControlNets
    "lineart_anime_sd15": {
        "repo": "lllyasviel/control_v11p_sd15s2_lineart_anime",
        "base": "sd15",
        "preprocessor": "lineart_anime",
        "description": "Anime lineart extraction and generation",
    },
    "canny_anime_sd15": {
        "repo": "lllyasviel/control_v11p_sd15_canny",
        "base": "sd15",
        "preprocessor": "canny",
        "description": "Edge detection for anime",
    },
    "openpose_sd15": {
        "repo": "lllyasviel/control_v11p_sd15_openpose",
        "base": "sd15",
        "preprocessor": "openpose",
        "description": "Pose detection",
    },
    
    # SDXL Anime ControlNets
    "lineart_anime_sdxl": {
        "repo": "SargeZT/controlnet-sd-xl-1.0-lineart-anime",
        "base": "sdxl",
        "preprocessor": "lineart_anime",
        "description": "SDXL anime lineart",
    },
    "canny_sdxl": {
        "repo": "diffusers/controlnet-canny-sdxl-1.0",
        "base": "sdxl",
        "preprocessor": "canny",
        "description": "SDXL canny edge",
    },
    
    # Specialized anime models
    "anime_style": {
        "repo": "TencentARC/t2i-adapter-lineart-sdxl-1.0",
        "base": "sdxl",
        "preprocessor": "lineart",
        "type": "t2i_adapter",
        "description": "T2I Adapter for style",
    },
    "anime_face": {
        "repo": "CrucibleAI/ControlNetMediaPipeFace",
        "base": "sd15",
        "preprocessor": "mediapipe_face",
        "description": "Anime face control",
    },
}

# Anime-optimized preprocessor settings
ANIME_PREPROCESS_SETTINGS = {
    "lineart_anime": {
        "detect_resolution": 512,
        "image_resolution": 1024,
        "coarse": False,
    },
    "canny": {
        "low_threshold": 50,
        "high_threshold": 200,
        "detect_resolution": 512,
    },
    "openpose": {
        "detect_resolution": 512,
        "include_hand": True,
        "include_face": True,
    },
}


# ==============================================================================
# Anime Preprocessors
# ==============================================================================

class AnimePreprocessor:
    """
    Preprocessors optimized for anime-style images.
    """
    
    def __init__(self, device: str = "cuda"):
        self.device = device
        self._processors: Dict[str, Any] = {}
        
        logger.info("AnimePreprocessor initialized")
    
    def _load_processor(self, name: str):
        """Load a specific preprocessor."""
        if name in self._processors:
            return self._processors[name]
        
        try:
            from controlnet_aux import (
                LineartAnimeDetector,
                CannyDetector,
                OpenposeDetector,
                LineartDetector,
            )
            
            if name == "lineart_anime":
                self._processors[name] = LineartAnimeDetector.from_pretrained(
                    "lllyasviel/Annotators"
                ).to(self.device)
            elif name == "lineart":
                self._processors[name] = LineartDetector.from_pretrained(
                    "lllyasviel/Annotators"
                ).to(self.device)
            elif name == "canny":
                self._processors[name] = CannyDetector()
            elif name == "openpose":
                self._processors[name] = OpenposeDetector.from_pretrained(
                    "lllyasviel/Annotators"
                ).to(self.device)
            else:
                raise ValueError(f"Unknown preprocessor: {name}")
            
            logger.info(f"Loaded preprocessor: {name}")
            return self._processors[name]
            
        except ImportError:
            logger.error("controlnet_aux not installed")
            logger.info("Install with: pip install controlnet-aux")
            raise
    
    def preprocess(
        self,
        image: Image.Image,
        processor_name: str,
        **kwargs,
    ) -> Image.Image:
        """
        Preprocess image for ControlNet.
        
        Args:
            image: Input image
            processor_name: Name of preprocessor to use
            **kwargs: Additional preprocessor arguments
            
        Returns:
            Preprocessed control image
        """
        # Get default settings
        settings = ANIME_PREPROCESS_SETTINGS.get(processor_name, {}).copy()
        settings.update(kwargs)
        
        processor = self._load_processor(processor_name)
        
        # Run preprocessing
        result = processor(image, **settings)
        
        return result
    
    def lineart_anime(
        self,
        image: Image.Image,
        coarse: bool = False,
    ) -> Image.Image:
        """
        Extract anime-style lineart from image.
        
        Args:
            image: Input image (can be photo or illustration)
            coarse: Use coarser lines
            
        Returns:
            Lineart image
        """
        return self.preprocess(
            image,
            "lineart_anime",
            coarse=coarse,
        )
    
    def canny_anime(
        self,
        image: Image.Image,
        low_threshold: int = 50,
        high_threshold: int = 200,
    ) -> Image.Image:
        """
        Extract edges optimized for anime.
        
        Uses softer thresholds than standard canny.
        """
        return self.preprocess(
            image,
            "canny",
            low_threshold=low_threshold,
            high_threshold=high_threshold,
        )
    
    def openpose_anime(
        self,
        image: Image.Image,
        include_hand: bool = True,
        include_face: bool = True,
    ) -> Image.Image:
        """
        Extract pose for anime character generation.
        """
        return self.preprocess(
            image,
            "openpose",
            include_hand=include_hand,
            include_face=include_face,
        )


# ==============================================================================
# Anime ControlNet Pipeline
# ==============================================================================

class AnimeControlNetPipeline:
    """
    ControlNet pipeline optimized for anime generation.
    
    Usage:
        pipeline = AnimeControlNetPipeline()
        
        # Lineart to anime
        result = pipeline.generate(
            control_image=lineart_image,
            prompt="1girl, anime, detailed, beautiful",
            controlnet="lineart_anime_sd15",
        )
        
        # Photo to anime with style transfer
        result = pipeline.photo_to_anime(
            photo=photo_image,
            prompt="anime style, detailed",
        )
    """
    
    def __init__(
        self,
        device: str = "cuda",
        dtype: torch.dtype = torch.float16,
        models_dir: str = "./models/controlnet",
    ):
        self.device = device
        self.dtype = dtype
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.preprocessor = AnimePreprocessor(device=device)
        
        self._pipelines: Dict[str, Any] = {}
        self._controlnets: Dict[str, Any] = {}
        
        logger.info("AnimeControlNetPipeline initialized")
    
    def _load_controlnet(self, name: str):
        """Load a specific ControlNet model."""
        if name in self._controlnets:
            return self._controlnets[name]
        
        model_info = ANIME_CONTROLNET_MODELS.get(name)
        if model_info is None:
            raise ValueError(f"Unknown ControlNet: {name}")
        
        try:
            from diffusers import ControlNetModel
            
            logger.info(f"Loading ControlNet: {name}")
            
            self._controlnets[name] = ControlNetModel.from_pretrained(
                model_info["repo"],
                torch_dtype=self.dtype,
            ).to(self.device)
            
            return self._controlnets[name]
            
        except Exception as e:
            logger.error(f"Failed to load ControlNet {name}: {e}")
            raise
    
    def _get_pipeline(self, controlnet_name: str):
        """Get or create pipeline for controlnet."""
        if controlnet_name in self._pipelines:
            return self._pipelines[controlnet_name]
        
        model_info = ANIME_CONTROLNET_MODELS[controlnet_name]
        base = model_info["base"]
        
        try:
            from diffusers import (
                StableDiffusionControlNetPipeline,
                StableDiffusionXLControlNetPipeline,
            )
            
            controlnet = self._load_controlnet(controlnet_name)
            
            if base == "sdxl":
                # Use anime-optimized SDXL model
                base_model = "cagliostrolab/animagine-xl-3.1"
                PipelineClass = StableDiffusionXLControlNetPipeline
            else:
                # Use anime SD 1.5 model
                base_model = "Linaqruf/anything-v3.0"
                PipelineClass = StableDiffusionControlNetPipeline
            
            logger.info(f"Loading base model: {base_model}")
            
            pipe = PipelineClass.from_pretrained(
                base_model,
                controlnet=controlnet,
                torch_dtype=self.dtype,
                safety_checker=None,
            ).to(self.device)
            
            # Enable optimizations
            if hasattr(pipe, "enable_xformers_memory_efficient_attention"):
                try:
                    pipe.enable_xformers_memory_efficient_attention()
                except Exception:
                    pass
            
            self._pipelines[controlnet_name] = pipe
            return pipe
            
        except Exception as e:
            logger.error(f"Failed to create pipeline: {e}")
            raise
    
    def generate(
        self,
        control_image: Image.Image,
        prompt: str,
        controlnet: str = "lineart_anime_sd15",
        negative_prompt: Optional[str] = None,
        controlnet_conditioning_scale: float = 1.0,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.5,
        width: Optional[int] = None,
        height: Optional[int] = None,
        seed: Optional[int] = None,
        **kwargs,
    ) -> Image.Image:
        """
        Generate anime image with ControlNet guidance.
        
        Args:
            control_image: Control image (lineart, pose, etc.)
            prompt: Text prompt
            controlnet: ControlNet model to use
            negative_prompt: Negative prompt
            controlnet_conditioning_scale: ControlNet strength
            num_inference_steps: Denoising steps
            guidance_scale: CFG scale
            width: Output width (uses control image size if None)
            height: Output height
            seed: Random seed
            
        Returns:
            Generated anime image
        """
        pipe = self._get_pipeline(controlnet)
        
        # Default negative prompt for anime
        if negative_prompt is None:
            negative_prompt = (
                "lowres, bad anatomy, bad hands, text, error, missing fingers, "
                "extra digit, fewer digits, cropped, worst quality, low quality, "
                "normal quality, jpeg artifacts, signature, watermark, username, blurry"
            )
        
        # Use control image size if not specified
        if width is None:
            width = control_image.width
        if height is None:
            height = control_image.height
        
        # Ensure dimensions are multiples of 8
        width = (width // 8) * 8
        height = (height // 8) * 8
        
        # Generator
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        # Resize control image
        control_image = control_image.resize((width, height), Image.Resampling.LANCZOS)
        
        # Generate
        result = pipe(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=control_image,
            controlnet_conditioning_scale=controlnet_conditioning_scale,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            generator=generator,
            **kwargs,
        )
        
        return result.images[0]
    
    def lineart_to_anime(
        self,
        lineart: Image.Image,
        prompt: str,
        **kwargs,
    ) -> Image.Image:
        """
        Convert lineart to full anime illustration.
        
        Args:
            lineart: Lineart image (black lines on white background)
            prompt: Description of desired output
            
        Returns:
            Colored anime illustration
        """
        # Invert if needed (lineart should be white lines on black)
        lineart_array = np.array(lineart.convert("L"))
        if lineart_array.mean() > 127:  # Mostly white
            lineart_array = 255 - lineart_array
            lineart = Image.fromarray(lineart_array)
        
        return self.generate(
            control_image=lineart,
            prompt=prompt,
            controlnet="lineart_anime_sd15",
            **kwargs,
        )
    
    def photo_to_anime(
        self,
        photo: Image.Image,
        prompt: str,
        style: str = "anime",
        preserve_pose: bool = True,
        **kwargs,
    ) -> Image.Image:
        """
        Convert photo to anime style.
        
        Args:
            photo: Input photo
            prompt: Style description
            style: Style preset (anime, manga, chibi)
            preserve_pose: Whether to preserve pose from photo
            
        Returns:
            Anime-styled image
        """
        # Extract lineart from photo
        lineart = self.preprocessor.lineart_anime(photo)
        
        # Add style-specific tags
        style_tags = {
            "anime": "anime style, detailed, beautiful, vibrant colors",
            "manga": "manga style, black and white, screentone, detailed",
            "chibi": "chibi, cute, simple, kawaii, big head",
        }
        
        full_prompt = f"{prompt}, {style_tags.get(style, style_tags['anime'])}"
        
        if preserve_pose:
            # Also extract pose and blend
            pose = self.preprocessor.openpose_anime(photo)
            # Could use multi-controlnet here
        
        return self.generate(
            control_image=lineart,
            prompt=full_prompt,
            controlnet="lineart_anime_sd15",
            **kwargs,
        )
    
    def sketch_to_anime(
        self,
        sketch: Image.Image,
        prompt: str,
        cleanup_sketch: bool = True,
        **kwargs,
    ) -> Image.Image:
        """
        Convert rough sketch to finished anime illustration.
        
        Args:
            sketch: Hand-drawn sketch
            prompt: Description of desired output
            cleanup_sketch: Whether to clean up sketch lines first
            
        Returns:
            Finished anime illustration
        """
        if cleanup_sketch:
            # Use lineart preprocessor to clean up sketch
            sketch = self.preprocessor.lineart_anime(sketch, coarse=False)
        
        return self.generate(
            control_image=sketch,
            prompt=prompt,
            controlnet="lineart_anime_sd15",
            controlnet_conditioning_scale=0.8,  # Lower for more creative freedom
            **kwargs,
        )
    
    def pose_to_anime(
        self,
        reference_image: Image.Image,
        prompt: str,
        **kwargs,
    ) -> Image.Image:
        """
        Generate anime character with pose from reference.
        
        Args:
            reference_image: Image with pose to extract
            prompt: Character description
            
        Returns:
            Anime character in same pose
        """
        # Extract pose
        pose = self.preprocessor.openpose_anime(reference_image)
        
        return self.generate(
            control_image=pose,
            prompt=prompt,
            controlnet="openpose_sd15",
            **kwargs,
        )
    
    def multi_controlnet(
        self,
        lineart: Optional[Image.Image] = None,
        pose: Optional[Image.Image] = None,
        prompt: str = "",
        lineart_scale: float = 1.0,
        pose_scale: float = 0.5,
        **kwargs,
    ) -> Image.Image:
        """
        Generate with multiple ControlNet conditions.
        
        Args:
            lineart: Lineart control image
            pose: Pose control image
            prompt: Text prompt
            lineart_scale: Lineart conditioning strength
            pose_scale: Pose conditioning strength
            
        Returns:
            Generated image with both controls
        """
        # Load both controlnets
        from diffusers import StableDiffusionControlNetPipeline, ControlNetModel
        
        controlnets = []
        images = []
        scales = []
        
        if lineart is not None:
            controlnets.append(self._load_controlnet("lineart_anime_sd15"))
            images.append(lineart)
            scales.append(lineart_scale)
        
        if pose is not None:
            controlnets.append(self._load_controlnet("openpose_sd15"))
            images.append(pose)
            scales.append(pose_scale)
        
        if not controlnets:
            raise ValueError("Provide at least one control image")
        
        # Create multi-controlnet pipeline
        pipe = StableDiffusionControlNetPipeline.from_pretrained(
            "Linaqruf/anything-v3.0",
            controlnet=controlnets,
            torch_dtype=self.dtype,
            safety_checker=None,
        ).to(self.device)
        
        # Generate
        generator = kwargs.pop("generator", None)
        seed = kwargs.pop("seed", None)
        if seed is not None and generator is None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        result = pipe(
            prompt=prompt,
            image=images,
            controlnet_conditioning_scale=scales,
            generator=generator,
            **kwargs,
        )
        
        return result.images[0]
    
    def unload(self, name: Optional[str] = None):
        """Unload models to free memory."""
        if name:
            if name in self._pipelines:
                del self._pipelines[name]
            if name in self._controlnets:
                del self._controlnets[name]
        else:
            self._pipelines.clear()
            self._controlnets.clear()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# ==============================================================================
# Convenience Functions
# ==============================================================================

_pipeline: Optional[AnimeControlNetPipeline] = None

def get_anime_controlnet() -> AnimeControlNetPipeline:
    """Get singleton anime ControlNet pipeline."""
    global _pipeline
    if _pipeline is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _pipeline = AnimeControlNetPipeline(device=device)
    return _pipeline


def lineart_to_anime(
    lineart: Image.Image,
    prompt: str,
    **kwargs,
) -> Image.Image:
    """Quick lineart to anime conversion."""
    pipeline = get_anime_controlnet()
    return pipeline.lineart_to_anime(lineart, prompt, **kwargs)


def photo_to_anime(
    photo: Image.Image,
    prompt: str = "anime style",
    **kwargs,
) -> Image.Image:
    """Quick photo to anime conversion."""
    pipeline = get_anime_controlnet()
    return pipeline.photo_to_anime(photo, prompt, **kwargs)


def extract_anime_lineart(image: Image.Image) -> Image.Image:
    """Extract anime-style lineart from image."""
    preprocessor = AnimePreprocessor()
    return preprocessor.lineart_anime(image)
