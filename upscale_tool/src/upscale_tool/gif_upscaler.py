"""
GIF upscaler - upscale animated GIFs frame by frame
"""
import numpy as np
from PIL import Image
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GIFUpscaler:
    """Upscale animated GIFs"""
    
    def __init__(self, upscaler):
        """
        Args:
            upscaler: MultiArchUpscaler instance
        """
        self.upscaler = upscaler
    
    def upscale_gif(self, gif_path, scale=4, max_frames=None, output_path=None):
        """
        Upscale animated GIF frame by frame
        
        Args:
            gif_path: Path to input GIF
            scale: Upscale ratio
            max_frames: Maximum frames to process (None = all)
            output_path: Output path (default: auto-generate)
            
        Returns:
            output_path: Path to upscaled GIF
        """
        gif_path = Path(gif_path)
        
        # Open GIF
        gif = Image.open(gif_path)
        
        # Get info
        n_frames = getattr(gif, 'n_frames', 1)
        duration = gif.info.get('duration', 100)  # ms per frame
        loop = gif.info.get('loop', 0)
        
        logger.info(f"Processing GIF: {n_frames} frames, {duration}ms/frame")
        
        # Limit frames if specified
        if max_frames:
            n_frames = min(n_frames, max_frames)
        
        # Process frames
        upscaled_frames = []
        for i in range(n_frames):
            gif.seek(i)
            
            # Convert to RGB (GIF might be palette mode)
            frame = gif.convert('RGB')
            frame_array = np.array(frame)
            
            logger.info(f"Upscaling frame {i+1}/{n_frames}...")
            
            # Upscale
            upscaled = self.upscaler.upscale_array(frame_array, scale=scale)
            upscaled_frame = Image.fromarray(upscaled)
            upscaled_frames.append(upscaled_frame)
        
        # Generate output path
        if output_path is None:
            output_path = gif_path.parent / f"{gif_path.stem}_upscaled_{scale}x.gif"
        
        output_path = Path(output_path)
        
        # Save as animated GIF
        logger.info(f"Saving {len(upscaled_frames)} frames to {output_path}...")
        upscaled_frames[0].save(
            output_path,
            save_all=True,
            append_images=upscaled_frames[1:],
            duration=duration,
            loop=loop,
            optimize=False  # Don't optimize to preserve quality
        )
        
        logger.info(f"GIF upscaled successfully: {output_path}")
        return output_path


def is_gif(file_path):
    """Check if file is a GIF"""
    return Path(file_path).suffix.lower() == '.gif'
