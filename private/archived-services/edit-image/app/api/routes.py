"""
API Routes for Edit Image Service.
Provides RESTful endpoints for image generation and editing.
"""

import io
import base64
import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from PIL import Image

from ..core.pipeline import get_pipeline_manager
from ..core.config import get_settings


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["edit-image"])


# ==============================================================================
# Request/Response Models
# ==============================================================================

class GenerationRequest(BaseModel):
    """Request model for image generation."""
    prompt: str = Field(..., description="Text prompt for generation")
    negative_prompt: Optional[str] = Field(None, description="Negative prompt")
    model: Optional[str] = Field(None, description="Model name to use")
    width: int = Field(1024, ge=256, le=2048, description="Output width")
    height: int = Field(1024, ge=256, le=2048, description="Output height")
    num_inference_steps: int = Field(30, ge=1, le=150, description="Number of steps")
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0, description="CFG scale")
    seed: Optional[int] = Field(None, description="Random seed")


class EditRequest(BaseModel):
    """Request model for image editing with instructions."""
    instruction: str = Field(..., description="Edit instruction")
    num_inference_steps: int = Field(50, ge=1, le=150)
    image_guidance_scale: float = Field(1.5, ge=1.0, le=5.0)
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)
    seed: Optional[int] = None


class Img2ImgRequest(BaseModel):
    """Request model for image-to-image generation."""
    prompt: str = Field(..., description="Text prompt")
    negative_prompt: Optional[str] = None
    model: Optional[str] = None
    strength: float = Field(0.75, ge=0.0, le=1.0, description="Denoising strength")
    num_inference_steps: int = Field(30, ge=1, le=150)
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)
    seed: Optional[int] = None


class InpaintRequest(BaseModel):
    """Request model for inpainting."""
    prompt: str = Field(..., description="Text prompt for inpainted region")
    negative_prompt: Optional[str] = None
    model: Optional[str] = None
    strength: float = Field(0.85, ge=0.0, le=1.0)
    num_inference_steps: int = Field(30, ge=1, le=150)
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)
    seed: Optional[int] = None


class ControlNetRequest(BaseModel):
    """Request model for ControlNet generation."""
    prompt: str = Field(..., description="Text prompt")
    negative_prompt: Optional[str] = None
    model: Optional[str] = None
    controlnet: str = Field(..., description="ControlNet model name")
    controlnet_conditioning_scale: float = Field(1.0, ge=0.0, le=2.0)
    num_inference_steps: int = Field(30, ge=1, le=150)
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)
    seed: Optional[int] = None


class GenerationResponse(BaseModel):
    """Response model for generation requests."""
    success: bool
    image: Optional[str] = Field(None, description="Base64 encoded image")
    seed: Optional[int] = None
    model: str = ""
    generation_time: float = 0.0
    error: Optional[str] = None


class ModelInfo(BaseModel):
    """Model information."""
    name: str
    type: str
    vram: int
    enabled: bool


class ModelsResponse(BaseModel):
    """Response model for available models."""
    base_models: List[str]
    edit_models: List[str]
    controlnet: List[str]
    controlnet_sdxl: List[str]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    device: str
    vram_allocated_gb: Optional[float] = None
    cached_pipelines: List[str] = []


# ==============================================================================
# Helper Functions
# ==============================================================================

def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def base64_to_image(data: str) -> Image.Image:
    """Convert base64 string to PIL Image."""
    image_bytes = base64.b64decode(data)
    return Image.open(io.BytesIO(image_bytes))


def file_to_image(file: UploadFile) -> Image.Image:
    """Convert uploaded file to PIL Image."""
    return Image.open(io.BytesIO(file.file.read())).convert("RGB")


def save_output(image: Image.Image, prefix: str = "output") -> Path:
    """Save image to output directory."""
    settings = get_settings()
    output_dir = Path(settings.output.directory)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.{settings.output.format}"
    filepath = output_dir / filename
    
    image.save(filepath, quality=settings.output.quality)
    return filepath


# ==============================================================================
# API Endpoints
# ==============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    from .. import __version__
    
    manager = get_pipeline_manager()
    vram_info = manager.get_vram_usage()
    
    return HealthResponse(
        status="healthy",
        version=__version__,
        device=str(manager.device),
        vram_allocated_gb=vram_info.get("allocated"),
        cached_pipelines=vram_info.get("cached_pipelines", []),
    )


@router.get("/models", response_model=ModelsResponse)
async def list_models():
    """List available models."""
    manager = get_pipeline_manager()
    models = manager.get_available_models()
    return ModelsResponse(**models)


@router.post("/generate", response_model=GenerationResponse)
async def generate_image(request: GenerationRequest):
    """
    Generate an image from text prompt.
    
    This endpoint creates a new image based on the provided text description.
    """
    import time
    start_time = time.time()
    
    try:
        manager = get_pipeline_manager()
        
        image = manager.generate(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            model_name=request.model,
            width=request.width,
            height=request.height,
            num_inference_steps=request.num_inference_steps,
            guidance_scale=request.guidance_scale,
            seed=request.seed,
        )
        
        # Save and encode
        save_output(image, "txt2img")
        image_b64 = image_to_base64(image)
        
        return GenerationResponse(
            success=True,
            image=image_b64,
            seed=request.seed,
            model=request.model or get_settings().models.default,
            generation_time=time.time() - start_time,
        )
        
    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        return GenerationResponse(
            success=False,
            error=str(e),
            generation_time=time.time() - start_time,
        )


@router.post("/edit", response_model=GenerationResponse)
async def edit_image(
    image: UploadFile = File(..., description="Image to edit"),
    instruction: str = Form(..., description="Edit instruction"),
    num_inference_steps: int = Form(50),
    image_guidance_scale: float = Form(1.5),
    guidance_scale: float = Form(7.5),
    seed: Optional[int] = Form(None),
):
    """
    Edit an image using natural language instructions.
    
    Uses InstructPix2Pix model for instruction-based editing.
    Example: "Make the sky sunset colors", "Add glasses to the person"
    """
    import time
    start_time = time.time()
    
    try:
        # Load image
        input_image = file_to_image(image)
        
        manager = get_pipeline_manager()
        
        result = manager.edit_with_instructions(
            image=input_image,
            instruction=instruction,
            num_inference_steps=num_inference_steps,
            image_guidance_scale=image_guidance_scale,
            guidance_scale=guidance_scale,
            seed=seed,
        )
        
        # Save and encode
        save_output(result, "edit")
        image_b64 = image_to_base64(result)
        
        return GenerationResponse(
            success=True,
            image=image_b64,
            seed=seed,
            model="instructpix2pix",
            generation_time=time.time() - start_time,
        )
        
    except Exception as e:
        logger.error(f"Edit error: {e}", exc_info=True)
        return GenerationResponse(
            success=False,
            error=str(e),
            generation_time=time.time() - start_time,
        )


@router.post("/img2img", response_model=GenerationResponse)
async def image_to_image(
    image: UploadFile = File(..., description="Source image"),
    prompt: str = Form(..., description="Text prompt"),
    negative_prompt: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    strength: float = Form(0.75),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    seed: Optional[int] = Form(None),
):
    """
    Transform an image based on text prompt.
    
    The strength parameter controls how much the output differs from input:
    - 0.0 = identical to input
    - 1.0 = completely regenerated
    """
    import time
    start_time = time.time()
    
    try:
        input_image = file_to_image(image)
        manager = get_pipeline_manager()
        
        result = manager.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            model_name=model,
            image=input_image,
            strength=strength,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )
        
        save_output(result, "img2img")
        image_b64 = image_to_base64(result)
        
        return GenerationResponse(
            success=True,
            image=image_b64,
            seed=seed,
            model=model or get_settings().models.default,
            generation_time=time.time() - start_time,
        )
        
    except Exception as e:
        logger.error(f"Img2Img error: {e}", exc_info=True)
        return GenerationResponse(
            success=False,
            error=str(e),
            generation_time=time.time() - start_time,
        )


@router.post("/inpaint", response_model=GenerationResponse)
async def inpaint_image(
    image: UploadFile = File(..., description="Source image"),
    mask: UploadFile = File(..., description="Mask image (white = inpaint area)"),
    prompt: str = Form(..., description="Text prompt for inpainted region"),
    negative_prompt: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    strength: float = Form(0.85),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    seed: Optional[int] = Form(None),
):
    """
    Inpaint (fill in) regions of an image.
    
    Provide a mask where white pixels indicate areas to regenerate.
    The prompt describes what should appear in those regions.
    """
    import time
    start_time = time.time()
    
    try:
        input_image = file_to_image(image)
        mask_image = file_to_image(mask)
        
        manager = get_pipeline_manager()
        
        result = manager.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            model_name=model,
            image=input_image,
            mask=mask_image,
            strength=strength,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )
        
        save_output(result, "inpaint")
        image_b64 = image_to_base64(result)
        
        return GenerationResponse(
            success=True,
            image=image_b64,
            seed=seed,
            model=model or get_settings().models.default,
            generation_time=time.time() - start_time,
        )
        
    except Exception as e:
        logger.error(f"Inpaint error: {e}", exc_info=True)
        return GenerationResponse(
            success=False,
            error=str(e),
            generation_time=time.time() - start_time,
        )


@router.post("/controlnet", response_model=GenerationResponse)
async def controlnet_generate(
    image: UploadFile = File(..., description="Condition image"),
    prompt: str = Form(..., description="Text prompt"),
    negative_prompt: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
    controlnet: str = Form(..., description="ControlNet type (canny, openpose, depth, etc.)"),
    controlnet_conditioning_scale: float = Form(1.0),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    seed: Optional[int] = Form(None),
):
    """
    Generate image with ControlNet conditioning.
    
    ControlNet types:
    - canny: Edge detection
    - openpose: Pose estimation
    - depth: Depth map
    - lineart: Line art
    - lineart_anime: Anime-style line art
    - softedge: Soft edge detection
    - scribble: Scribble/sketch
    """
    import time
    start_time = time.time()
    
    try:
        condition_image = file_to_image(image)
        manager = get_pipeline_manager()
        
        result = manager.generate(
            prompt=prompt,
            negative_prompt=negative_prompt,
            model_name=model,
            controlnet=controlnet,
            controlnet_image=condition_image,
            controlnet_conditioning_scale=controlnet_conditioning_scale,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            seed=seed,
        )
        
        save_output(result, f"controlnet_{controlnet}")
        image_b64 = image_to_base64(result)
        
        return GenerationResponse(
            success=True,
            image=image_b64,
            seed=seed,
            model=model or get_settings().models.default,
            generation_time=time.time() - start_time,
        )
        
    except Exception as e:
        logger.error(f"ControlNet error: {e}", exc_info=True)
        return GenerationResponse(
            success=False,
            error=str(e),
            generation_time=time.time() - start_time,
        )


@router.post("/clear-cache")
async def clear_pipeline_cache():
    """Clear the pipeline cache to free memory."""
    manager = get_pipeline_manager()
    manager.clear_cache()
    return {"success": True, "message": "Pipeline cache cleared"}


@router.get("/vram")
async def get_vram_usage():
    """Get current VRAM usage statistics."""
    manager = get_pipeline_manager()
    return manager.get_vram_usage()


# ==============================================================================
# Search API Endpoints
# ==============================================================================

class SearchRequest(BaseModel):
    """Request model for image search."""
    query: str = Field(..., description="Search query (tags or keywords)")
    sources: List[str] = Field(
        default=["danbooru", "gelbooru"],
        description="Sources to search: danbooru, gelbooru, anilist, mal"
    )
    limit: int = Field(20, ge=1, le=100, description="Max results per source")
    rating: str = Field("general", description="Rating filter: general, sensitive, explicit")


class CharacterSearchRequest(BaseModel):
    """Request model for character search."""
    name: str = Field(..., description="Character name to search")
    series: Optional[str] = Field(None, description="Series/anime name (optional)")
    include_tags: bool = Field(True, description="Include character tags in result")


class SearchResult(BaseModel):
    """Individual search result."""
    id: str
    source: str
    url: str
    preview_url: Optional[str] = None
    tags: List[str] = []
    score: Optional[int] = None
    rating: Optional[str] = None


class SearchResponse(BaseModel):
    """Response model for search."""
    success: bool
    results: List[SearchResult] = []
    total: int = 0
    sources_searched: List[str] = []
    error: Optional[str] = None


class CharacterInfo(BaseModel):
    """Character information."""
    name: str
    series: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    tags: List[str] = []
    prompt: Optional[str] = None


class CharacterResponse(BaseModel):
    """Response for character search."""
    success: bool
    characters: List[CharacterInfo] = []
    suggested_prompt: Optional[str] = None
    error: Optional[str] = None


@router.post("/search/images", response_model=SearchResponse, tags=["search"])
async def search_images(request: SearchRequest):
    """
    Search for reference images across multiple sources.
    
    Searches Danbooru, Gelbooru, and other image boards for reference images.
    Useful for finding character references or art styles.
    """
    try:
        from ..core.search import WebSearchManager
        
        search_manager = WebSearchManager()
        all_results = []
        sources_searched = []
        
        for source in request.sources:
            source = source.lower()
            sources_searched.append(source)
            
            try:
                if source == "danbooru":
                    results = await search_manager.danbooru.search_posts(
                        tags=request.query,
                        limit=request.limit,
                        rating=request.rating
                    )
                elif source == "gelbooru":
                    results = await search_manager.gelbooru.search_posts(
                        tags=request.query,
                        limit=request.limit,
                        rating=request.rating
                    )
                else:
                    continue
                
                for r in results:
                    all_results.append(SearchResult(
                        id=str(r.get("id", "")),
                        source=source,
                        url=r.get("file_url", r.get("large_file_url", "")),
                        preview_url=r.get("preview_file_url", r.get("preview_url", "")),
                        tags=r.get("tags", []) if isinstance(r.get("tags"), list) 
                             else r.get("tag_string", "").split()[:20],
                        score=r.get("score"),
                        rating=r.get("rating"),
                    ))
            except Exception as e:
                logger.warning(f"Search error for {source}: {e}")
        
        return SearchResponse(
            success=True,
            results=all_results,
            total=len(all_results),
            sources_searched=sources_searched,
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return SearchResponse(
            success=False,
            error=str(e),
            sources_searched=request.sources,
        )


@router.post("/search/character", response_model=CharacterResponse, tags=["search"])
async def search_character(request: CharacterSearchRequest):
    """
    Search for character information and generate prompts.
    
    Searches AniList and MyAnimeList for character info,
    then generates appropriate prompts for image generation.
    """
    try:
        from ..core.search import WebSearchManager
        
        search_manager = WebSearchManager()
        characters = []
        
        # Search AniList
        try:
            anilist_results = await search_manager.anilist.search_character(
                name=request.name
            )
            for char in anilist_results[:5]:
                char_info = CharacterInfo(
                    name=char.get("name", {}).get("full", request.name),
                    series=char.get("media", {}).get("nodes", [{}])[0].get("title", {}).get("english")
                            if char.get("media", {}).get("nodes") else None,
                    description=char.get("description", "")[:500] if char.get("description") else None,
                    image_url=char.get("image", {}).get("large"),
                    tags=[],
                )
                characters.append(char_info)
        except Exception as e:
            logger.warning(f"AniList search error: {e}")
        
        # Search MAL via Jikan
        try:
            mal_results = await search_manager.jikan.search_character(
                name=request.name
            )
            for char in mal_results[:5]:
                char_info = CharacterInfo(
                    name=char.get("name", request.name),
                    series=char.get("anime", [{}])[0].get("title") if char.get("anime") else None,
                    description=char.get("about", "")[:500] if char.get("about") else None,
                    image_url=char.get("images", {}).get("jpg", {}).get("image_url"),
                    tags=[],
                )
                # Avoid duplicates
                if not any(c.name.lower() == char_info.name.lower() for c in characters):
                    characters.append(char_info)
        except Exception as e:
            logger.warning(f"MAL search error: {e}")
        
        # If tags requested, search Danbooru for character tags
        if request.include_tags and characters:
            try:
                char_name = characters[0].name.lower().replace(" ", "_")
                danbooru_results = await search_manager.danbooru.search_posts(
                    tags=f"{char_name} solo",
                    limit=10,
                    rating="general"
                )
                # Extract common tags
                all_tags = []
                for r in danbooru_results:
                    tags = r.get("tag_string", "").split() if isinstance(r.get("tag_string"), str) else r.get("tags", [])
                    all_tags.extend(tags[:30])
                
                # Find most common appearance tags
                from collections import Counter
                tag_counts = Counter(all_tags)
                appearance_tags = [tag for tag, count in tag_counts.most_common(20)
                                   if count >= 2 and tag not in ["solo", "1girl", "1boy", char_name]]
                
                if appearance_tags:
                    characters[0].tags = appearance_tags[:15]
            except Exception as e:
                logger.warning(f"Danbooru tag extraction error: {e}")
        
        # Generate suggested prompt
        suggested_prompt = None
        if characters:
            char = characters[0]
            prompt_parts = [char.name]
            if char.series:
                prompt_parts.append(f"from {char.series}")
            if char.tags:
                prompt_parts.append(", ".join(char.tags[:10]))
            prompt_parts.append("masterpiece, best quality, highres")
            suggested_prompt = ", ".join(prompt_parts)
        
        return CharacterResponse(
            success=True,
            characters=characters,
            suggested_prompt=suggested_prompt,
        )
        
    except Exception as e:
        logger.error(f"Character search error: {e}", exc_info=True)
        return CharacterResponse(
            success=False,
            error=str(e),
        )


# ==============================================================================
# Tagging API Endpoints
# ==============================================================================

class TagRequest(BaseModel):
    """Request model for auto-tagging."""
    threshold: float = Field(0.35, ge=0.0, le=1.0, description="Tag confidence threshold")
    max_tags: int = Field(50, ge=1, le=200, description="Maximum number of tags")
    model: str = Field("wd14", description="Tagger model: wd14 or deepdanbooru")


class TagResponse(BaseModel):
    """Response for tagging."""
    success: bool
    tags: List[str] = []
    tag_scores: dict = {}
    prompt: Optional[str] = None
    rating: Optional[str] = None
    error: Optional[str] = None


@router.post("/tag", response_model=TagResponse, tags=["tagging"])
async def tag_image(
    image: UploadFile = File(..., description="Image to analyze"),
    threshold: float = Form(0.35),
    max_tags: int = Form(50),
    model: str = Form("wd14"),
):
    """
    Automatically tag an image using AI.
    
    Uses WD14 Tagger or DeepDanbooru to analyze the image
    and generate anime-style tags.
    """
    try:
        from ..utils.tagger import AutoTagger
        
        input_image = file_to_image(image)
        tagger = AutoTagger(model=model)
        
        result = tagger.tag(
            image=input_image,
            threshold=threshold,
            max_tags=max_tags,
        )
        
        return TagResponse(
            success=True,
            tags=result.get("tags", []),
            tag_scores=result.get("scores", {}),
            prompt=result.get("prompt"),
            rating=result.get("rating"),
        )
        
    except Exception as e:
        logger.error(f"Tagging error: {e}", exc_info=True)
        return TagResponse(
            success=False,
            error=str(e),
        )


@router.post("/image-to-prompt", tags=["tagging"])
async def image_to_prompt(
    image: UploadFile = File(..., description="Image to convert to prompt"),
    threshold: float = Form(0.35),
    style: str = Form("anime", description="Style: anime, general"),
):
    """
    Convert an image to a text prompt for regeneration.
    
    Analyzes the image and generates a detailed prompt
    that can be used to create similar images.
    """
    try:
        from ..utils.tagger import image_to_prompt as convert_to_prompt
        
        input_image = file_to_image(image)
        prompt = convert_to_prompt(
            image=input_image,
            threshold=threshold,
            style=style,
        )
        
        return {
            "success": True,
            "prompt": prompt,
            "style": style,
        }
        
    except Exception as e:
        logger.error(f"Image-to-prompt error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


# ==============================================================================
# Upscaling API Endpoints
# ==============================================================================

class UpscaleRequest(BaseModel):
    """Request model for upscaling."""
    model: str = Field("realesrgan_x4plus", description="Upscaler model")
    scale: int = Field(4, ge=2, le=8, description="Upscale factor")
    tile_size: int = Field(512, description="Tile size for processing")
    denoise_strength: float = Field(0.5, ge=0.0, le=1.0, description="Denoise strength")


class UpscaleResponse(BaseModel):
    """Response for upscaling."""
    success: bool
    image: Optional[str] = None
    original_size: List[int] = []
    new_size: List[int] = []
    model: str = ""
    processing_time: float = 0.0
    error: Optional[str] = None


class FaceRestoreRequest(BaseModel):
    """Request model for face restoration."""
    model: str = Field("gfpgan", description="Face restoration model: gfpgan, codeformer")
    fidelity: float = Field(0.5, ge=0.0, le=1.0, description="Fidelity weight (codeformer)")
    upscale: int = Field(2, ge=1, le=4, description="Upscale factor")


class FaceRestoreResponse(BaseModel):
    """Response for face restoration."""
    success: bool
    image: Optional[str] = None
    faces_found: int = 0
    model: str = ""
    processing_time: float = 0.0
    error: Optional[str] = None


@router.post("/upscale", response_model=UpscaleResponse, tags=["upscaling"])
async def upscale_image(
    image: UploadFile = File(..., description="Image to upscale"),
    model: str = Form("realesrgan_x4plus"),
    scale: int = Form(4),
    tile_size: int = Form(512),
    denoise_strength: float = Form(0.5),
):
    """
    Upscale an image using Real-ESRGAN.
    
    Models:
    - realesrgan_x4plus: General purpose 4x upscaler
    - realesrgan_x4plus_anime_6B: Optimized for anime
    - realesrgan_x2plus: 2x upscaler for less aggressive scaling
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.upscaler import PostProcessor
        
        input_image = file_to_image(image)
        original_size = list(input_image.size)
        
        processor = PostProcessor()
        result = processor.upscale(
            image=input_image,
            model_name=model,
            scale=scale,
            tile_size=tile_size,
            denoise_strength=denoise_strength,
        )
        
        save_output(result, "upscale")
        image_b64 = image_to_base64(result)
        
        return UpscaleResponse(
            success=True,
            image=image_b64,
            original_size=original_size,
            new_size=list(result.size),
            model=model,
            processing_time=time.time() - start_time,
        )
        
    except Exception as e:
        logger.error(f"Upscale error: {e}", exc_info=True)
        return UpscaleResponse(
            success=False,
            error=str(e),
            processing_time=time.time() - start_time,
        )


@router.post("/restore-faces", response_model=FaceRestoreResponse, tags=["upscaling"])
async def restore_faces(
    image: UploadFile = File(..., description="Image with faces to restore"),
    model: str = Form("gfpgan"),
    fidelity: float = Form(0.5),
    upscale: int = Form(2),
):
    """
    Restore and enhance faces in an image.
    
    Models:
    - gfpgan: GFPGAN v1.4 for face restoration
    - codeformer: CodeFormer for high-fidelity restoration
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.upscaler import PostProcessor
        
        input_image = file_to_image(image)
        
        processor = PostProcessor()
        result, faces_found = processor.restore_faces(
            image=input_image,
            model_name=model,
            fidelity=fidelity,
            upscale=upscale,
        )
        
        save_output(result, "face_restore")
        image_b64 = image_to_base64(result)
        
        return FaceRestoreResponse(
            success=True,
            image=image_b64,
            faces_found=faces_found,
            model=model,
            processing_time=time.time() - start_time,
        )
        
    except Exception as e:
        logger.error(f"Face restore error: {e}", exc_info=True)
        return FaceRestoreResponse(
            success=False,
            error=str(e),
            processing_time=time.time() - start_time,
        )


@router.post("/enhance", tags=["upscaling"])
async def enhance_image(
    image: UploadFile = File(..., description="Image to enhance"),
    upscale_model: str = Form("realesrgan_x4plus_anime_6B"),
    scale: int = Form(4),
    restore_faces: bool = Form(False),
    face_model: str = Form("gfpgan"),
):
    """
    Full image enhancement pipeline.
    
    Combines upscaling and optional face restoration
    for complete image enhancement.
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.upscaler import PostProcessor
        
        input_image = file_to_image(image)
        original_size = list(input_image.size)
        
        processor = PostProcessor()
        
        # Upscale
        result = processor.upscale(
            image=input_image,
            model_name=upscale_model,
            scale=scale,
        )
        
        # Restore faces if requested
        faces_found = 0
        if restore_faces:
            result, faces_found = processor.restore_faces(
                image=result,
                model_name=face_model,
                upscale=1,  # Don't upscale again
            )
        
        save_output(result, "enhance")
        image_b64 = image_to_base64(result)
        
        return {
            "success": True,
            "image": image_b64,
            "original_size": original_size,
            "new_size": list(result.size),
            "upscale_model": upscale_model,
            "faces_restored": faces_found if restore_faces else None,
            "processing_time": time.time() - start_time,
        }
        
    except Exception as e:
        logger.error(f"Enhance error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "processing_time": time.time() - start_time,
        }


# ==============================================================================
# IP-Adapter API Endpoints
# ==============================================================================

class IPAdapterRequest(BaseModel):
    """Request model for IP-Adapter generation."""
    prompt: str = Field(..., description="Text prompt")
    negative_prompt: Optional[str] = None
    scale: float = Field(0.7, ge=0.0, le=1.0, description="IP-Adapter influence scale")
    num_inference_steps: int = Field(30, ge=1, le=150)
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)
    width: int = Field(1024, ge=256, le=2048)
    height: int = Field(1024, ge=256, le=2048)
    seed: Optional[int] = None


class FaceIDRequest(BaseModel):
    """Request model for FaceID generation."""
    prompt: str = Field(..., description="Text prompt")
    negative_prompt: Optional[str] = None
    face_scale: float = Field(0.6, ge=0.0, le=1.0, description="Face preservation strength")
    num_inference_steps: int = Field(30, ge=1, le=150)
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)
    width: int = Field(1024, ge=256, le=2048)
    height: int = Field(1024, ge=256, le=2048)
    seed: Optional[int] = None


@router.post("/ip-adapter/style", tags=["ip-adapter"])
async def ip_adapter_style_transfer(
    reference_image: UploadFile = File(..., description="Style reference image"),
    prompt: str = Form(...),
    negative_prompt: Optional[str] = Form(None),
    scale: float = Form(0.7),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    width: int = Form(1024),
    height: int = Form(1024),
    seed: Optional[int] = Form(None),
):
    """
    Generate image using reference image as style prompt.
    
    Uses IP-Adapter to transfer style from reference to generated image.
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.ip_adapter import get_ip_adapter_manager
        from ..core.pipeline import get_pipeline_manager
        
        ref_image = file_to_image(reference_image)
        
        # Get pipeline and load IP-Adapter
        pm = get_pipeline_manager()
        pipe = pm.get_pipeline("sdxl")
        
        manager = get_ip_adapter_manager()
        pipe = manager.load_ip_adapter(pipe, model_name="ip_adapter_plus", base_model="sdxl")
        
        result = manager.generate_with_image_prompt(
            pipeline=pipe,
            prompt=prompt,
            image_prompt=ref_image,
            negative_prompt=negative_prompt,
            scale=scale,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            seed=seed,
        )
        
        save_output(result, "ip_adapter_style")
        image_b64 = image_to_base64(result)
        
        return {
            "success": True,
            "image": image_b64,
            "scale": scale,
            "seed": seed,
            "processing_time": time.time() - start_time,
        }
        
    except Exception as e:
        logger.error(f"IP-Adapter style transfer error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/ip-adapter/face", tags=["ip-adapter"])
async def ip_adapter_face_preserve(
    face_image: UploadFile = File(..., description="Face reference image"),
    prompt: str = Form(...),
    negative_prompt: Optional[str] = Form(None),
    face_scale: float = Form(0.6),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(7.5),
    width: int = Form(1024),
    height: int = Form(1024),
    seed: Optional[int] = Form(None),
):
    """
    Generate image while preserving face identity from reference.
    
    Uses IP-Adapter FaceID for face preservation.
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.ip_adapter import get_ip_adapter_manager
        from ..core.pipeline import get_pipeline_manager
        
        face_img = file_to_image(face_image)
        
        # Get pipeline and load FaceID IP-Adapter
        pm = get_pipeline_manager()
        pipe = pm.get_pipeline("sd15")
        
        manager = get_ip_adapter_manager()
        pipe = manager.load_ip_adapter(
            pipe, model_name="ip_adapter_faceid_plus", base_model="faceid"
        )
        
        result = manager.generate_with_face(
            pipeline=pipe,
            prompt=prompt,
            face_image=face_img,
            negative_prompt=negative_prompt,
            face_scale=face_scale,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            seed=seed,
        )
        
        if result is None:
            return {"success": False, "error": "No face detected in reference image"}
        
        save_output(result, "ip_adapter_face")
        image_b64 = image_to_base64(result)
        
        return {
            "success": True,
            "image": image_b64,
            "face_scale": face_scale,
            "seed": seed,
            "processing_time": time.time() - start_time,
        }
        
    except Exception as e:
        logger.error(f"IP-Adapter face preserve error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ==============================================================================
# InstantID API Endpoints
# ==============================================================================

class InstantIDRequest(BaseModel):
    """Request for InstantID face swap."""
    prompt: str = Field(..., description="Text prompt")
    negative_prompt: Optional[str] = None
    ip_adapter_scale: float = Field(0.8, ge=0.0, le=1.0)
    controlnet_scale: float = Field(0.8, ge=0.0, le=1.0)
    num_inference_steps: int = Field(30, ge=1, le=150)
    guidance_scale: float = Field(5.0, ge=1.0, le=20.0)
    width: int = Field(1024, ge=256, le=2048)
    height: int = Field(1024, ge=256, le=2048)
    seed: Optional[int] = None


@router.post("/instantid/generate", tags=["instantid"])
async def instantid_generate(
    face_image: UploadFile = File(..., description="Face reference image"),
    prompt: str = Form(...),
    negative_prompt: Optional[str] = Form(None),
    ip_adapter_scale: float = Form(0.8),
    controlnet_scale: float = Form(0.8),
    num_inference_steps: int = Form(30),
    guidance_scale: float = Form(5.0),
    width: int = Form(1024),
    height: int = Form(1024),
    seed: Optional[int] = Form(None),
):
    """
    Generate image with preserved face identity using InstantID.
    
    Zero-shot face preservation using a single reference image.
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.instantid import get_instantid_pipeline
        
        face_img = file_to_image(face_image)
        
        pipeline = get_instantid_pipeline()
        pipeline.load_models()
        
        result = pipeline.generate(
            face_image=face_img,
            prompt=prompt,
            negative_prompt=negative_prompt,
            ip_adapter_scale=ip_adapter_scale,
            controlnet_scale=controlnet_scale,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            width=width,
            height=height,
            seed=seed,
        )
        
        if result is None:
            return {"success": False, "error": "No face detected in reference image"}
        
        save_output(result, "instantid")
        image_b64 = image_to_base64(result)
        
        return {
            "success": True,
            "image": image_b64,
            "ip_adapter_scale": ip_adapter_scale,
            "controlnet_scale": controlnet_scale,
            "seed": seed,
            "processing_time": time.time() - start_time,
        }
        
    except Exception as e:
        logger.error(f"InstantID generate error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/instantid/swap", tags=["instantid"])
async def instantid_face_swap(
    source_image: UploadFile = File(..., description="Image to modify"),
    face_image: UploadFile = File(..., description="Face to use"),
    prompt: Optional[str] = Form(None),
    strength: float = Form(0.6),
    seed: Optional[int] = Form(None),
):
    """
    Swap face in source image with reference face using InstantID.
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.instantid import get_instantid_pipeline
        
        source_img = file_to_image(source_image)
        face_img = file_to_image(face_image)
        
        pipeline = get_instantid_pipeline()
        pipeline.load_models()
        
        result = pipeline.swap_face(
            source_image=source_img,
            face_image=face_img,
            prompt=prompt,
            strength=strength,
        )
        
        if result is None:
            return {"success": False, "error": "No face detected in reference image"}
        
        save_output(result, "instantid_swap")
        image_b64 = image_to_base64(result)
        
        return {
            "success": True,
            "image": image_b64,
            "strength": strength,
            "processing_time": time.time() - start_time,
        }
        
    except Exception as e:
        logger.error(f"InstantID swap error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ==============================================================================
# Inpaint Anything API Endpoints
# ==============================================================================

@router.post("/inpaint-anything/segment", tags=["inpaint-anything"])
async def segment_by_point(
    image: UploadFile = File(..., description="Image to segment"),
    x: int = Form(..., description="X coordinate of click"),
    y: int = Form(..., description="Y coordinate of click"),
):
    """
    Segment object at clicked point using SAM.
    
    Returns visualization of segmented region and mask.
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.inpaint_anything import get_inpaint_anything
        
        input_image = file_to_image(image)
        
        inpainter = get_inpaint_anything()
        inpainter.set_image(input_image)
        
        vis = inpainter.click_to_segment((x, y))
        mask = inpainter.get_current_mask()
        
        vis_b64 = image_to_base64(vis)
        
        # Convert mask to base64 image
        from PIL import Image as PILImage
        import numpy as np
        mask_img = PILImage.fromarray((mask * 255).astype(np.uint8))
        mask_b64 = image_to_base64(mask_img)
        
        return {
            "success": True,
            "visualization": vis_b64,
            "mask": mask_b64,
            "point": [x, y],
            "processing_time": time.time() - start_time,
        }
        
    except Exception as e:
        logger.error(f"Segment error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/inpaint-anything/remove", tags=["inpaint-anything"])
async def remove_by_point(
    image: UploadFile = File(..., description="Image to edit"),
    x: int = Form(..., description="X coordinate of object to remove"),
    y: int = Form(..., description="Y coordinate of object to remove"),
    dilate_mask: int = Form(15, description="Mask dilation in pixels"),
):
    """
    Remove object at clicked point.
    
    Combines SAM segmentation with LaMa inpainting for seamless removal.
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.inpaint_anything import get_inpaint_anything
        
        input_image = file_to_image(image)
        
        inpainter = get_inpaint_anything()
        inpainter.set_image(input_image)
        
        result = inpainter.click_to_remove((x, y), dilate_mask=dilate_mask)
        
        save_output(result, "inpaint_remove")
        image_b64 = image_to_base64(result)
        
        return {
            "success": True,
            "image": image_b64,
            "point": [x, y],
            "processing_time": time.time() - start_time,
        }
        
    except Exception as e:
        logger.error(f"Remove error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/inpaint-anything/remove-box", tags=["inpaint-anything"])
async def remove_by_box(
    image: UploadFile = File(..., description="Image to edit"),
    x1: int = Form(..., description="Box left"),
    y1: int = Form(..., description="Box top"),
    x2: int = Form(..., description="Box right"),
    y2: int = Form(..., description="Box bottom"),
    dilate_mask: int = Form(15),
):
    """
    Remove object within bounding box.
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.inpaint_anything import get_inpaint_anything
        
        input_image = file_to_image(image)
        
        inpainter = get_inpaint_anything()
        inpainter.set_image(input_image)
        
        result = inpainter.box_to_remove((x1, y1, x2, y2), dilate_mask=dilate_mask)
        
        save_output(result, "inpaint_remove_box")
        image_b64 = image_to_base64(result)
        
        return {
            "success": True,
            "image": image_b64,
            "box": [x1, y1, x2, y2],
            "processing_time": time.time() - start_time,
        }
        
    except Exception as e:
        logger.error(f"Remove box error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/inpaint-anything/segment-all", tags=["inpaint-anything"])
async def segment_all(
    image: UploadFile = File(..., description="Image to segment"),
    points_per_side: int = Form(32),
):
    """
    Automatically segment all objects in image.
    
    Returns list of all detected segments with metadata.
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.inpaint_anything import get_inpaint_anything
        
        input_image = file_to_image(image)
        
        inpainter = get_inpaint_anything()
        inpainter.set_image(input_image)
        
        segments = inpainter.segment_all()
        
        # Convert segments to JSON-serializable format
        result_segments = []
        for seg in segments[:50]:  # Limit to 50 segments
            result_segments.append({
                "area": int(seg["area"]),
                "bbox": [int(x) for x in seg["bbox"]],
                "predicted_iou": float(seg["predicted_iou"]),
                "stability_score": float(seg["stability_score"]),
            })
        
        return {
            "success": True,
            "segments": result_segments,
            "total_segments": len(segments),
            "processing_time": time.time() - start_time,
        }
        
    except Exception as e:
        logger.error(f"Segment all error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# ==============================================================================
# Enhanced InstructPix2Pix API Endpoints
# ==============================================================================

class SmartEditRequest(BaseModel):
    """Request for LLM-enhanced editing."""
    instruction: str = Field(..., description="Natural language editing instruction")
    character_name: Optional[str] = Field(None, description="Character for tag lookup")
    style_reference: Optional[str] = Field(None, description="Style reference name")
    image_guidance_scale: float = Field(1.5, ge=1.0, le=5.0)
    guidance_scale: float = Field(7.5, ge=1.0, le=20.0)
    num_inference_steps: int = Field(30, ge=1, le=150)
    seed: Optional[int] = None


@router.post("/smart-edit", tags=["enhanced-editing"])
async def smart_edit(
    image: UploadFile = File(..., description="Image to edit"),
    instruction: str = Form(..., description="Natural language instruction"),
    character_name: Optional[str] = Form(None),
    style_reference: Optional[str] = Form(None),
    image_guidance_scale: float = Form(1.5),
    guidance_scale: float = Form(7.5),
    num_inference_steps: int = Form(30),
    seed: Optional[int] = Form(None),
):
    """
    Smart image editing with LLM-enhanced instruction parsing.
    
    Parses natural language instructions and enriches prompts
    with character tags and style references from web search.
    """
    import time
    start_time = time.time()
    
    try:
        from ..core.enhanced_ip2p import get_enhanced_ip2p
        
        input_image = file_to_image(image)
        
        pipeline = get_enhanced_ip2p()
        result, parsed = pipeline.edit(
            image=input_image,
            instruction=instruction,
            character_name=character_name,
            style_reference=style_reference,
            image_guidance_scale=image_guidance_scale,
            guidance_scale=guidance_scale,
            num_inference_steps=num_inference_steps,
            seed=seed,
        )
        
        save_output(result, "smart_edit")
        image_b64 = image_to_base64(result)
        
        return {
            "success": True,
            "image": image_b64,
            "parsed_instruction": parsed.to_dict(),
            "seed": seed,
            "processing_time": time.time() - start_time,
        }
        
    except Exception as e:
        logger.error(f"Smart edit error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/parse-instruction", tags=["enhanced-editing"])
async def parse_edit_instruction(
    instruction: str = Form(..., description="Instruction to parse"),
    character_name: Optional[str] = Form(None),
    style_reference: Optional[str] = Form(None),
):
    """
    Parse editing instruction without applying it.
    
    Returns structured analysis of the instruction including
    detected action, extracted subjects/targets, and composed prompts.
    """
    try:
        from ..core.enhanced_ip2p import get_enhanced_ip2p
        
        pipeline = get_enhanced_ip2p()
        parsed = pipeline.parse_instruction(
            instruction,
            character_name=character_name,
            style_reference=style_reference,
        )
        
        return {
            "success": True,
            "parsed": parsed.to_dict(),
        }
        
    except Exception as e:
        logger.error(f"Parse instruction error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
