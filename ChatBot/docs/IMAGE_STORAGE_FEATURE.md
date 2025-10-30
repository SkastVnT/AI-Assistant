# 💾 Image Storage Feature - Tránh tràn Browser localStorage

## Vấn đề trước đây
- Ảnh được lưu dưới dạng **base64** trong chat sessions
- Base64 chiếm rất nhiều dung lượng trong **localStorage** (200MB limit)
- 1 ảnh 768x768 ~ 1-2MB base64 → Chỉ lưu được ~100 ảnh
- localStorage đầy → Tự động xóa chat cũ
- Chat có nhiều ảnh → localStorage tràn nhanh

## Giải pháp mới ✅
- Ảnh được lưu vào **disk** (file system) thay vì localStorage
- Location: `./ChatBot/Storage/Image_Gen/`
- Chat chỉ lưu **URL** thay vì base64
- Không giới hạn số lượng ảnh
- localStorage chỉ lưu text → Tiết kiệm 90% dung lượng

## Cấu trúc lưu trữ

### Image Files
```
ChatBot/Storage/Image_Gen/
├── generated_20251029_101530.png
├── generated_20251029_101530.json    (metadata)
├── generated_20251029_102045.png
├── generated_20251029_102045.json
└── ...
```

### Metadata File (JSON)
```json
{
  "filename": "generated_20251029_101530.png",
  "created_at": "2025-10-29T10:15:30.123456",
  "metadata": {
    "prompt": "beautiful landscape, mountains, sunset",
    "negative_prompt": "bad quality, blurry",
    "width": 768,
    "height": 768,
    "steps": 20,
    "cfg_scale": 7.5,
    "sampler_name": "DPM++ 2M Karras",
    "model": "AnythingV4_v45",
    "source": "manual" // or "text2image_tool"
  }
}
```

## Flow hoạt động

### 1. Tạo ảnh từ Modal
```
User → Click "Tạo ảnh" → Fill form → Generate
    ↓
Stable Diffusion API → Trả về base64
    ↓
Frontend → POST /api/save-image (base64 + metadata)
    ↓
Backend → Save to ./Storage/Image_Gen/generated_TIMESTAMP.png
    ↓
Backend → Trả về URL: /storage/images/generated_TIMESTAMP.png
    ↓
Frontend → Hiển thị <img src="/storage/images/...">
    ↓
Chat session chỉ lưu URL (không lưu base64)
```

### 2. Tạo ảnh từ Text2Image Tool
```
User → Type: "Tạo ảnh một con mèo"
    ↓
AI → Generate prompt + negative prompt
    ↓
Call Stable Diffusion API
    ↓
POST /api/save-image
    ↓
Display with server URL
```

## API Endpoints

### POST /api/save-image
Lưu ảnh vào disk

**Request:**
```json
{
  "image": "base64_string",
  "metadata": {
    "prompt": "string",
    "negative_prompt": "string",
    "width": 768,
    "height": 768,
    "steps": 20,
    "cfg_scale": 7.5,
    "sampler_name": "string"
  }
}
```

**Response:**
```json
{
  "success": true,
  "filename": "generated_20251029_101530.png",
  "url": "/storage/images/generated_20251029_101530.png",
  "path": "I:\\AI-Assistant\\ChatBot\\Storage\\Image_Gen\\generated_20251029_101530.png"
}
```

### GET /storage/images/<filename>
Serve ảnh đã lưu

**Example:**
```
GET /storage/images/generated_20251029_101530.png
→ Returns PNG image
```

### GET /api/list-images
Lấy danh sách tất cả ảnh đã tạo

**Response:**
```json
{
  "images": [
    {
      "filename": "generated_20251029_101530.png",
      "url": "/storage/images/generated_20251029_101530.png",
      "created_at": "2025-10-29T10:15:30",
      "metadata": { ... }
    }
  ],
  "count": 42
}
```

### DELETE /api/delete-image/<filename>
Xóa ảnh

**Example:**
```
DELETE /api/delete-image/generated_20251029_101530.png
```

## So sánh Before vs After

| Metric | Before (base64) | After (File Storage) |
|--------|----------------|---------------------|
| **Storage** | localStorage (200MB) | Disk (Unlimited) |
| **Image size** | 1-2MB base64/image | URL only (~50 bytes) |
| **Max images** | ~100 images | Unlimited |
| **Chat size** | Rất lớn (nhiều ảnh) | Nhỏ (chỉ URL) |
| **Load time** | Nhanh (cached) | Nhanh (lazy load) |
| **Persistence** | Mất khi clear browser | Vĩnh viễn trên disk |
| **Backup** | Khó (export localStorage) | Dễ (copy folder) |

## Ví dụ cụ thể

### Before (localStorage):
```html
<!-- Chat session lưu full base64 -->
<img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA...50000+ chars...">
<!-- Size: ~1.5MB per image -->
```

### After (File Storage):
```html
<!-- Chat session chỉ lưu URL -->
<img src="/storage/images/generated_20251029_101530.png" loading="lazy">
<!-- Size: ~50 bytes -->
```

**Kết quả**: Tiết kiệm **99% dung lượng localStorage** cho mỗi ảnh!

## Technical Implementation

### Backend (app.py)
```python
# Add storage directory
IMAGE_STORAGE_DIR = Path(__file__).parent / 'Storage' / 'Image_Gen'

# Save image
@app.route('/api/save-image', methods=['POST'])
def save_image():
    image_data = base64.b64decode(image_base64)
    filepath = IMAGE_STORAGE_DIR / filename
    with open(filepath, 'wb') as f:
        f.write(image_data)
    return jsonify({'url': f'/storage/images/{filename}'})

# Serve image
@app.route('/storage/images/<filename>')
def serve_image(filename):
    return send_file(IMAGE_STORAGE_DIR / filename)
```

### Frontend (index.html)
```javascript
// After generating image
const saveResponse = await fetch('/api/save-image', {
    method: 'POST',
    body: JSON.stringify({
        image: base64Image,
        metadata: {...}
    })
});

const {url} = await saveResponse.json();

// Display with server URL instead of base64
imageEl.src = url; // /storage/images/generated_xxx.png
```

## Lợi ích

### ✅ Cho User:
1. **Không lo localStorage đầy** - Tạo ảnh thoải mái
2. **Chat không bị mất** - Không auto-delete khi đầy
3. **Load nhanh hơn** - Lazy loading images
4. **Backup dễ** - Copy folder Image_Gen

### ✅ Cho Developer:
1. **Dễ quản lý** - Files trên disk
2. **Dễ migrate** - Copy/move folder
3. **Dễ backup** - Standard file backup
4. **Scalable** - Không giới hạn storage

### ✅ Cho System:
1. **Browser performance** - localStorage nhỏ hơn
2. **Memory efficient** - Images lazy loaded
3. **Network efficient** - Cache images at server
4. **Storage unlimited** - Disk space thay vì 200MB

## Backward Compatibility

### Ảnh cũ (base64):
- Vẫn hiển thị bình thường
- Tự động convert sang URL nếu re-save chat
- Không cần migration

### Ảnh mới:
- Luôn lưu vào disk
- Chat lưu URL
- Fallback to base64 nếu save fail

## Testing

### Test save image:
```bash
# 1. Start server
python app.py

# 2. Generate image
# 3. Check folder:
ls ChatBot/Storage/Image_Gen/

# Should see:
# generated_TIMESTAMP.png
# generated_TIMESTAMP.json
```

### Test serve image:
```bash
# Open browser:
http://localhost:5000/storage/images/generated_20251029_101530.png

# Should display image
```

### Test localStorage savings:
```javascript
// Open DevTools Console
// Before (with base64):
localStorage.getItem('chatSessions').length
// → 5000000 (5MB for 3 images)

// After (with URLs):
localStorage.getItem('chatSessions').length
// → 150000 (150KB for 3 images)

// Savings: 97% reduction!
```

## Maintenance

### Clean up old images:
```python
# Delete images older than 30 days
import os
from datetime import datetime, timedelta

IMAGE_DIR = "./ChatBot/Storage/Image_Gen"
for file in os.listdir(IMAGE_DIR):
    filepath = os.path.join(IMAGE_DIR, file)
    modified = datetime.fromtimestamp(os.path.getmtime(filepath))
    if datetime.now() - modified > timedelta(days=30):
        os.remove(filepath)
```

### Disk space monitoring:
```python
import shutil

total, used, free = shutil.disk_usage(IMAGE_DIR)
print(f"Free: {free / (1024**3):.2f} GB")
```

## Version
- **Added in**: v1.8.0
- **Date**: October 29, 2025
- **Status**: ✅ Implemented & Tested

## Future Enhancements
- [ ] Image compression (optimize file size)
- [ ] Thumbnail generation
- [ ] Gallery view UI
- [ ] Batch delete old images
- [ ] Cloud storage integration (S3, Cloudinary)
- [ ] Image search by prompt
- [ ] CDN integration
