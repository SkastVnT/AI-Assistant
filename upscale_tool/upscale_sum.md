# Upscale Tool - Development Summary

## Session Overview
Phát triển AI Image Upscaler với hỗ trợ GIF animation, UI enhancement, và hot reload development environment.

---

## 🎯 Main Features Implemented

### 1. Multi-Architecture Upscaler (11 Models)
**Real-ESRGAN Models (7):**
- RealESRGAN_x4plus (Tencent - Best overall)
- RealESRGAN_x4plus_anime_6B (Anime specialized)
- RealESRGANv2-animevideo-xsx2/xsx4 (Anime video)
- RealESRGAN_x2plus (2x scale)
- RealESRNet_x4plus (Conservative)

**Chinese Architecture Models (4):**
- realesr-animevideov3 (SRVGG - Anime video)
- realesr-general-x4v3 (SRVGG - General purpose)
- SwinIR_4x (Swin Transformer)
- Swin2SR RealworldSR_4x (Swin2 Transformer)

**CUDA Optimization:**
- RTX 3060 6GB support
- FP32 for Swin models (stability)
- FP16 for RRDB models (performance)
- Dynamic tile size adjustment

---

### 2. GIF Animation Support

**Frame-by-Frame Processing:**
```python
class GIFUpscaler:
    def upscale_gif(self, gif_path, scale, max_frames=None):
        # Extract all frames
        # Upscale each frame
        # Preserve duration, loop metadata
        # Reassemble animated GIF
```

**Key Features:**
- Process ALL frames (max_frames=0 or None)
- Preserve animation timing (duration per frame)
- Preserve loop count
- Animated output display via base64 HTML

**Upload Detection Fix:**
- Separate "Upload GIF" tab with `gr.File(file_types=[".gif"])`
- Detection priority: Upload GIF → Select GIF from folder → Upload Image
- Handle Gradio `_TemporaryFileWrapper` object (`.name` attribute)

---

### 3. UI Enhancements

**Image Information Display:**
```
📊 Original: 512x512 PNG (0.45 MB)
📈 Upscaled: 2048x2048 (Scale: 4x)
💾 Saved to: data/output/image_4x.png
```

**Upscale Preview Calculator:**
- Shows output dimensions before processing
- Calculates based on current scale setting
- Real-time update on scale change

**Custom CSS Styling:**
- Modern dark theme
- Gradient backgrounds
- Smooth transitions
- Responsive layout

**Dual Output System:**
- `output_image` (gr.Image) - For static images
- `output_gif` (gr.HTML) - For animated GIFs with base64 encoding

---

### 4. Hot Reload Development Server

**Watchdog Integration:**
```python
class HotReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            # Auto-restart Gradio
```

**Features:**
- Monitor `.py` files in `src/upscale_tool/`
- Auto-restart on code changes
- Press `Ctrl+Shift+R` to reload browser
- Development mode flag

**Start Command:**
```powershell
python -m upscale_tool.web_ui --dev
```

---

### 5. Security Hardening

**.gitignore Protection:**
```gitignore
# API Keys & Credentials
.env
*.env
*_credentials.json
google_oauth_credentials.json

# User Data
data/input/*
data/output/*
!data/input/.gitkeep
!data/output/.gitkeep

# Models (large files)
models/*.pth
```

**Protected:**
- ImgBB API keys
- Google OAuth credentials
- User uploaded images
- Upscaled output files

---

## 🔧 Technical Implementation

### File Structure
```
upscale_tool/
├── src/upscale_tool/
│   ├── web_ui.py (627 lines) - Main Gradio UI
│   ├── gif_upscaler.py (91 lines) - GIF processing
│   ├── __main__.py - Entry point
│   └── ...
├── data/
│   ├── input/ - User uploads
│   └── output/ - Upscaled results
├── models/ - Downloaded .pth files
└── requirements.txt
```

### Key Code Segments

**GIF Upload Detection (web_ui.py):**
```python
def upscale_image_ui(
    self,
    image,
    gif_file,  # NEW: Separate GIF upload
    selected_file,
    model_name,
    scale,
    device,
    tile_size,
    save_output,
    max_gif_frames
):
    # Check Upload GIF tab
    if gif_file:
        gif_path = Path(gif_file.name) if hasattr(gif_file, 'name') else Path(gif_file)
    
    # Check Select from Folder (if .gif)
    elif selected_file and selected_file != "None":
        file_path = self.input_dir / selected_file
        if is_gif(file_path):
            gif_path = file_path
    
    # Process GIF
    if gif_path:
        # Frame-by-frame upscaling
        # Return animated HTML
```

**Animated GIF Display:**
```python
# Base64 encode for HTML embedding
with open(upscaled_path, 'rb') as f:
    gif_bytes = f.read()
    gif_base64 = base64.b64encode(gif_bytes).decode('utf-8')

gif_html = f'''
<div style="text-align: center;">
    <img src="data:image/gif;base64,{gif_base64}" 
         style="max-width: 100%; height: auto; border-radius: 8px;">
</div>
'''

return None, gif_html, info_text, str(upscaled_path)
```

**Event Handler Wiring:**
```python
upscale_btn.click(
    fn=self.upscale_image_ui,
    inputs=[
        input_image,
        input_gif_file,  # NEW: Wired GIF upload
        file_dropdown,
        model_choice,
        scale_slider,
        device_choice,
        tile_size,
        save_output,
        max_gif_frames
    ],
    outputs=[output_image, output_gif, info_text, download_file]
)
```

---

## 🐛 Issues Resolved

### Issue 1: GIF Files Not Showing in Dropdown
**Problem:** Dropdown only showed PNG/JPG files  
**Solution:** Added `.gif` to `get_available_images()` filter

### Issue 2: GIF Output Shows as Static Image
**Problem:** Gradio Image component doesn't support animation  
**Solution:** Created separate HTML component with base64-encoded GIF

### Issue 3: GIF Upload Detected as PNG
**Root Cause:** Gradio `gr.Image` converts GIF to numpy array, loses file type  
**Solution:**
1. Created separate "Upload GIF" tab with `gr.File(file_types=[".gif"])`
2. Modified function signature to accept `gif_file` parameter
3. Handle `_TemporaryFileWrapper` object (`.name` attribute)
4. Updated event handler to wire `input_gif_file`

### Issue 4: Gradio `type="filepath"` Error
**Problem:** Gradio 3.41.2 doesn't support `type="filepath"`  
**Solution:** Changed to `type="file"` (valid values: `file`, `binary`, `bytes`)

---

## 📊 Progress Tracking

### ✅ Completed Tasks
- [x] 11 models working (RRDBNet, SRVGG, SwinIR, Swin2SR)
- [x] CUDA optimization (FP16/FP32 dynamic selection)
- [x] Image info display (dimensions, format, size)
- [x] Upscale preview calculator
- [x] GIF dropdown visibility
- [x] All frames processing (max_frames=0)
- [x] Animated GIF display via base64 HTML
- [x] GIF upload detection (separate tab)
- [x] Hot reload dev server (watchdog)
- [x] .gitignore security hardening

### 🎯 System Status
**Fully Operational** - All features working as intended

---

## 🚀 Usage Guide

### Start Development Server
```powershell
cd upscale_tool
python -m upscale_tool.web_ui --dev
```

### Upload & Upscale
1. **Upload Image:** Use "Upload Image" tab for PNG/JPG/WEBP
2. **Upload GIF:** Use "Upload GIF" tab for animated GIFs
3. **Select from Folder:** Choose from `data/input/` directory
4. **Configure:** Select model, scale (2x/4x), device (CUDA/CPU)
5. **Process:** Click "🚀 Upscale Image"
6. **Download:** Use download button for upscaled result

### GIF Processing
- Upload GIF via dedicated tab
- Set `max_gif_frames=0` for ALL frames
- Output displays as animated GIF
- Download preserves animation

---

## 🔬 Technical Notes

### Gradio Version: 3.41.2
**Limitations:**
- No native dark/light mode toggle
- Image component doesn't support GIF animation
- File component: `type` must be `file`, `binary`, or `bytes`
- File upload returns `_TemporaryFileWrapper` object

**Workarounds:**
- Custom CSS for dark theme
- HTML component for animated GIF (base64 encoding)
- Extract file path via `.name` attribute

### CUDA Memory Management
```python
# Auto tile size based on image resolution
if image_width * image_height > 1920 * 1080:
    tile_size = 256  # Large images
else:
    tile_size = 512  # Normal images
```

### ImgBB Integration
- Auto-upload upscaled images
- Retry logic (3 attempts)
- API key in `.env` file (secured via .gitignore)

---

## 📝 Development Timeline

1. **Phase 1:** Basic upscaler with 11 models + CUDA optimization
2. **Phase 2:** UI enhancement (image info, preview calculator, custom CSS)
3. **Phase 3:** Dark mode attempt (removed due to Gradio limitation)
4. **Phase 4:** Hot reload setup (Flask + watchdog)
5. **Phase 5:** GIF support (frame-by-frame processing)
6. **Phase 6:** Security hardening (.gitignore)
7. **Phase 7:** GIF display fix (base64 HTML component)
8. **Phase 8:** GIF upload detection fix (separate File component) ✅

---

## 🎓 Lessons Learned

### Gradio Component Selection
- `gr.Image` → For static images only
- `gr.File` → For file uploads (GIF detection)
- `gr.HTML` → For custom rendering (animated GIF)

### File Type Detection
- Upload tab converts to numpy array → loses file extension
- Separate upload components for different file types
- Check file object attributes (`.name` for path)

### Animation Preservation
- PIL Image maintains GIF metadata (duration, loop)
- Base64 encoding preserves animation in HTML
- Browser native rendering (no JavaScript needed)

---

## 🔮 Future Enhancements (Not Implemented)

- Video upscaling (MP4, AVI)
- Batch processing queue
- Model comparison slider
- Custom model upload
- API endpoint for programmatic access
- Progress bar for long GIF processing

---

## 📌 Commands Reference

### Installation
```powershell
pip install -r requirements.txt
```

### Run Server
```powershell
# Production
python -m upscale_tool.web_ui

# Development (hot reload)
python -m upscale_tool.web_ui --dev
```

### Model Download
Models auto-download on first use, saved to `models/` directory.

---

**Last Updated:** December 2, 2025  
**Status:** Production Ready ✅  
**Version:** 1.0.0
