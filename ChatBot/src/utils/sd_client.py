"""
Stable Diffusion API Client
Kết nối tới Stable Diffusion WebUI API để tạo ảnh
"""

import requests
import base64
import io
from PIL import Image
from typing import Optional, List, Dict


class StableDiffusionClient:
    """Client để tương tác với Stable Diffusion WebUI API"""
    
    def __init__(self, api_url: str = "http://127.0.0.1:7860"):
        """
        Initialize SD Client
        
        Args:
            api_url: URL của Stable Diffusion WebUI (mặc định: http://127.0.0.1:7860)
        """
        self.api_url = api_url.rstrip('/')
        self.base_timeout = 300  # Base timeout 5 minutes
        
    def _calculate_timeout(self, width: int, height: int, steps: int) -> int:
        """
        Tính timeout động dựa trên kích thước ảnh và số steps
        
        Args:
            width: Chiều rộng
            height: Chiều cao
            steps: Số steps
            
        Returns:
            Timeout in seconds (None = no timeout)
        """
        # No timeout - wait indefinitely until image is generated
        # User can manually cancel if needed
        return None
        
    def check_health(self) -> bool:
        """Kiểm tra xem Stable Diffusion API có đang chạy không"""
        try:
            response = requests.get(f"{self.api_url}/sdapi/v1/sd-models", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_models(self) -> List[Dict]:
        """
        Lấy danh sách tất cả các checkpoint models
        
        Returns:
            List of model dicts với keys: title, model_name, hash, sha256, filename, config
        """
        try:
            response = requests.get(f"{self.api_url}/sdapi/v1/sd-models", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting models: {e}")
            return []
    
    def get_current_model(self) -> Dict:
        """Lấy thông tin model hiện tại đang được sử dụng"""
        try:
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
        Đổi checkpoint model
        
        Args:
            model_name: Tên model (title hoặc model_name từ get_models())
        
        Returns:
            True nếu thành công, False nếu thất bại
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
        Tạo ảnh từ text prompt
        
        Args:
            prompt: Text prompt mô tả ảnh muốn tạo
            negative_prompt: Những gì KHÔNG muốn có trong ảnh
            width: Chiều rộng ảnh (khuyến nghị: 512, 768, 1024)
            height: Chiều cao ảnh (khuyến nghị: 512, 768, 1024)
            steps: Số bước sampling (20-50 là tốt)
            cfg_scale: Độ tuân theo prompt (7-12 là tốt)
            sampler_name: Tên sampler (DPM++ 2M Karras, Euler a, DDIM, etc.)
            seed: Random seed (-1 = random)
            batch_size: Số ảnh tạo mỗi lần
            n_iter: Số lần lặp
            restore_faces: Có restore faces không (GFPGAN/CodeFormer)
            enable_hr: Bật Hires. fix để tạo ảnh chất lượng cao hơn
            hr_scale: Hệ số scale khi dùng Hires. fix
            hr_upscaler: Upscaler dùng cho Hires. fix
            denoising_strength: Độ mạnh denoising cho Hires. fix
            save_images: Có lưu ảnh vào outputs/ không
            lora_models: List of Lora models to apply [{"name": "lora_name", "weight": 0.8}]
            vae: VAE model name (None = Automatic)
        
        Returns:
            Dict với keys: images (list base64), parameters, info
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
        
        # No timeout - wait until completion or manual cancellation
        timeout = None
        print(f"[INFO] Generating {width}x{height} image with {steps} steps (no timeout - will wait until complete)")
        
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
            # Should never happen with timeout=None
            return {"error": f"Timeout - This shouldn't happen. Please report this bug."}
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"error": f"Lỗi khi tạo ảnh: {str(e)}"}
    
    def get_samplers(self) -> List[str]:
        """Lấy danh sách tất cả các samplers có sẵn"""
        try:
            response = requests.get(f"{self.api_url}/sdapi/v1/samplers", timeout=10)
            response.raise_for_status()
            samplers = response.json()
            return [s["name"] for s in samplers]
        except Exception as e:
            print(f"Error getting samplers: {e}")
            return ["Euler a", "Euler", "DPM++ 2M Karras", "DPM++ SDE Karras", "DDIM"]
    
    def get_loras(self) -> List[Dict]:
        """
        Lấy danh sách tất cả các Lora models
        
        Returns:
            List of Lora dicts với keys: name, alias, path, metadata
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
        Lấy danh sách tất cả các VAE models
        
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
        Tạo ảnh từ ảnh gốc (img2img)
        
        Args:
            init_images: List of base64 encoded images
            prompt: Text prompt mô tả ảnh muốn tạo
            negative_prompt: Những gì KHÔNG muốn có
            denoising_strength: Tỉ lệ thay đổi so với ảnh gốc (0.0-1.0)
                - 0.0 = giữ nguyên 100%
                - 1.0 = tạo mới hoàn toàn
                - 0.75-0.85 = recommended (75-85% mới, 15-25% giữ lại)
            width: Chiều rộng
            height: Chiều cao
            steps: Số bước sampling (img2img thường cần nhiều steps hơn txt2img)
            cfg_scale: Độ tuân theo prompt
            sampler_name: Tên sampler
            seed: Random seed (-1 = random)
            restore_faces: Có restore faces không
            resize_mode: Cách resize ảnh input
            lora_models: List of Lora models to apply [{"name": "lora_name", "weight": 0.8}]
            vae: VAE model name (None = Automatic)
        
        Returns:
            Dict với keys: images (list base64), parameters, info
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
        
        # No timeout - wait until completion
        timeout = None
        print(f"[INFO] Img2Img: {width}x{height}, {steps} steps, denoising={denoising_strength}")
        
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
            return {"error": f"Lỗi khi tạo ảnh: {str(e)}"}
    
    def interrupt(self) -> bool:
        """Dừng việc tạo ảnh đang chạy"""
        try:
            response = requests.post(f"{self.api_url}/sdapi/v1/interrupt", timeout=5)
            response.raise_for_status()
            return True
        except:
            return False
    
    def base64_to_image(self, base64_string: str) -> Image.Image:
        """Convert base64 string thành PIL Image"""
        image_data = base64.b64decode(base64_string)
        return Image.open(io.BytesIO(image_data))
    
    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image thành base64 string"""
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()


# Singleton instance
_sd_client = None

def get_sd_client(api_url: str = "http://127.0.0.1:7860") -> StableDiffusionClient:
    """Get hoặc tạo SD client instance"""
    global _sd_client
    if _sd_client is None:
        _sd_client = StableDiffusionClient(api_url)
    return _sd_client
