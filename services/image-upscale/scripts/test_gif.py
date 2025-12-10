"""
Test GIF upscaling
"""
from upscale_tool.multi_upscaler import MultiArchUpscaler
from upscale_tool.gif_upscaler import GIFUpscaler
from pathlib import Path


def test_gif_upscale():
    """Test GIF upscaling"""
    
    # Create upscaler
    print("Loading model...")
    upscaler = MultiArchUpscaler(
        model='RealESRGAN_animevideov3',
        device='cuda'
    )
    
    # Create GIF upscaler
    gif_upscaler = GIFUpscaler(upscaler)
    
    # Find a test GIF
    input_dir = Path('./data/input')
    gif_files = list(input_dir.glob('*.gif'))
    
    if not gif_files:
        print(f"No GIF files found in {input_dir}")
        print("Please put a GIF file in data/input/ folder")
        return
    
    test_gif = gif_files[0]
    print(f"\nTesting with: {test_gif}")
    
    # Upscale with limited frames for testing
    print("\nUpscaling GIF (max 10 frames for testing)...")
    output_gif = gif_upscaler.upscale_gif(
        test_gif,
        scale=4,
        max_frames=10
    )
    
    print(f"\n✅ Success! Output: {output_gif}")


if __name__ == '__main__':
    test_gif_upscale()
