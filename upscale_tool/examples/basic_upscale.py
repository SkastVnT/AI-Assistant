"""
Basic upscaling example
"""
from upscale_tool import ImageUpscaler

def main():
    # Initialize upscaler
    print("Initializing upscaler...")
    upscaler = ImageUpscaler(
        model='RealESRGAN_x4plus',  # or 'RealESRGAN_x4plus_anime_6B' for anime
        device='cuda'                # or 'cpu'
    )
    
    # Upscale single image
    print("Upscaling image...")
    output_path = upscaler.upscale_image(
        input_path='input.jpg',
        output_path='output.png',
        scale=4
    )
    
    print(f"Done! Output saved to: {output_path}")


if __name__ == '__main__':
    main()
