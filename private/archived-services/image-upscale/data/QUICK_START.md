# Quick Start Guide - Data Folder Workflow

## 🎯 Mục đích

Hướng dẫn sử dụng thư mục `data/` để upscale ảnh với Web UI và CLI.

---

## 📁 Cấu trúc thư mục

```
upscale_tool/
├── data/
│   ├── input/      ← Đặt ảnh cần upscale vào đây
│   └── output/     ← Kết quả sẽ được lưu tự động vào đây
```

---

## 🌐 Cách 1: Sử dụng Web UI

### Bước 1: Khởi động Web UI

```bash
cd upscale_tool
python -m upscale_tool.web_ui
```

Mở trình duyệt: http://localhost:7860

### Bước 2: Chọn ảnh

**Option A - Upload trực tiếp:**
1. Tab "Upload"
2. Kéo thả hoặc click để chọn ảnh
3. Chọn model và settings
4. Click "🚀 Upscale"

**Option B - Chọn từ thư mục (Recommended):**
1. Đặt ảnh vào `data/input/`
2. Tab "Select from Folder"
3. Chọn ảnh từ dropdown
4. Xem preview
5. Chọn settings
6. Click "🚀 Upscale"
7. ✅ Kết quả tự động lưu vào `data/output/`

### Bước 3: Download kết quả

- Kết quả hiển thị ngay trên Web UI
- File tự động lưu vào `data/output/`
- Click "Download" để tải về
- Tên file có timestamp: `upscaled_RealESRGAN_x4plus_4x_20241202_143025.png`

---

## 💻 Cách 2: Sử dụng CLI (Command Line)

### Upscale 1 ảnh

```bash
# Tự động lưu vào data/output/
python -m upscale_tool.cli upscale -i data/input/photo.jpg -s 4

# Hoặc chỉ định output
python -m upscale_tool.cli upscale -i data/input/photo.jpg -o data/output/photo_4k.png -s 4
```

### Upscale cả folder

```bash
# Tự động lưu tất cả vào data/output/
python -m upscale_tool.cli upscale-folder -i data/input/ -s 4

# Với model anime
python -m upscale_tool.cli upscale-folder -i data/input/anime/ -m RealESRGAN_x4plus_anime_6B -s 4
```

### Tùy chọn nâng cao

```bash
# Với GPU (auto)
python -m upscale_tool.cli upscale -i data/input/image.png -d auto -s 4

# Với CPU
python -m upscale_tool.cli upscale -i data/input/image.png -d cpu -s 2

# Với FP16 (faster)
python -m upscale_tool.cli upscale -i data/input/image.png --half-precision -s 4

# Với tile size nhỏ (low VRAM)
python -m upscale_tool.cli upscale -i data/input/image.png --tile-size 256 -s 4
```

---

## 🎨 Tạo ảnh test

```bash
python create_test_images.py
```

Tạo 5 ảnh mẫu trong `data/input/`:
- ✅ gradient.png
- ✅ shapes.png
- ✅ text_sample.png
- ✅ random_pattern.png
- ✅ checkerboard.png

---

## 📊 Ví dụ workflow hoàn chỉnh

### Scenario 1: Upscale ảnh anime

```bash
# Bước 1: Đặt ảnh vào input
cp ~/Downloads/anime.jpg data/input/

# Bước 2: Upscale với model anime
python -m upscale_tool.cli upscale -i data/input/anime.jpg -m RealESRGAN_x4plus_anime_6B -s 4

# Bước 3: Kiểm tra kết quả
ls data/output/
# Output: anime_upscaled.jpg
```

### Scenario 2: Batch upscale nhiều ảnh

```bash
# Bước 1: Copy nhiều ảnh vào input
cp ~/Photos/*.jpg data/input/

# Bước 2: Upscale tất cả
python -m upscale_tool.cli upscale-folder -i data/input/ -s 4

# Bước 3: Kiểm tra
ls data/output/
# Output: tất cả ảnh đã được upscale
```

### Scenario 3: Web UI workflow

```bash
# Bước 1: Đặt ảnh vào input
cp ~/Photos/*.png data/input/

# Bước 2: Khởi động Web UI
python -m upscale_tool.web_ui

# Bước 3: Trên browser (http://localhost:7860)
# - Tab "Select from Folder"
# - Chọn ảnh từ dropdown
# - Preview hiển thị
# - Click "Upscale"
# - Kết quả tự động lưu vào data/output/
```

---

## 🔧 Models có sẵn

| Model | Best For | Size | Speed |
|-------|----------|------|-------|
| RealESRGAN_x4plus | Photos, general | 64MB | Medium |
| RealESRGAN_x4plus_anime_6B | Anime/manga | 17MB | Fast |
| RealESRNet_x4plus | Natural images | 64MB | Medium |
| realesr-general-x4v3 | General purpose | 17MB | Fast |

---

## ⚙️ Settings giải thích

### Scale (Tỷ lệ phóng to)
- **2x**: 1080p → 2160p (4K), nhanh nhất
- **4x**: 540p → 2160p (4K), chất lượng tốt nhất

### Device
- **auto**: Tự động chọn GPU nếu có, không thì CPU
- **cuda**: Dùng GPU (RTX 3060: ~4s/image)
- **cpu**: Dùng CPU (slow: ~180s/image)

### Tile Size
- **128-256**: Low VRAM (<4GB)
- **384-512**: Medium VRAM (4-8GB)
- **768-1024**: High VRAM (8GB+)

---

## 💡 Tips & Tricks

### 1. Tối ưu tốc độ
```bash
# Dùng FP16 + GPU + model nhỏ
python -m upscale_tool.cli upscale -i data/input/photo.jpg -m realesr-general-x4v3 --half-precision -d cuda -s 2
```

### 2. Tối ưu chất lượng
```bash
# Dùng model lớn + scale 4x
python -m upscale_tool.cli upscale -i data/input/photo.jpg -m RealESRGAN_x4plus -s 4
```

### 3. Xử lý nhiều ảnh
```bash
# Loop qua từng ảnh với settings khác nhau
for img in data/input/*.jpg; do
    python -m upscale_tool.cli upscale -i "$img" -s 4
done
```

### 4. Organize outputs
```bash
# Tạo subfolder cho mỗi model
python -m upscale_tool.cli upscale-folder -i data/input/ -o data/output/anime/ -m RealESRGAN_x4plus_anime_6B
python -m upscale_tool.cli upscale-folder -i data/input/ -o data/output/general/ -m RealESRGAN_x4plus
```

---

## 🐛 Troubleshooting

### Web UI không hiện ảnh trong dropdown
```bash
# Click "🔄 Refresh List" button
# Hoặc restart Web UI
```

### Out of Memory (OOM) Error
```bash
# Giảm tile size
python -m upscale_tool.cli upscale -i image.jpg --tile-size 256

# Hoặc dùng CPU
python -m upscale_tool.cli upscale -i image.jpg -d cpu
```

### Ảnh output quá lớn
```bash
# Dùng JPG thay vì PNG
# Hoặc scale 2x thay vì 4x
python -m upscale_tool.cli upscale -i image.jpg -s 2
```

---

## 📝 Summary

✅ **Web UI**: http://localhost:7860
- Upload hoặc chọn từ `data/input/`
- Tự động lưu vào `data/output/`
- Download kết quả

✅ **CLI**: Terminal commands
- `upscale`: 1 ảnh
- `upscale-folder`: nhiều ảnh
- Tự động output vào `data/output/` nếu không chỉ định

✅ **Test**: `python create_test_images.py`

**Ready to upscale! 🚀**
