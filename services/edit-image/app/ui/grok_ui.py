"""
Gradio UI cho Grok-like Anime Edit
==================================

UI đơn giản:
1. Upload ảnh
2. Nhập text tự nhiên
3. Nhấn Edit
4. Nhận kết quả
"""

import os
import io
import logging
from pathlib import Path
from typing import Optional, Tuple

import gradio as gr
from PIL import Image

from app.core.grok_editor import GrokLikeEditor, ComfyUIConfig

logger = logging.getLogger(__name__)

# Global editor
_editor: Optional[GrokLikeEditor] = None


def get_editor() -> GrokLikeEditor:
    """Get or create editor"""
    global _editor
    if _editor is None:
        _editor = GrokLikeEditor(
            comfyui_config=ComfyUIConfig(
                host="127.0.0.1",
                port=8188,
            )
        )
    return _editor


async def edit_image(
    image: Image.Image,
    instruction: str,
    style_image: Optional[Image.Image] = None,
) -> Tuple[Image.Image, str]:
    """
    Edit ảnh với text tự nhiên
    
    Returns:
        (result_image, status_message)
    """
    if image is None:
        return None, "❌ Vui lòng upload ảnh!"
    
    if not instruction or not instruction.strip():
        return None, "❌ Vui lòng nhập instruction!"
    
    try:
        editor = get_editor()
        
        # Upload images to ComfyUI
        await editor.upload_image(image, "input_image.png")
        if style_image is not None:
            await editor.upload_image(style_image, "style_image.png")
        
        # Edit
        result = await editor.edit(
            image=image,
            instruction=instruction.strip(),
            style_reference=style_image,
        )
        
        return result, f"✅ Thành công! Instruction: {instruction}"
    
    except Exception as e:
        logger.exception("Edit failed")
        return None, f"❌ Lỗi: {str(e)}"


def create_grok_ui() -> gr.Blocks:
    """Create Gradio UI"""
    
    with gr.Blocks(
        title="Grok-like Anime Edit",
        theme=gr.themes.Soft(
            primary_hue="purple",
            secondary_hue="pink",
        ),
        css="""
        .main-title {
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 1rem;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 2rem;
        }
        """
    ) as ui:
        gr.HTML("<h1 class='main-title'>🎨 Grok-like Anime Edit</h1>")
        gr.HTML("<p class='subtitle'>Nhập text tự nhiên để edit ảnh - Không cần prompt phức tạp!</p>")
        
        with gr.Row():
            # Left column - Input
            with gr.Column(scale=1):
                input_image = gr.Image(
                    label="📷 Upload ảnh cần edit",
                    type="pil",
                    height=400,
                )
                
                instruction = gr.Textbox(
                    label="✏️ Nhập instruction (text tự nhiên)",
                    placeholder="VD: đổi tóc màu xanh, thêm cat ears, làm cho cô ấy cười...",
                    lines=3,
                )
                
                with gr.Accordion("🎨 Style Reference (Optional)", open=False):
                    style_image = gr.Image(
                        label="Upload ảnh style",
                        type="pil",
                        height=200,
                    )
                    gr.Markdown("*Upload ảnh để học style, màu sắc, nét vẽ*")
                
                edit_btn = gr.Button(
                    "🚀 Edit Image",
                    variant="primary",
                    size="lg",
                )
            
            # Right column - Output
            with gr.Column(scale=1):
                output_image = gr.Image(
                    label="🖼️ Kết quả",
                    type="pil",
                    height=400,
                )
                
                status = gr.Textbox(
                    label="📊 Status",
                    interactive=False,
                )
        
        # Examples
        gr.Markdown("### 💡 Ví dụ Instructions")
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("""
                **🎀 Hair:**
                - đổi màu tóc sang xanh lá
                - làm tóc dài hơn
                - thêm twintails
                
                **😊 Face:**
                - làm cho cô ấy cười
                - đổi màu mắt sang đỏ
                - thêm blush
                """)
            
            with gr.Column():
                gr.Markdown("""
                **👗 Clothing:**
                - đổi sang school uniform
                - mặc maid outfit
                - thêm ribbon
                
                **🌸 Background:**
                - đổi background thành bãi biển
                - thêm hoa anh đào
                """)
            
            with gr.Column():
                gr.Markdown("""
                **✨ Add/Remove:**
                - thêm cat ears
                - thêm cánh thiên thần
                - xóa kính
                
                **🔥 NSFW:**
                - bỏ quần áo
                - đổi sang bikini
                - lingerie
                """)
        
        # Event handlers
        edit_btn.click(
            fn=edit_image,
            inputs=[input_image, instruction, style_image],
            outputs=[output_image, status],
        )
        
        # Quick example buttons
        gr.Markdown("### ⚡ Quick Examples")
        
        with gr.Row():
            btn1 = gr.Button("🔵 Tóc xanh")
            btn2 = gr.Button("😺 Cat ears")
            btn3 = gr.Button("😊 Smile")
            btn4 = gr.Button("👙 Bikini")
            btn5 = gr.Button("🌸 Sakura BG")
        
        btn1.click(lambda: "đổi màu tóc sang xanh lá", outputs=instruction)
        btn2.click(lambda: "thêm cat ears và cat tail", outputs=instruction)
        btn3.click(lambda: "làm cho cô ấy cười tươi", outputs=instruction)
        btn4.click(lambda: "đổi trang phục sang bikini", outputs=instruction)
        btn5.click(lambda: "đổi background thành hoa anh đào đang rơi", outputs=instruction)
    
    return ui


def launch_standalone(port: int = 7860):
    """Launch as standalone Gradio app"""
    ui = create_grok_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=False,
    )


if __name__ == "__main__":
    launch_standalone()
