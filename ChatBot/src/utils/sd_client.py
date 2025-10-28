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
        save_images: bool = False
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
        
        Returns:
            Dict với keys: images (list base64), parameters, info
        """
        payload = {
            "prompt": prompt,
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
