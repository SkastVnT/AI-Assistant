"""
Batch upscaling example
"""
from upscale_tool import ImageUpscaler
from pathlib import Path

def main():
    # Initialize upscaler
    print("Initializing upscaler...")
    upscaler = ImageUpscaler(
        model='RealESRGAN_x4plus_anime_6B',  # Fast model for anime
        device='cuda'
    )
    
    # Upscale entire folder
    print("Upscaling folder...")
    output_paths = upscaler.upscale_folder(
        input_folder='./input_images',
        output_folder='./output_images',
        scale=2  # 2x upscale
    )
    
    print(f"\nUpscaled {len(output_paths)} images:")
    for path in output_paths[:5]:  # Show first 5
        print(f"  - {Path(path).name}")
    
    if len(output_paths) > 5:
        print(f"  ... and {len(output_paths) - 5} more")


if __name__ == '__main__':
    main()
