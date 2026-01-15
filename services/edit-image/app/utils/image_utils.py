"""
Image processing utilities for Edit Image Service.
"""

import io
import base64
from pathlib import Path
from typing import Optional, Tuple, Union, List

from PIL import Image
import numpy as np


def load_image(
    source: Union[str, Path, bytes, Image.Image],
    mode: str = "RGB",
) -> Image.Image:
    """
    Load an image from various sources.
    
    Args:
        source: Image source (file path, URL, bytes, or PIL Image)
        mode: Color mode to convert to
        
    Returns:
        PIL Image object
    """
    if isinstance(source, Image.Image):
        return source.convert(mode)
    
    if isinstance(source, bytes):
        return Image.open(io.BytesIO(source)).convert(mode)
    
    if isinstance(source, (str, Path)):
        source = str(source)
        
        # Check if it's a URL
        if source.startswith(("http://", "https://")):
            import requests
            response = requests.get(source)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content)).convert(mode)
        
        # Check if it's base64
        if source.startswith("data:image"):
            # Extract base64 data
            _, data = source.split(",", 1)
            return Image.open(io.BytesIO(base64.b64decode(data))).convert(mode)
        
        # Assume it's a file path
        return Image.open(source).convert(mode)
    
    raise ValueError(f"Unsupported image source type: {type(source)}")


def image_to_base64(
    image: Image.Image,
    format: str = "PNG",
    quality: int = 95,
) -> str:
    """
    Convert PIL Image to base64 string.
    
    Args:
        image: PIL Image object
        format: Output format (PNG, JPEG, WEBP)
        quality: Quality for lossy formats
        
    Returns:
        Base64 encoded string
    """
    buffer = io.BytesIO()
    
    save_kwargs = {}
    if format.upper() in ("JPEG", "WEBP"):
        save_kwargs["quality"] = quality
    
    image.save(buffer, format=format, **save_kwargs)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def base64_to_image(data: str, mode: str = "RGB") -> Image.Image:
    """
    Convert base64 string to PIL Image.
    
    Args:
        data: Base64 encoded string (with or without data URL prefix)
        mode: Color mode to convert to
        
    Returns:
        PIL Image object
    """
    # Handle data URL format
    if data.startswith("data:image"):
        _, data = data.split(",", 1)
    
    image_bytes = base64.b64decode(data)
    return Image.open(io.BytesIO(image_bytes)).convert(mode)


def resize_image(
    image: Image.Image,
    width: Optional[int] = None,
    height: Optional[int] = None,
    max_size: Optional[int] = None,
    resample: int = Image.Resampling.LANCZOS,
) -> Image.Image:
    """
    Resize an image maintaining aspect ratio.
    
    Args:
        image: PIL Image object
        width: Target width (maintains aspect if height is None)
        height: Target height (maintains aspect if width is None)
        max_size: Maximum dimension (maintains aspect ratio)
        resample: Resampling method
        
    Returns:
        Resized PIL Image
    """
    orig_width, orig_height = image.size
    
    if max_size is not None:
        # Scale to fit within max_size
        scale = min(max_size / orig_width, max_size / orig_height)
        if scale < 1:
            width = int(orig_width * scale)
            height = int(orig_height * scale)
        else:
            return image
    
    elif width is not None and height is not None:
        # Resize to exact dimensions
        pass
    
    elif width is not None:
        # Calculate height maintaining aspect
        scale = width / orig_width
        height = int(orig_height * scale)
    
    elif height is not None:
        # Calculate width maintaining aspect
        scale = height / orig_height
        width = int(orig_width * scale)
    
    else:
        return image
    
    return image.resize((width, height), resample=resample)


def make_divisible(
    image: Image.Image,
    divisor: int = 8,
    resample: int = Image.Resampling.LANCZOS,
) -> Image.Image:
    """
    Resize image so dimensions are divisible by a number.
    
    Args:
        image: PIL Image object
        divisor: Number dimensions should be divisible by
        resample: Resampling method
        
    Returns:
        Resized PIL Image
    """
    width, height = image.size
    new_width = (width // divisor) * divisor
    new_height = (height // divisor) * divisor
    
    if new_width != width or new_height != height:
        return image.resize((new_width, new_height), resample=resample)
    
    return image


def create_mask_from_alpha(image: Image.Image) -> Image.Image:
    """
    Create a mask from image alpha channel.
    
    Args:
        image: PIL Image with alpha channel
        
    Returns:
        Grayscale mask image
    """
    if image.mode != "RGBA":
        return Image.new("L", image.size, 255)
    
    return image.split()[-1]


def apply_mask(
    image: Image.Image,
    mask: Image.Image,
    background: Optional[Image.Image] = None,
) -> Image.Image:
    """
    Apply a mask to an image.
    
    Args:
        image: Foreground image
        mask: Mask image (white = foreground)
        background: Optional background image
        
    Returns:
        Composited image
    """
    if mask.mode != "L":
        mask = mask.convert("L")
    
    if background is None:
        background = Image.new("RGB", image.size, (255, 255, 255))
    
    # Resize if needed
    if background.size != image.size:
        background = background.resize(image.size)
    if mask.size != image.size:
        mask = mask.resize(image.size)
    
    return Image.composite(image.convert("RGB"), background.convert("RGB"), mask)


def create_image_grid(
    images: List[Image.Image],
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    padding: int = 10,
    background: Tuple[int, int, int] = (255, 255, 255),
) -> Image.Image:
    """
    Create a grid of images.
    
    Args:
        images: List of PIL Images
        rows: Number of rows (calculated if None)
        cols: Number of columns (calculated if None)
        padding: Padding between images
        background: Background color
        
    Returns:
        Grid image
    """
    if not images:
        raise ValueError("No images provided")
    
    n = len(images)
    
    if rows is None and cols is None:
        cols = int(np.ceil(np.sqrt(n)))
        rows = int(np.ceil(n / cols))
    elif rows is None:
        rows = int(np.ceil(n / cols))
    elif cols is None:
        cols = int(np.ceil(n / rows))
    
    # Get max dimensions
    max_width = max(img.width for img in images)
    max_height = max(img.height for img in images)
    
    # Create grid
    grid_width = cols * max_width + (cols + 1) * padding
    grid_height = rows * max_height + (rows + 1) * padding
    
    grid = Image.new("RGB", (grid_width, grid_height), background)
    
    for i, img in enumerate(images):
        row = i // cols
        col = i % cols
        
        x = padding + col * (max_width + padding)
        y = padding + row * (max_height + padding)
        
        # Center image in cell
        offset_x = (max_width - img.width) // 2
        offset_y = (max_height - img.height) // 2
        
        grid.paste(img, (x + offset_x, y + offset_y))
    
    return grid


def image_to_numpy(image: Image.Image) -> np.ndarray:
    """Convert PIL Image to numpy array."""
    return np.array(image)


def numpy_to_image(array: np.ndarray) -> Image.Image:
    """Convert numpy array to PIL Image."""
    if array.dtype != np.uint8:
        array = (array * 255).clip(0, 255).astype(np.uint8)
    return Image.fromarray(array)
