"""
Test upscale functionality by creating a small test image
"""
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# Create a small 100x100 test image with text
img = Image.new('RGB', (100, 100), color='white')
draw = ImageDraw.Draw(img)

# Draw some shapes and text
draw.rectangle([10, 10, 90, 90], outline='blue', width=2)
draw.ellipse([30, 30, 70, 70], fill='red')
draw.text((35, 80), "TEST", fill='black')

# Save as test input
img.save('test_input.png')
print("✓ Created test_input.png (100x100)")

# Now upscale it
from upscale_tool.upscaler import ImageUpscaler

upscaler = ImageUpscaler(
    model_name='RealESRGAN_x4plus',
    scale=4
)

print(f"✓ Loaded model: {upscaler.model_name}")
print(f"✓ Device: {upscaler.device}")

# Upscale
output_path = upscaler.upscale_image('test_input.png', 'test_output.png')
print(f"✓ Upscaled to: {output_path}")

# Check result
result = Image.open(output_path)
print(f"✓ Result size: {result.size} (expected 400x400)")

assert result.size == (400, 400), f"Expected (400, 400), got {result.size}"
print("\n✅ All tests passed!")
