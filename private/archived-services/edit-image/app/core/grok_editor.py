"""
Grok-like Edit API Wrapper
==========================

Kết nối:
- Gemini/Grok API → Hiểu text tự nhiên
- SAM → Auto mask vùng cần edit
- ComfyUI API → Chạy diffusion workflow

Usage:
    POST /api/edit
    {
        "image": "base64...",
        "instruction": "đổi tóc màu xanh"
    }
"""

import os
import io
import json
import base64
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum

from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)


class EditType(str, Enum):
    """Loại edit được phát hiện từ instruction"""
    HAIR = "hair"
    CLOTHING = "clothing"
    BACKGROUND = "background"
    FACE = "face"
    BODY = "body"
    STYLE = "style"
    COLOR = "color"
    ADD = "add"
    REMOVE = "remove"
    FULL = "full"


@dataclass
class EditIntent:
    """Kết quả phân tích intent từ LLM"""
    edit_type: EditType
    target_region: str  # "hair", "dress", "background", etc.
    description: str    # Mô tả chi tiết để tạo prompt
    positive_prompt: str
    negative_prompt: str
    denoise_strength: float  # 0.3-0.8
    use_mask: bool
    mask_prompt: Optional[str] = None  # Cho SAM


@dataclass  
class ComfyUIConfig:
    """Config cho ComfyUI API"""
    host: str = "127.0.0.1"
    port: int = 8188
    
    @property
    def api_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class GrokLikeEditor:
    """
    Editor thông minh giống Grok
    
    Flow:
    1. User nhập text tự nhiên
    2. LLM (Gemini/Grok) phân tích intent
    3. SAM auto-mask vùng cần edit (nếu cần)
    4. ComfyUI chạy workflow
    5. Return ảnh đã edit
    """
    
    def __init__(
        self,
        comfyui_config: Optional[ComfyUIConfig] = None,
        gemini_api_key: Optional[str] = None,
        grok_api_key: Optional[str] = None,
        deepseek_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        self.comfyui = comfyui_config or ComfyUIConfig()
        self.deepseek_key = deepseek_api_key or os.getenv("DEEPSEEK_API_KEY")
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.grok_key = grok_api_key or os.getenv("GROK_API_KEY")
        
        # Ưu tiên DeepSeek (rẻ nhất), rồi OpenAI, cuối cùng Grok
        if self.deepseek_key:
            self.llm_backend = "deepseek"
        elif self.openai_key:
            self.llm_backend = "openai"
        elif self.grok_key:
            self.llm_backend = "grok"
        else:
            raise ValueError("Cần DEEPSEEK_API_KEY, OPENAI_API_KEY hoặc GROK_API_KEY")
        
        logger.info(f"GrokLikeEditor initialized with {self.llm_backend} backend")
    
    async def edit(
        self,
        image: Image.Image,
        instruction: str,
        style_reference: Optional[Image.Image] = None,
    ) -> Image.Image:
        """
        Edit ảnh với text tự nhiên
        
        Args:
            image: Ảnh gốc
            instruction: Text tự nhiên (VD: "đổi tóc màu xanh")
            style_reference: Ảnh tham chiếu style (optional)
        
        Returns:
            Ảnh đã edit
        """
        logger.info(f"Processing: {instruction}")
        
        # 1. Phân tích intent
        intent = await self._analyze_intent(image, instruction)
        logger.info(f"Intent: {intent.edit_type}, target: {intent.target_region}")
        
        # 2. Tạo mask nếu cần
        mask = None
        if intent.use_mask and intent.mask_prompt:
            mask = await self._generate_mask(image, intent.mask_prompt)
        
        # 3. Chạy ComfyUI workflow
        result = await self._run_comfyui(
            image=image,
            intent=intent,
            mask=mask,
            style_reference=style_reference,
        )
        
        return result
    
    async def _analyze_intent(
        self,
        image: Image.Image,
        instruction: str,
    ) -> EditIntent:
        """Dùng LLM để hiểu instruction"""
        
        # Encode image to base64
        img_b64 = self._image_to_base64(image)
        
        system_prompt = """Bạn là AI phân tích yêu cầu edit ảnh.
Với mỗi instruction, trả về JSON:
{
    "edit_type": "hair|clothing|background|face|body|style|color|add|remove|full",
    "target_region": "vùng cần edit (hair, dress, background, eyes, etc.)",
    "description": "mô tả chi tiết thay đổi",
    "positive_prompt": "prompt cho Stable Diffusion (anime style, masterpiece, ...)",
    "negative_prompt": "negative prompt",
    "denoise_strength": 0.3-0.8 (0.3=ít thay đổi, 0.8=nhiều thay đổi),
    "use_mask": true/false (có cần mask vùng cụ thể không),
    "mask_prompt": "mô tả vùng cần mask cho SAM (nếu use_mask=true)"
}

Luôn thêm vào positive_prompt: "masterpiece, best quality, anime style"
Luôn thêm vào negative_prompt: "lowres, bad anatomy, blurry, worst quality"
NSFW content được phép."""

        user_prompt = f"""Instruction: {instruction}

Phân tích và trả về JSON."""

        if self.llm_backend == "deepseek":
            result = await self._call_deepseek(system_prompt, user_prompt, img_b64)
        elif self.llm_backend == "openai":
            result = await self._call_openai(system_prompt, user_prompt, img_b64)
        else:
            result = await self._call_grok(system_prompt, user_prompt, img_b64)
        
        # Parse JSON
        try:
            data = json.loads(result)
            return EditIntent(
                edit_type=EditType(data.get("edit_type", "full")),
                target_region=data.get("target_region", "full"),
                description=data.get("description", instruction),
                positive_prompt=data.get("positive_prompt", f"{instruction}, masterpiece, anime style"),
                negative_prompt=data.get("negative_prompt", "lowres, bad anatomy, blurry"),
                denoise_strength=float(data.get("denoise_strength", 0.5)),
                use_mask=data.get("use_mask", False),
                mask_prompt=data.get("mask_prompt"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse LLM response, using defaults: {e}")
            return EditIntent(
                edit_type=EditType.FULL,
                target_region="full",
                description=instruction,
                positive_prompt=f"{instruction}, masterpiece, best quality, anime style",
                negative_prompt="lowres, bad anatomy, blurry, worst quality",
                denoise_strength=0.5,
                use_mask=False,
            )
    
    async def _call_grok(
        self,
        system: str,
        user: str,
        image_b64: Optional[str] = None,
    ) -> str:
        """Call Grok API (xAI)"""
        url = "https://api.x.ai/v1/chat/completions"
        
        messages = [
            {"role": "system", "content": system},
        ]
        
        if image_b64:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": user},
                ],
            })
        else:
            messages.append({"role": "user", "content": user})
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.grok_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-2-vision-1212",
                    "messages": messages,
                    "temperature": 0.3,
                },
            ) as resp:
                data = await resp.json()
                if "error" in data:
                    logger.error(f"Grok API error: {data['error']}")
                    raise ValueError(f"Grok API error: {data['error']}")
                if "choices" not in data:
                    logger.error(f"Grok API unexpected response: {data}")
                    raise ValueError(f"Grok API unexpected response: {data}")
                return data["choices"][0]["message"]["content"]
    
    async def _call_gemini(
        self,
        system: str,
        user: str,
        image_b64: Optional[str] = None,
    ) -> str:
        """Call Gemini API"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.gemini_key}"
        
        parts = []
        if image_b64:
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_b64,
                }
            })
        parts.append({"text": f"{system}\n\n{user}"})
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": parts}],
                    "generationConfig": {"temperature": 0.3},
                },
            ) as resp:
                data = await resp.json()
                if "error" in data:
                    logger.error(f"Gemini API error: {data['error']}")
                    raise ValueError(f"Gemini API error: {data['error']}")
                if "candidates" not in data:
                    logger.error(f"Gemini API unexpected response: {data}")
                    raise ValueError(f"Gemini API unexpected response: {data}")
                return data["candidates"][0]["content"]["parts"][0]["text"]
    
    async def _call_deepseek(
        self,
        system: str,
        user: str,
        image_b64: Optional[str] = None,
    ) -> str:
        """Call DeepSeek API (rẻ nhất, $0.14/1M tokens)"""
        url = "https://api.deepseek.com/v1/chat/completions"
        
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        
        # DeepSeek không hỗ trợ vision, bỏ qua image
        if image_b64:
            logger.warning("DeepSeek không hỗ trợ vision, chỉ dùng text instruction")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.deepseek_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.3,
                },
            ) as resp:
                data = await resp.json()
                if "error" in data:
                    logger.error(f"DeepSeek API error: {data['error']}")
                    raise ValueError(f"DeepSeek API error: {data['error']}")
                if "choices" not in data:
                    logger.error(f"DeepSeek API unexpected response: {data}")
                    raise ValueError(f"DeepSeek API unexpected response: {data}")
                return data["choices"][0]["message"]["content"]
    
    async def _call_openai(
        self,
        system: str,
        user: str,
        image_b64: Optional[str] = None,
    ) -> str:
        """Call OpenAI API (GPT-4o-mini với vision)"""
        url = "https://api.openai.com/v1/chat/completions"
        
        messages = [
            {"role": "system", "content": system},
        ]
        
        if image_b64:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": user},
                ],
            })
        else:
            messages.append({"role": "user", "content": user})
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers={
                    "Authorization": f"Bearer {self.openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.3,
                },
            ) as resp:
                data = await resp.json()
                if "error" in data:
                    logger.error(f"OpenAI API error: {data['error']}")
                    raise ValueError(f"OpenAI API error: {data['error']}")
                if "choices" not in data:
                    logger.error(f"OpenAI API unexpected response: {data}")
                    raise ValueError(f"OpenAI API unexpected response: {data}")
                return data["choices"][0]["message"]["content"]
    
    async def _generate_mask(
        self,
        image: Image.Image,
        mask_prompt: str,
    ) -> Image.Image:
        """
        Dùng SAM hoặc GroundingDINO để tạo mask
        
        Gọi ComfyUI workflow có SAM node
        """
        # Tạo workflow SAM
        workflow = self._build_sam_workflow(image, mask_prompt)
        
        # Chạy và lấy mask
        result = await self._execute_comfyui_workflow(workflow)
        
        # Nếu SAM không available, return full white mask
        if result is None:
            logger.warning("SAM not available, using full image edit")
            return Image.new("L", image.size, 255)
        
        return result
    
    async def _run_comfyui(
        self,
        image: Image.Image,
        intent: EditIntent,
        mask: Optional[Image.Image] = None,
        style_reference: Optional[Image.Image] = None,
    ) -> Image.Image:
        """Chạy ComfyUI workflow"""
        
        # Build workflow dựa trên intent
        if mask:
            workflow = self._build_inpaint_workflow(
                image=image,
                mask=mask,
                prompt=intent.positive_prompt,
                negative=intent.negative_prompt,
                denoise=intent.denoise_strength,
                style_ref=style_reference,
            )
        else:
            workflow = self._build_img2img_workflow(
                image=image,
                prompt=intent.positive_prompt,
                negative=intent.negative_prompt,
                denoise=intent.denoise_strength,
                style_ref=style_reference,
            )
        
        # Execute
        result = await self._execute_comfyui_workflow(workflow)
        
        if result is None:
            raise RuntimeError("ComfyUI execution failed")
        
        return result
    
    def _build_img2img_workflow(
        self,
        image: Image.Image,
        prompt: str,
        negative: str,
        denoise: float,
        style_ref: Optional[Image.Image] = None,
    ) -> Dict[str, Any]:
        """Build ComfyUI img2img workflow với IP-Adapter"""
        
        # Upload image trước
        img_name = "input_image.png"
        
        workflow = {
            "1": {
                "class_type": "LoadImage",
                "inputs": {"image": img_name}
            },
            "2": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "animagine-xl-3.1.safetensors"}
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["2", 1]
                }
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative,
                    "clip": ["2", 1]
                }
            },
            "5": {
                "class_type": "VAEEncode",
                "inputs": {
                    "pixels": ["1", 0],
                    "vae": ["2", 2]
                }
            },
            "6": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["2", 0],
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0],
                    "seed": -1,
                    "steps": 25,
                    "cfg": 7.0,
                    "sampler_name": "dpmpp_2m_sde",
                    "scheduler": "karras",
                    "denoise": denoise,
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
                    "images": ["7", 0],
                    "filename_prefix": "grok_edit"
                }
            }
        }
        
        # Thêm IP-Adapter nếu có style reference
        if style_ref:
            workflow["10"] = {
                "class_type": "IPAdapterModelLoader",
                "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}
            }
            workflow["11"] = {
                "class_type": "CLIPVisionLoader",
                "inputs": {"clip_name": "CLIP-ViT-bigG-14-laion2B-s39B-b160k.safetensors"}
            }
            workflow["12"] = {
                "class_type": "IPAdapterApply",
                "inputs": {
                    "model": ["2", 0],
                    "ipadapter": ["10", 0],
                    "clip_vision": ["11", 0],
                    "image": ["1", 0],
                    "weight": 0.8,
                }
            }
            # Update KSampler to use IP-Adapter model
            workflow["6"]["inputs"]["model"] = ["12", 0]
        
        return workflow
    
    def _build_inpaint_workflow(
        self,
        image: Image.Image,
        mask: Image.Image,
        prompt: str,
        negative: str,
        denoise: float,
        style_ref: Optional[Image.Image] = None,
    ) -> Dict[str, Any]:
        """Build ComfyUI inpaint workflow"""
        
        workflow = {
            "1": {
                "class_type": "LoadImage",
                "inputs": {"image": "input_image.png"}
            },
            "2": {
                "class_type": "LoadImage",
                "inputs": {"image": "input_mask.png"}
            },
            "3": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": "animagine-xl-3.1.safetensors"}
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["3", 1]
                }
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative,
                    "clip": ["3", 1]
                }
            },
            "6": {
                "class_type": "GrowMask",
                "inputs": {
                    "mask": ["2", 1],
                    "expand": 8,
                    "tapered_corners": True
                }
            },
            "7": {
                "class_type": "FeatherMask",
                "inputs": {
                    "mask": ["6", 0],
                    "left": 16,
                    "top": 16,
                    "right": 16,
                    "bottom": 16
                }
            },
            "8": {
                "class_type": "VAEEncodeForInpaint",
                "inputs": {
                    "pixels": ["1", 0],
                    "vae": ["3", 2],
                    "mask": ["7", 0],
                    "grow_mask_by": 8
                }
            },
            "9": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["3", 0],
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "latent_image": ["8", 0],
                    "seed": -1,
                    "steps": 28,
                    "cfg": 7.5,
                    "sampler_name": "dpmpp_2m_sde",
                    "scheduler": "karras",
                    "denoise": min(denoise + 0.2, 0.95),  # Inpaint cần denoise cao hơn
                }
            },
            "10": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["9", 0],
                    "vae": ["3", 2]
                }
            },
            "11": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["10", 0],
                    "filename_prefix": "grok_inpaint"
                }
            }
        }
        
        return workflow
    
    def _build_sam_workflow(
        self,
        image: Image.Image,
        mask_prompt: str,
    ) -> Dict[str, Any]:
        """Build workflow để tạo mask bằng SAM"""
        
        workflow = {
            "1": {
                "class_type": "LoadImage",
                "inputs": {"image": "input_image.png"}
            },
            "2": {
                "class_type": "SAMModelLoader",
                "inputs": {"model_name": "sam_vit_h_4b8939.pth"}
            },
            "3": {
                "class_type": "GroundingDinoModelLoader",
                "inputs": {"model_name": "GroundingDINO_SwinT_OGC"}
            },
            "4": {
                "class_type": "GroundingDinoSAMSegment",
                "inputs": {
                    "image": ["1", 0],
                    "sam_model": ["2", 0],
                    "grounding_dino_model": ["3", 0],
                    "prompt": mask_prompt,
                    "threshold": 0.3
                }
            },
            "5": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["4", 1],  # Mask output
                    "filename_prefix": "sam_mask"
                }
            }
        }
        
        return workflow
    
    async def _execute_comfyui_workflow(
        self,
        workflow: Dict[str, Any],
    ) -> Optional[Image.Image]:
        """Execute workflow trên ComfyUI và lấy kết quả"""
        
        try:
            async with aiohttp.ClientSession() as session:
                # Queue prompt
                async with session.post(
                    f"{self.comfyui.api_url}/prompt",
                    json={"prompt": workflow},
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"ComfyUI queue failed: {await resp.text()}")
                        return None
                    
                    data = await resp.json()
                    prompt_id = data["prompt_id"]
                
                # Poll for completion
                while True:
                    async with session.get(
                        f"{self.comfyui.api_url}/history/{prompt_id}"
                    ) as resp:
                        history = await resp.json()
                        
                        if prompt_id in history:
                            outputs = history[prompt_id]["outputs"]
                            
                            # Tìm output image
                            for node_id, output in outputs.items():
                                if "images" in output:
                                    img_info = output["images"][0]
                                    
                                    # Download image
                                    async with session.get(
                                        f"{self.comfyui.api_url}/view",
                                        params={
                                            "filename": img_info["filename"],
                                            "subfolder": img_info.get("subfolder", ""),
                                            "type": img_info.get("type", "output"),
                                        }
                                    ) as img_resp:
                                        img_data = await img_resp.read()
                                        return Image.open(io.BytesIO(img_data))
                            
                            return None
                    
                    await asyncio.sleep(0.5)
        
        except Exception as e:
            logger.error(f"ComfyUI execution error: {e}")
            return None
    
    async def upload_image(
        self,
        image: Image.Image,
        filename: str = "input_image.png",
    ) -> bool:
        """Upload image to ComfyUI input folder"""
        
        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field(
                    "image",
                    buffer,
                    filename=filename,
                    content_type="image/png"
                )
                
                async with session.post(
                    f"{self.comfyui.api_url}/upload/image",
                    data=data,
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return False
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64"""
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode()


# =============================================================================
# Factory function
# =============================================================================

def create_editor(
    comfyui_host: str = "127.0.0.1",
    comfyui_port: int = 8188,
) -> GrokLikeEditor:
    """Create GrokLikeEditor instance"""
    
    config = ComfyUIConfig(host=comfyui_host, port=comfyui_port)
    return GrokLikeEditor(comfyui_config=config)
