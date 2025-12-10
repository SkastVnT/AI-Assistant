"""
Advanced usage example
"""
import numpy as np
from PIL import Image
from upscale_tool import ImageUpscaler, load_config, UpscaleConfig

def example_with_config_file():
    """Use config file"""
    print("=== Example 1: Using config file ===")
    
    # Create config file first
    config = UpscaleConfig()
    config.default_model = 'RealESRGAN_x4plus_anime_6B'
    config.tile_size = 400
    config.half_precision = True
    
    from upscale_tool.config import save_config
    save_config(config, 'my_config.yaml')
    
    # Load and use
    upscaler = ImageUpscaler.from_config('my_config.yaml')
    upscaler.upscale_image('input.jpg', 'output.png')
    
    print("Done!\n")


def example_with_numpy_array():
    """Upscale numpy array"""
    print("=== Example 2: Using numpy array ===")
    
    upscaler = ImageUpscaler(model='RealESRGAN_x4plus')
    
    # Load image as numpy array
    img = Image.open('input.jpg')
    img_array = np.array(img)
    
    print(f"Input shape: {img_array.shape}")
    
    # Upscale
    output_array = upscaler.upscale_array(img_array, scale=4)
    
    print(f"Output shape: {output_array.shape}")
    
    # Save
    output_img = Image.fromarray(output_array)
    output_img.save('output_from_array.png')
    
    print("Done!\n")


def example_with_custom_options():
    """Custom tile size and other options"""
    print("=== Example 3: Custom options ===")
    
    upscaler = ImageUpscaler(
        model='RealESRGAN_x4plus',
        tile_size=200,        # Smaller tiles for low VRAM
        half_precision=True,  # fp16 for speed
        device='cuda'
    )
    
    # Upscale large image
    upscaler.upscale_image(
        input_path='large_input.jpg',
        output_path='large_output.png',
        scale=2,
        tile_size=300  # Override tile size for this image
    )
    
    print("Done!\n")


def example_error_handling():
    """Error handling"""
    print("=== Example 4: Error handling ===")
    
    try:
        upscaler = ImageUpscaler(model='RealESRGAN_x4plus', device='cuda')
        upscaler.upscale_image('input.jpg', 'output.png')
    except RuntimeError as e:
        print(f"CUDA error, falling back to CPU: {e}")
        upscaler = ImageUpscaler(model='RealESRGAN_x4plus', device='cpu')
        upscaler.upscale_image('input.jpg', 'output.png')
    
    print("Done!\n")


def example_quick_upscale():
    """Quick upscale function"""
    print("=== Example 5: Quick upscale ===")
    
    from upscale_tool import upscale
    
    # Single line upscale
    output = upscale(
        'input.jpg',
        output_path='quick_output.png',
        model='RealESRGAN_x4plus_anime_6B',
        scale=4
    )
    
    print(f"Output: {output}\n")


def list_available_models():
    """List all models"""
    print("=== Available Models ===")
    
    models = ImageUpscaler.list_models()
    for name, description in models.items():
        print(f"{name:30s} - {description}")
    
    print()


if __name__ == '__main__':
    # List available models
    list_available_models()
    
    # Run examples (uncomment to try)
    # example_with_config_file()
    # example_with_numpy_array()
    # example_with_custom_options()
    # example_error_handling()
    # example_quick_upscale()
