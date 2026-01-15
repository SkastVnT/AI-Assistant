"""
InstantID Integration for Edit Image Service.

InstantID enables zero-shot face identity preservation using a single reference image.
It combines InsightFace for face embedding extraction with IP-Adapter and ControlNet
for high-quality face-consistent image generation.

Key Features:
- Zero-shot face swap without fine-tuning
- Single reference image required
- High-fidelity identity preservation
- Works with SDXL base models

References:
- https://github.com/InstantID/InstantID
- https://huggingface.co/InstantX/InstantID
"""

import logging
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple

import torch
import numpy as np
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


# ==============================================================================
# Model Configuration
# ==============================================================================

INSTANTID_MODELS = {
    "ip_adapter": {
        "repo": "InstantX/InstantID",
        "filename": "ip-adapter.bin",
    },
    "controlnet": {
        "repo": "InstantX/InstantID",
        "filename": "ControlNetModel",
        "subfolder": "ControlNetModel",
    },
    "antelopev2": {
        "repo": "DIAMONIK7777/antelopev2",
        "type": "insightface",
    },
}

# Face landmark indices for drawing
FACE_LANDMARKS = {
    "left_eye": [36, 37, 38, 39, 40, 41],
    "right_eye": [42, 43, 44, 45, 46, 47],
    "nose": [27, 28, 29, 30, 31, 32, 33, 34, 35],
    "mouth": [48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59],
    "left_eyebrow": [17, 18, 19, 20, 21],
    "right_eyebrow": [22, 23, 24, 25, 26],
    "face_contour": list(range(17)),
}


# ==============================================================================
# InstantID Pipeline
# ==============================================================================

class InstantIDPipeline:
    """
    InstantID pipeline for zero-shot face identity preservation.
    
    Usage:
        pipeline = InstantIDPipeline(device="cuda")
        pipeline.load_models()
        
        result = pipeline.generate(
            face_image=face_photo,
            prompt="a person as an astronaut",
            negative_prompt="low quality",
        )
    """
    
    def __init__(
        self,
        device: str = "cuda",
        dtype: torch.dtype = torch.float16,
        models_dir: str = "./models/instantid",
    ):
        self.device = device
        self.dtype = dtype
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self._face_analyzer = None
        self._controlnet = None
        self._pipeline = None
        self._is_loaded = False
        
        logger.info(f"InstantIDPipeline initialized on {device}")
    
    def _load_face_analyzer(self):
        """Load InsightFace analyzer with AntelopeV2 model."""
        if self._face_analyzer is not None:
            return self._face_analyzer
        
        try:
            from insightface.app import FaceAnalysis
            
            logger.info("Loading InsightFace with AntelopeV2...")
            
            # Download AntelopeV2 if needed
            self._face_analyzer = FaceAnalysis(
                name="antelopev2",
                root=str(self.models_dir),
                providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
            )
            self._face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
            
            logger.info("InsightFace loaded successfully")
            return self._face_analyzer
            
        except Exception as e:
            logger.error(f"Failed to load InsightFace: {e}")
            raise
    
    def _load_controlnet(self):
        """Load InstantID ControlNet model."""
        if self._controlnet is not None:
            return self._controlnet
        
        try:
            from diffusers import ControlNetModel
            
            logger.info("Loading InstantID ControlNet...")
            
            self._controlnet = ControlNetModel.from_pretrained(
                "InstantX/InstantID",
                subfolder="ControlNetModel",
                torch_dtype=self.dtype,
            ).to(self.device)
            
            logger.info("InstantID ControlNet loaded")
            return self._controlnet
            
        except Exception as e:
            logger.error(f"Failed to load ControlNet: {e}")
            raise
    
    def load_models(
        self,
        base_model: str = "stabilityai/stable-diffusion-xl-base-1.0",
    ):
        """
        Load all InstantID models.
        
        Args:
            base_model: SDXL base model to use
        """
        if self._is_loaded:
            return
        
        try:
            from diffusers import StableDiffusionXLInstantIDPipeline
            from huggingface_hub import hf_hub_download
            
            # Load components
            self._load_face_analyzer()
            controlnet = self._load_controlnet()
            
            # Download IP-Adapter weights
            ip_adapter_path = hf_hub_download(
                repo_id="InstantX/InstantID",
                filename="ip-adapter.bin",
                local_dir=self.models_dir,
            )
            
            logger.info(f"Loading InstantID pipeline with {base_model}...")
            
            # Load pipeline
            self._pipeline = StableDiffusionXLInstantIDPipeline.from_pretrained(
                base_model,
                controlnet=controlnet,
                torch_dtype=self.dtype,
            ).to(self.device)
            
            # Load IP-Adapter
            self._pipeline.load_ip_adapter_instantid(ip_adapter_path)
            
            # Enable optimizations
            if hasattr(self._pipeline, "enable_xformers_memory_efficient_attention"):
                try:
                    self._pipeline.enable_xformers_memory_efficient_attention()
                except Exception:
                    pass
            
            self._is_loaded = True
            logger.info("InstantID pipeline loaded successfully")
            
        except ImportError as e:
            logger.error(f"Missing dependencies for InstantID: {e}")
            logger.info("Install with: pip install diffusers[instantid] insightface onnxruntime-gpu")
            raise
        except Exception as e:
            logger.error(f"Failed to load InstantID: {e}")
            raise
    
    def extract_face_info(
        self,
        image: Image.Image,
        max_faces: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract face information from image.
        
        Args:
            image: Input image
            max_faces: Maximum number of faces to extract
            
        Returns:
            Dictionary with face embedding and keypoints, or None if no face found
        """
        if self._face_analyzer is None:
            self._load_face_analyzer()
        
        # Convert to numpy
        img_array = np.array(image.convert("RGB"))
        
        # Detect faces
        faces = self._face_analyzer.get(img_array)
        
        if not faces:
            logger.warning("No face detected in image")
            return None
        
        # Sort by face size (largest first)
        faces = sorted(
            faces,
            key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]),
            reverse=True
        )[:max_faces]
        
        results = []
        for face in faces:
            results.append({
                "embedding": face.normed_embedding,
                "bbox": face.bbox.astype(int),
                "kps": face.kps.astype(int) if hasattr(face, "kps") else None,
                "landmark_2d_106": face.landmark_2d_106 if hasattr(face, "landmark_2d_106") else None,
                "age": face.age if hasattr(face, "age") else None,
                "gender": "F" if hasattr(face, "gender") and face.gender == 0 else "M",
            })
        
        return results[0] if len(results) == 1 else results
    
    def draw_face_keypoints(
        self,
        image: Image.Image,
        kps: np.ndarray,
        color: Tuple[int, int, int] = (255, 0, 0),
        radius: int = 3,
    ) -> Image.Image:
        """
        Draw face keypoints on image.
        
        Args:
            image: Input image
            kps: Keypoints array (5 points: eyes, nose, mouth corners)
            color: Point color
            radius: Point radius
            
        Returns:
            Image with drawn keypoints
        """
        result = image.copy()
        draw = ImageDraw.Draw(result)
        
        for point in kps:
            x, y = int(point[0]), int(point[1])
            draw.ellipse(
                [(x - radius, y - radius), (x + radius, y + radius)],
                fill=color,
                outline=color,
            )
        
        return result
    
    def create_face_kps_image(
        self,
        image: Image.Image,
        face_info: Dict[str, Any],
    ) -> Image.Image:
        """
        Create face keypoints conditioning image for ControlNet.
        
        Args:
            image: Input image (for size reference)
            face_info: Face information from extract_face_info
            
        Returns:
            Black image with face keypoints drawn
        """
        width, height = image.size
        kps_image = Image.new("RGB", (width, height), "black")
        
        if face_info.get("kps") is not None:
            kps_image = self.draw_face_keypoints(
                kps_image,
                face_info["kps"],
                color=(255, 255, 255),
                radius=5,
            )
        
        return kps_image
    
    def generate(
        self,
        face_image: Image.Image,
        prompt: str,
        negative_prompt: Optional[str] = None,
        num_inference_steps: int = 30,
        guidance_scale: float = 5.0,
        ip_adapter_scale: float = 0.8,
        controlnet_scale: float = 0.8,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        **kwargs,
    ) -> Optional[Image.Image]:
        """
        Generate image with face identity preserved.
        
        Args:
            face_image: Reference face image
            prompt: Text prompt
            negative_prompt: Negative prompt
            num_inference_steps: Denoising steps
            guidance_scale: CFG scale
            ip_adapter_scale: Face embedding strength
            controlnet_scale: Keypoint guidance strength
            width: Output width
            height: Output height
            seed: Random seed
            
        Returns:
            Generated image with preserved face identity
        """
        if not self._is_loaded:
            self.load_models()
        
        # Extract face info
        face_info = self.extract_face_info(face_image)
        if face_info is None:
            logger.error("No face found in reference image")
            return None
        
        # Prepare face embedding
        face_embedding = torch.from_numpy(face_info["embedding"]).unsqueeze(0)
        face_embedding = face_embedding.to(self.device, dtype=self.dtype)
        
        # Create keypoints image
        face_kps_image = self.create_face_kps_image(face_image, face_info)
        
        # Prepare generator
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        
        # Generate
        result = self._pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt or "low quality, worst quality, bad anatomy",
            image_embeds=face_embedding,
            image=face_kps_image,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            ip_adapter_scale=ip_adapter_scale,
            controlnet_conditioning_scale=controlnet_scale,
            width=width,
            height=height,
            generator=generator,
            **kwargs,
        )
        
        return result.images[0]
    
    def swap_face(
        self,
        source_image: Image.Image,
        face_image: Image.Image,
        prompt: Optional[str] = None,
        strength: float = 0.6,
        **kwargs,
    ) -> Optional[Image.Image]:
        """
        Swap face in source image with reference face.
        
        Args:
            source_image: Image to modify
            face_image: Face to use
            prompt: Optional text prompt
            strength: How much to change the source image
            
        Returns:
            Image with swapped face
        """
        if not self._is_loaded:
            self.load_models()
        
        # Extract face from reference
        face_info = self.extract_face_info(face_image)
        if face_info is None:
            logger.error("No face found in reference image")
            return None
        
        # Extract pose from source
        source_face_info = self.extract_face_info(source_image)
        if source_face_info is None:
            logger.warning("No face in source, using reference pose")
            source_face_info = face_info
        
        # Use source keypoints with reference embedding
        face_embedding = torch.from_numpy(face_info["embedding"]).unsqueeze(0)
        face_embedding = face_embedding.to(self.device, dtype=self.dtype)
        
        # Create keypoints image from source
        face_kps_image = self.create_face_kps_image(source_image, source_face_info)
        
        # Auto-generate prompt if not provided
        if prompt is None:
            prompt = "a person, high quality, detailed face"
        
        # Generate with img2img
        result = self._pipeline(
            prompt=prompt,
            image=source_image,
            image_embeds=face_embedding,
            control_image=face_kps_image,
            strength=strength,
            **kwargs,
        )
        
        return result.images[0]
    
    def unload(self):
        """Unload all models to free memory."""
        self._pipeline = None
        self._controlnet = None
        self._face_analyzer = None
        self._is_loaded = False
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("InstantID models unloaded")


# ==============================================================================
# Convenience Functions
# ==============================================================================

_pipeline: Optional[InstantIDPipeline] = None

def get_instantid_pipeline() -> InstantIDPipeline:
    """Get singleton InstantID pipeline instance."""
    global _pipeline
    if _pipeline is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _pipeline = InstantIDPipeline(device=device)
    return _pipeline


def instant_face_swap(
    source_image: Image.Image,
    face_image: Image.Image,
    prompt: Optional[str] = None,
    **kwargs,
) -> Optional[Image.Image]:
    """
    Quick face swap using InstantID.
    
    Args:
        source_image: Image to modify
        face_image: Face to use
        prompt: Optional text prompt
        
    Returns:
        Image with swapped face
    """
    pipeline = get_instantid_pipeline()
    pipeline.load_models()
    
    return pipeline.swap_face(
        source_image=source_image,
        face_image=face_image,
        prompt=prompt,
        **kwargs,
    )


def generate_with_face(
    face_image: Image.Image,
    prompt: str,
    **kwargs,
) -> Optional[Image.Image]:
    """
    Generate image preserving face identity.
    
    Args:
        face_image: Reference face
        prompt: What to generate
        
    Returns:
        Generated image with preserved face
    """
    pipeline = get_instantid_pipeline()
    pipeline.load_models()
    
    return pipeline.generate(
        face_image=face_image,
        prompt=prompt,
        **kwargs,
    )
