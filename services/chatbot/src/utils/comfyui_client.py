"""
ComfyUI API Client
Connect to ComfyUI for image generation
"""

import os
import json
import uuid
import time
import requests
import base64
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Client for ComfyUI API"""
    
    def __init__(self, api_url: str = None):
        """Initialize ComfyUI Client"""
        self.api_url = (api_url or os.getenv('COMFYUI_URL', 'http://localhost:8189')).rstrip('/')
        self.client_id = str(uuid.uuid4())
        
    def check_health(self) -> bool:
        """Check if ComfyUI is running"""
        try:
            response = requests.get(f"{self.api_url}/system_stats", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    # Known working models (verified with non-zero file size)
    WORKING_MODELS = [
        'animagine-xl-3.1.safetensors',
        'juggernautXL_v9.safetensors',
        'dreamshaper_xl.safetensors',
        'realvisxlV50_v50LightningBakedvae.safetensors',
        'sd_xl_base_1.0.safetensors',
        'counterfeit_v30.safetensors',
        'realisticVision_v60.safetensors',
    ]
    
    # Known corrupt models (0 bytes or broken)
    BROKEN_MODELS = [
        'absolutereality_v181.safetensors',
        'anythingV5_PrtRE.safetensors',
        'cyberrealistic_xl.safetensors',
        'epicrealism_xl.safetensors',
        'leosam_helloworld_xl.safetensors',
        'meinamix_v11.safetensors',
    ]
    
    def get_models(self) -> List[str]:
        """Get available checkpoint models (excludes known broken models)"""
        try:
            response = requests.get(f"{self.api_url}/object_info/CheckpointLoaderSimple", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = data.get('CheckpointLoaderSimple', {}).get('input', {}).get('required', {}).get('ckpt_name', [[]])[0]
                if isinstance(models, list):
                    # Filter out known broken models
                    working = [m for m in models if m not in self.BROKEN_MODELS]
                    return working if working else models
                return []
            return []
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            return []
    
    def get_current_model(self) -> str:
        """Get current/default model (prioritize known working models)"""
        models = self.get_models()
        if not models:
            return "No model loaded"
        
        # Prioritize known working models
        for preferred in self.WORKING_MODELS:
            if preferred in models:
                return preferred
        
        return models[0]
    
    def get_samplers(self) -> List[str]:
        """Get available samplers from ComfyUI"""
        try:
            response = requests.get(f"{self.api_url}/object_info/KSampler", timeout=10)
            if response.status_code == 200:
                data = response.json()
                samplers = data.get('KSampler', {}).get('input', {}).get('required', {}).get('sampler_name', [[]])[0]
                return samplers if isinstance(samplers, list) else []
            return ['euler', 'euler_ancestral', 'heun', 'dpm_2', 'dpm_2_ancestral', 'lms', 'dpm_fast', 'dpm_adaptive', 'dpmpp_2s_ancestral', 'dpmpp_sde', 'dpmpp_2m']
        except Exception as e:
            logger.error(f"Error getting samplers: {e}")
            return ['euler', 'dpmpp_2m', 'dpmpp_sde']
    
    def get_loras(self) -> List[Dict]:
        """Get available LoRA models"""
        try:
            response = requests.get(f"{self.api_url}/object_info/LoraLoader", timeout=10)
            if response.status_code == 200:
                data = response.json()
                loras = data.get('LoraLoader', {}).get('input', {}).get('required', {}).get('lora_name', [[]])[0]
                if isinstance(loras, list):
                    return [{'name': lora, 'alias': lora} for lora in loras]
            return []
        except Exception as e:
            logger.error(f"Error getting LoRAs: {e}")
            return []
    
    def get_vaes(self) -> List[Dict]:
        """Get available VAE models"""
        try:
            response = requests.get(f"{self.api_url}/object_info/VAELoader", timeout=10)
            if response.status_code == 200:
                data = response.json()
                vaes = data.get('VAELoader', {}).get('input', {}).get('required', {}).get('vae_name', [[]])[0]
                if isinstance(vaes, list):
                    return [{'name': vae, 'alias': vae} for vae in vaes]
            return [{'name': 'Automatic (Default)', 'alias': 'auto'}]
        except Exception as e:
            logger.error(f"Error getting VAEs: {e}")
            return [{'name': 'Automatic (Default)', 'alias': 'auto'}]
    
    def change_model(self, model_name: str) -> bool:
        """Change checkpoint model - Note: ComfyUI loads model per-workflow"""
        # ComfyUI doesn't have a global model change API
        # Model is specified per workflow, so we just validate it exists
        models = self.get_models()
        return model_name in models
    
    def interrupt(self) -> bool:
        """Interrupt current generation"""
        try:
            response = requests.post(f"{self.api_url}/interrupt", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def img2img(
        self,
        init_images: List[str],
        prompt: str,
        negative_prompt: str = "bad quality, blurry",
        denoising_strength: float = 0.7,
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: int = -1,
        sampler_name: str = "euler",
        **kwargs
    ) -> Dict:
        """
        Img2Img using ComfyUI workflow
        """
        try:
            if not init_images or not init_images[0]:
                return {'error': 'No input image provided'}
            
            # Get model
            model = self.get_current_model()
            if model == "No model loaded":
                model = "animagine-xl-3.1.safetensors"
            
            # Random seed if -1
            if seed == -1:
                seed = int(time.time() * 1000) % (2**32)
            
            # Decode base64 image and upload to ComfyUI
            image_data = init_images[0]
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Upload image to ComfyUI
            image_bytes = base64.b64decode(image_data)
            upload_result = self._upload_image(image_bytes)
            if not upload_result:
                return {'error': 'Failed to upload image to ComfyUI'}
            
            input_image_name = upload_result.get('name')
            
            # Img2Img workflow with image scaling to ensure compatible dimensions
            workflow = {
                "1": {
                    "class_type": "LoadImage",
                    "inputs": {
                        "image": input_image_name
                    }
                },
                "1b": {
                    "class_type": "ImageScale",
                    "inputs": {
                        "image": ["1", 0],
                        "upscale_method": "lanczos",
                        "width": width,
                        "height": height,
                        "crop": "center"
                    }
                },
                "2": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {
                        "ckpt_name": model
                    }
                },
                "3": {
                    "class_type": "VAEEncode",
                    "inputs": {
                        "pixels": ["1b", 0],
                        "vae": ["2", 2]
                    }
                },
                "4": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "clip": ["2", 1],
                        "text": prompt
                    }
                },
                "5": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "clip": ["2", 1],
                        "text": negative_prompt
                    }
                },
                "6": {
                    "class_type": "KSampler",
                    "inputs": {
                        "cfg": cfg_scale,
                        "denoise": denoising_strength,
                        "latent_image": ["3", 0],
                        "model": ["2", 0],
                        "negative": ["5", 0],
                        "positive": ["4", 0],
                        "sampler_name": sampler_name if sampler_name in self.get_samplers() else "euler",
                        "scheduler": "normal",
                        "seed": seed,
                        "steps": steps
                    }
                },
                "7": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["6", 0],
                        "vae": ["2", 2]
                    }
                },
                "8": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": "ComfyUI_img2img",
                        "images": ["7", 0]
                    }
                }
            }
            
            # Queue the prompt
            prompt_id = self._queue_prompt(workflow)
            if not prompt_id:
                return {'error': 'Failed to queue prompt'}
            
            # Wait for completion
            output = self._wait_for_prompt(prompt_id, timeout=300)
            if not output:
                return {'error': 'Generation timeout'}
            
            # Get the image
            image_bytes = self._get_image(output)
            if not image_bytes:
                return {'error': 'Failed to get generated image'}
            
            # Return base64 encoded image
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            return {'images': [base64_image]}
            
        except Exception as e:
            logger.error(f"Error in img2img: {e}")
            return {'error': str(e)}
    
    def _upload_image(self, image_bytes: bytes, filename: str = None) -> Optional[Dict]:
        """Upload image to ComfyUI input folder"""
        try:
            if not filename:
                filename = f"input_{int(time.time() * 1000)}.png"
            
            files = {
                'image': (filename, image_bytes, 'image/png')
            }
            
            response = requests.post(
                f"{self.api_url}/upload/image",
                files=files,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            return None
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "bad quality, blurry, distorted, ugly, worst quality",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: int = -1,
        model: str = None
    ) -> Optional[bytes]:
        """
        Generate image using ComfyUI
        
        Returns:
            Image bytes or None if failed
        """
        try:
            # Get model if not specified, or validate provided model
            if not model or model in self.BROKEN_MODELS:
                # Use known working model
                model = self.get_current_model()
                if model == "No model loaded":
                    model = "animagine-xl-3.1.safetensors"
            
            logger.info(f"Using model: {model}")
            
            # Random seed if -1
            if seed == -1:
                seed = int(time.time() * 1000) % (2**32)
            
            # ComfyUI workflow
            workflow = {
                "3": {
                    "class_type": "KSampler",
                    "inputs": {
                        "cfg": cfg_scale,
                        "denoise": 1,
                        "latent_image": ["5", 0],
                        "model": ["4", 0],
                        "negative": ["7", 0],
                        "positive": ["6", 0],
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "seed": seed,
                        "steps": steps
                    }
                },
                "4": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {
                        "ckpt_name": model
                    }
                },
                "5": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "batch_size": 1,
                        "height": height,
                        "width": width
                    }
                },
                "6": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "clip": ["4", 1],
                        "text": prompt
                    }
                },
                "7": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "clip": ["4", 1],
                        "text": negative_prompt
                    }
                },
                "8": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["3", 0],
                        "vae": ["4", 2]
                    }
                },
                "9": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "filename_prefix": "ComfyUI",
                        "images": ["8", 0]
                    }
                }
            }
            
            # Queue the prompt
            prompt_id = self._queue_prompt(workflow)
            if not prompt_id:
                return None
            
            # Wait for completion
            output = self._wait_for_prompt(prompt_id, timeout=300)
            if not output:
                return None
            
            # Get the image
            image_data = self._get_image(output)
            return image_data
            
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            return None
    
    def _queue_prompt(self, workflow: Dict) -> Optional[str]:
        """Queue a prompt and return prompt_id"""
        try:
            data = {
                "prompt": workflow,
                "client_id": self.client_id
            }
            response = requests.post(
                f"{self.api_url}/prompt",
                json=data,
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get('prompt_id')
            return None
        except Exception as e:
            logger.error(f"Error queuing prompt: {e}")
            return None
    
    def _wait_for_prompt(self, prompt_id: str, timeout: int = 300) -> Optional[Dict]:
        """Wait for prompt to complete"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(f"{self.api_url}/history/{prompt_id}", timeout=10)
                if response.status_code == 200:
                    history = response.json()
                    if prompt_id in history:
                        return history[prompt_id].get('outputs', {})
            except:
                pass
            time.sleep(1)
        
        return None
    
    def _get_image(self, outputs: Dict) -> Optional[bytes]:
        """Get image from outputs"""
        try:
            for node_id, output in outputs.items():
                if 'images' in output:
                    for image_info in output['images']:
                        filename = image_info.get('filename')
                        subfolder = image_info.get('subfolder', '')
                        folder_type = image_info.get('type', 'output')
                        
                        params = {
                            'filename': filename,
                            'subfolder': subfolder,
                            'type': folder_type
                        }
                        
                        response = requests.get(
                            f"{self.api_url}/view",
                            params=params,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            return response.content
            return None
        except Exception as e:
            logger.error(f"Error getting image: {e}")
            return None


def get_comfyui_client(api_url: str = None) -> ComfyUIClient:
    """Get ComfyUI client instance"""
    return ComfyUIClient(api_url)


# Alias for compatibility
def get_sd_client(api_url: str = None) -> ComfyUIClient:
    """Get SD client (uses ComfyUI) - Alias for compatibility"""
    return ComfyUIClient(api_url)
def get_sd_client(api_url: str = None):
    """Get SD client (uses ComfyUI)"""
    return get_comfyui_client(api_url)
