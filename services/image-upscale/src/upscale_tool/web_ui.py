"""
Web UI for upscale tool using Gradio
"""
import gradio as gr
import numpy as np
import os
from PIL import Image
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from .multi_upscaler import MultiArchUpscaler
from .imgbb_uploader import ImgBBUploader
from .gif_upscaler import GIFUpscaler, is_gif

# Load .env file
load_dotenv()


class UpscaleWebUI:
    """Web UI for image upscaling"""
    
    def __init__(self, data_dir="./data"):
        self.upscaler = None
        self.current_model = None
        self.data_dir = Path(data_dir)
        self.input_dir = self.data_dir / "input"
        self.output_dir = self.data_dir / "output"
        
        # ImgBB uploader - get API key from .env
        imgbb_api_key = os.getenv('IMGBB_API_KEY', '77d36ef945e9beec28e41d4e746d98bb')
        self.imgbb_uploader = ImgBBUploader(api_key=imgbb_api_key)
        
        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_available_images(self):
        """Get list of available images and GIFs in input folder"""
        extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif')
        images = []
        for ext in extensions:
            images.extend(self.input_dir.glob(f'*{ext}'))
            images.extend(self.input_dir.glob(f'*{ext.upper()}'))
        return sorted([img.name for img in images])
    
    def get_upscaler(self, model_name: str, device: str):
        """Get or create upscaler"""
        if self.upscaler is None or self.current_model != model_name:
            print(f"Loading model: {model_name}")
            self.upscaler = MultiArchUpscaler(model=model_name, device=device)
            self.current_model = model_name
        return self.upscaler
    
    def load_image_from_folder(self, filename: str):
        """Load image from input folder"""
        if not filename:
            return None
        image_path = self.input_dir / filename
        if image_path.exists():
            img = Image.open(image_path)
            return np.array(img)
        return None
    
    def upscale_image_ui(
        self,
        image: np.ndarray,
        gif_file: str,
        selected_file: str,
        model_name: str,
        scale: int,
        device: str,
        tile_size: int,
        save_output: bool,
        max_gif_frames: int = 50
    ):
        """Upscale image or GIF from UI"""
        # Extract model name from annotated choice (e.g., "RealESRGAN_x4plus (Tencent - Best)" -> "RealESRGAN_x4plus")
        model_name = model_name.split(' (')[0].split(' [')[0].strip()
        
        # Check if GIF uploaded via Upload GIF tab
        gif_path = None
        if gif_file:
            # Gradio File component returns _TemporaryFileWrapper, get .name attribute
            gif_path = Path(gif_file.name) if hasattr(gif_file, 'name') else Path(gif_file)
        # Check if selected file is a GIF
        elif selected_file and selected_file != "None":
            file_path = self.input_dir / selected_file
            if is_gif(file_path):
                gif_path = file_path
            else:
                image = self.load_image_from_folder(selected_file)
                if image is None:
                    return None, "", f"❌ Error: Could not load {selected_file}", None
        
        # Handle GIF upscaling
        if gif_path:
            try:
                # Get upscaler
                upscaler = self.get_upscaler(model_name, device)
                
                # Update tile size
                if tile_size > 0 and hasattr(upscaler.upsampler, 'tile'):
                    upscaler.upsampler.tile = tile_size
                
                # Create GIF upscaler
                gif_upscaler = GIFUpscaler(upscaler)
                
                # Output path
                output_path = None
                if save_output:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"upscaled_{model_name}_{scale}x_{timestamp}.gif"
                    output_path = self.output_dir / filename
                    output_path = output_path.resolve()
                
                # Upscale GIF
                frames_text = "ALL frames" if max_gif_frames == 0 else f"max {max_gif_frames} frames"
                info = f"🎬 Processing GIF: {gif_path.name}\n"
                info += f"⚙️ Model: {model_name}\n"
                info += f"📏 Scale: {scale}x\n"
                info += f"🎞️ Processing: {frames_text}\n\n"
                info += "⏳ Upscaling frames... This may take a while...\n"
                
                # Convert 0 to None for "all frames"
                max_frames_param = None if max_gif_frames == 0 else int(max_gif_frames)
                
                output_gif = gif_upscaler.upscale_gif(
                    gif_path, 
                    scale=scale, 
                    max_frames=max_frames_param,
                    output_path=output_path
                )
                
                info += f"\n✅ GIF upscaling successful!\n"
                info += f"💾 Saved to: {output_gif}\n"
                
                # Create HTML for animated GIF preview using base64
                import base64
                with open(output_gif, 'rb') as f:
                    gif_data = base64.b64encode(f.read()).decode()
                
                gif_html = f"""
                <div style="text-align: center; padding: 20px; background: rgba(102, 126, 234, 0.05); border-radius: 12px;">
                    <h3 style="color: #667eea; margin-bottom: 15px;">🎬 Animated GIF Result</h3>
                    <img src="data:image/gif;base64,{gif_data}" 
                         style="max-width: 100%; max-height: 600px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" />
                    <p style="margin-top: 10px; color: #888; font-size: 14px;">
                        ✅ Animation is working! Click Download button to save the GIF file.
                    </p>
                </div>
                """
                
                # Return: image=None, gif_html, info, download_file
                return None, gif_html, info, str(output_gif)
                
            except Exception as e:
                import traceback
                error_msg = f"❌ Error upscaling GIF: {str(e)}\n{traceback.format_exc()}"
                return None, "", error_msg, None
        
        # Normal image upscaling
        if image is None:
            return None, "", "Please upload an image or select from folder", None
        
        try:
            # Get upscaler
            upscaler = self.get_upscaler(model_name, device)
            
            # Update tile size
            if tile_size > 0 and hasattr(upscaler.upsampler, 'tile'):
                upscaler.upsampler.tile = tile_size
            
            # Upscale
            output = upscaler.upscale_array(image, scale=scale)
            
            # Save output if requested
            output_path = None
            if save_output:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"upscaled_{model_name}_{scale}x_{timestamp}.png"
                output_path = self.output_dir / filename
                # Make absolute path
                output_path = output_path.resolve()
                Image.fromarray(output).save(output_path)
            
            # Info
            info = (
                f"✅ Upscaling successful!\n"
                f"Input size: {image.shape[1]}x{image.shape[0]}\n"
                f"Output size: {output.shape[1]}x{output.shape[0]}\n"
                f"Scale: {scale}x\n"
                f"Model: {model_name}\n"
            )
            if output_path:
                # Use absolute path or try relative, fallback to str if error
                try:
                    rel_path = output_path.relative_to(Path.cwd())
                    info += f"Saved to: {rel_path}\n"
                except ValueError:
                    info += f"Saved to: {output_path}\n"
            
            # Return: image, gif_html="", info, download_file
            return output, "", info, str(output_path) if output_path else None
            
        except Exception as e:
            import traceback
            error_msg = f"❌ Error: {str(e)}\n{traceback.format_exc()}"
            return None, "", error_msg, None
    
    def get_image_info(self, image):
        """Get image information"""
        if image is None:
            return "No image loaded"
        
        import numpy as np
        from PIL import Image
        
        if isinstance(image, np.ndarray):
            h, w = image.shape[:2]
            channels = image.shape[2] if len(image.shape) > 2 else 1
            
            # Estimate size
            if channels == 3:
                format_type = "RGB/PNG"
            elif channels == 4:
                format_type = "RGBA/PNG"
            else:
                format_type = "Grayscale"
            
            # Rough size estimate in MB
            size_mb = (w * h * channels) / (1024 * 1024)
            
            info = f"""📊 **Image Information:**
- **Dimensions**: {w} x {h} pixels
- **Format**: {format_type}
- **Size**: ~{size_mb:.2f} MB
"""
            return info
        
        return "Unable to read image info"
    
    def calculate_upscale_preview(self, image, scale):
        """Calculate what the upscaled dimensions will be"""
        if image is None:
            return "Select an image to see upscale preview"
        
        import numpy as np
        
        if isinstance(image, np.ndarray):
            h, w = image.shape[:2]
            new_h = int(h * scale)
            new_w = int(w * scale)
            channels = image.shape[2] if len(image.shape) > 2 else 1
            
            # Estimate upscaled size
            new_size_mb = (new_w * new_h * channels) / (1024 * 1024)
            
            info = f"""🔍 **Upscale Preview:**
- **Current**: {w} x {h} pixels
- **After {scale}x upscale**: {new_w} x {new_h} pixels
- **Estimated size**: ~{new_size_mb:.2f} MB
"""
            return info
        
        return ""
    
    def share_to_imgbb(self, output_path):
        """Upload image to ImgBB and get shareable link"""
        # Handle TemporaryFileWrapper from Gradio
        if hasattr(output_path, 'name'):
            output_path = output_path.name
        
        if not output_path or not os.path.exists(str(output_path)):
            return "⚠️ No output image to share. Please upscale an image first."
        
        try:
            result = self.imgbb_uploader.upload_image(output_path)
            if result:
                share_info = (
                    f"✅ Image uploaded to ImgBB!\n\n"
                    f"🔗 Direct Link: {result['url']}\n\n"
                    f"👁️ View Link: {result['display_url']}\n\n"
                    f"📊 Size: {result['width']}x{result['height']}\n\n"
                    f"🗑️ Delete Link: {result['delete_url']}\n\n"
                    f"💡 Tip: Copy the Direct Link to share your image!"
                )
                return share_info
            else:
                return "❌ Failed to upload image to ImgBB"
        except Exception as e:
            return f"❌ Error uploading to ImgBB: {str(e)}"
    
    def create_interface(self):
        """Create Gradio interface"""
        
        # Custom CSS for better styling
        custom_css = """
        .gradio-container {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
            max-width: 1400px;
            margin: auto;
        }
        .gr-button-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            border: none !important;
            font-weight: 600 !important;
            transition: transform 0.2s !important;
        }
        .gr-button-primary:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4) !important;
        }
        .gr-button-secondary {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
            border: none !important;
            font-weight: 600 !important;
        }
        .gr-button-secondary:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 12px rgba(240, 147, 251, 0.4) !important;
        }
        .gr-form {
            border: 1px solid rgba(102, 126, 234, 0.2) !important;
            border-radius: 12px !important;
            padding: 20px !important;
        }
        h1 {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        """
        
        with gr.Blocks(title="AI Image Upscaler") as interface:
            gr.Markdown(
                """
                # 🎨 AI Image Upscaler - Super Resolution
                ### 🚀 11 Models: Real-ESRGAN + SwinIR + Swin2SR + ScuNET
                """
            )
            
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 📁 Input Source")
                    
                    with gr.Tabs():
                        with gr.Tab("Upload Image"):
                            input_image = gr.Image(
                                label="Upload Image (PNG/JPG/WEBP)",
                                type="numpy"
                            )
                        
                        with gr.Tab("Upload GIF"):
                            input_gif_file = gr.File(
                                label="Upload GIF File",
                                file_types=[".gif"],
                                type="filepath"
                            )
                        
                        with gr.Tab("Select from Folder"):
                            file_dropdown = gr.Dropdown(
                                choices=["None"] + self.get_available_images(),
                                value="None",
                                label=f"📂 Select from {self.input_dir}",
                                interactive=True
                            )
                            refresh_btn = gr.Button("🔄 Refresh List", size="sm")
                            preview_image = gr.Image(
                                label="Preview",
                                type="numpy",
                                interactive=False
                            )
                    
                    # Image info display
                    input_info = gr.Markdown("📊 *Upload or select an image to see details*")
                    
                    gr.Markdown("### ⚙️ Settings")
                    
                    model_choice = gr.Dropdown(
                        choices=[
                            # Real-ESRGAN Models (RRDBNet)
                            "RealESRGAN_x4plus (Tencent - Tốt nhất cho ảnh)",
                            "RealESRGAN_x2plus (Tencent - Nhanh, x2)",
                            "RealESRGAN_x4plus_anime_6B (Tencent - Anime)",
                            "RealESRGAN_animevideov3 (Tencent - Video anime)",
                            "RealESRNet_x4plus (Tencent - Ít artifacts)",
                            "realesr-general-x4v3 (Tencent - Nhỏ gọn)",
                            "realesr-general-wdn-x4v3 (Tencent - Khử nhiễu)",
                            # Chinese Models (Swin Transformer, U-Net)
                            "SwinIR_realSR_x4 [CUHK - Chất lượng cao nhất]",
                            "Swin2SR_realSR_x4 [ETH Zurich - Nhanh hơn SwinIR]",
                            "ScuNET_GAN [CUHK - Khử nhiễu mạnh + GAN]",
                            "ScuNET_PSNR [CUHK - Ít artifacts, ảnh cũ]",
                        ],
                        value="RealESRGAN_x4plus (Tencent - Tốt nhất cho ảnh)",
                        label="🎯 Model Selection (11 models)"
                    )
                    
                    scale_slider = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=4,
                        step=1,
                        label="📏 Upscale Ratio"
                    )
                    
                    # Upscale preview
                    upscale_preview = gr.Markdown("🔍 *Adjust ratio to see output preview*")
                    
                    save_output = gr.Checkbox(
                        value=True,
                        label=f"💾 Save output to {self.output_dir}"
                    )
                    
                    with gr.Accordion("🔧 Advanced Settings", open=False):
                        device_choice = gr.Radio(
                            choices=["auto", "cuda", "cpu"],
                            value="auto",
                            label="Device"
                        )
                        
                        tile_size = gr.Slider(
                            minimum=0,
                            maximum=800,
                            value=400,
                            step=100,
                            label="Tile Size (0 for auto)"
                        )
                        
                        max_gif_frames = gr.Slider(
                            minimum=0,
                            maximum=500,
                            value=0,
                            step=10,
                            label="🎬 Max GIF Frames (0 = process all frames)"
                        )
                        
                        gr.Markdown("💡 **GIF Tips**: Set to 0 for all frames, or limit to 50-100 for faster testing")
                    
                    upscale_btn = gr.Button("🚀 Upscale Now", variant="primary", size="lg")
                
                with gr.Column(scale=1):
                    gr.Markdown("### 📤 Output")
                    
                    # Output preview (image or GIF)
                    output_image = gr.Image(
                        label="Upscaled Image (Preview)",
                        type="numpy",
                        visible=True
                    )
                    
                    # GIF preview using HTML
                    output_gif = gr.HTML(
                        label="Animated GIF Preview",
                        visible=False
                    )
                    
                    with gr.Row():
                        download_file = gr.File(
                            label="💾 Download",
                            visible=True
                        )
                        share_btn = gr.Button("🔗 Share to ImgBB", variant="secondary")
                    
                    info_text = gr.Textbox(
                        label="📋 Status",
                        lines=10,
                        max_lines=20
                    )
            
            with gr.Accordion("📖 Model Guide & Tips", open=False):
                gr.Markdown(
                    """
                    ### 🌟 Real-ESRGAN Models (7 models)
                    - **RealESRGAN_x4plus**: Best for general photos, 4x upscale
                    - **RealESRGAN_x2plus**: Faster, 2x upscale
                    - **RealESRGAN_x4plus_anime_6B**: Optimized for anime/manga
                    - **RealESRGAN_animevideov3**: Best for anime videos **& GIFs**
                    - **RealESRNet_x4plus**: Less artifacts, more natural
                    - **realesr-general-x4v3**: Small, fast model
                    - **realesr-general-wdn-x4v3**: With denoise, good for noisy images
                    
                    ### 👑 Chinese Models (4 models - NEW!)
                    - **SwinIR_realSR_x4**: Highest quality, Swin Transformer (slow, high VRAM)
                    - **Swin2SR_realSR_x4**: Swin Transformer v2, faster than SwinIR
                    - **ScuNET_GAN**: Strong denoise + upscale, for noisy/old images
                    - **ScuNET_PSNR**: Less artifacts, good for old photos
                    
                    ### 🎬 Animated GIF Support (NEW!)
                    - **Select GIF** from folder dropdown (GIF files now visible!)
                    - **Upload tab** also works for GIFs
                    - Each frame upscaled individually with consistent quality
                    - **Max GIF Frames slider**:
                      - `0` = Process ALL frames (recommended)
                      - `50-100` = Limit for quick testing
                      - `200+` = For very long GIFs
                    - Recommended models: 
                      - 🥇 **RealESRGAN_animevideov3** - Best for anime GIFs
                      - 🥈 **RealESRGAN_x4plus_anime_6B** - Anime/manga style
                      - 🥉 **RealESRGAN_x4plus** - General purpose
                    - ⏱️ Processing time: ~1-3 seconds per frame (GPU)
                    - 📦 Output format: Animated GIF with original timing
                    
                    ### 💡 Tips
                    - **Images**: Upload or select from `data/input/` folder
                    - **GIFs**: Upload OR select from `data/input/` (both work!)
                    - Outputs auto-saved to `data/output/` folder
                    - Use Share button to get ImgBB public link
                    - Chinese models need more VRAM (6GB+ recommended)
                    - Reduce tile size if you get CUDA out of memory error
                    - **For GIFs**: Start with max_frames=0 to process all, or limit to 10-20 for testing
                    """
                )
            
            # Event handlers
            
            # Update image info when image changes
            input_image.change(
                fn=self.get_image_info,
                inputs=input_image,
                outputs=input_info
            )
            
            preview_image.change(
                fn=self.get_image_info,
                inputs=preview_image,
                outputs=input_info
            )
            
            # Update upscale preview when scale changes
            def update_preview_wrapper(image, preview, scale):
                img = image if image is not None else preview
                return self.calculate_upscale_preview(img, scale)
            
            scale_slider.change(
                fn=update_preview_wrapper,
                inputs=[input_image, preview_image, scale_slider],
                outputs=upscale_preview
            )
            
            input_image.change(
                fn=update_preview_wrapper,
                inputs=[input_image, preview_image, scale_slider],
                outputs=upscale_preview
            )
            
            preview_image.change(
                fn=update_preview_wrapper,
                inputs=[input_image, preview_image, scale_slider],
                outputs=upscale_preview
            )
            
            # Refresh file list
            refresh_btn.click(
                fn=lambda: gr.Dropdown.update(choices=["None"] + self.get_available_images()),
                outputs=file_dropdown
            )
            
            # Preview selected file
            file_dropdown.change(
                fn=self.load_image_from_folder,
                inputs=file_dropdown,
                outputs=preview_image
            )
            
            # Upscale button
            upscale_btn.click(
                fn=self.upscale_image_ui,
                inputs=[
                    input_image,
                    input_gif_file,
                    file_dropdown,
                    model_choice,
                    scale_slider,
                    device_choice,
                    tile_size,
                    save_output,
                    max_gif_frames
                ],
                outputs=[output_image, output_gif, info_text, download_file]
            )
            
            # Share button
            share_btn.click(
                fn=self.share_to_imgbb,
                inputs=download_file,
                outputs=info_text
            )
        
        # Store custom_css as interface attribute for later use
        interface.custom_css = custom_css
        interface.custom_theme = gr.themes.Soft()
        
        return interface


def launch_ui(share=False, server_port=7861, debug=False):
    """Launch web UI"""
    ui = UpscaleWebUI()
    interface = ui.create_interface()
    
    print(f"""
    ╔════════════════════════════════════════════════════════════╗
    ║          🎨 AI Image Upscaler - Super Resolution          ║
    ║                                                            ║
    ║  🌐 URL: http://127.0.0.1:{server_port}                          ║
    ║  🔄 Hot Reload: {'Enabled - Press Ctrl+Shift+R to refresh UI' if debug else 'Disabled'}        ║
    ║                                                            ║
    ║  💡 Features:                                              ║
    ║     ✓ 11 AI Models (7 Real-ESRGAN + 4 Chinese)            ║
    ║     ✓ Auto image info & upscale preview                   ║
    ║     ✓ ImgBB sharing with retry                            ║
    ║     ✓ CUDA GPU acceleration                               ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    interface.launch(
        share=share, 
        server_port=server_port,
        show_error=True,
        inbrowser=True
    )


if __name__ == '__main__':
    # Enable debug mode for development
    import sys
    debug = '--debug' in sys.argv
    launch_ui(debug=debug)
