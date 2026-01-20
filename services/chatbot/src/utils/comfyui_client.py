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
    
    def get_models(self) -> List[str]:
        """Get available checkpoint models"""
        try:
            response = requests.get(f"{self.api_url}/object_info/CheckpointLoaderSimple", timeout=10)
            if response.status_code == 200:
                data = response.json()
                models = data.get('CheckpointLoaderSimple', {}).get('input', {}).get('required', {}).get('ckpt_name', [[]])[0]
                return models if isinstance(models, list) else []
            return []
        except Exception as e:
            logger.error(f"Error getting models: {e}")
            return []
    
    def get_current_model(self) -> str:
        """Get current/default model"""
        models = self.get_models()
        return models[0] if models else "No model loaded"
    
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
            # Get model if not specified
            if not model:
                models = self.get_models()
                model = models[0] if models else "animagine-xl-3.1.safetensors"
            
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


# For compatibility with existing sd_client imports
def get_sd_client(api_url: str = None):
    """Get SD client (uses ComfyUI)"""
    return get_comfyui_client(api_url)
