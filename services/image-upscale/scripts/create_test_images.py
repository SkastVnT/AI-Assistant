"""
Create sample test images in data/input folder
"""
from PIL import Image, ImageDraw, ImageFont
import random

def create_test_images():
    """Create various test images"""
    
    # 1. Simple gradient image
    img1 = Image.new('RGB', (200, 200))
    draw = ImageDraw.Draw(img1)
    for y in range(200):
        color = int(255 * y / 200)
        draw.rectangle([0, y, 200, y+1], fill=(color, 100, 255-color))
    img1.save('data/input/gradient.png')
    print("✓ Created gradient.png")
    
    # 2. Geometric shapes
    img2 = Image.new('RGB', (300, 300), color='white')
    draw = ImageDraw.Draw(img2)
    draw.rectangle([50, 50, 150, 150], fill='red', outline='black', width=2)
    draw.ellipse([150, 50, 250, 150], fill='blue', outline='black', width=2)
    draw.polygon([(150, 250), (200, 200), (250, 250)], fill='green', outline='black')
    img2.save('data/input/shapes.png')
    print("✓ Created shapes.png")
    
    # 3. Text image
    img3 = Image.new('RGB', (400, 200), color='lightblue')
    draw = ImageDraw.Draw(img3)
    try:
        draw.text((50, 80), "Test Image\n4K Upscale", fill='black')
    except:
        draw.text((50, 80), "Test Image", fill='black')
    img3.save('data/input/text_sample.png')
    print("✓ Created text_sample.png")
    
    # 4. Random pattern
    img4 = Image.new('RGB', (256, 256))
    pixels = img4.load()
    for i in range(256):
        for j in range(256):
            pixels[i, j] = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255)
            )
    img4.save('data/input/random_pattern.png')
    print("✓ Created random_pattern.png")
    
    # 5. Checkerboard
    img5 = Image.new('RGB', (400, 400), color='white')
    draw = ImageDraw.Draw(img5)
    square_size = 50
    for i in range(0, 400, square_size):
        for j in range(0, 400, square_size):
            if (i // square_size + j // square_size) % 2 == 0:
                draw.rectangle([i, j, i+square_size, j+square_size], fill='black')
    img5.save('data/input/checkerboard.png')
    print("✓ Created checkerboard.png")
    
    print(f"\n✅ Created 5 test images in data/input/")

if __name__ == '__main__':
    import os
    os.makedirs('data/input', exist_ok=True)
    os.makedirs('data/output', exist_ok=True)
    create_test_images()
