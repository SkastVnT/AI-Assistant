# 📸 PostImages Cloud Storage Integration

**Status:** ✅ READY TO USE  
**Date:** 09/11/2025  
**API Key:** ❌ NOT REQUIRED!

---

## 🎯 GIẢI PHÁP

### **Vấn đề:**
Bạn muốn: _"Có cách nào chuyển ảnh từ local path sang URL online và lưu lại image_url tại MongoDB?"_

### **Giải pháp: PostImages**
✅ **Free unlimited uploads** - Không giới hạn  
✅ **No API key needed** - Không cần đăng ký  
✅ **Permanent URLs** - Link không expire  
✅ **Fast CDN** - Tốc độ tải nhanh  
✅ **Easy integration** - 0 setup required  

---

## 🚀 CÁCH SỬ DỤNG

### **BƯỚC 1: Test Upload**

```bash
cd I:\AI-Assistant\ChatBot

# Test với ảnh có sẵn
python scripts\test_postimages.py

# Hoặc test với ảnh cụ thể
python scripts\test_postimages.py "Storage\Image_Gen\your_image.png"
```

**Kết quả mong đợi:**
```
✅ UPLOAD SUCCESS!
🔗 Image URL: https://i.postimg.cc/abc123/image.png
```

### **BƯỚC 2: Sử dụng qua API**

```bash
# Start Flask server
python app.py

# Generate image (tự động upload PostImages)
curl -X POST http://localhost:5000/api/generate-image \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "negative_prompt": "blurry, low quality",
    "save_to_storage": true
  }'
```

**Response:**
```json
{
  "success": true,
  "images": ["generated_20251109_182345_0.png"],
  "cloud_urls": ["https://i.postimg.cc/abc123/generated_20251109_182345_0.png"],
  "cloud_url": "https://i.postimg.cc/abc123/generated_20251109_182345_0.png",
  "cloud_service": "postimages"
}
```

### **BƯỚC 3: Lưu vào MongoDB**

```python
from config.mongodb_helpers import MessageDB

# Sau khi generate image, lưu message với cloud URL
message = MessageDB.add_message(
    conversation_id="673e5f8a9b1d2c3f4a5b6c7d",
    role="assistant",
    content="Here's your generated image!",
    images=[{
        "url": "/static/Storage/Image_Gen/generated_xxx.png",  # Local path
        "cloud_url": "https://i.postimg.cc/abc123/image.png",  # Cloud URL
        "delete_url": "https://postimg.cc/delete/xyz789",
        "generated": True,
        "service": "postimages"
    }]
)
```

---

## 📊 WORKFLOW

```
User request: "Vẽ cho tôi bức hoàng hôn"
        ↓
Generate image via Stable Diffusion
        ↓
Save locally: Storage/Image_Gen/generated_xxx.png
        ↓
Upload to PostImages (NO API KEY!)
        ↓
Receive permanent URL: https://i.postimg.cc/abc123/image.png
        ↓
Save metadata.json with cloud_url & delete_url
        ↓
Return response with cloud_url to frontend
        ↓
Frontend saves to MongoDB with cloud URL
```

---

## 🎨 TÍNH NĂNG

### **1. Auto-Upload trong Generate Image**

Khi user generate ảnh qua `/api/generate-image` với `save_to_storage: true`:

1. ✅ Generate image qua Stable Diffusion
2. ✅ Save local file: `Storage/Image_Gen/generated_xxx.png`
3. ✅ **Auto-upload to PostImages** (không cần config)
4. ✅ Nhận cloud URL: `https://i.postimg.cc/...`
5. ✅ Save metadata.json với `cloud_url`, `delete_url`
6. ✅ Return response với `cloud_urls` array

### **2. Manual Upload**

```python
from src.utils.postimages_uploader import upload_to_postimages

# Upload ảnh cũ
url = upload_to_postimages("Storage/Image_Gen/old_image.png")
print(f"Cloud URL: {url}")
# Output: https://i.postimg.cc/xyz789/old_image.png
```

### **3. Delete Image**

```python
from src.utils.postimages_uploader import PostImagesUploader

# Xóa ảnh khỏi PostImages
delete_url = "https://postimg.cc/delete/abc123"
success = PostImagesUploader.delete_image(delete_url)
```

---

## 📁 FILES STRUCTURE

```
ChatBot/
├── app.py                                 ← Auto-upload PostImages
│   - Import PostImagesUploader
│   - Upload after SD generation
│   - Return cloud_urls in response
│
├── src/utils/
│   └── postimages_uploader.py             ← PostImages module
│       - PostImagesUploader.upload_image()
│       - PostImagesUploader.delete_image()
│       - upload_to_postimages() helper
│
├── config/
│   └── mongodb_schema.py                  ← Updated schema
│       - messages.images[].cloud_url
│       - messages.images[].delete_url
│       - messages.images[].service
│
├── scripts/
│   └── test_postimages.py                 ← Test upload
│
└── Storage/Image_Gen/
    ├── generated_xxx.png                  ← Local backup
    └── generated_xxx.json                 ← Metadata with cloud_url
```

---

## 🧪 TESTING

### **Test 1: Module Test**
```bash
# Test uploader module directly
python src\utils\postimages_uploader.py "Storage\Image_Gen\test.png"
```

### **Test 2: Integration Test**
```bash
# Test via test script
python scripts\test_postimages.py
```

### **Test 3: API Test**
```bash
# Start server
python app.py

# Generate image
curl -X POST http://localhost:5000/api/generate-image \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Test image", "save_to_storage": true}'
```

---

## 📋 API RESPONSE FORMAT

### **Successful Upload:**
```json
{
  "success": true,
  "images": ["generated_20251109_182345_0.png"],
  "image": "generated_20251109_182345_0.png",
  "cloud_urls": ["https://i.postimg.cc/abc123/generated_20251109_182345_0.png"],
  "cloud_url": "https://i.postimg.cc/abc123/generated_20251109_182345_0.png",
  "base64_images": ["iVBORw0KG..."],
  "cloud_service": "postimages",
  "info": "...",
  "parameters": {...}
}
```

### **MongoDB Document:**
```javascript
{
  "_id": ObjectId("..."),
  "conversation_id": ObjectId("..."),
  "role": "assistant",
  "content": "Here's your image!",
  "images": [{
    "url": "/static/Storage/Image_Gen/generated_xxx.png",
    "cloud_url": "https://i.postimg.cc/abc123/image.png",
    "delete_url": "https://postimg.cc/delete/xyz789",
    "caption": "AI Generated Art",
    "size": 245680,
    "mime_type": "image/png",
    "generated": true,
    "service": "postimages"
  }],
  "created_at": ISODate("2025-11-09T12:00:00Z")
}
```

---

## ✅ ƯU ĐIỂM POSTIMAGES

| Feature | PostImages | Imgur | ImgBB |
|---------|------------|-------|-------|
| API Key | ❌ **Not required** | ✅ Required | ✅ Required |
| Registration | ❌ **Not required** | ✅ Required | ✅ Required |
| Upload Limit | ✅ **Unlimited** | 1250/day | Limited |
| File Size | 24 MB | 25 MB | 32 MB |
| Expiration | ✅ **Never** | Never | Optional |
| CDN Speed | ✅ Fast | Fast | Medium |
| Setup Time | ✅ **0 seconds** | ~5 min | ~2 min |

---

## 🔧 TROUBLESHOOTING

### **❌ "Upload failed: No URL in response"**
**Nguyên nhân:** PostImages API tạm thời chậm  
**Giải pháp:**
- Thử lại sau vài giây
- Kiểm tra internet connection
- File size < 10MB recommended

### **❌ "requests module not found"**
**Giải pháp:**
```bash
pip install requests
```

### **❌ "Image not found"**
**Giải pháp:**
```bash
# Check file path
ls Storage\Image_Gen\
```

### **❌ Upload chậm**
**Nguyên nhân:** File size quá lớn  
**Giải pháp:**
- Giảm resolution: 512x512 thay vì 1024x1024
- Compress PNG before upload
- Wait up to 60s (timeout)

---

## 📊 METADATA.JSON FORMAT

Sau khi upload, file `.json` sẽ có thêm cloud info:

```json
{
  "filename": "generated_20251109_182345_0.png",
  "created_at": "2025-11-09T18:23:45.123456",
  "prompt": "A beautiful sunset over mountains",
  "negative_prompt": "blurry, low quality",
  "parameters": {
    "width": 512,
    "height": 512,
    "steps": 20
  },
  "cloud_url": "https://i.postimg.cc/abc123/generated_20251109_182345_0.png",
  "delete_url": "https://postimg.cc/delete/xyz789",
  "service": "postimages"
}
```

---

## 🎯 USAGE EXAMPLES

### **Example 1: Frontend JavaScript**
```javascript
// Generate image
const response = await fetch('/api/generate-image', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: "Beautiful landscape",
    save_to_storage: true
  })
});

const data = await response.json();

// Display cloud URL
console.log(data.cloud_url);
// https://i.postimg.cc/abc123/image.png

// Save to MongoDB
await saveMessage({
  role: 'assistant',
  content: 'Here is your image!',
  images: [{
    url: data.images[0],  // Local path
    cloud_url: data.cloud_url,  // Cloud URL
    generated: true
  }]
});
```

### **Example 2: Python Script**
```python
from src.utils.postimages_uploader import PostImagesUploader

uploader = PostImagesUploader()

# Upload
result = uploader.upload_image("test.png", title="My Art")

if result:
    print(f"URL: {result['url']}")
    print(f"Delete: {result['delete_url']}")
    
    # Save delete URL for later cleanup
    with open('delete_urls.txt', 'a') as f:
        f.write(f"{result['url']} -> {result['delete_url']}\n")
```

### **Example 3: Batch Upload**
```python
from pathlib import Path
from src.utils.postimages_uploader import PostImagesUploader

uploader = PostImagesUploader()
storage = Path("Storage/Image_Gen")

for img_file in storage.glob("*.png"):
    result = uploader.upload_image(str(img_file))
    if result:
        print(f"✅ {img_file.name} -> {result['url']}")
    else:
        print(f"❌ {img_file.name} failed")
```

---

## 🎊 HOÀN TẤT!

### **✅ Đã triển khai:**
1. ✅ PostImages uploader module (`src/utils/postimages_uploader.py`)
2. ✅ Auto-upload trong `/api/generate-image`
3. ✅ MongoDB schema updated (cloud_url, delete_url)
4. ✅ Test script (`scripts/test_postimages.py`)
5. ✅ Complete documentation

### **🔥 Sử dụng ngay:**
```bash
# Test upload
python scripts\test_postimages.py

# Generate image (auto-upload)
python app.py
# Then call /api/generate-image with save_to_storage: true
```

### **📝 Lưu ý:**
- ✅ **Không cần API key** - Work ngay lập tức
- ✅ **Không cần config** - Zero setup
- ✅ **Free unlimited** - Không giới hạn uploads
- ✅ **Permanent URLs** - Link không expire

---

**🚀 READY TO USE!** Không cần setup gì cả, test ngay! 🎉
