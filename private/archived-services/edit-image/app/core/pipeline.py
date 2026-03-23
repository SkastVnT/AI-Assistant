"""
Pipeline Manager for Edit Image Service.
Handles loading, caching, and managing diffusion pipelines.
"""

import gc
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import torch
from PIL import Image

try:
    from diffusers import (
        StableDiffusionPipeline,
        StableDiffusionImg2ImgPipeline,
        StableDiffusionInpaintPipeline,
        StableDiffusionXLPipeline,
        StableDiffusionXLImg2ImgPipeline,
        StableDiffusionXLInpaintPipeline,
        StableDiffusionInstructPix2PixPipeline,
        ControlNetModel,
        StableDiffusionControlNetPipeline,
        StableDiffusionXLControlNetPipeline,
        AutoPipelineForText2Image,
        AutoPipelineForImage2Image,
        AutoPipelineForInpainting,
    )
    from diffusers.utils import load_image
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False

from .config import Settings, get_settings, ModelConfig


logger = logging.getLogger(__name__)


class PipelineManager:
    """
    Manages diffusion pipelines for image generation and editing.
    
    Features:
    - Lazy loading of models
    - Pipeline caching with LRU eviction
    - Automatic VRAM management
    - Support for multiple model types (SD1.5, SDXL, FLUX)
    - ControlNet integration
    - IP-Adapter support
    """
    
    def __init__(
        self,
        settings: Optional[Settings] = None,
        max_cached_pipelines: int = 2,
    ):
        """
        Initialize the Pipeline Manager.
        
        Args:
            settings: Configuration settings
            max_cached_pipelines: Maximum number of pipelines to keep in memory
        """
        self.settings = settings or get_settings()
        self.max_cached_pipelines = max_cached_pipelines
        
        # Pipeline cache: {model_name: pipeline}
        self._pipelines: Dict[str, Any] = {}
        self._pipeline_order: List[str] = []  # For LRU tracking
        
        # ControlNet cache: {controlnet_name: model}
        self._controlnets: Dict[str, Any] = {}
        
        # Device and dtype
        self.device = self._get_device()
        self.dtype = self._get_dtype()
        
        # Ensure model cache directory exists
        self.cache_dir = Path(self.settings.models.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"PipelineManager initialized on {self.device} with {self.dtype}")
    
    def _get_device(self) -> torch.device:
        """Determine the best available device."""
        device_str = self.settings.inference.device.lower()
        
        if device_str == "cuda" and torch.cuda.is_available():
            return torch.device("cuda")
        elif device_str == "mps" and torch.backends.mps.is_available():
            return torch.device("mps")
        else:
            logger.warning("GPU not available, falling back to CPU")
            return torch.device("cpu")
    
    def _get_dtype(self) -> torch.dtype:
        """Get the appropriate dtype based on settings and device."""
        dtype_str = self.settings.inference.dtype.lower()
        
        if self.device.type == "cpu":
            return torch.float32
        
        dtype_map = {
            "float16": torch.float16,
            "float32": torch.float32,
            "bfloat16": torch.bfloat16,
        }
        return dtype_map.get(dtype_str, torch.float16)
    
    def _apply_optimizations(self, pipeline: Any) -> Any:
        """Apply memory optimizations to a pipeline."""
        opt = self.settings.inference.optimization
        
        try:
            # Enable xformers if available
            if opt.enable_xformers:
                try:
                    pipeline.enable_xformers_memory_efficient_attention()
                    logger.debug("xformers enabled")
                except Exception as e:
                    logger.debug(f"xformers not available: {e}")
            
            # Attention slicing
            if opt.enable_attention_slicing:
                pipeline.enable_attention_slicing("auto")
                logger.debug("Attention slicing enabled")
            
            # VAE slicing
            if opt.enable_vae_slicing:
                pipeline.enable_vae_slicing()
                logger.debug("VAE slicing enabled")
            
            # CPU offload
            if opt.enable_model_cpu_offload:
                pipeline.enable_model_cpu_offload()
                logger.debug("Model CPU offload enabled")
            elif opt.enable_sequential_cpu_offload:
                pipeline.enable_sequential_cpu_offload()
                logger.debug("Sequential CPU offload enabled")
                
        except Exception as e:
            logger.warning(f"Error applying optimizations: {e}")
        
        return pipeline
    
    def _evict_oldest_pipeline(self) -> None:
        """Evict the least recently used pipeline from cache."""
        if self._pipeline_order:
            oldest = self._pipeline_order.pop(0)
            if oldest in self._pipelines:
                del self._pipelines[oldest]
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                logger.info(f"Evicted pipeline: {oldest}")
    
    def _update_lru(self, model_name: str) -> None:
        """Update LRU order for a model."""
        if model_name in self._pipeline_order:
            self._pipeline_order.remove(model_name)
        self._pipeline_order.append(model_name)
    
    def load_pipeline(
        self,
        model_name: str,
        pipeline_type: str = "text2img",
        controlnet: Optional[str] = None,
    ) -> Any:
        """
        Load or retrieve a diffusion pipeline.
        
        Args:
            model_name: Name of the model (e.g., 'sdxl', 'animagine')
            pipeline_type: Type of pipeline ('text2img', 'img2img', 'inpaint')
            controlnet: Optional ControlNet model name
            
        Returns:
            Loaded pipeline ready for inference
        """
        if not DIFFUSERS_AVAILABLE:
            raise ImportError("diffusers library is required. Install with: pip install diffusers")
        
        # Create cache key
        cache_key = f"{model_name}_{pipeline_type}"
        if controlnet:
            cache_key += f"_{controlnet}"
        
        # Check cache
        if cache_key in self._pipelines:
            self._update_lru(cache_key)
            return self._pipelines[cache_key]
        
        # Evict if necessary
        while len(self._pipelines) >= self.max_cached_pipelines:
            self._evict_oldest_pipeline()
        
        # Get model configuration
        model_config = self.settings.get_model_config(model_name)
        if model_config is None:
            # Try as direct HuggingFace model ID
            model_id = model_name
            model_type = "sdxl" if "xl" in model_name.lower() else "sd15"
        else:
            model_id = model_config.name
            model_type = model_config.type
        
        logger.info(f"Loading pipeline: {model_id} ({pipeline_type})")
        
        # Load ControlNet if specified
        controlnet_model = None
        if controlnet:
            controlnet_model = self._load_controlnet(controlnet, model_type)
        
        # Load appropriate pipeline
        pipeline = self._create_pipeline(
            model_id=model_id,
            model_type=model_type,
            pipeline_type=pipeline_type,
            controlnet_model=controlnet_model,
        )
        
        # Apply optimizations
        pipeline = self._apply_optimizations(pipeline)
        
        # Move to device
        if not self.settings.inference.optimization.enable_model_cpu_offload:
            pipeline = pipeline.to(self.device)
        
        # Cache pipeline
        self._pipelines[cache_key] = pipeline
        self._update_lru(cache_key)
        
        logger.info(f"Pipeline loaded: {cache_key}")
        return pipeline
    
    def _create_pipeline(
        self,
        model_id: str,
        model_type: str,
        pipeline_type: str,
        controlnet_model: Optional[Any] = None,
    ) -> Any:
        """Create a diffusion pipeline based on type."""
        
        common_kwargs = {
            "torch_dtype": self.dtype,
            "cache_dir": str(self.cache_dir),
            "use_safetensors": True,
        }
        
        # Select pipeline class based on model type and task
        if model_type == "pix2pix":
            return StableDiffusionInstructPix2PixPipeline.from_pretrained(
                model_id, **common_kwargs
            )
        
        if controlnet_model is not None:
            # ControlNet pipeline
            if model_type == "sdxl":
                return StableDiffusionXLControlNetPipeline.from_pretrained(
                    model_id,
                    controlnet=controlnet_model,
                    **common_kwargs
                )
            else:
                return StableDiffusionControlNetPipeline.from_pretrained(
                    model_id,
                    controlnet=controlnet_model,
                    **common_kwargs
                )
        
        # Standard pipelines
        if model_type == "sdxl":
            if pipeline_type == "text2img":
                return StableDiffusionXLPipeline.from_pretrained(model_id, **common_kwargs)
            elif pipeline_type == "img2img":
                return StableDiffusionXLImg2ImgPipeline.from_pretrained(model_id, **common_kwargs)
            elif pipeline_type == "inpaint":
                return StableDiffusionXLInpaintPipeline.from_pretrained(model_id, **common_kwargs)
        else:
            # SD 1.5 or similar
            if pipeline_type == "text2img":
                return StableDiffusionPipeline.from_pretrained(model_id, **common_kwargs)
            elif pipeline_type == "img2img":
                return StableDiffusionImg2ImgPipeline.from_pretrained(model_id, **common_kwargs)
            elif pipeline_type == "inpaint":
                return StableDiffusionInpaintPipeline.from_pretrained(model_id, **common_kwargs)
        
        raise ValueError(f"Unknown pipeline type: {pipeline_type}")
    
    def _load_controlnet(self, controlnet_name: str, model_type: str) -> Any:
        """Load a ControlNet model."""
        if controlnet_name in self._controlnets:
            return self._controlnets[controlnet_name]
        
        # Get ControlNet config
        is_sdxl = model_type == "sdxl"
        controlnet_configs = self.settings.controlnet.sdxl if is_sdxl else self.settings.controlnet.models
        
        if controlnet_name in controlnet_configs:
            model_id = controlnet_configs[controlnet_name].name
        else:
            model_id = controlnet_name  # Use as direct HuggingFace ID
        
        logger.info(f"Loading ControlNet: {model_id}")
        
        controlnet = ControlNetModel.from_pretrained(
            model_id,
            torch_dtype=self.dtype,
            cache_dir=str(self.cache_dir),
        )
        
        self._controlnets[controlnet_name] = controlnet
        return controlnet
    
    def generate(
        self,
        prompt: str,
        model_name: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        image: Optional[Image.Image] = None,
        mask: Optional[Image.Image] = None,
        controlnet: Optional[str] = None,
        controlnet_image: Optional[Image.Image] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        strength: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        seed: Optional[int] = None,
        **kwargs
    ) -> Image.Image:
        """
        Generate or edit an image.
        
        Args:
            prompt: Text prompt for generation
            model_name: Model to use (default from settings)
            negative_prompt: Negative prompt
            image: Input image for img2img/inpaint
            mask: Mask for inpainting
            controlnet: ControlNet model name
            controlnet_image: Condition image for ControlNet
            num_inference_steps: Number of diffusion steps
            guidance_scale: CFG scale
            strength: Denoising strength for img2img
            width: Output width
            height: Output height
            seed: Random seed for reproducibility
            
        Returns:
            Generated PIL Image
        """
        # Use defaults from settings
        defaults = self.settings.inference.default
        model_name = model_name or self.settings.models.default
        num_inference_steps = num_inference_steps or defaults.num_inference_steps
        guidance_scale = guidance_scale or defaults.guidance_scale
        strength = strength or defaults.strength
        width = width or defaults.width
        height = height or defaults.height
        
        # Determine pipeline type
        if mask is not None:
            pipeline_type = "inpaint"
        elif image is not None:
            pipeline_type = "img2img"
        else:
            pipeline_type = "text2img"
        
        # Load pipeline
        pipeline = self.load_pipeline(
            model_name=model_name,
            pipeline_type=pipeline_type,
            controlnet=controlnet,
        )
        
        # Set seed
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        # Build generation kwargs
        gen_kwargs = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "generator": generator,
            **kwargs
        }
        
        # Add image-specific kwargs
        if pipeline_type == "text2img":
            gen_kwargs["width"] = width
            gen_kwargs["height"] = height
        elif pipeline_type == "img2img":
            gen_kwargs["image"] = image
            gen_kwargs["strength"] = strength
        elif pipeline_type == "inpaint":
            gen_kwargs["image"] = image
            gen_kwargs["mask_image"] = mask
            gen_kwargs["strength"] = strength
        
        # Add ControlNet image
        if controlnet and controlnet_image is not None:
            gen_kwargs["image"] = controlnet_image
        
        # Generate
        logger.info(f"Generating with {model_name} ({pipeline_type})")
        result = pipeline(**gen_kwargs)
        
        return result.images[0]
    
    def edit_with_instructions(
        self,
        image: Image.Image,
        instruction: str,
        num_inference_steps: int = 50,
        image_guidance_scale: float = 1.5,
        guidance_scale: float = 7.5,
        seed: Optional[int] = None,
    ) -> Image.Image:
        """
        Edit an image using InstructPix2Pix.
        
        Args:
            image: Input image to edit
            instruction: Text instruction for editing
            num_inference_steps: Number of diffusion steps
            image_guidance_scale: How much to follow input image
            guidance_scale: How much to follow text instruction
            seed: Random seed
            
        Returns:
            Edited PIL Image
        """
        pipeline = self.load_pipeline("instructpix2pix", "pix2pix")
        
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        result = pipeline(
            prompt=instruction,
            image=image,
            num_inference_steps=num_inference_steps,
            image_guidance_scale=image_guidance_scale,
            guidance_scale=guidance_scale,
            generator=generator,
        )
        
        return result.images[0]
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Get list of available models by category."""
        return {
            "base_models": list(self.settings.models.base_models.keys()),
            "edit_models": list(self.settings.models.edit_models.keys()),
            "controlnet": list(self.settings.controlnet.models.keys()),
            "controlnet_sdxl": list(self.settings.controlnet.sdxl.keys()),
        }
    
    def get_vram_usage(self) -> Dict[str, Any]:
        """Get current VRAM usage statistics."""
        if not torch.cuda.is_available():
            return {"available": False}
        
        return {
            "available": True,
            "allocated": torch.cuda.memory_allocated() / 1024**3,
            "reserved": torch.cuda.memory_reserved() / 1024**3,
            "max_allocated": torch.cuda.max_memory_allocated() / 1024**3,
            "cached_pipelines": list(self._pipelines.keys()),
        }
    
    def clear_cache(self) -> None:
        """Clear all cached pipelines and free memory."""
        self._pipelines.clear()
        self._pipeline_order.clear()
        self._controlnets.clear()
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        logger.info("Pipeline cache cleared")


# Global pipeline manager instance
_manager: Optional[PipelineManager] = None


def get_pipeline_manager() -> PipelineManager:
    """Get or create the global pipeline manager."""
    global _manager
    if _manager is None:
        _manager = PipelineManager()
    return _manager
