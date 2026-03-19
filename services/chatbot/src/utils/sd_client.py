"""
Stable Diffusion API Client
Káº¿t ná»‘i tá»›i Stable Diffusion WebUI API Ä‘á»ƒ táº¡o áº£nh
"""

import requests
import base64
import io
from PIL import Image
from typing import Optional, List, Dict


class StableDiffusionClient:
    """Client Ä‘á»ƒ tÆ°Æ¡ng tÃ¡c vá»›i Stable Diffusion WebUI API"""
    
    def __init__(self, api_url: str = "http://127.0.0.1:7860"):
        """
        Initialize SD Client
        
        Args:
            api_url: URL cá»§a Stable Diffusion WebUI (máº·c Ä‘á»‹nh: http://127.0.0.1:7860)
        """
        self.api_url = api_url.rstrip('/')
        self.base_timeout = 300  # Base timeout 5 minutes
        
    def _calculate_timeout(self, width: int, height: int, steps: int) -> int:
        """
        TÃ­nh timeout Ä‘á»™ng dá»±a trÃªn kÃ­ch thÆ°á»›c áº£nh vÃ  sá»‘ steps
        
        Args:
            width: Chiá»u rá»™ng
            height: Chiá»u cao
            steps: Sá»‘ steps
            
        Returns:
            Timeout in seconds
        """
        # Base time per step (seconds)
        time_per_step = 0.5  # Average 0.5s per step
        
        # Calculate based on pixels and steps
        pixels = width * height
        base_time = (pixels / (512 * 512)) * steps * time_per_step
        
        # Add overhead and safety margin
        timeout = max(60, int(base_time * 2) + 30)  # At least 60s, with 2x safety margin + 30s overhead
        
        return timeout
        
    def check_health(self) -> bool:
        """Kiá»ƒm tra xem Stable Diffusion API cÃ³ Ä‘ang cháº¡y khÃ´ng (há»— trá»£ cáº£ ComfyUI vÃ  A1111)"""
        try:
            print(f"[SD Client] Checking health at {self.api_url}", flush=True)
            
            # Try ComfyUI endpoint first
            try:
                response = requests.get(f"{self.api_url}/system_stats", timeout=5)
                if response.status_code == 200:
                    print(f"[SD Client] ComfyUI detected and running", flush=True)
                    return True
            except:
                pass
            
            # Fallback to A1111 endpoint
            try:
                response = requests.get(f"{self.api_url}/sdapi/v1/sd-models", timeout=10)
                if response.status_code == 200:
                    print(f"[SD Client] A1111 WebUI detected and running", flush=True)
                    return True
            except:
                pass
            
            print(f"[SD Client] No SD backend detected", flush=True)
            return False
        except Exception as e:
            print(f"[SD Client] Health check failed: {e}", flush=True)
            return False
    
    def get_models(self) -> List[Dict]:
        """
        Láº¥y danh sÃ¡ch táº¥t cáº£ cÃ¡c checkpoint models (há»— trá»£ ComfyUI vÃ  A1111)
        
        Returns:
            List of model dicts vá»›i keys: title, model_name, hash, sha256, filename, config
        """
        try:
            # Try ComfyUI first
            try:
                response = requests.get(f"{self.api_url}/object_info/CheckpointLoaderSimple", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    models = data.get('CheckpointLoaderSimple', {}).get('input', {}).get('required', {}).get('ckpt_name', [[]])[0]
                    if isinstance(models, list):
                        return [{'title': m, 'model_name': m} for m in models]
            except:
                pass
            
            # Fallback to A1111
            response = requests.get(f"{self.api_url}/sdapi/v1/sd-models", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting models: {e}")
            return []
    
    def get_current_model(self) -> Dict:
        """Láº¥y thÃ´ng tin model hiá»‡n táº¡i Ä‘ang Ä‘Æ°á»£c sá»­ dá»¥ng"""
        try:
            # Try ComfyUI first
            models = self.get_models()
            if models:
                return {"model": models[0].get('title', 'animagine-xl-3.1'), "vae": "Automatic"}
            
            # Fallback to A1111
            response = requests.get(f"{self.api_url}/sdapi/v1/options", timeout=10)
            response.raise_for_status()
            options = response.json()
            return {
                "model": options.get("sd_model_checkpoint", "Unknown"),
                "vae": options.get("sd_vae", "Automatic")
            }
        except Exception as e:
            print(f"Error getting current model: {e}")
            return {"model": "Unknown", "vae": "Unknown"}
    
    def change_model(self, model_name: str) -> bool:
        """
        Äá»•i checkpoint model
        
        Args:
            model_name: TÃªn model (title hoáº·c model_name tá»« get_models())
        
        Returns:
            True náº¿u thÃ nh cÃ´ng, False náº¿u tháº¥t báº¡i
        """
        try:
            payload = {
                "sd_model_checkpoint": model_name
            }
            response = requests.post(
                f"{self.api_url}/sdapi/v1/options", 
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error changing model: {e}")
            return False
    
    def txt2img(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 512,
        height: int = 512,
        steps: int = 20,
        cfg_scale: float = 7.0,
        sampler_name: str = "DPM++ 2M Karras",
        seed: int = -1,
        batch_size: int = 1,
        n_iter: int = 1,
        restore_faces: bool = False,
        enable_hr: bool = False,
        hr_scale: float = 2.0,
        hr_upscaler: str = "Latent",
        denoising_strength: float = 0.7,
        save_images: bool = False,
        lora_models: Optional[List[Dict]] = None,
        vae: Optional[str] = None
    ) -> Dict:
        """
        Táº¡o áº£nh tá»« text prompt
        
        Args:
            prompt: Text prompt mÃ´ táº£ áº£nh muá»‘n táº¡o
            negative_prompt: Nhá»¯ng gÃ¬ KHÃ”NG muá»‘n cÃ³ trong áº£nh
            width: Chiá»u rá»™ng áº£nh (khuyáº¿n nghá»‹: 512, 768, 1024)
            height: Chiá»u cao áº£nh (khuyáº¿n nghá»‹: 512, 768, 1024)
            steps: Sá»‘ bÆ°á»›c sampling (20-50 lÃ  tá»‘t)
            cfg_scale: Äá»™ tuÃ¢n theo prompt (7-12 lÃ  tá»‘t)
            sampler_name: TÃªn sampler (DPM++ 2M Karras, Euler a, DDIM, etc.)
            seed: Random seed (-1 = random)
            batch_size: Sá»‘ áº£nh táº¡o má»—i láº§n
            n_iter: Sá»‘ láº§n láº·p
            restore_faces: CÃ³ restore faces khÃ´ng (GFPGAN/CodeFormer)
            enable_hr: Báº­t Hires. fix Ä‘á»ƒ táº¡o áº£nh cháº¥t lÆ°á»£ng cao hÆ¡n
            hr_scale: Há»‡ sá»‘ scale khi dÃ¹ng Hires. fix
            hr_upscaler: Upscaler dÃ¹ng cho Hires. fix
            denoising_strength: Äá»™ máº¡nh denoising cho Hires. fix
            save_images: CÃ³ lÆ°u áº£nh vÃ o outputs/ khÃ´ng
            lora_models: List of Lora models to apply [{"name": "lora_name", "weight": 0.8}]
            vae: VAE model name (None = Automatic)
        
        Returns:
            Dict vá»›i keys: images (list base64), parameters, info
        """
        # Apply Lora to prompt
        final_prompt = prompt
        if lora_models:
            for lora in lora_models:
                lora_name = lora.get('name', '')
                lora_weight = lora.get('weight', 1.0)
                # Add Lora syntax to prompt: <lora:name:weight>
                final_prompt = f"<lora:{lora_name}:{lora_weight}> {final_prompt}"
        
        payload = {
            "prompt": final_prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler_name,
            "seed": seed,
            "batch_size": batch_size,
            "n_iter": n_iter,
            "restore_faces": restore_faces,
            "enable_hr": enable_hr,
            "hr_scale": hr_scale,
            "hr_upscaler": hr_upscaler,
            "denoising_strength": denoising_strength,
            "save_images": save_images,
            "send_images": True,
            "do_not_save_samples": not save_images
        }
        
        # Add VAE override if specified
        if vae:
            payload["override_settings"] = {
                "sd_vae": vae
            }
        
        # Calculate dynamic timeout based on image size and steps
        timeout = self._calculate_timeout(width, height, steps)
        print(f"[INFO] Generating {width}x{height} image with {steps} steps (timeout: {timeout}s)")
        
        # Check if SD WebUI is running
        if not self.check_health():
            return {"error": "Stable Diffusion WebUI is not running. Please start it first."}
        
        try:
            response = requests.post(
                f"{self.api_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            print(f"[SUCCESS] Image generated successfully!")
            return response.json()
        except requests.exceptions.Timeout:
            # Log detailed timeout information server-side, return generic message to client
            print(f"[ERROR] Timeout after {timeout}s when calling txt2img API")
            return {"error": "Image generation timed out. Try reducing image size or steps, or check if the image service is responding."}
        except requests.exceptions.RequestException as e:
            # Log detailed network error server-side, return generic message to client
            print(f"[ERROR] Network error when calling txt2img API: {e}")
            return {"error": "A network error occurred while generating the image. Please try again later."}
        except Exception as e:
            # Log unexpected errors server-side, return generic message to client
            print(f"[ERROR] Unexpected error when generating image: {e}")
            return {"error": "An internal error occurred while generating the image."}
    
    def get_samplers(self) -> List[Dict]:
        """Láº¥y danh sÃ¡ch táº¥t cáº£ cÃ¡c samplers cÃ³ sáºµn"""
        try:
            response = requests.get(f"{self.api_url}/sdapi/v1/samplers", timeout=10)
            response.raise_for_status()
            samplers = response.json()
            # Return array of {name: sampler_name} for frontend compatibility
            return [{"name": s["name"]} for s in samplers]
        except Exception as e:
            print(f"Error getting samplers: {e}")
            # Return default samplers
            return [
                {"name": "Euler a"},
                {"name": "Euler"},
                {"name": "DPM++ 2M Karras"},
                {"name": "DPM++ SDE Karras"},
                {"name": "DDIM"}
            ]
    
    def get_loras(self) -> List[Dict]:
        """
        Láº¥y danh sÃ¡ch táº¥t cáº£ cÃ¡c Lora models
        
        Returns:
            List of Lora dicts vá»›i keys: name, alias, path, metadata
        """
        try:
            response = requests.get(f"{self.api_url}/sdapi/v1/loras", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting loras: {e}")
            return []
    
    def get_vaes(self) -> List[Dict]:
        """
        Láº¥y danh sÃ¡ch táº¥t cáº£ cÃ¡c VAE models
        
        Returns:
            List of VAE names
        """
        try:
            response = requests.get(f"{self.api_url}/sdapi/v1/sd-vae", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting VAEs: {e}")
            return []
    
    def img2img(
        self,
        init_images: List[str],
        prompt: str,
        negative_prompt: str = "",
        denoising_strength: float = 0.75,
        width: int = 512,
        height: int = 512,
        steps: int = 30,
        cfg_scale: float = 7.0,
        sampler_name: str = "DPM++ 2M Karras",
        seed: int = -1,
        restore_faces: bool = False,
        resize_mode: int = 0,  # 0=Just resize, 1=Crop and resize, 2=Resize and fill
        lora_models: Optional[List[Dict]] = None,
        vae: Optional[str] = None
    ) -> Dict:
        """
        Táº¡o áº£nh tá»« áº£nh gá»‘c (img2img)
        
        Args:
            init_images: List of base64 encoded images
            prompt: Text prompt mÃ´ táº£ áº£nh muá»‘n táº¡o
            negative_prompt: Nhá»¯ng gÃ¬ KHÃ”NG muá»‘n cÃ³
            denoising_strength: Tá»‰ lá»‡ thay Ä‘á»•i so vá»›i áº£nh gá»‘c (0.0-1.0)
                - 0.0 = giá»¯ nguyÃªn 100%
                - 1.0 = táº¡o má»›i hoÃ n toÃ n
                - 0.75-0.85 = recommended (75-85% má»›i, 15-25% giá»¯ láº¡i)
            width: Chiá»u rá»™ng
            height: Chiá»u cao
            steps: Sá»‘ bÆ°á»›c sampling (img2img thÆ°á»ng cáº§n nhiá»u steps hÆ¡n txt2img)
            cfg_scale: Äá»™ tuÃ¢n theo prompt
            sampler_name: TÃªn sampler
            seed: Random seed (-1 = random)
            restore_faces: CÃ³ restore faces khÃ´ng
            resize_mode: CÃ¡ch resize áº£nh input
            lora_models: List of Lora models to apply [{"name": "lora_name", "weight": 0.8}]
            vae: VAE model name (None = Automatic)
        
        Returns:
            Dict vá»›i keys: images (list base64), parameters, info
        """
        # Apply Lora to prompt
        final_prompt = prompt
        if lora_models:
            for lora in lora_models:
                lora_name = lora.get('name', '')
                lora_weight = lora.get('weight', 1.0)
                final_prompt = f"<lora:{lora_name}:{lora_weight}> {final_prompt}"
        
        payload = {
            "init_images": init_images,
            "prompt": final_prompt,
            "negative_prompt": negative_prompt,
            "denoising_strength": denoising_strength,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "sampler_name": sampler_name,
            "seed": seed,
            "restore_faces": restore_faces,
            "resize_mode": resize_mode,
            "send_images": True,
            "save_images": False
        }
        
        # Add VAE override if specified
        if vae:
            payload["override_settings"] = {
                "sd_vae": vae
            }
        
        timeout = self._calculate_timeout(width, height, steps)
        print(f"[INFO] Img2Img: {width}x{height}, {steps} steps, denoising={denoising_strength}, timeout={timeout}s")
        
        try:
            response = requests.post(
                f"{self.api_url}/sdapi/v1/img2img",
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            print(f"[SUCCESS] Img2Img generated successfully!")
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Lá»—i khi táº¡o áº£nh: {str(e)}"}
    
    def interrupt(self) -> bool:
        """Dá»«ng viá»‡c táº¡o áº£nh Ä‘ang cháº¡y"""
        try:
            response = requests.post(f"{self.api_url}/sdapi/v1/interrupt", timeout=5)
            response.raise_for_status()
            return True
        except:
            return False
    
    def base64_to_image(self, base64_string: str) -> Image.Image:
        """Convert base64 string thÃ nh PIL Image"""
        image_data = base64.b64decode(base64_string)
        return Image.open(io.BytesIO(image_data))
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image thÃ nh base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()


# Singleton instance
_sd_client = None

def get_sd_client(api_url: str = None) -> StableDiffusionClient:
    """Get hoáº·c táº¡o SD client instance"""
    import os
    global _sd_client
    
    # Use environment variable or default
    if api_url is None:
        api_url = os.getenv('SD_API_URL', os.getenv('COMFYUI_URL', 'http://127.0.0.1:8189'))
    
    # Náº¿u URL thay Ä‘á»•i, táº¡o client má»›i
    if (
        _sd_client is None
        or getattr(_sd_client, "api_url", "").rstrip("/") != api_url.rstrip("/")
    ):
        _sd_client = StableDiffusionClient(api_url)
    return _sd_client
