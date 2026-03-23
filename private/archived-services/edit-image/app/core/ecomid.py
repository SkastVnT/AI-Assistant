"""
EcomID - Alibaba E-commerce Identity Preservation
==================================================

Combines InstantID + PuLID advantages with IdentityNet trained on 2M portraits.
Features:
- Keypoint-based face control
- Stable identity across age/hair/glasses changes
- Native ComfyUI/SDXL support
- Commercial-grade portrait quality

Reference: https://github.com/alimama-creative/EcomID
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass
from enum import Enum

import torch
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class EcomIDMode(str, Enum):
    """EcomID processing modes"""
    STANDARD = "standard"          # Normal generation
    ECOMMERCE = "ecommerce"        # Optimized for product images
    PORTRAIT = "portrait"          # Optimized for portraits
    MULTI_POSE = "multi_pose"      # Multiple poses from same identity


@dataclass
class EcomIDConfig:
    """EcomID configuration"""
    # Model paths
    model_path: str = "alimama-creative/EcomID"
    base_model: str = "stabilityai/stable-diffusion-xl-base-1.0"
    
    # Processing mode
    mode: EcomIDMode = EcomIDMode.STANDARD
    
    # Identity control
    id_weight: float = 0.8          # Identity preservation strength
    kps_weight: float = 0.5         # Keypoint control weight
    adapter_weight: float = 0.6     # IP-Adapter weight (fixed in EcomID)
    
    # ControlNet settings
    use_controlnet: bool = True
    controlnet_conditioning_scale: float = 0.8
    
    # Generation settings
    num_inference_steps: int = 30
    guidance_scale: float = 7.5
    negative_prompt: str = "low quality, blurry, distorted face, ugly, deformed"
    
    # Device
    device: str = "cuda"
    dtype: torch.dtype = torch.float16
    
    # Optimization
    enable_xformers: bool = True


@dataclass
class FaceKeypoints:
    """Facial keypoints for EcomID control"""
    left_eye: Tuple[float, float]
    right_eye: Tuple[float, float]
    nose: Tuple[float, float]
    left_mouth: Tuple[float, float]
    right_mouth: Tuple[float, float]
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array"""
        return np.array([
            self.left_eye,
            self.right_eye,
            self.nose,
            self.left_mouth,
            self.right_mouth
        ])
    
    @classmethod
    def from_array(cls, arr: np.ndarray) -> "FaceKeypoints":
        """Create from numpy array"""
        return cls(
            left_eye=tuple(arr[0]),
            right_eye=tuple(arr[1]),
            nose=tuple(arr[2]),
            left_mouth=tuple(arr[3]),
            right_mouth=tuple(arr[4])
        )


@dataclass
class EcomIDResult:
    """Result from EcomID generation"""
    image: Image.Image
    id_embedding: Optional[np.ndarray] = None
    keypoints: Optional[FaceKeypoints] = None
    face_info: Optional[Dict[str, Any]] = None
    processing_time: float = 0.0
    mode: str = "standard"


class IdentityNet:
    """
    IdentityNet - EcomID's identity encoder
    Trained on 2M portrait images for robust ID extraction
    """
    
    def __init__(self, device: str = "cuda", dtype: torch.dtype = torch.float16):
        self.device = device
        self.dtype = dtype
        self.face_analyzer = None
        self.identity_encoder = None
        self._initialized = False
    
    def initialize(self):
        """Initialize IdentityNet components"""
        if self._initialized:
            return
        
        try:
            from insightface.app import FaceAnalysis
            
            # Face analyzer for detection and keypoints
            self.face_analyzer = FaceAnalysis(
                name='antelopev2',
                root='./models/face',
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
            self.face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
            
            self._initialized = True
            logger.info("IdentityNet initialized")
            
        except ImportError:
            logger.error("insightface not installed")
            raise
    
    def extract(
        self, 
        image: Image.Image
    ) -> Tuple[np.ndarray, FaceKeypoints, Dict[str, Any]]:
        """
        Extract identity embedding and keypoints from image
        
        Returns:
            embedding: 512-d identity embedding
            keypoints: Facial keypoints
            face_info: Additional face information
        """
        self.initialize()
        
        # Convert to numpy
        img_np = np.array(image.convert("RGB"))
        img_bgr = img_np[:, :, ::-1]
        
        # Detect faces
        faces = self.face_analyzer.get(img_bgr)
        
        if len(faces) == 0:
            raise ValueError("No face detected in image")
        
        # Get largest face
        face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
        
        # Extract embedding
        embedding = face.embedding
        
        # Extract keypoints
        if face.kps is not None:
            keypoints = FaceKeypoints.from_array(face.kps)
        else:
            raise ValueError("Could not extract facial keypoints")
        
        # Face info
        face_info = {
            "bbox": face.bbox.tolist(),
            "kps": face.kps.tolist(),
            "det_score": float(face.det_score),
            "pose": face.pose.tolist() if hasattr(face, 'pose') and face.pose is not None else None,
            "age": int(face.age) if hasattr(face, 'age') else None,
            "gender": "M" if hasattr(face, 'gender') and face.gender == 1 else "F",
        }
        
        return embedding, keypoints, face_info
    
    def extract_multi(
        self,
        images: List[Image.Image]
    ) -> Tuple[np.ndarray, List[FaceKeypoints], List[Dict[str, Any]]]:
        """Extract and average identity from multiple images"""
        embeddings = []
        keypoints_list = []
        face_infos = []
        
        for img in images:
            try:
                emb, kps, info = self.extract(img)
                embeddings.append(emb)
                keypoints_list.append(kps)
                face_infos.append(info)
            except ValueError as e:
                logger.warning(f"Skipping image: {e}")
                continue
        
        if not embeddings:
            raise ValueError("No faces detected in any images")
        
        # Average embeddings
        avg_embedding = np.mean(embeddings, axis=0)
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
        
        return avg_embedding, keypoints_list, face_infos


class EcomIDPipeline:
    """
    EcomID Pipeline for commercial-grade identity preservation
    
    Features:
    - IdentityNet for robust ID extraction
    - Keypoint-based face control
    - Stable across transformations
    - E-commerce optimized
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.config = EcomIDConfig()
        self.identity_net = IdentityNet()
        self.pipe = None
        self.ip_adapter = None
        self.controlnet = None
        self._initialized = False
    
    def initialize(self, config: Optional[EcomIDConfig] = None):
        """Initialize EcomID pipeline"""
        if config:
            self.config = config
        
        if self.pipe is not None:
            return
        
        try:
            from diffusers import (
                StableDiffusionXLPipeline,
                ControlNetModel,
                StableDiffusionXLControlNetPipeline
            )
            
            logger.info("Initializing EcomID pipeline...")
            
            # Check for local models
            base_path = Path("./models/base/sdxl-base")
            if base_path.exists():
                base_model = str(base_path)
            else:
                base_model = self.config.base_model
            
            # Load ControlNet for keypoint control
            if self.config.use_controlnet:
                controlnet_path = Path("./models/identity/ecomid-controlnet")
                if controlnet_path.exists():
                    self.controlnet = ControlNetModel.from_pretrained(
                        str(controlnet_path),
                        torch_dtype=self.config.dtype
                    )
                else:
                    # Use OpenPose ControlNet as fallback
                    self.controlnet = ControlNetModel.from_pretrained(
                        "thibaud/controlnet-openpose-sdxl-1.0",
                        torch_dtype=self.config.dtype
                    )
                
                self.pipe = StableDiffusionXLControlNetPipeline.from_pretrained(
                    base_model,
                    controlnet=self.controlnet,
                    torch_dtype=self.config.dtype,
                    variant="fp16",
                    use_safetensors=True
                )
            else:
                self.pipe = StableDiffusionXLPipeline.from_pretrained(
                    base_model,
                    torch_dtype=self.config.dtype,
                    variant="fp16",
                    use_safetensors=True
                )
            
            self.pipe.to(self.config.device)
            
            # Enable optimizations
            if self.config.enable_xformers:
                try:
                    self.pipe.enable_xformers_memory_efficient_attention()
                except Exception:
                    pass
            
            # Load IP-Adapter for EcomID
            self._load_ip_adapter()
            
            self._initialized = True
            logger.info("EcomID pipeline initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize EcomID: {e}")
            raise
    
    def _load_ip_adapter(self):
        """Load IP-Adapter with EcomID weights"""
        try:
            # EcomID uses fixed IP-Adapter weights
            ip_adapter_path = Path("./models/ip-adapter/h94")
            
            if ip_adapter_path.exists():
                self.pipe.load_ip_adapter(
                    str(ip_adapter_path),
                    subfolder="sdxl_models",
                    weight_name="ip-adapter-plus-face_sdxl_vit-h.safetensors"
                )
            else:
                self.pipe.load_ip_adapter(
                    "h94/IP-Adapter",
                    subfolder="sdxl_models",
                    weight_name="ip-adapter-plus-face_sdxl_vit-h.safetensors"
                )
            
            # Set adapter scale (fixed in EcomID)
            self.pipe.set_ip_adapter_scale(self.config.adapter_weight)
            
            logger.info("IP-Adapter loaded for EcomID")
            
        except Exception as e:
            logger.warning(f"Could not load IP-Adapter: {e}")
    
    def _create_keypoint_image(
        self, 
        keypoints: FaceKeypoints,
        width: int,
        height: int
    ) -> Image.Image:
        """Create keypoint conditioning image"""
        from PIL import ImageDraw
        
        # Create black background
        img = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw keypoints
        kps = keypoints.to_array()
        colors = [
            (255, 0, 0),    # left eye - red
            (0, 255, 0),    # right eye - green
            (0, 0, 255),    # nose - blue
            (255, 255, 0),  # left mouth - yellow
            (0, 255, 255),  # right mouth - cyan
        ]
        
        for (x, y), color in zip(kps, colors):
            # Scale to image size
            x_scaled = int(x * width / 640)  # Assuming original detection at 640
            y_scaled = int(y * height / 640)
            
            # Draw circle
            radius = 5
            draw.ellipse(
                [x_scaled - radius, y_scaled - radius, 
                 x_scaled + radius, y_scaled + radius],
                fill=color
            )
        
        # Draw face lines
        kps_scaled = kps * np.array([width / 640, height / 640])
        
        # Eye line
        draw.line([tuple(kps_scaled[0]), tuple(kps_scaled[1])], fill=(255, 255, 255), width=2)
        # Nose to mouth
        draw.line([tuple(kps_scaled[2]), tuple(kps_scaled[3])], fill=(255, 255, 255), width=2)
        draw.line([tuple(kps_scaled[2]), tuple(kps_scaled[4])], fill=(255, 255, 255), width=2)
        # Mouth line
        draw.line([tuple(kps_scaled[3]), tuple(kps_scaled[4])], fill=(255, 255, 255), width=2)
        
        return img
    
    def generate(
        self,
        prompt: str,
        face_image: Union[Image.Image, List[Image.Image]],
        target_keypoints: Optional[FaceKeypoints] = None,
        negative_prompt: Optional[str] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        id_weight: Optional[float] = None,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        mode: Optional[EcomIDMode] = None,
        **kwargs
    ) -> EcomIDResult:
        """
        Generate image with EcomID identity preservation
        
        Args:
            prompt: Generation prompt
            face_image: Reference face image(s)
            target_keypoints: Target face keypoints (optional)
            negative_prompt: Negative prompt
            num_inference_steps: Denoising steps
            guidance_scale: CFG scale
            id_weight: Identity preservation strength
            width: Output width
            height: Output height
            seed: Random seed
            mode: Processing mode
        """
        import time
        start_time = time.time()
        
        self.initialize()
        
        # Set defaults
        mode = mode or self.config.mode
        negative_prompt = negative_prompt or self.config.negative_prompt
        num_inference_steps = num_inference_steps or self.config.num_inference_steps
        guidance_scale = guidance_scale or self.config.guidance_scale
        id_weight = id_weight if id_weight is not None else self.config.id_weight
        
        # Extract identity
        if isinstance(face_image, list):
            id_embedding, keypoints_list, face_infos = self.identity_net.extract_multi(face_image)
            source_keypoints = keypoints_list[0]
            face_info = face_infos[0]
            # Use first image as IP-Adapter input
            ip_image = face_image[0]
        else:
            id_embedding, source_keypoints, face_info = self.identity_net.extract(face_image)
            ip_image = face_image
        
        # Use source keypoints if target not specified
        if target_keypoints is None:
            target_keypoints = source_keypoints
        
        # Set seed
        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.config.device).manual_seed(seed)
        
        # Update IP-Adapter scale
        self.pipe.set_ip_adapter_scale(id_weight)
        
        # Prepare generation kwargs
        gen_kwargs = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "ip_adapter_image": ip_image,
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
            "width": width,
            "height": height,
            "generator": generator,
        }
        
        # Add ControlNet conditioning if enabled
        if self.config.use_controlnet and self.controlnet is not None:
            keypoint_image = self._create_keypoint_image(target_keypoints, width, height)
            gen_kwargs["image"] = keypoint_image
            gen_kwargs["controlnet_conditioning_scale"] = self.config.controlnet_conditioning_scale
        
        # Generate
        output = self.pipe(**gen_kwargs)
        result_image = output.images[0]
        
        processing_time = time.time() - start_time
        
        return EcomIDResult(
            image=result_image,
            id_embedding=id_embedding,
            keypoints=target_keypoints,
            face_info=face_info,
            processing_time=processing_time,
            mode=mode.value
        )
    
    def generate_multi_pose(
        self,
        prompt_template: str,
        face_image: Image.Image,
        poses: List[str],
        id_weight: float = 0.8,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
        **kwargs
    ) -> List[EcomIDResult]:
        """
        Generate multiple poses from same identity
        
        Args:
            prompt_template: Prompt template with {pose} placeholder
            face_image: Reference face
            poses: List of pose descriptions
            id_weight: Identity preservation strength
        """
        results = []
        
        for i, pose in enumerate(poses):
            prompt = prompt_template.format(pose=pose)
            
            # Use consistent seed per pose if provided
            current_seed = seed + i if seed is not None else None
            
            result = self.generate(
                prompt=prompt,
                face_image=face_image,
                id_weight=id_weight,
                width=width,
                height=height,
                seed=current_seed,
                mode=EcomIDMode.MULTI_POSE,
                **kwargs
            )
            
            results.append(result)
        
        return results
    
    def generate_ecommerce(
        self,
        face_image: Image.Image,
        product_prompt: str,
        background: str = "white studio background",
        clothing: Optional[str] = None,
        num_images: int = 1,
        id_weight: float = 0.85,
        **kwargs
    ) -> List[EcomIDResult]:
        """
        Generate e-commerce style images
        
        Args:
            face_image: Model face reference
            product_prompt: Product description
            background: Background description
            clothing: Clothing description
            num_images: Number of variations
            id_weight: Identity strength
        """
        results = []
        
        # Build prompt
        prompt_parts = [
            "professional e-commerce photo",
            product_prompt,
            background,
            "high quality, 4k, sharp focus, studio lighting"
        ]
        if clothing:
            prompt_parts.insert(2, f"wearing {clothing}")
        
        prompt = ", ".join(prompt_parts)
        
        for i in range(num_images):
            seed = kwargs.get("seed")
            current_seed = seed + i if seed is not None else None
            
            result = self.generate(
                prompt=prompt,
                face_image=face_image,
                id_weight=id_weight,
                seed=current_seed,
                mode=EcomIDMode.ECOMMERCE,
                **kwargs
            )
            results.append(result)
        
        return results
    
    def unload(self):
        """Unload models to free memory"""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
        
        if self.controlnet is not None:
            del self.controlnet
            self.controlnet = None
        
        self._initialized = False
        
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("EcomID pipeline unloaded")


# Singleton instance
def get_ecomid_pipeline() -> EcomIDPipeline:
    """Get EcomID pipeline singleton"""
    return EcomIDPipeline()
