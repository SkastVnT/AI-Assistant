"""
Gradio Web Interface for Edit Image Service.
Provides an interactive UI for image generation and editing.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple, List
import time

import gradio as gr
from PIL import Image

from ..core.pipeline import get_pipeline_manager, PipelineManager
from ..core.config import get_settings, Settings


logger = logging.getLogger(__name__)


# ==============================================================================
# UI Components
# ==============================================================================

def create_txt2img_tab(manager: PipelineManager, settings: Settings) -> gr.Tab:
    """Create Text-to-Image generation tab."""
    
    with gr.Tab("Text to Image") as tab:
        with gr.Row():
            with gr.Column(scale=1):
                prompt = gr.Textbox(
                    label="Prompt",
                    placeholder="Describe the image you want to generate...",
                    lines=3,
                )
                negative_prompt = gr.Textbox(
                    label="Negative Prompt",
                    placeholder="What to avoid...",
                    lines=2,
                    value="low quality, blurry, distorted, ugly, bad anatomy",
                )
                
                with gr.Row():
                    model = gr.Dropdown(
                        label="Model",
                        choices=list(settings.models.base_models.keys()),
                        value=settings.models.default,
                    )
                
                with gr.Row():
                    width = gr.Slider(256, 2048, value=1024, step=64, label="Width")
                    height = gr.Slider(256, 2048, value=1024, step=64, label="Height")
                
                with gr.Row():
                    steps = gr.Slider(1, 150, value=30, step=1, label="Steps")
                    cfg = gr.Slider(1.0, 20.0, value=7.5, step=0.5, label="CFG Scale")
                
                seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                
                generate_btn = gr.Button("Generate", variant="primary")
            
            with gr.Column(scale=1):
                output_image = gr.Image(label="Generated Image", type="pil")
                generation_info = gr.Textbox(label="Info", lines=2)
        
        def generate(prompt, negative_prompt, model, width, height, steps, cfg, seed):
            try:
                start = time.time()
                actual_seed = None if seed == -1 else int(seed)
                
                image = manager.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model_name=model,
                    width=int(width),
                    height=int(height),
                    num_inference_steps=int(steps),
                    guidance_scale=cfg,
                    seed=actual_seed,
                )
                
                elapsed = time.time() - start
                info = f"Model: {model}\nTime: {elapsed:.2f}s | Seed: {actual_seed}"
                return image, info
                
            except Exception as e:
                logger.error(f"Generation error: {e}", exc_info=True)
                return None, f"Error: {str(e)}"
        
        generate_btn.click(
            generate,
            inputs=[prompt, negative_prompt, model, width, height, steps, cfg, seed],
            outputs=[output_image, generation_info],
        )
    
    return tab


def create_img2img_tab(manager: PipelineManager, settings: Settings) -> gr.Tab:
    """Create Image-to-Image tab."""
    
    with gr.Tab("Image to Image") as tab:
        with gr.Row():
            with gr.Column(scale=1):
                input_image = gr.Image(label="Input Image", type="pil")
                
                prompt = gr.Textbox(
                    label="Prompt",
                    placeholder="Describe how to transform the image...",
                    lines=3,
                )
                negative_prompt = gr.Textbox(
                    label="Negative Prompt",
                    lines=2,
                    value="low quality, blurry, distorted",
                )
                
                model = gr.Dropdown(
                    label="Model",
                    choices=list(settings.models.base_models.keys()),
                    value=settings.models.default,
                )
                
                strength = gr.Slider(0.0, 1.0, value=0.75, step=0.05, label="Strength")
                
                with gr.Row():
                    steps = gr.Slider(1, 150, value=30, step=1, label="Steps")
                    cfg = gr.Slider(1.0, 20.0, value=7.5, step=0.5, label="CFG Scale")
                
                seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                
                transform_btn = gr.Button("Transform", variant="primary")
            
            with gr.Column(scale=1):
                output_image = gr.Image(label="Output Image", type="pil")
                generation_info = gr.Textbox(label="Info", lines=2)
        
        def transform(input_img, prompt, negative_prompt, model, strength, steps, cfg, seed):
            if input_img is None:
                return None, "Please upload an input image"
            
            try:
                start = time.time()
                actual_seed = None if seed == -1 else int(seed)
                
                image = manager.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model_name=model,
                    image=input_img,
                    strength=strength,
                    num_inference_steps=int(steps),
                    guidance_scale=cfg,
                    seed=actual_seed,
                )
                
                elapsed = time.time() - start
                info = f"Model: {model}\nTime: {elapsed:.2f}s | Strength: {strength}"
                return image, info
                
            except Exception as e:
                logger.error(f"Img2Img error: {e}", exc_info=True)
                return None, f"Error: {str(e)}"
        
        transform_btn.click(
            transform,
            inputs=[input_image, prompt, negative_prompt, model, strength, steps, cfg, seed],
            outputs=[output_image, generation_info],
        )
    
    return tab


def create_edit_tab(manager: PipelineManager, settings: Settings) -> gr.Tab:
    """Create Edit (InstructPix2Pix) tab."""
    
    with gr.Tab("Edit Image") as tab:
        gr.Markdown("""
        ### Edit images with natural language instructions
        Upload an image and describe the changes you want to make.
        
        **Examples:**
        - "Make the sky look like sunset"
        - "Add sunglasses to the person"
        - "Turn it into a watercolor painting"
        - "Make the person smile"
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                input_image = gr.Image(label="Input Image", type="pil")
                
                instruction = gr.Textbox(
                    label="Edit Instruction",
                    placeholder="Describe what changes to make...",
                    lines=2,
                )
                
                with gr.Row():
                    steps = gr.Slider(1, 150, value=50, step=1, label="Steps")
                    cfg = gr.Slider(1.0, 20.0, value=7.5, step=0.5, label="Text CFG")
                
                image_cfg = gr.Slider(1.0, 5.0, value=1.5, step=0.1, label="Image CFG")
                seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                
                edit_btn = gr.Button("Edit", variant="primary")
            
            with gr.Column(scale=1):
                output_image = gr.Image(label="Edited Image", type="pil")
                generation_info = gr.Textbox(label="Info", lines=2)
        
        def edit(input_img, instruction, steps, cfg, image_cfg, seed):
            if input_img is None:
                return None, "Please upload an input image"
            if not instruction.strip():
                return None, "Please enter an edit instruction"
            
            try:
                start = time.time()
                actual_seed = None if seed == -1 else int(seed)
                
                image = manager.edit_with_instructions(
                    image=input_img,
                    instruction=instruction,
                    num_inference_steps=int(steps),
                    guidance_scale=cfg,
                    image_guidance_scale=image_cfg,
                    seed=actual_seed,
                )
                
                elapsed = time.time() - start
                info = f"Time: {elapsed:.2f}s | Instruction: {instruction[:50]}..."
                return image, info
                
            except Exception as e:
                logger.error(f"Edit error: {e}", exc_info=True)
                return None, f"Error: {str(e)}"
        
        edit_btn.click(
            edit,
            inputs=[input_image, instruction, steps, cfg, image_cfg, seed],
            outputs=[output_image, generation_info],
        )
    
    return tab


def create_inpaint_tab(manager: PipelineManager, settings: Settings) -> gr.Tab:
    """Create Inpainting tab."""
    
    with gr.Tab("Inpaint") as tab:
        gr.Markdown("""
        ### Inpainting - Fill in parts of an image
        Use the brush tool to mark the area you want to regenerate.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                input_image = gr.ImageEditor(
                    label="Draw mask on image (white = area to regenerate)",
                    type="pil",
                    brush=gr.Brush(colors=["#FFFFFF"], default_size=50),
                )
                
                prompt = gr.Textbox(
                    label="Prompt",
                    placeholder="Describe what should appear in the masked area...",
                    lines=2,
                )
                negative_prompt = gr.Textbox(
                    label="Negative Prompt",
                    lines=2,
                    value="low quality, blurry",
                )
                
                model = gr.Dropdown(
                    label="Model",
                    choices=list(settings.models.base_models.keys()),
                    value=settings.models.default,
                )
                
                strength = gr.Slider(0.0, 1.0, value=0.85, step=0.05, label="Strength")
                
                with gr.Row():
                    steps = gr.Slider(1, 150, value=30, step=1, label="Steps")
                    cfg = gr.Slider(1.0, 20.0, value=7.5, step=0.5, label="CFG Scale")
                
                seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                
                inpaint_btn = gr.Button("Inpaint", variant="primary")
            
            with gr.Column(scale=1):
                output_image = gr.Image(label="Output Image", type="pil")
                generation_info = gr.Textbox(label="Info", lines=2)
        
        def inpaint(editor_data, prompt, negative_prompt, model, strength, steps, cfg, seed):
            if editor_data is None:
                return None, "Please upload an image and draw a mask"
            
            try:
                # Extract image and mask from editor
                if isinstance(editor_data, dict):
                    input_img = editor_data.get("background")
                    mask_layers = editor_data.get("layers", [])
                    if mask_layers and len(mask_layers) > 0:
                        mask_img = mask_layers[0]
                    else:
                        return None, "Please draw a mask on the image"
                else:
                    return None, "Invalid editor data format"
                
                start = time.time()
                actual_seed = None if seed == -1 else int(seed)
                
                image = manager.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model_name=model,
                    image=input_img,
                    mask=mask_img,
                    strength=strength,
                    num_inference_steps=int(steps),
                    guidance_scale=cfg,
                    seed=actual_seed,
                )
                
                elapsed = time.time() - start
                info = f"Model: {model}\nTime: {elapsed:.2f}s"
                return image, info
                
            except Exception as e:
                logger.error(f"Inpaint error: {e}", exc_info=True)
                return None, f"Error: {str(e)}"
        
        inpaint_btn.click(
            inpaint,
            inputs=[input_image, prompt, negative_prompt, model, strength, steps, cfg, seed],
            outputs=[output_image, generation_info],
        )
    
    return tab


def create_controlnet_tab(manager: PipelineManager, settings: Settings) -> gr.Tab:
    """Create ControlNet tab."""
    
    controlnet_types = list(settings.controlnet.models.keys())
    
    with gr.Tab("ControlNet") as tab:
        gr.Markdown("""
        ### ControlNet - Guided image generation
        Upload a condition image (edge map, pose, depth, etc.) to guide generation.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                condition_image = gr.Image(label="Condition Image", type="pil")
                
                controlnet_type = gr.Dropdown(
                    label="ControlNet Type",
                    choices=controlnet_types,
                    value=controlnet_types[0] if controlnet_types else None,
                )
                
                prompt = gr.Textbox(
                    label="Prompt",
                    placeholder="Describe the image to generate...",
                    lines=3,
                )
                negative_prompt = gr.Textbox(
                    label="Negative Prompt",
                    lines=2,
                    value="low quality, blurry, distorted",
                )
                
                model = gr.Dropdown(
                    label="Base Model",
                    choices=list(settings.models.base_models.keys()),
                    value=settings.models.default,
                )
                
                control_scale = gr.Slider(
                    0.0, 2.0, value=1.0, step=0.1,
                    label="ControlNet Scale"
                )
                
                with gr.Row():
                    steps = gr.Slider(1, 150, value=30, step=1, label="Steps")
                    cfg = gr.Slider(1.0, 20.0, value=7.5, step=0.5, label="CFG Scale")
                
                seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                
                generate_btn = gr.Button("Generate", variant="primary")
            
            with gr.Column(scale=1):
                output_image = gr.Image(label="Generated Image", type="pil")
                generation_info = gr.Textbox(label="Info", lines=2)
        
        def generate_with_controlnet(
            condition_img, controlnet_type, prompt, negative_prompt,
            model, control_scale, steps, cfg, seed
        ):
            if condition_img is None:
                return None, "Please upload a condition image"
            
            try:
                start = time.time()
                actual_seed = None if seed == -1 else int(seed)
                
                image = manager.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model_name=model,
                    controlnet=controlnet_type,
                    controlnet_image=condition_img,
                    controlnet_conditioning_scale=control_scale,
                    num_inference_steps=int(steps),
                    guidance_scale=cfg,
                    seed=actual_seed,
                )
                
                elapsed = time.time() - start
                info = f"Model: {model} + {controlnet_type}\nTime: {elapsed:.2f}s"
                return image, info
                
            except Exception as e:
                logger.error(f"ControlNet error: {e}", exc_info=True)
                return None, f"Error: {str(e)}"
        
        generate_btn.click(
            generate_with_controlnet,
            inputs=[
                condition_image, controlnet_type, prompt, negative_prompt,
                model, control_scale, steps, cfg, seed
            ],
            outputs=[output_image, generation_info],
        )
    
    return tab


def create_anime_tab(manager: PipelineManager, settings: Settings) -> gr.Tab:
    """Create Anime generation tab with specialized settings."""
    
    anime_models = ["animagine", "anything_v5"]
    available_anime = [m for m in anime_models if m in settings.models.base_models]
    
    with gr.Tab("Anime") as tab:
        gr.Markdown("""
        ### Anime / Manga Style Generation
        Optimized settings for anime-style image generation using specialized models.
        
        **Tips:**
        - Use Danbooru-style tags for better results: `1girl, solo, long_hair, blue_eyes`
        - Add quality tags: `masterpiece, best quality, detailed`
        - Specify art style: `anime style, manga style, illustration`
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                prompt = gr.Textbox(
                    label="Prompt (Danbooru tags recommended)",
                    placeholder="1girl, solo, long_hair, blue_eyes, school_uniform, smile, masterpiece, best quality",
                    lines=4,
                )
                negative_prompt = gr.Textbox(
                    label="Negative Prompt",
                    lines=2,
                    value="lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry",
                )
                
                model = gr.Dropdown(
                    label="Anime Model",
                    choices=available_anime if available_anime else ["animagine"],
                    value=available_anime[0] if available_anime else "animagine",
                )
                
                with gr.Row():
                    width = gr.Slider(256, 2048, value=832, step=64, label="Width")
                    height = gr.Slider(256, 2048, value=1216, step=64, label="Height")
                
                gr.Markdown("*Recommended: 832x1216 (portrait) or 1216x832 (landscape)*")
                
                with gr.Row():
                    steps = gr.Slider(1, 150, value=28, step=1, label="Steps")
                    cfg = gr.Slider(1.0, 20.0, value=7.0, step=0.5, label="CFG Scale")
                
                seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                
                generate_btn = gr.Button("Generate Anime", variant="primary")
            
            with gr.Column(scale=1):
                output_image = gr.Image(label="Generated Image", type="pil")
                generation_info = gr.Textbox(label="Info", lines=2)
        
        def generate_anime(prompt, negative_prompt, model, width, height, steps, cfg, seed):
            try:
                start = time.time()
                actual_seed = None if seed == -1 else int(seed)
                
                image = manager.generate(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model_name=model,
                    width=int(width),
                    height=int(height),
                    num_inference_steps=int(steps),
                    guidance_scale=cfg,
                    seed=actual_seed,
                )
                
                elapsed = time.time() - start
                info = f"Model: {model}\nTime: {elapsed:.2f}s | Size: {width}x{height}"
                return image, info
                
            except Exception as e:
                logger.error(f"Anime generation error: {e}", exc_info=True)
                return None, f"Error: {str(e)}"
        
        generate_btn.click(
            generate_anime,
            inputs=[prompt, negative_prompt, model, width, height, steps, cfg, seed],
            outputs=[output_image, generation_info],
        )
    
    return tab


def create_search_tab(settings: Settings) -> gr.Tab:
    """Create Character/Reference Search tab."""
    
    with gr.Tab("🔍 Search") as tab:
        gr.Markdown("""
        ### Character & Reference Search
        Search for anime characters and reference images across multiple sources.
        Use found references to enhance your prompts!
        """)
        
        with gr.Tabs():
            # Character Search Tab
            with gr.Tab("Character Search"):
                with gr.Row():
                    with gr.Column(scale=1):
                        char_name = gr.Textbox(
                            label="Character Name",
                            placeholder="e.g., Rem, Hatsune Miku, Anya Forger",
                        )
                        series_name = gr.Textbox(
                            label="Series/Anime (optional)",
                            placeholder="e.g., Re:Zero, Vocaloid, Spy x Family",
                        )
                        include_tags = gr.Checkbox(
                            label="Include appearance tags",
                            value=True,
                        )
                        
                        search_char_btn = gr.Button("Search Character", variant="primary")
                    
                    with gr.Column(scale=2):
                        char_results = gr.JSON(label="Character Info")
                        suggested_prompt = gr.Textbox(
                            label="Suggested Prompt",
                            lines=3,
                            interactive=False,
                        )
                        copy_prompt_btn = gr.Button("Copy to Clipboard")
                
                async def search_character(name, series, include_tags):
                    if not name.strip():
                        return {}, "Please enter a character name"
                    
                    try:
                        from ..core.search import WebSearchManager
                        
                        search_manager = WebSearchManager()
                        characters = []
                        
                        # Search AniList
                        try:
                            anilist_results = await search_manager.anilist.search_character(name)
                            for char in anilist_results[:3]:
                                char_info = {
                                    "name": char.get("name", {}).get("full", name),
                                    "series": char.get("media", {}).get("nodes", [{}])[0].get("title", {}).get("english") if char.get("media", {}).get("nodes") else None,
                                    "image": char.get("image", {}).get("large"),
                                }
                                characters.append(char_info)
                        except Exception:
                            pass
                        
                        # Generate prompt
                        prompt_parts = [name]
                        if series:
                            prompt_parts.append(f"({series})")
                        prompt_parts.append("solo, masterpiece, best quality, highres")
                        
                        # Try to get appearance tags from Danbooru
                        if include_tags:
                            try:
                                char_tag = name.lower().replace(" ", "_")
                                results = await search_manager.danbooru.search_posts(
                                    tags=f"{char_tag} solo",
                                    limit=10,
                                    rating="general"
                                )
                                all_tags = []
                                for r in results:
                                    tags = r.get("tag_string", "").split()[:20]
                                    all_tags.extend(tags)
                                
                                from collections import Counter
                                tag_counts = Counter(all_tags)
                                appearance_tags = [
                                    tag for tag, count in tag_counts.most_common(10)
                                    if count >= 2 and tag not in ["solo", "1girl", "1boy", char_tag]
                                ]
                                if appearance_tags:
                                    prompt_parts.append(", ".join(appearance_tags[:8]))
                            except Exception:
                                pass
                        
                        suggested = ", ".join(prompt_parts)
                        
                        return {"characters": characters}, suggested
                        
                    except Exception as e:
                        return {"error": str(e)}, ""
                
                search_char_btn.click(
                    search_character,
                    inputs=[char_name, series_name, include_tags],
                    outputs=[char_results, suggested_prompt],
                )
            
            # Reference Image Search Tab
            with gr.Tab("Reference Images"):
                with gr.Row():
                    with gr.Column(scale=1):
                        search_query = gr.Textbox(
                            label="Search Tags",
                            placeholder="e.g., 1girl long_hair blue_eyes school_uniform",
                            lines=2,
                        )
                        
                        with gr.Row():
                            source_danbooru = gr.Checkbox(label="Danbooru", value=True)
                            source_gelbooru = gr.Checkbox(label="Gelbooru", value=True)
                        
                        rating_filter = gr.Dropdown(
                            label="Rating",
                            choices=["general", "sensitive", "explicit"],
                            value="general",
                        )
                        
                        max_results = gr.Slider(5, 50, value=20, step=5, label="Max Results")
                        
                        search_ref_btn = gr.Button("Search References", variant="primary")
                    
                    with gr.Column(scale=2):
                        ref_gallery = gr.Gallery(
                            label="Reference Images",
                            columns=4,
                            height=400,
                        )
                        ref_info = gr.JSON(label="Search Results Info")
                
                async def search_references(query, danbooru, gelbooru, rating, limit):
                    if not query.strip():
                        return [], {"error": "Please enter search tags"}
                    
                    try:
                        from ..core.search import WebSearchManager
                        
                        search_manager = WebSearchManager()
                        images = []
                        results_info = {"sources": [], "total": 0}
                        
                        sources = []
                        if danbooru:
                            sources.append("danbooru")
                        if gelbooru:
                            sources.append("gelbooru")
                        
                        for source in sources:
                            try:
                                if source == "danbooru":
                                    results = await search_manager.danbooru.search_posts(
                                        tags=query,
                                        limit=limit // len(sources),
                                        rating=rating
                                    )
                                elif source == "gelbooru":
                                    results = await search_manager.gelbooru.search_posts(
                                        tags=query,
                                        limit=limit // len(sources),
                                        rating=rating
                                    )
                                else:
                                    continue
                                
                                for r in results:
                                    preview = r.get("preview_file_url", r.get("preview_url", ""))
                                    full = r.get("file_url", r.get("large_file_url", ""))
                                    if preview or full:
                                        images.append(preview or full)
                                
                                results_info["sources"].append(source)
                                results_info["total"] += len(results)
                            except Exception as e:
                                results_info[f"{source}_error"] = str(e)
                        
                        return images, results_info
                        
                    except Exception as e:
                        return [], {"error": str(e)}
                
                search_ref_btn.click(
                    search_references,
                    inputs=[search_query, source_danbooru, source_gelbooru, rating_filter, max_results],
                    outputs=[ref_gallery, ref_info],
                )
    
    return tab


def create_upscale_tab(settings: Settings) -> gr.Tab:
    """Create Image Upscaling and Enhancement tab."""
    
    with gr.Tab("⬆️ Upscale") as tab:
        gr.Markdown("""
        ### Image Upscaling & Face Restoration
        Enhance image quality using Real-ESRGAN and GFPGAN.
        """)
        
        with gr.Tabs():
            # Upscale Tab
            with gr.Tab("Upscale"):
                with gr.Row():
                    with gr.Column(scale=1):
                        input_image = gr.Image(label="Input Image", type="pil")
                        
                        upscale_model = gr.Dropdown(
                            label="Model",
                            choices=[
                                "realesrgan_x4plus",
                                "realesrgan_x4plus_anime_6B",
                                "realesrgan_x2plus",
                            ],
                            value="realesrgan_x4plus_anime_6B",
                        )
                        
                        scale = gr.Slider(2, 4, value=4, step=1, label="Scale Factor")
                        tile_size = gr.Slider(128, 1024, value=512, step=128, label="Tile Size")
                        denoise = gr.Slider(0.0, 1.0, value=0.5, step=0.1, label="Denoise Strength")
                        
                        upscale_btn = gr.Button("Upscale", variant="primary")
                    
                    with gr.Column(scale=1):
                        output_image = gr.Image(label="Upscaled Image", type="pil")
                        upscale_info = gr.Textbox(label="Info", lines=2)
                
                def upscale(input_img, model, scale, tile_size, denoise):
                    if input_img is None:
                        return None, "Please upload an image"
                    
                    try:
                        import time
                        start = time.time()
                        
                        from ..core.upscaler import PostProcessor
                        
                        processor = PostProcessor()
                        result = processor.upscale(
                            image=input_img,
                            model_name=model,
                            scale=int(scale),
                            tile_size=int(tile_size),
                            denoise_strength=denoise,
                        )
                        
                        elapsed = time.time() - start
                        original = f"{input_img.size[0]}x{input_img.size[1]}"
                        new = f"{result.size[0]}x{result.size[1]}"
                        info = f"Model: {model}\n{original} → {new} | Time: {elapsed:.2f}s"
                        
                        return result, info
                        
                    except Exception as e:
                        logger.error(f"Upscale error: {e}", exc_info=True)
                        return None, f"Error: {str(e)}"
                
                upscale_btn.click(
                    upscale,
                    inputs=[input_image, upscale_model, scale, tile_size, denoise],
                    outputs=[output_image, upscale_info],
                )
            
            # Face Restoration Tab
            with gr.Tab("Face Restoration"):
                with gr.Row():
                    with gr.Column(scale=1):
                        face_input = gr.Image(label="Input Image", type="pil")
                        
                        face_model = gr.Dropdown(
                            label="Model",
                            choices=["gfpgan", "codeformer"],
                            value="gfpgan",
                        )
                        
                        fidelity = gr.Slider(
                            0.0, 1.0, value=0.5, step=0.1,
                            label="Fidelity (CodeFormer only)"
                        )
                        
                        face_upscale = gr.Slider(1, 4, value=2, step=1, label="Upscale Factor")
                        
                        restore_btn = gr.Button("Restore Faces", variant="primary")
                    
                    with gr.Column(scale=1):
                        face_output = gr.Image(label="Restored Image", type="pil")
                        face_info = gr.Textbox(label="Info", lines=2)
                
                def restore_faces(input_img, model, fidelity, upscale_factor):
                    if input_img is None:
                        return None, "Please upload an image"
                    
                    try:
                        import time
                        start = time.time()
                        
                        from ..core.upscaler import PostProcessor
                        
                        processor = PostProcessor()
                        result, faces_found = processor.restore_faces(
                            image=input_img,
                            model_name=model,
                            fidelity=fidelity,
                            upscale=int(upscale_factor),
                        )
                        
                        elapsed = time.time() - start
                        info = f"Model: {model}\nFaces found: {faces_found} | Time: {elapsed:.2f}s"
                        
                        return result, info
                        
                    except Exception as e:
                        logger.error(f"Face restore error: {e}", exc_info=True)
                        return None, f"Error: {str(e)}"
                
                restore_btn.click(
                    restore_faces,
                    inputs=[face_input, face_model, fidelity, face_upscale],
                    outputs=[face_output, face_info],
                )
            
            # Full Enhancement Tab
            with gr.Tab("Full Enhancement"):
                gr.Markdown("""
                Combine upscaling and face restoration for best results.
                """)
                
                with gr.Row():
                    with gr.Column(scale=1):
                        enhance_input = gr.Image(label="Input Image", type="pil")
                        
                        enhance_model = gr.Dropdown(
                            label="Upscale Model",
                            choices=[
                                "realesrgan_x4plus",
                                "realesrgan_x4plus_anime_6B",
                            ],
                            value="realesrgan_x4plus_anime_6B",
                        )
                        
                        enhance_scale = gr.Slider(2, 4, value=4, step=1, label="Scale")
                        
                        do_face_restore = gr.Checkbox(
                            label="Also restore faces",
                            value=False,
                        )
                        
                        enhance_btn = gr.Button("Enhance", variant="primary")
                    
                    with gr.Column(scale=1):
                        enhance_output = gr.Image(label="Enhanced Image", type="pil")
                        enhance_info = gr.Textbox(label="Info", lines=2)
                
                def enhance(input_img, model, scale, restore_faces_opt):
                    if input_img is None:
                        return None, "Please upload an image"
                    
                    try:
                        import time
                        start = time.time()
                        
                        from ..core.upscaler import PostProcessor
                        
                        processor = PostProcessor()
                        
                        # Upscale
                        result = processor.upscale(
                            image=input_img,
                            model_name=model,
                            scale=int(scale),
                        )
                        
                        # Face restore
                        faces_found = 0
                        if restore_faces_opt:
                            result, faces_found = processor.restore_faces(
                                image=result,
                                model_name="gfpgan",
                                upscale=1,
                            )
                        
                        elapsed = time.time() - start
                        original = f"{input_img.size[0]}x{input_img.size[1]}"
                        new = f"{result.size[0]}x{result.size[1]}"
                        info = f"Model: {model}\n{original} → {new}"
                        if restore_faces_opt:
                            info += f" | Faces: {faces_found}"
                        info += f" | Time: {elapsed:.2f}s"
                        
                        return result, info
                        
                    except Exception as e:
                        logger.error(f"Enhance error: {e}", exc_info=True)
                        return None, f"Error: {str(e)}"
                
                enhance_btn.click(
                    enhance,
                    inputs=[enhance_input, enhance_model, enhance_scale, do_face_restore],
                    outputs=[enhance_output, enhance_info],
                )
    
    return tab


def create_tagger_tab(settings: Settings) -> gr.Tab:
    """Create Auto-Tagging tab."""
    
    with gr.Tab("🏷️ Tagger") as tab:
        gr.Markdown("""
        ### Automatic Image Tagging
        Analyze images to generate Danbooru-style tags for prompt creation.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                input_image = gr.Image(label="Input Image", type="pil")
                
                tagger_model = gr.Dropdown(
                    label="Tagger Model",
                    choices=["wd14", "deepdanbooru"],
                    value="wd14",
                )
                
                threshold = gr.Slider(0.1, 0.9, value=0.35, step=0.05, label="Threshold")
                max_tags = gr.Slider(10, 100, value=50, step=10, label="Max Tags")
                
                tag_btn = gr.Button("Analyze Image", variant="primary")
            
            with gr.Column(scale=1):
                generated_prompt = gr.Textbox(
                    label="Generated Prompt",
                    lines=5,
                )
                
                rating_output = gr.Textbox(label="Detected Rating")
                
                tags_output = gr.Dataframe(
                    headers=["Tag", "Confidence"],
                    label="Detected Tags",
                    row_count=20,
                )
        
        def analyze_image(input_img, model, threshold, max_tags):
            if input_img is None:
                return "", "", []
            
            try:
                from ..utils.tagger import AutoTagger
                
                tagger = AutoTagger(model=model)
                result = tagger.tag(
                    image=input_img,
                    threshold=threshold,
                    max_tags=int(max_tags),
                )
                
                prompt = result.get("prompt", "")
                rating = result.get("rating", "unknown")
                
                # Create dataframe data
                tags = result.get("tags", [])
                scores = result.get("scores", {})
                tag_data = [[tag, f"{scores.get(tag, 0):.2%}"] for tag in tags[:20]]
                
                return prompt, rating, tag_data
                
            except Exception as e:
                logger.error(f"Tagging error: {e}", exc_info=True)
                return f"Error: {str(e)}", "", []
        
        tag_btn.click(
            analyze_image,
            inputs=[input_image, tagger_model, threshold, max_tags],
            outputs=[generated_prompt, rating_output, tags_output],
        )
    
    return tab


def create_settings_tab(manager: PipelineManager, settings: Settings) -> gr.Tab:
    """Create Settings and Info tab."""
    
    with gr.Tab("⚙️ Settings") as tab:
        gr.Markdown("### System Information")
        
        with gr.Row():
            with gr.Column():
                device_info = gr.Textbox(
                    label="Device",
                    value=str(manager.device),
                    interactive=False,
                )
                
                vram_info = gr.JSON(
                    label="VRAM Usage",
                    value=manager.get_vram_usage(),
                )
                
                refresh_btn = gr.Button("Refresh")
                clear_cache_btn = gr.Button("Clear Cache", variant="secondary")
            
            with gr.Column():
                models_info = gr.JSON(
                    label="Available Models",
                    value=manager.get_available_models(),
                )
        
        def refresh_info():
            return manager.get_vram_usage(), manager.get_available_models()
        
        def clear_cache():
            manager.clear_cache()
            return manager.get_vram_usage(), manager.get_available_models()
        
        refresh_btn.click(
            refresh_info,
            outputs=[vram_info, models_info],
        )
        
        clear_cache_btn.click(
            clear_cache,
            outputs=[vram_info, models_info],
        )
    
    return tab


# ==============================================================================
# IP-Adapter Tab
# ==============================================================================

def create_ip_adapter_tab(manager: PipelineManager, settings: Settings) -> gr.Tab:
    """Create IP-Adapter style transfer and face preserve tab."""
    
    with gr.Tab("IP-Adapter") as tab:
        gr.Markdown("""
        ## IP-Adapter: Image Prompt Adapter
        
        Use reference images to guide generation:
        - **Style Transfer**: Transfer style from reference to generated image
        - **Face Preserve**: Generate while preserving face identity
        """)
        
        with gr.Tabs():
            # Style Transfer Sub-tab
            with gr.Tab("Style Transfer"):
                with gr.Row():
                    with gr.Column(scale=1):
                        style_ref_image = gr.Image(
                            label="Style Reference Image",
                            type="pil",
                        )
                        style_prompt = gr.Textbox(
                            label="Prompt",
                            placeholder="Describe what to generate with this style...",
                            lines=2,
                        )
                        style_negative = gr.Textbox(
                            label="Negative Prompt",
                            value="low quality, blurry, distorted",
                            lines=1,
                        )
                        
                        with gr.Row():
                            style_scale = gr.Slider(0.0, 1.0, value=0.7, label="Style Scale")
                            style_cfg = gr.Slider(1.0, 20.0, value=7.5, label="CFG Scale")
                        
                        with gr.Row():
                            style_width = gr.Slider(512, 2048, value=1024, step=64, label="Width")
                            style_height = gr.Slider(512, 2048, value=1024, step=64, label="Height")
                        
                        style_steps = gr.Slider(10, 100, value=30, step=1, label="Steps")
                        style_seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                        
                        style_generate_btn = gr.Button("Generate with Style", variant="primary")
                    
                    with gr.Column(scale=1):
                        style_output = gr.Image(label="Generated Image", type="pil")
                        style_info = gr.Textbox(label="Info", lines=2)
                
                def generate_with_style(ref_img, prompt, negative, scale, cfg, width, height, steps, seed):
                    if ref_img is None:
                        return None, "Please upload a reference image"
                    
                    try:
                        from ..core.ip_adapter import get_ip_adapter_manager
                        
                        start = time.time()
                        actual_seed = None if seed == -1 else int(seed)
                        
                        pipe = manager.get_pipeline("sdxl")
                        ip_manager = get_ip_adapter_manager()
                        pipe = ip_manager.load_ip_adapter(pipe, "ip_adapter_plus", "sdxl")
                        
                        result = ip_manager.generate_with_image_prompt(
                            pipeline=pipe,
                            prompt=prompt,
                            image_prompt=ref_img,
                            negative_prompt=negative,
                            scale=scale,
                            guidance_scale=cfg,
                            width=int(width),
                            height=int(height),
                            num_inference_steps=int(steps),
                            seed=actual_seed,
                        )
                        
                        elapsed = time.time() - start
                        return result, f"Style scale: {scale} | Time: {elapsed:.2f}s"
                        
                    except Exception as e:
                        logger.error(f"Style transfer error: {e}", exc_info=True)
                        return None, f"Error: {str(e)}"
                
                style_generate_btn.click(
                    generate_with_style,
                    inputs=[style_ref_image, style_prompt, style_negative, style_scale, 
                            style_cfg, style_width, style_height, style_steps, style_seed],
                    outputs=[style_output, style_info],
                )
            
            # Face Preserve Sub-tab
            with gr.Tab("Face Preserve"):
                with gr.Row():
                    with gr.Column(scale=1):
                        face_ref_image = gr.Image(
                            label="Face Reference Image",
                            type="pil",
                        )
                        face_prompt = gr.Textbox(
                            label="Prompt",
                            placeholder="Describe the scene while preserving the face...",
                            lines=2,
                        )
                        face_negative = gr.Textbox(
                            label="Negative Prompt",
                            value="low quality, blurry, deformed face",
                            lines=1,
                        )
                        
                        face_scale = gr.Slider(0.0, 1.0, value=0.6, label="Face Preserve Scale")
                        
                        with gr.Row():
                            face_width = gr.Slider(512, 2048, value=1024, step=64, label="Width")
                            face_height = gr.Slider(512, 2048, value=1024, step=64, label="Height")
                        
                        face_steps = gr.Slider(10, 100, value=30, step=1, label="Steps")
                        face_seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                        
                        face_generate_btn = gr.Button("Generate with Face", variant="primary")
                    
                    with gr.Column(scale=1):
                        face_output = gr.Image(label="Generated Image", type="pil")
                        face_info = gr.Textbox(label="Info", lines=2)
                
                def generate_with_face(ref_img, prompt, negative, scale, width, height, steps, seed):
                    if ref_img is None:
                        return None, "Please upload a face reference image"
                    
                    try:
                        from ..core.ip_adapter import get_ip_adapter_manager
                        
                        start = time.time()
                        actual_seed = None if seed == -1 else int(seed)
                        
                        pipe = manager.get_pipeline("sd15")
                        ip_manager = get_ip_adapter_manager()
                        pipe = ip_manager.load_ip_adapter(pipe, "ip_adapter_faceid_plus", "faceid")
                        
                        result = ip_manager.generate_with_face(
                            pipeline=pipe,
                            prompt=prompt,
                            face_image=ref_img,
                            negative_prompt=negative,
                            face_scale=scale,
                            width=int(width),
                            height=int(height),
                            num_inference_steps=int(steps),
                            seed=actual_seed,
                        )
                        
                        if result is None:
                            return None, "No face detected in reference image"
                        
                        elapsed = time.time() - start
                        return result, f"Face scale: {scale} | Time: {elapsed:.2f}s"
                        
                    except Exception as e:
                        logger.error(f"Face preserve error: {e}", exc_info=True)
                        return None, f"Error: {str(e)}"
                
                face_generate_btn.click(
                    generate_with_face,
                    inputs=[face_ref_image, face_prompt, face_negative, face_scale,
                            face_width, face_height, face_steps, face_seed],
                    outputs=[face_output, face_info],
                )
    
    return tab


# ==============================================================================
# InstantID Tab
# ==============================================================================

def create_instantid_tab(settings: Settings) -> gr.Tab:
    """Create InstantID face swap tab."""
    
    with gr.Tab("InstantID") as tab:
        gr.Markdown("""
        ## InstantID: Zero-Shot Face Identity Preservation
        
        Generate images or swap faces while maintaining perfect identity from a single reference photo.
        - **Generate**: Create new images with your face
        - **Face Swap**: Replace faces in existing images
        """)
        
        with gr.Tabs():
            # Generate with face
            with gr.Tab("Generate"):
                with gr.Row():
                    with gr.Column(scale=1):
                        instant_face = gr.Image(
                            label="Face Reference",
                            type="pil",
                        )
                        instant_prompt = gr.Textbox(
                            label="Prompt",
                            placeholder="a person as an astronaut, professional photo...",
                            lines=2,
                        )
                        instant_negative = gr.Textbox(
                            label="Negative Prompt",
                            value="low quality, bad anatomy, deformed",
                            lines=1,
                        )
                        
                        with gr.Row():
                            instant_ip_scale = gr.Slider(0.0, 1.0, value=0.8, label="Face Scale")
                            instant_cn_scale = gr.Slider(0.0, 1.0, value=0.8, label="Pose Scale")
                        
                        with gr.Row():
                            instant_width = gr.Slider(512, 2048, value=1024, step=64, label="Width")
                            instant_height = gr.Slider(512, 2048, value=1024, step=64, label="Height")
                        
                        instant_steps = gr.Slider(10, 100, value=30, step=1, label="Steps")
                        instant_cfg = gr.Slider(1.0, 20.0, value=5.0, label="CFG Scale")
                        instant_seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                        
                        instant_generate_btn = gr.Button("Generate", variant="primary")
                    
                    with gr.Column(scale=1):
                        instant_output = gr.Image(label="Generated Image", type="pil")
                        instant_info = gr.Textbox(label="Info", lines=2)
                
                def instant_generate(face_img, prompt, negative, ip_scale, cn_scale, 
                                     width, height, steps, cfg, seed):
                    if face_img is None:
                        return None, "Please upload a face reference image"
                    
                    try:
                        from ..core.instantid import get_instantid_pipeline
                        
                        start = time.time()
                        actual_seed = None if seed == -1 else int(seed)
                        
                        pipeline = get_instantid_pipeline()
                        pipeline.load_models()
                        
                        result = pipeline.generate(
                            face_image=face_img,
                            prompt=prompt,
                            negative_prompt=negative,
                            ip_adapter_scale=ip_scale,
                            controlnet_scale=cn_scale,
                            width=int(width),
                            height=int(height),
                            num_inference_steps=int(steps),
                            guidance_scale=cfg,
                            seed=actual_seed,
                        )
                        
                        if result is None:
                            return None, "No face detected in reference image"
                        
                        elapsed = time.time() - start
                        return result, f"Face: {ip_scale} | Pose: {cn_scale} | Time: {elapsed:.2f}s"
                        
                    except Exception as e:
                        logger.error(f"InstantID error: {e}", exc_info=True)
                        return None, f"Error: {str(e)}"
                
                instant_generate_btn.click(
                    instant_generate,
                    inputs=[instant_face, instant_prompt, instant_negative, instant_ip_scale,
                            instant_cn_scale, instant_width, instant_height, instant_steps,
                            instant_cfg, instant_seed],
                    outputs=[instant_output, instant_info],
                )
            
            # Face Swap
            with gr.Tab("Face Swap"):
                with gr.Row():
                    with gr.Column(scale=1):
                        swap_source = gr.Image(
                            label="Source Image (to modify)",
                            type="pil",
                        )
                        swap_face = gr.Image(
                            label="Face Reference (face to use)",
                            type="pil",
                        )
                        swap_prompt = gr.Textbox(
                            label="Optional Prompt",
                            placeholder="Optional text to guide the generation...",
                            lines=1,
                        )
                        swap_strength = gr.Slider(0.3, 1.0, value=0.6, label="Swap Strength")
                        swap_seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                        
                        swap_btn = gr.Button("Swap Faces", variant="primary")
                    
                    with gr.Column(scale=1):
                        swap_output = gr.Image(label="Result", type="pil")
                        swap_info = gr.Textbox(label="Info", lines=2)
                
                def swap_faces(source_img, face_img, prompt, strength, seed):
                    if source_img is None or face_img is None:
                        return None, "Please upload both source and face images"
                    
                    try:
                        from ..core.instantid import get_instantid_pipeline
                        
                        start = time.time()
                        
                        pipeline = get_instantid_pipeline()
                        pipeline.load_models()
                        
                        result = pipeline.swap_face(
                            source_image=source_img,
                            face_image=face_img,
                            prompt=prompt if prompt else None,
                            strength=strength,
                        )
                        
                        if result is None:
                            return None, "No face detected in reference image"
                        
                        elapsed = time.time() - start
                        return result, f"Strength: {strength} | Time: {elapsed:.2f}s"
                        
                    except Exception as e:
                        logger.error(f"Face swap error: {e}", exc_info=True)
                        return None, f"Error: {str(e)}"
                
                swap_btn.click(
                    swap_faces,
                    inputs=[swap_source, swap_face, swap_prompt, swap_strength, swap_seed],
                    outputs=[swap_output, swap_info],
                )
    
    return tab


# ==============================================================================
# Inpaint Anything Tab
# ==============================================================================

def create_inpaint_anything_tab(settings: Settings) -> gr.Tab:
    """Create Inpaint Anything (SAM + LaMa) tab."""
    
    with gr.Tab("Inpaint Anything") as tab:
        gr.Markdown("""
        ## Inpaint Anything: Click to Remove
        
        Use AI to segment and remove any object from your images:
        1. Upload an image
        2. Click on the object you want to remove
        3. AI will segment it and seamlessly remove it
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                inpaint_input = gr.Image(
                    label="Input Image (click to select point)",
                    type="pil",
                    interactive=True,
                )
                
                gr.Markdown("### Click Coordinates")
                with gr.Row():
                    click_x = gr.Number(label="X", value=0, precision=0)
                    click_y = gr.Number(label="Y", value=0, precision=0)
                
                dilate_slider = gr.Slider(0, 50, value=15, step=1, label="Mask Dilation (pixels)")
                
                with gr.Row():
                    segment_btn = gr.Button("Segment", variant="secondary")
                    remove_btn = gr.Button("Remove Object", variant="primary")
                
                gr.Markdown("### Or use bounding box")
                with gr.Row():
                    box_x1 = gr.Number(label="X1", value=0, precision=0)
                    box_y1 = gr.Number(label="Y1", value=0, precision=0)
                with gr.Row():
                    box_x2 = gr.Number(label="X2", value=100, precision=0)
                    box_y2 = gr.Number(label="Y2", value=100, precision=0)
                
                remove_box_btn = gr.Button("Remove in Box", variant="primary")
            
            with gr.Column(scale=1):
                inpaint_preview = gr.Image(label="Segmentation Preview", type="pil")
                inpaint_output = gr.Image(label="Result", type="pil")
                inpaint_info = gr.Textbox(label="Info", lines=2)
        
        # Store current state
        current_image_state = gr.State(None)
        
        def segment_object(img, x, y):
            if img is None:
                return None, None, "Please upload an image"
            
            try:
                from ..core.inpaint_anything import get_inpaint_anything
                
                start = time.time()
                
                inpainter = get_inpaint_anything()
                inpainter.set_image(img)
                
                vis = inpainter.click_to_segment((int(x), int(y)))
                
                elapsed = time.time() - start
                return vis, img, f"Segmented at ({x}, {y}) | Time: {elapsed:.2f}s"
                
            except Exception as e:
                logger.error(f"Segment error: {e}", exc_info=True)
                return None, img, f"Error: {str(e)}"
        
        def remove_object(img, x, y, dilate):
            if img is None:
                return None, "Please upload an image"
            
            try:
                from ..core.inpaint_anything import get_inpaint_anything
                
                start = time.time()
                
                inpainter = get_inpaint_anything()
                inpainter.set_image(img)
                
                result = inpainter.click_to_remove((int(x), int(y)), dilate_mask=int(dilate))
                
                elapsed = time.time() - start
                return result, f"Removed object at ({x}, {y}) | Time: {elapsed:.2f}s"
                
            except Exception as e:
                logger.error(f"Remove error: {e}", exc_info=True)
                return None, f"Error: {str(e)}"
        
        def remove_in_box(img, x1, y1, x2, y2, dilate):
            if img is None:
                return None, "Please upload an image"
            
            try:
                from ..core.inpaint_anything import get_inpaint_anything
                
                start = time.time()
                
                inpainter = get_inpaint_anything()
                inpainter.set_image(img)
                
                result = inpainter.box_to_remove(
                    (int(x1), int(y1), int(x2), int(y2)),
                    dilate_mask=int(dilate)
                )
                
                elapsed = time.time() - start
                return result, f"Removed in box | Time: {elapsed:.2f}s"
                
            except Exception as e:
                logger.error(f"Remove box error: {e}", exc_info=True)
                return None, f"Error: {str(e)}"
        
        segment_btn.click(
            segment_object,
            inputs=[inpaint_input, click_x, click_y],
            outputs=[inpaint_preview, current_image_state, inpaint_info],
        )
        
        remove_btn.click(
            remove_object,
            inputs=[inpaint_input, click_x, click_y, dilate_slider],
            outputs=[inpaint_output, inpaint_info],
        )
        
        remove_box_btn.click(
            remove_in_box,
            inputs=[inpaint_input, box_x1, box_y1, box_x2, box_y2, dilate_slider],
            outputs=[inpaint_output, inpaint_info],
        )
    
    return tab


# ==============================================================================
# Smart Edit Tab
# ==============================================================================

def create_smart_edit_tab(manager: PipelineManager, settings: Settings) -> gr.Tab:
    """Create LLM-enhanced smart editing tab."""
    
    with gr.Tab("Smart Edit") as tab:
        gr.Markdown("""
        ## Smart Edit: LLM-Enhanced Image Editing
        
        Edit images using natural language instructions. The system:
        1. Parses your instruction using AI
        2. Enriches prompts with character/style tags
        3. Generates optimal editing prompts
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                smart_input = gr.Image(
                    label="Input Image",
                    type="pil",
                )
                smart_instruction = gr.Textbox(
                    label="Instruction",
                    placeholder="e.g., 'make her hair blue and add cat ears'",
                    lines=2,
                )
                
                with gr.Accordion("Advanced Options", open=False):
                    smart_character = gr.Textbox(
                        label="Character Name (for tag lookup)",
                        placeholder="e.g., 'hatsune miku'",
                    )
                    smart_style = gr.Textbox(
                        label="Style Reference",
                        placeholder="e.g., 'ghibli', 'makoto shinkai'",
                    )
                    smart_img_guide = gr.Slider(1.0, 5.0, value=1.5, label="Image Guidance Scale")
                    smart_cfg = gr.Slider(1.0, 20.0, value=7.5, label="CFG Scale")
                    smart_steps = gr.Slider(10, 100, value=30, step=1, label="Steps")
                    smart_seed = gr.Number(label="Seed (-1 for random)", value=-1, precision=0)
                
                with gr.Row():
                    smart_parse_btn = gr.Button("Parse Only", variant="secondary")
                    smart_edit_btn = gr.Button("Edit Image", variant="primary")
            
            with gr.Column(scale=1):
                smart_output = gr.Image(label="Edited Image", type="pil")
                smart_parsed = gr.JSON(label="Parsed Instruction")
                smart_info = gr.Textbox(label="Info", lines=2)
        
        def parse_only(instruction, character, style):
            try:
                from ..core.enhanced_ip2p import get_enhanced_ip2p
                
                pipeline = get_enhanced_ip2p()
                parsed = pipeline.parse_instruction(
                    instruction,
                    character_name=character if character else None,
                    style_reference=style if style else None,
                )
                
                return parsed.to_dict(), "Instruction parsed successfully"
                
            except Exception as e:
                logger.error(f"Parse error: {e}", exc_info=True)
                return None, f"Error: {str(e)}"
        
        def smart_edit_image(img, instruction, character, style, img_guide, cfg, steps, seed):
            if img is None:
                return None, None, "Please upload an image"
            if not instruction:
                return None, None, "Please enter an instruction"
            
            try:
                from ..core.enhanced_ip2p import get_enhanced_ip2p
                
                start = time.time()
                actual_seed = None if seed == -1 else int(seed)
                
                pipeline = get_enhanced_ip2p()
                result, parsed = pipeline.edit(
                    image=img,
                    instruction=instruction,
                    character_name=character if character else None,
                    style_reference=style if style else None,
                    image_guidance_scale=img_guide,
                    guidance_scale=cfg,
                    num_inference_steps=int(steps),
                    seed=actual_seed,
                )
                
                elapsed = time.time() - start
                return result, parsed.to_dict(), f"Action: {parsed.action.value} | Time: {elapsed:.2f}s"
                
            except Exception as e:
                logger.error(f"Smart edit error: {e}", exc_info=True)
                return None, None, f"Error: {str(e)}"
        
        smart_parse_btn.click(
            parse_only,
            inputs=[smart_instruction, smart_character, smart_style],
            outputs=[smart_parsed, smart_info],
        )
        
        smart_edit_btn.click(
            smart_edit_image,
            inputs=[smart_input, smart_instruction, smart_character, smart_style,
                    smart_img_guide, smart_cfg, smart_steps, smart_seed],
            outputs=[smart_output, smart_parsed, smart_info],
        )
    
    return tab


# ==============================================================================
# Main App Creation
# ==============================================================================

def create_gradio_app(
    manager: Optional[PipelineManager] = None,
    settings: Optional[Settings] = None,
) -> gr.Blocks:
    """
    Create the Gradio web application.
    
    Args:
        manager: Pipeline manager instance
        settings: Configuration settings
        
    Returns:
        Gradio Blocks application
    """
    if manager is None:
        manager = get_pipeline_manager()
    if settings is None:
        settings = get_settings()
    
    with gr.Blocks(
        title="Edit Image Service",
        theme=gr.themes.Soft(),
        css="""
        .gradio-container { max-width: 1400px !important; }
        .contain { display: flex; flex-direction: column; }
        """
    ) as app:
        
        gr.Markdown("""
        # 🎨 Edit Image Service v0.3.0
        
        AI-powered image generation and editing with support for:
        - **Text-to-Image**: Generate images from text descriptions
        - **Image-to-Image**: Transform existing images
        - **Edit**: Natural language instruction-based editing
        - **Inpaint**: Fill in or modify parts of images
        - **ControlNet**: Guided generation with poses, edges, depth maps
        - **Anime**: Specialized anime/manga style generation
        - **IP-Adapter**: Use images as style/face prompts
        - **InstantID**: Zero-shot face identity preservation
        - **Inpaint Anything**: Click to remove any object (SAM + LaMa)
        - **Smart Edit**: LLM-enhanced natural language editing
        - **Search**: Find character references and inspiration
        - **Tagger**: Auto-generate prompts from images
        - **Upscale**: Enhance image quality with AI
        """)
        
        with gr.Tabs():
            create_txt2img_tab(manager, settings)
            create_img2img_tab(manager, settings)
            create_edit_tab(manager, settings)
            create_inpaint_tab(manager, settings)
            create_controlnet_tab(manager, settings)
            create_anime_tab(manager, settings)
            create_ip_adapter_tab(manager, settings)
            create_instantid_tab(settings)
            create_inpaint_anything_tab(settings)
            create_smart_edit_tab(manager, settings)
            create_search_tab(settings)
            create_tagger_tab(settings)
            create_upscale_tab(settings)
            create_settings_tab(manager, settings)
    
    return app


def launch_gradio_app(
    host: str = "0.0.0.0",
    port: int = 8100,
    share: bool = False,
    **kwargs
) -> None:
    """
    Launch the Gradio application.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        share: Whether to create a public link
        **kwargs: Additional arguments for gr.launch()
    """
    app = create_gradio_app()
    app.launch(
        server_name=host,
        server_port=port,
        share=share,
        **kwargs
    )


if __name__ == "__main__":
    launch_gradio_app()
