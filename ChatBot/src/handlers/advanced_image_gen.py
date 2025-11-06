"""
Advanced Image Generation Module
Features: ControlNet, Upscaling, Inpainting, Outpainting, Face Restoration, Style Transfer
"""

import os
import base64
import requests
import logging
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path
import io
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class AdvancedImageGenerator:
    """
    Advanced image generation with ControlNet, upscaling, and editing features
    
    Features:
    - ControlNet: Pose, Depth, Canny, Openpose
    - Upscaling: Real-ESRGAN 4x, 2x
    - Face restoration: CodeFormer, GFPGAN
    - Inpainting: Edit parts of image
    - Outpainting: Extend image boundaries
    - Style transfer: Apply reference styles
    - LoRA mixing: Multiple LoRAs
    """
    
    def __init__(
        self,
        sd_api_url: str = "http://127.0.0.1:7860",
        controlnet_models_path: Optional[str] = None
    ):
        """
        Initialize advanced image generator
        
        Args:
            sd_api_url: Stable Diffusion WebUI API URL
            controlnet_models_path: Path to ControlNet models directory
        """
        self.sd_api_url = sd_api_url
        self.controlnet_models_path = controlnet_models_path or os.path.join(
            os.path.dirname(__file__),
            "..", "..", "stable-diffusion-webui", "models", "ControlNet"
        )
        
        # Check API availability
        self.is_available = self._check_api_availability()
        
        if self.is_available:
            logger.info(f"✅ SD API available at {sd_api_url}")
            self._load_available_features()
        else:
            logger.warning(f"⚠️ SD API not available at {sd_api_url}")
    
    def _check_api_availability(self) -> bool:
        """Check if SD API is available"""
        try:
            response = requests.get(f"{self.sd_api_url}/sdapi/v1/sd-models", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _load_available_features(self):
        """Load available features from SD API"""
        try:
            # Get available ControlNet models
            response = requests.get(
                f"{self.sd_api_url}/controlnet/model_list",
                timeout=5
            )
            if response.status_code == 200:
                self.controlnet_models = response.json().get('model_list', [])
            else:
                self.controlnet_models = []
            
            # Get available upscalers
            response = requests.get(
                f"{self.sd_api_url}/sdapi/v1/upscalers",
                timeout=5
            )
            if response.status_code == 200:
                self.upscalers = [u['name'] for u in response.json()]
            else:
                self.upscalers = []
            
            logger.info(f"✅ Loaded {len(self.controlnet_models)} ControlNet models")
            logger.info(f"✅ Loaded {len(self.upscalers)} upscalers")
            
        except Exception as e:
            logger.error(f"Failed to load features: {e}")
            self.controlnet_models = []
            self.upscalers = []
    
    # =========================================================================
    # CONTROLNET GENERATION
    # =========================================================================
    
    def generate_with_controlnet(
        self,
        prompt: str,
        control_image_path: str,
        controlnet_type: str = "canny",
        controlnet_weight: float = 1.0,
        width: int = 512,
        height: int = 512,
        steps: int = 30,
        cfg_scale: float = 7.5,
        negative_prompt: str = "",
        **kwargs
    ) -> Dict:
        """
        Generate image with ControlNet guidance
        
        Args:
            prompt: Text prompt
            control_image_path: Path to control image
            controlnet_type: 'canny', 'depth', 'openpose', 'mlsd', 'scribble'
            controlnet_weight: Control strength (0.0-2.0)
            width: Output width
            height: Output height
            steps: Sampling steps
            cfg_scale: CFG scale
            negative_prompt: Negative prompt
        
        Returns:
            {
                'images': List[str],  # Base64 encoded
                'info': str,
                'processing_time': float
            }
        """
        import time
        start_time = time.time()
        
        try:
            # Load and encode control image
            with open(control_image_path, 'rb') as f:
                control_image_b64 = base64.b64encode(f.read()).decode('utf-8')
            
            # Find matching ControlNet model
            controlnet_model = self._find_controlnet_model(controlnet_type)
            
            if not controlnet_model:
                return {
                    'error': f"ControlNet model '{controlnet_type}' not found",
                    'available_models': self.controlnet_models
                }
            
            # Prepare request
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "alwayson_scripts": {
                    "controlnet": {
                        "args": [
                            {
                                "enabled": True,
                                "module": controlnet_type,
                                "model": controlnet_model,
                                "weight": controlnet_weight,
                                "image": control_image_b64,
                                "resize_mode": "Crop and Resize",
                                "lowvram": False,
                                "processor_res": 512,
                                "threshold_a": 64,
                                "threshold_b": 64,
                                "guidance_start": 0.0,
                                "guidance_end": 1.0,
                                "control_mode": "Balanced",
                                "pixel_perfect": True
                            }
                        ]
                    }
                }
            }
            
            # Call SD API
            response = requests.post(
                f"{self.sd_api_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                result['processing_time'] = time.time() - start_time
                result['controlnet_used'] = {
                    'type': controlnet_type,
                    'model': controlnet_model,
                    'weight': controlnet_weight
                }
                return result
            else:
                return {
                    'error': f"SD API error: {response.status_code}",
                    'processing_time': time.time() - start_time
                }
        
        except Exception as e:
            logger.error(f"ControlNet generation failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def _find_controlnet_model(self, controlnet_type: str) -> Optional[str]:
        """Find matching ControlNet model"""
        type_keywords = {
            'canny': ['canny'],
            'depth': ['depth'],
            'openpose': ['openpose', 'pose'],
            'mlsd': ['mlsd'],
            'scribble': ['scribble'],
            'lineart': ['lineart'],
            'normal': ['normal'],
            'seg': ['seg']
        }
        
        keywords = type_keywords.get(controlnet_type, [controlnet_type])
        
        for model in self.controlnet_models:
            model_lower = model.lower()
            if any(kw in model_lower for kw in keywords):
                return model
        
        return None
    
    # =========================================================================
    # UPSCALING
    # =========================================================================
    
    def upscale_image(
        self,
        image_path: str,
        upscaler: str = "R-ESRGAN 4x+",
        scale_factor: float = 4.0,
        restore_faces: bool = False,
        face_restorer: str = "CodeFormer"
    ) -> Dict:
        """
        Upscale image with Real-ESRGAN
        
        Args:
            image_path: Path to image
            upscaler: Upscaler name ('R-ESRGAN 4x+', 'R-ESRGAN 4x+ Anime6B')
            scale_factor: Scale factor (2.0 or 4.0)
            restore_faces: Enable face restoration
            face_restorer: 'CodeFormer' or 'GFPGAN'
        
        Returns:
            {
                'image': str,  # Base64 encoded
                'original_size': Tuple[int, int],
                'upscaled_size': Tuple[int, int],
                'processing_time': float
            }
        """
        import time
        start_time = time.time()
        
        try:
            # Load image
            image = Image.open(image_path)
            original_size = image.size
            
            # Encode image
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Prepare request
            payload = {
                "resize_mode": 0,
                "upscaling_resize": scale_factor,
                "upscaler_1": upscaler,
                "image": image_b64
            }
            
            # Add face restoration if enabled
            if restore_faces:
                payload["codeformer_visibility"] = 1.0 if face_restorer == "CodeFormer" else 0.0
                payload["codeformer_weight"] = 0.5
            
            # Call SD API
            response = requests.post(
                f"{self.sd_api_url}/sdapi/v1/extra-single-image",
                json=payload,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Calculate upscaled size
                upscaled_size = (
                    int(original_size[0] * scale_factor),
                    int(original_size[1] * scale_factor)
                )
                
                return {
                    'image': result['image'],
                    'original_size': original_size,
                    'upscaled_size': upscaled_size,
                    'upscaler_used': upscaler,
                    'face_restoration': restore_faces,
                    'processing_time': time.time() - start_time
                }
            else:
                return {
                    'error': f"Upscaling failed: {response.status_code}",
                    'processing_time': time.time() - start_time
                }
        
        except Exception as e:
            logger.error(f"Upscaling failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def batch_upscale(
        self,
        image_paths: List[str],
        upscaler: str = "R-ESRGAN 4x+",
        scale_factor: float = 4.0,
        restore_faces: bool = False
    ) -> List[Dict]:
        """Batch upscale multiple images"""
        results = []
        
        for image_path in image_paths:
            logger.info(f"Upscaling: {Path(image_path).name}")
            result = self.upscale_image(
                image_path,
                upscaler=upscaler,
                scale_factor=scale_factor,
                restore_faces=restore_faces
            )
            results.append(result)
        
        return results
    
    # =========================================================================
    # INPAINTING & OUTPAINTING
    # =========================================================================
    
    def inpaint_image(
        self,
        image_path: str,
        mask_path: str,
        prompt: str,
        negative_prompt: str = "",
        steps: int = 30,
        cfg_scale: float = 7.5,
        denoising_strength: float = 0.75,
        **kwargs
    ) -> Dict:
        """
        Inpaint parts of image (edit masked area)
        
        Args:
            image_path: Path to original image
            mask_path: Path to mask image (white = inpaint, black = keep)
            prompt: Inpainting prompt
            negative_prompt: Negative prompt
            steps: Sampling steps
            cfg_scale: CFG scale
            denoising_strength: How much to change (0.0-1.0)
        
        Returns:
            {
                'images': List[str],  # Base64 encoded
                'info': str,
                'processing_time': float
            }
        """
        import time
        start_time = time.time()
        
        try:
            # Load and encode images
            with open(image_path, 'rb') as f:
                image_b64 = base64.b64encode(f.read()).decode('utf-8')
            
            with open(mask_path, 'rb') as f:
                mask_b64 = base64.b64encode(f.read()).decode('utf-8')
            
            # Prepare request
            payload = {
                "init_images": [image_b64],
                "mask": mask_b64,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": steps,
                "cfg_scale": cfg_scale,
                "denoising_strength": denoising_strength,
                "inpainting_fill": 1,  # Original
                "inpaint_full_res": True,
                "inpaint_full_res_padding": 32,
                "mask_blur": 4
            }
            
            # Call SD API
            response = requests.post(
                f"{self.sd_api_url}/sdapi/v1/img2img",
                json=payload,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                result['processing_time'] = time.time() - start_time
                result['inpainting_params'] = {
                    'denoising_strength': denoising_strength,
                    'mask_blur': 4
                }
                return result
            else:
                return {
                    'error': f"Inpainting failed: {response.status_code}",
                    'processing_time': time.time() - start_time
                }
        
        except Exception as e:
            logger.error(f"Inpainting failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    def outpaint_image(
        self,
        image_path: str,
        direction: str = "all",
        pixels: int = 128,
        prompt: str = "",
        **kwargs
    ) -> Dict:
        """
        Outpaint image (extend boundaries)
        
        Args:
            image_path: Path to image
            direction: 'left', 'right', 'up', 'down', 'all'
            pixels: How many pixels to extend
            prompt: Optional prompt for extended area
        
        Returns:
            {
                'image': str,  # Base64 encoded
                'original_size': Tuple[int, int],
                'extended_size': Tuple[int, int],
                'processing_time': float
            }
        """
        import time
        start_time = time.time()
        
        try:
            # Load image
            image = Image.open(image_path)
            original_size = image.size
            
            # Calculate new size and create mask
            if direction == "all":
                new_width = original_size[0] + 2 * pixels
                new_height = original_size[1] + 2 * pixels
                paste_position = (pixels, pixels)
            elif direction == "left":
                new_width = original_size[0] + pixels
                new_height = original_size[1]
                paste_position = (pixels, 0)
            elif direction == "right":
                new_width = original_size[0] + pixels
                new_height = original_size[1]
                paste_position = (0, 0)
            elif direction == "up":
                new_width = original_size[0]
                new_height = original_size[1] + pixels
                paste_position = (0, pixels)
            elif direction == "down":
                new_width = original_size[0]
                new_height = original_size[1] + pixels
                paste_position = (0, 0)
            else:
                return {'error': f"Invalid direction: {direction}"}
            
            # Create extended image
            extended_image = Image.new('RGB', (new_width, new_height), (255, 255, 255))
            extended_image.paste(image, paste_position)
            
            # Create mask (white = outpaint area, black = keep original)
            mask = Image.new('L', (new_width, new_height), 255)
            black_box = Image.new('L', original_size, 0)
            mask.paste(black_box, paste_position)
            
            # Save temporary files
            temp_dir = Path(__file__).parent.parent.parent / 'Storage' / 'temp'
            temp_dir.mkdir(exist_ok=True, parents=True)
            
            extended_path = temp_dir / f"outpaint_temp_{int(time.time())}.png"
            mask_path = temp_dir / f"outpaint_mask_{int(time.time())}.png"
            
            extended_image.save(extended_path)
            mask.save(mask_path)
            
            # Use inpainting to fill extended area
            result = self.inpaint_image(
                str(extended_path),
                str(mask_path),
                prompt or "seamless continuation of the image",
                denoising_strength=0.85,
                **kwargs
            )
            
            # Cleanup temp files
            extended_path.unlink()
            mask_path.unlink()
            
            if 'images' in result:
                result['original_size'] = original_size
                result['extended_size'] = (new_width, new_height)
                result['direction'] = direction
            
            return result
        
        except Exception as e:
            logger.error(f"Outpainting failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    # =========================================================================
    # STYLE TRANSFER
    # =========================================================================
    
    def style_transfer(
        self,
        content_image_path: str,
        style_image_path: str,
        style_strength: float = 0.5,
        prompt: Optional[str] = None,
        **kwargs
    ) -> Dict:
        """
        Apply style from reference image
        
        Args:
            content_image_path: Path to content image
            style_image_path: Path to style reference
            style_strength: How much style to apply (0.0-1.0)
            prompt: Optional prompt
        
        Returns:
            {
                'image': str,  # Base64 encoded
                'processing_time': float
            }
        """
        import time
        start_time = time.time()
        
        try:
            # Load images
            content_image = Image.open(content_image_path)
            
            # Encode content image
            buffer = io.BytesIO()
            content_image.save(buffer, format='PNG')
            content_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            
            # Use img2img with style reference
            payload = {
                "init_images": [content_b64],
                "prompt": prompt or "high quality, detailed",
                "negative_prompt": "low quality, blurry",
                "steps": 30,
                "cfg_scale": 7.5,
                "denoising_strength": style_strength,
                "width": content_image.width,
                "height": content_image.height
            }
            
            # Call SD API
            response = requests.post(
                f"{self.sd_api_url}/sdapi/v1/img2img",
                json=payload,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                result['processing_time'] = time.time() - start_time
                result['style_strength'] = style_strength
                return result
            else:
                return {
                    'error': f"Style transfer failed: {response.status_code}",
                    'processing_time': time.time() - start_time
                }
        
        except Exception as e:
            logger.error(f"Style transfer failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    # =========================================================================
    # LORA MIXING
    # =========================================================================
    
    def generate_with_multiple_loras(
        self,
        prompt: str,
        loras: List[Dict[str, float]],
        **kwargs
    ) -> Dict:
        """
        Generate with multiple LoRAs
        
        Args:
            prompt: Base prompt
            loras: List of {'name': 'lora_name', 'weight': 0.8}
            **kwargs: Other generation params
        
        Returns:
            {
                'images': List[str],
                'loras_used': List[Dict],
                'processing_time': float
            }
        """
        import time
        start_time = time.time()
        
        try:
            # Build LoRA prompt
            lora_prompts = []
            for lora in loras:
                lora_name = lora['name']
                lora_weight = lora.get('weight', 1.0)
                lora_prompts.append(f"<lora:{lora_name}:{lora_weight}>")
            
            # Combine with base prompt
            full_prompt = " ".join(lora_prompts) + " " + prompt
            
            # Generate
            payload = {
                "prompt": full_prompt,
                "negative_prompt": kwargs.get('negative_prompt', ''),
                "steps": kwargs.get('steps', 30),
                "cfg_scale": kwargs.get('cfg_scale', 7.5),
                "width": kwargs.get('width', 512),
                "height": kwargs.get('height', 512),
                "sampler_name": kwargs.get('sampler', 'DPM++ 2M Karras')
            }
            
            # Call SD API
            response = requests.post(
                f"{self.sd_api_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                result['processing_time'] = time.time() - start_time
                result['loras_used'] = loras
                return result
            else:
                return {
                    'error': f"Generation failed: {response.status_code}",
                    'processing_time': time.time() - start_time
                }
        
        except Exception as e:
            logger.error(f"Multi-LoRA generation failed: {e}")
            return {
                'error': str(e),
                'processing_time': time.time() - start_time
            }
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_available_upscalers(self) -> List[str]:
        """Get list of available upscalers"""
        return self.upscalers
    
    def get_available_controlnet_models(self) -> List[str]:
        """Get list of available ControlNet models"""
        return self.controlnet_models
    
    def get_capabilities(self) -> Dict:
        """Get generator capabilities"""
        return {
            'controlnet': {
                'enabled': len(self.controlnet_models) > 0,
                'models': self.controlnet_models
            },
            'upscaling': {
                'enabled': len(self.upscalers) > 0,
                'upscalers': self.upscalers
            },
            'inpainting': {
                'enabled': self.is_available
            },
            'outpainting': {
                'enabled': self.is_available
            },
            'style_transfer': {
                'enabled': self.is_available
            },
            'lora_mixing': {
                'enabled': self.is_available
            }
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_advanced_image_generator() -> AdvancedImageGenerator:
    """Get singleton advanced image generator instance"""
    global _advanced_image_generator
    
    if '_advanced_image_generator' not in globals():
        _advanced_image_generator = AdvancedImageGenerator()
    
    return _advanced_image_generator


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Initialize generator
    generator = AdvancedImageGenerator()
    
    print("=== Advanced Image Generator Capabilities ===")
    print(generator.get_capabilities())
    
    # Example 1: ControlNet generation
    print("\n=== ControlNet Example ===")
    # result = generator.generate_with_controlnet(
    #     prompt="beautiful landscape, detailed",
    #     control_image_path="edge.png",
    #     controlnet_type="canny",
    #     controlnet_weight=1.0
    # )
    
    # Example 2: Upscaling
    print("\n=== Upscaling Example ===")
    # result = generator.upscale_image(
    #     image_path="small_image.png",
    #     upscaler="R-ESRGAN 4x+",
    #     scale_factor=4.0,
    #     restore_faces=True
    # )
    
    # Example 3: Inpainting
    print("\n=== Inpainting Example ===")
    # result = generator.inpaint_image(
    #     image_path="original.png",
    #     mask_path="mask.png",
    #     prompt="beautiful flowers",
    #     denoising_strength=0.75
    # )
