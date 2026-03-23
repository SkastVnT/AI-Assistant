"""
Grok-like Edit API Routes
=========================

REST API cho edit ảnh với text tự nhiên
"""

import io
import base64
import logging
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from PIL import Image

from app.core.grok_editor import GrokLikeEditor, ComfyUIConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/grok", tags=["Grok-like Edit"])


# =============================================================================
# Schemas
# =============================================================================

class EditRequest(BaseModel):
    """Request body cho edit với base64 image"""
    image: str  # base64
    instruction: str
    style_image: Optional[str] = None  # base64, optional


class EditResponse(BaseModel):
    """Response với base64 result"""
    success: bool
    image: Optional[str] = None  # base64
    error: Optional[str] = None


# =============================================================================
# Global editor instance
# =============================================================================

_editor: Optional[GrokLikeEditor] = None


def get_editor() -> GrokLikeEditor:
    """Get or create editor instance"""
    global _editor
    
    if _editor is None:
        _editor = GrokLikeEditor(
            comfyui_config=ComfyUIConfig(
                host="127.0.0.1",
                port=8188
            )
        )
    
    return _editor


# =============================================================================
# Routes
# =============================================================================

@router.post("/edit", response_model=EditResponse)
async def edit_image(request: EditRequest):
    """
    Edit ảnh với text tự nhiên (giống Grok)
    
    - **image**: Base64 encoded image
    - **instruction**: Text tự nhiên (VD: "đổi tóc màu xanh", "thêm neko mimi", ...)
    - **style_image**: Base64 style reference (optional)
    
    Returns:
        Base64 edited image
    
    Examples:
        - "đổi màu tóc sang xanh lá"
        - "thêm cat ears"
        - "làm cho cô ấy cười"
        - "thay đổi background thành bãi biển"
        - "vẽ lại theo style anime moe"
    """
    try:
        editor = get_editor()
        
        # Decode input image
        try:
            img_data = base64.b64decode(request.image)
            image = Image.open(io.BytesIO(img_data)).convert("RGB")
        except Exception as e:
            raise HTTPException(400, f"Invalid image data: {e}")
        
        # Decode style reference if provided
        style_ref = None
        if request.style_image:
            try:
                style_data = base64.b64decode(request.style_image)
                style_ref = Image.open(io.BytesIO(style_data)).convert("RGB")
            except:
                pass  # Ignore invalid style image
        
        # Upload to ComfyUI
        await editor.upload_image(image, "input_image.png")
        if style_ref:
            await editor.upload_image(style_ref, "style_image.png")
        
        # Edit
        result = await editor.edit(
            image=image,
            instruction=request.instruction,
            style_reference=style_ref,
        )
        
        # Encode result
        buffer = io.BytesIO()
        result.save(buffer, format="PNG")
        result_b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return EditResponse(
            success=True,
            image=result_b64,
        )
    
    except Exception as e:
        logger.exception("Edit failed")
        return EditResponse(
            success=False,
            error=str(e),
        )


@router.post("/edit/upload")
async def edit_image_upload(
    image: UploadFile = File(..., description="Ảnh cần edit"),
    instruction: str = Form(..., description="Text tự nhiên"),
    style_image: Optional[UploadFile] = File(None, description="Ảnh style reference"),
):
    """
    Edit ảnh với file upload (multipart/form-data)
    
    - **image**: File ảnh cần edit
    - **instruction**: Text tự nhiên
    - **style_image**: File ảnh style (optional)
    
    Returns:
        PNG image stream
    """
    try:
        editor = get_editor()
        
        # Read input image
        img_data = await image.read()
        input_img = Image.open(io.BytesIO(img_data)).convert("RGB")
        
        # Read style reference
        style_ref = None
        if style_image:
            style_data = await style_image.read()
            style_ref = Image.open(io.BytesIO(style_data)).convert("RGB")
        
        # Upload to ComfyUI
        await editor.upload_image(input_img, "input_image.png")
        if style_ref:
            await editor.upload_image(style_ref, "style_image.png")
        
        # Edit
        result = await editor.edit(
            image=input_img,
            instruction=instruction,
            style_reference=style_ref,
        )
        
        # Return as stream
        buffer = io.BytesIO()
        result.save(buffer, format="PNG")
        buffer.seek(0)
        
        return StreamingResponse(
            buffer,
            media_type="image/png",
            headers={
                "Content-Disposition": "attachment; filename=edited.png"
            }
        )
    
    except Exception as e:
        logger.exception("Edit failed")
        raise HTTPException(500, str(e))


@router.get("/health")
async def health_check():
    """Check service health"""
    import aiohttp
    
    editor = get_editor()
    
    # Check ComfyUI
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{editor.comfyui.api_url}/system_stats",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                comfyui_ok = resp.status == 200
                if comfyui_ok:
                    stats = await resp.json()
    except:
        comfyui_ok = False
        stats = None
    
    return {
        "status": "ok" if comfyui_ok else "degraded",
        "comfyui": {
            "connected": comfyui_ok,
            "url": editor.comfyui.api_url,
            "stats": stats,
        },
        "llm_backend": editor.llm_backend,
    }


@router.get("/examples")
async def get_examples():
    """Các ví dụ instruction"""
    return {
        "examples": [
            {
                "category": "Hair",
                "instructions": [
                    "đổi màu tóc sang xanh lá",
                    "làm tóc dài hơn",
                    "thêm twintails",
                    "đổi kiểu tóc bob cut",
                ]
            },
            {
                "category": "Face",
                "instructions": [
                    "làm cho cô ấy cười",
                    "thay đổi biểu cảm sang buồn",
                    "đổi màu mắt sang đỏ",
                    "thêm blush",
                ]
            },
            {
                "category": "Clothing",
                "instructions": [
                    "thay đổi trang phục sang school uniform",
                    "mặc áo màu trắng",
                    "thêm ribbon trên tóc",
                    "đổi sang maid outfit",
                ]
            },
            {
                "category": "Background",
                "instructions": [
                    "đổi background thành bãi biển",
                    "thêm hoa anh đào phía sau",
                    "làm background tối hơn",
                    "đổi sang phong cảnh thành phố",
                ]
            },
            {
                "category": "Style",
                "instructions": [
                    "vẽ lại theo style anime moe",
                    "làm cho nét vẽ mềm hơn",
                    "thêm hiệu ứng ánh sáng",
                    "đổi sang style pixel art",
                ]
            },
            {
                "category": "Add/Remove",
                "instructions": [
                    "thêm cat ears",
                    "thêm cánh thiên thần",
                    "xóa kính",
                    "thêm halo",
                ]
            },
            {
                "category": "NSFW",
                "instructions": [
                    "bỏ quần áo",
                    "thêm lingerie",
                    "đổi sang bikini",
                    "làm trang phục sexy hơn",
                ]
            }
        ]
    }
