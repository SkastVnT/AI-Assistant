# 🎨 STABLE DIFFUSION IMAGE GENERATION - HƯỚNG DẪN

## ✅ ĐÃ TÍCH HỢP THÀNH CÔNG!

Tính năng tạo ảnh bằng Stable Diffusion đã được tích hợp vào ChatBot!

---

## 🚀 CÁCH SỬ DỤNG:

### Bước 1: Khởi động Stable Diffusion WebUI

**Cách 1 - Khởi động tất cả (Recommended):**
```
Double-click: start_all_with_sd.bat
```

**Cách 2 - Khởi động riêng:**
```
Double-click: start_stable_diffusion_api.bat
```

**Quan trọng:** Stable Diffusion phải chạy với flag `--api`

---

### Bước 2: Mở ChatBot

Truy cập: **http://127.0.0.1:5000**

---

### Bước 3: Tạo ảnh

1. Click nút **🎨 Tạo ảnh** trên thanh công cụ
2. Chọn Model Checkpoint (model bạn đã tải về)
3. Nhập Prompt (mô tả ảnh muốn tạo)
4. Điều chỉnh các thông số (width, height, steps, CFG scale)
5. Click **🎨 Tạo ảnh**
6. Đợi khoảng 10-30 giây (tùy cấu hình GPU)
7. Ảnh sẽ hiển thị - có thể gửi vào chat hoặc tải xuống

---

## 🔧 CÁC THÔNG SỐ:

### Prompt
- Mô tả ảnh bạn muốn tạo
- Ví dụ: `1girl, beautiful, long hair, blue eyes, sunset, detailed, masterpiece`
- Tags cách nhau bằng dấu phẩy
- Càng chi tiết càng tốt

### Negative Prompt  
- Những gì KHÔNG muốn có
- Ví dụ: `bad quality, blurry, ugly, deformed, worst quality, low quality`
- Giúp loại bỏ những yếu tố không mong muốn

### Width & Height
- **512x512**: Nhanh nhất, ít VRAM nhất
- **768x768**: Cân bằng chất lượng/tốc độ
- **1024x1024**: Chất lượng cao nhất, cần nhiều VRAM

### Steps
- **20-30**: Đủ tốt cho hầu hết ảnh
- **40-50**: Chất lượng cao hơn
- Nhiều steps = chậm hơn

### CFG Scale
- **7-9**: Cân bằng
- **10-15**: Tuân theo prompt chặt chẽ hơn
- Quá cao có thể làm ảnh bị oversaturated

### Sampler
- **DPM++ 2M Karras**: Khuyến nghị (nhanh + chất lượng)
- **Euler a**: Nhanh, kết quả đa dạng
- **DDIM**: Ổn định, nhưng chậm hơn

### Restore Faces
- Bật khi muốn cải thiện khuôn mặt
- Dùng GFPGAN/CodeFormer

### Hires. Fix
- Bật để tạo ảnh chất lượng cao hơn
- Scale lên 2x với upscaler
- Cần nhiều thời gian và VRAM hơn

---

## 📦 CHECKPOINT MODELS:

Bạn cần tải checkpoint models về và đặt vào:
```
i:\AI-Assistant\stable-diffusion-webui\models\Stable-diffusion\
```

### Recommended Models:

#### 🔞 NSFW Allowed (Không filter):
- **Anything V5** - Anime style, rất đa dạng
- **Counterfeit V3** - Anime nhẹ nhàng
- **ChilloutMix** - Realistic người thật
- **MeinaMix** - Anime chất lượng cao
- **Realistic Vision** - Photorealistic

#### 🎨 General Purpose:
- **Stable Diffusion v1.5** - Base model
- **Stable Diffusion v2.1** - Cải tiến hơn

### Tải models từ:
- **CivitAI**: https://civitai.com/ (nhiều model NSFW)
- **HuggingFace**: https://huggingface.co/models
- **Stable Diffusion Models**: Official releases

---

## 🚫 KHÔNG CÓ GIỚI HẠN NSFW:

✅ Đã **BYPASS** mọi safety filter
✅ Có thể tạo **mọi loại ảnh** không bị kiểm duyệt
✅ Flag `--disable-safe-unpickle` cho phép load mọi checkpoint
✅ `filter_nsfw: False` trong API settings

**Lưu ý:** Vui lòng sử dụng có trách nhiệm và tuân thủ pháp luật địa phương.

---

## 💡 TIPS & TRICKS:

### 1. Prompt Engineering
```
Tốt:
masterpiece, best quality, 1girl, long black hair, red eyes, 
detailed face, looking at viewer, cherry blossoms, sunset, 
cinematic lighting, depth of field

Không tốt:
a girl with hair
```

### 2. Negative Prompt mạnh
```
Standard:
bad quality, blurry, ugly

Mạnh hơn:
(worst quality:1.4), (low quality:1.4), (bad anatomy:1.2), 
bad hands, mutation, deformed, blurry, ugly, 
text, watermark, signature
```

### 3. Tăng chất lượng
- Dùng Hires. Fix với HR scale 2.0
- Tăng steps lên 30-40
- CFG scale 7-10
- Enable Restore Faces nếu có người

### 4. Tối ưu tốc độ
- Giảm resolution (512x512)
- Steps 20-25
- Sampler DPM++ 2M Karras
- Tắt Hires. Fix

### 5. Style cụ thể
- Anime: `anime, manga, detailed, colorful`
- Realistic: `photorealistic, 8k, detailed, sharp focus`
- Oil painting: `oil painting, artistic, classical art`
- Cyberpunk: `cyberpunk, neon lights, futuristic`

---

## 🐛 TROUBLESHOOTING:

### Lỗi: "Stable Diffusion offline"
→ Chưa khởi động SD WebUI hoặc chưa dùng flag `--api`
→ Giải pháp: Chạy `start_stable_diffusion_api.bat`

### Lỗi: "CUDA out of memory"
→ VRAM không đủ
→ Giải pháp: 
  - Giảm resolution (512x512)
  - Giảm batch size xuống 1
  - Tắt Hires. Fix
  - Thêm flag `--medvram` hoặc `--lowvram` vào launch

### Ảnh bị đen (black image)
→ VAE issue
→ Giải pháp: Dùng flag `--no-half-vae` (đã có trong script)

### Không tìm thấy models
→ Chưa tải checkpoint về
→ Giải pháp: Tải model .safetensors hoặc .ckpt về `models/Stable-diffusion/`

### Tạo ảnh chậm
→ CPU rendering (không có GPU CUDA)
→ Giải pháp:
  - Cần GPU NVIDIA với CUDA
  - Hoặc giảm resolution + steps

### Lỗi: "Connection timeout"
→ Ảnh mất quá lâu để tạo (>5 phút)
→ Giải pháp: Giảm steps, giảm resolution

---

## 📊 YÊU CẦU HỆ THỐNG:

### Tối thiểu:
- GPU: NVIDIA GTX 1060 6GB VRAM
- RAM: 8GB
- Disk: 20GB (cho models)

### Khuyến nghị:
- GPU: NVIDIA RTX 3060 12GB VRAM
- RAM: 16GB+
- Disk: 50GB+ (nhiều models)

### Hỗ trợ:
- ✅ Windows 10/11
- ✅ NVIDIA GPU với CUDA
- ⚠️ AMD GPU (chậm hơn, ít hỗ trợ)
- ⚠️ CPU only (rất chậm)

---

## 🎯 VÍ DỤ PROMPTS:

### Anime Girl
```
Prompt: 
masterpiece, best quality, 1girl, beautiful, long silver hair, 
blue eyes, smile, school uniform, cherry blossoms, 
spring, sunlight, detailed face, looking at viewer

Negative: 
(worst quality:1.2), bad anatomy, bad hands, blurry, ugly
```

### Realistic Portrait
```
Prompt:
photorealistic, 8k uhd, professional photo, 1girl, 
beautiful woman, long brown hair, green eyes, 
natural makeup, white dress, outdoor, golden hour, 
bokeh, depth of field, sharp focus

Negative:
bad quality, blurry, low resolution, oversaturated, 
plastic skin, fake, CGI
```

### Fantasy Landscape
```
Prompt:
fantasy landscape, magical forest, glowing mushrooms, 
fireflies, night scene, moonlight, mystical atmosphere, 
detailed, concept art, trending on artstation

Negative:
low quality, blurry, simple, boring, daylight
```

### Cyberpunk City
```
Prompt:
cyberpunk city, neon lights, rain, reflections, 
night scene, futuristic, detailed architecture, 
atmospheric, cinematic lighting, 8k

Negative:
low quality, blurry, daytime, clean, simple
```

---

## 📞 HỖ TRỢ:

Nếu gặp vấn đề:
1. Kiểm tra Stable Diffusion WebUI console có lỗi gì
2. Thử giảm resolution + steps
3. Đảm bảo đã tải đúng checkpoint model
4. Check GPU có đang hoạt động không (Task Manager)

---

**Setup Date:** October 28, 2025
**Integration:** ChatBot + Stable Diffusion WebUI API
**Developer:** Thanh Nguyen

**Chúc bạn tạo ảnh vui vẻ! 🎨✨**
