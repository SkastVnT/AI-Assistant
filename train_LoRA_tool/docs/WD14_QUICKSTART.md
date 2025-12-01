# 🔒 WD14 Tagger - Quick Start Guide (NSFW-Safe)

## ✅ Đã Cài Đặt Xong!

Dependencies đã được cài vào venv `lora`:
- ✅ onnxruntime
- ✅ huggingface-hub  
- ✅ pillow

## 🚀 Cách Sử Dụng

### Bước 1: Chuẩn bị ảnh

```bash
# Bỏ ảnh NSFW của bạn vào folder này
data/train/
├── image1.jpg
├── image2.png
└── ...
```

### Bước 2: Kích hoạt venv (nếu chưa)

```powershell
.\lora\Scripts\Activate.ps1
```

### Bước 3: Chạy WD14 Tagger

**Cơ bản (recommended):**
```bash
python scripts\utilities\wd14_tagger.py --input data\train
```

**Với quality tags:**
```bash
python scripts\utilities\wd14_tagger.py --input data\train --prefix "masterpiece, best quality"
```

**Chi tiết hơn (lower threshold = more tags):**
```bash
python scripts\utilities\wd14_tagger.py --input data\train --threshold 0.25 --verbose
```

**Chỉ lấy tags quan trọng:**
```bash
python scripts\utilities\wd14_tagger.py --input data\train --threshold 0.5
```

### Kết quả

Mỗi ảnh sẽ có file `.txt` tương ứng:
```
image1.jpg → image1.txt
image2.png → image2.txt
```

Nội dung file `.txt`:
```
1girl, solo, nude, breasts, nipples, pussy, uncensored, rating:explicit, 
blue hair, red eyes, looking at viewer, smile, indoors, detailed, 
high resolution, anime style
```

## 📊 Tùy Chỉnh

### Threshold (Độ chính xác)

- `0.25-0.30`: Nhiều tags, chi tiết (recommended cho NSFW)
- `0.35`: Default, cân bằng
- `0.40-0.50`: Ít tags, chỉ tags quan trọng

### Models

```bash
# SwinV2 - Accuracy cao nhất (default)
--model swinv2

# ConvNeXt - Cân bằng
--model convnext

# ViT - Nhanh nhất
--model vit
```

### Formats

```bash
# Danbooru format (default) - comma-separated
--format danbooru

# Weighted format - với confidence scores
--format weighted

# Line-by-line - mỗi tag một dòng
--format line_by_line
```

## 🎯 Examples Cụ Thể

### Character LoRA (NSFW)

```bash
python scripts\utilities\wd14_tagger.py \
    --input data\train \
    --threshold 0.30 \
    --prefix "masterpiece, best quality, 1girl" \
    --verbose
```

### Style LoRA

```bash
python scripts\utilities\wd14_tagger.py \
    --input data\train \
    --threshold 0.35 \
    --prefix "high quality, detailed" \
    --verbose
```

### Concept LoRA (pose, situation)

```bash
python scripts\utilities\wd14_tagger.py \
    --input data\train \
    --threshold 0.25 \
    --include-scores \
    --verbose
```

## 🔄 Batch Scripts (Windows)

### quick_tag_nsfw.bat (Auto-run)

Chạy file này để tự động tag toàn bộ `data\train`:

```bash
quick_tag_nsfw.bat
```

## 💡 Tips

### 1. Review Tags Đầu Tiên
```bash
# Tag vài ảnh đầu tiên
python scripts\utilities\wd14_tagger.py --input data\train --verbose

# Kiểm tra data\train\*.txt
# Xem tags có phù hợp không
# Adjust threshold nếu cần
```

### 2. Combine Với Manual Tags
```bash
# WD14 tạo tags tự động
python scripts\utilities\wd14_tagger.py --input data\train

# Sau đó edit .txt files thủ công để:
# - Thêm character name
# - Thêm specific details
# - Xóa tags không cần thiết
```

### 3. Multiple Passes
```bash
# Pass 1: General tags
python scripts\utilities\wd14_tagger.py --input data\train --threshold 0.35

# Pass 2: Thêm quality prefix (không overwrite)
python scripts\utilities\wd14_tagger.py --input data\train --prefix "masterpiece, best quality"
```

## 🛡️ Privacy & Safety

✅ **100% Local Processing**
- Không upload ảnh lên internet
- Model chạy trên máy bạn
- Tags được tạo offline

✅ **NSFW Support**
- Nhận diện đầy đủ NSFW tags
- Rating tags (safe/questionable/explicit)
- Anatomical tags
- Uncensored/censored detection

✅ **No Restrictions**
- Không có content policy
- Không bị ban
- Không giới hạn số lượng

## 🚨 Troubleshooting

### Model download lần đầu

Lần đầu chạy sẽ download model (~800MB):
```
Downloading model (only first time)...
Downloading tags...
```

Model được cache tại: `~/.cache/huggingface/hub/`

### Out of memory

Nếu gặp lỗi memory với nhiều ảnh:
```bash
# Process theo batch nhỏ hơn
python scripts\utilities\wd14_tagger.py --input data\train\batch1
python scripts\utilities\wd14_tagger.py --input data\train\batch2
```

### Tags không phù hợp

```bash
# Lower threshold = more tags
--threshold 0.25

# Higher threshold = fewer tags
--threshold 0.5

# Try different model
--model convnext
```

## 📖 Next Steps

Sau khi đã có tags:

```bash
# 1. Review tags
# Check data\train\*.txt files

# 2. Configure training
copy configs\loraplus_config.yaml configs\my_nsfw.yaml

# 3. Train LoRA
python scripts\training\train_lora.py --config configs\my_nsfw.yaml
```

## 🎓 Best Practices

### Dataset Quality
- 50-200 images cho character LoRA
- 200-500 images cho style LoRA
- High resolution (512x512 minimum)
- Consistent art style

### Tag Quality
- Review first 10-20 captions
- Add character-specific tags manually
- Remove irrelevant tags
- Keep important anatomical details

### Training Config
```yaml
# Recommended for NSFW character LoRA
lora:
  rank: 64  # Higher for anatomical details
  alpha: 128

training:
  num_train_epochs: 12-15
  learning_rate: 5e-5  # Lower for NSFW
  use_loraplus: true
  loss_type: smooth_l1
```

---

**🎉 Bây giờ bạn có thể tag NSFW dataset an toàn và private!**

- Bỏ ảnh vào `data\train`
- Chạy `python scripts\utilities\wd14_tagger.py --input data\train`
- Done! Caption files tự động được tạo
