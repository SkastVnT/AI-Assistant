# Data Folder Structure

This folder contains input and output images for the upscale tool.

## 📁 Structure

```
data/
├── input/          # Place your images here for upscaling
│   ├── gradient.png
│   ├── shapes.png
│   └── ...
└── output/         # Upscaled images will be saved here
    ├── gradient_upscaled.png
    └── ...
```

## 🚀 Usage

### Web UI

1. **Upload Method:**
   - Open http://localhost:7860
   - Go to "Upload" tab
   - Upload your image
   - Click "🚀 Upscale"

2. **Select from Folder:**
   - Place images in `data/input/` folder
   - Open http://localhost:7860
   - Go to "Select from Folder" tab
   - Choose an image from dropdown
   - Preview will show the selected image
   - Click "🚀 Upscale"
   - Output saved to `data/output/` folder

### CLI (Command Line)

**Upscale single image:**
```bash
# Auto-save to data/output/
python -m upscale_tool.cli upscale -i data/input/gradient.png -s 4

# Or specify output path
python -m upscale_tool.cli upscale -i data/input/shapes.png -o data/output/shapes_4x.png -s 4
```

**Upscale entire folder:**
```bash
# Auto-save to data/output/
python -m upscale_tool.cli upscale-folder -i data/input/ -s 2

# Or specify output folder
python -m upscale_tool.cli upscale-folder -i data/input/ -o data/output/ -s 4
```

## 📝 Notes

- **Supported formats:** JPG, JPEG, PNG, WEBP, BMP
- **Input folder:** `data/input/` - Place your low-res images here
- **Output folder:** `data/output/` - Upscaled images are saved here
- **Auto-naming:** CLI auto-generates output names if not specified
- **Web UI:** Always saves to `data/output/` with timestamp

## 🎯 Tips

1. **Organize your inputs:**
   ```bash
   data/input/
   ├── photos/
   ├── anime/
   └── screenshots/
   ```

2. **Batch processing:**
   ```bash
   # Process all images in input folder
   python -m upscale_tool.cli upscale-folder -i data/input/
   ```

3. **Different models for different content:**
   ```bash
   # For anime/manga
   python -m upscale_tool.cli upscale -i data/input/anime.png -m RealESRGAN_x4plus_anime_6B
   
   # For photos
   python -m upscale_tool.cli upscale -i data/input/photo.jpg -m RealESRGAN_x4plus
   ```

## 📊 Examples

Create test images:
```bash
python create_test_images.py
```

This creates 5 sample images in `data/input/`:
- `gradient.png` - Color gradient
- `shapes.png` - Geometric shapes
- `text_sample.png` - Text rendering
- `random_pattern.png` - Random noise pattern
- `checkerboard.png` - Checkerboard pattern

## 🔧 Troubleshooting

**Issue:** Images not showing in dropdown
- **Solution:** Click "🔄 Refresh List" button
- Check images are in `data/input/` folder
- Verify file extensions (.png, .jpg, etc.)

**Issue:** Output files too large
- **Solution:** Use JPG format or adjust quality
- Change output format in settings

**Issue:** Cannot find output files
- **Solution:** Check `data/output/` folder
- Look for files with timestamp in name
- Check terminal output for exact path
