# 🎨 STABLE DIFFUSION + CHATBOT - QUICK START

## ⚡ KHỞI ĐỘNG NHANH (2 BƯỚC):

### 1️⃣ Khởi động Stable Diffusion WebUI:
```powershell
# Cách 1: Double-click file
start_stable_diffusion_api.bat

# Cách 2: PowerShell
cd i:\AI-Assistant\stable-diffusion-webui
python launch.py --api --xformers --no-half-vae --disable-safe-unpickle
```

### 2️⃣ ChatBot đã chạy sẵn!
```
http://127.0.0.1:5000
```

Click nút **🎨 Tạo ảnh** → Nhập prompt → Generate!

---

## 🎯 VÍ DỤ NHANH:

### Simple Test:
```
Prompt: 1girl, beautiful, anime
Negative: bad quality
512x512, Steps: 20
```

### Detailed:
```
Prompt: masterpiece, 1girl, long silver hair, blue eyes, 
        detailed face, cherry blossoms, sunset
Negative: (worst quality:1.2), bad anatomy, blurry
768x768, Steps: 30, CFG: 8
```

---

## 📥 TẢI MODELS:

1. Vào: https://civitai.com/
2. Tìm model (Anything V5, MeinaMix, ChilloutMix)
3. Tải file `.safetensors`
4. Đặt vào: `i:\AI-Assistant\stable-diffusion-webui\models\Stable-diffusion\`
5. Refresh trong modal tạo ảnh

---

## ✅ FEATURES:

- ✅ **No NSFW Filter** - Tạo mọi loại ảnh
- ✅ **Chọn Checkpoint** - Đổi model realtime
- ✅ **Full Controls** - Width, Height, Steps, CFG, Sampler
- ✅ **Gửi vào Chat** - Ảnh hiện trong chat history
- ✅ **Download** - Tải về máy ngay

---

## 🔧 THÔNG SỐ KHUYẾN NGHỊ:

| Mục đích | Size | Steps | CFG | Sampler |
|----------|------|-------|-----|---------|
| Test nhanh | 512x512 | 20 | 7 | DPM++ 2M Karras |
| Chất lượng tốt | 768x768 | 30 | 8 | DPM++ 2M Karras |
| Cao nhất | 1024x1024 | 40 | 9 | DPM++ 2M Karras |

---

## 🐛 LỖI THƯỜNG GẶP:

| Lỗi | Nguyên nhân | Giải pháp |
|-----|-------------|-----------|
| SD offline | Chưa khởi động | Chạy `start_stable_diffusion_api.bat` |
| No models | Chưa tải checkpoint | Tải model về `models/Stable-diffusion/` |
| CUDA OOM | VRAM không đủ | Giảm size xuống 512x512 |
| Black image | VAE issue | Dùng flag `--no-half-vae` (đã có) |
| Quá lâu | CPU rendering | Cần NVIDIA GPU với CUDA |

---

## 📚 DOCS:

- **IMAGE_GENERATION_GUIDE.md** - Hướng dẫn đầy đủ
- **SD_INTEGRATION_COMPLETE.md** - Tổng kết integration

---

**ChatBot:** http://127.0.0.1:5000  
**SD WebUI:** http://127.0.0.1:7860  
**Status:** ✅ Ready to generate images!

🎉 **Enjoy creating amazing images!** 🎨
