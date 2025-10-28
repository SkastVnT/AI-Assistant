# ⚠️ LỖI CÀI ĐẶT STABLE DIFFUSION - GIẢI PHÁP NHANH

## 🔴 VẤN ĐỀ:

Lỗi conflict protobuf giữa:
- **Google Generative AI**: cần protobuf 5.29.5
- **Stable Diffusion**: cần protobuf 3.20.0

→ Không thể cài cùng lúc!

---

## ✅ GIẢI PHÁP ĐƠN GIẢN NHẤT:

### Dùng script mới: `start_sd_simple.bat`

Script này sẽ dùng `webui.bat` có sẵn của SD WebUI, bypass bước install conflict.

**Bước 1:** Double-click file:
```
start_sd_simple.bat
```

**Bước 2:** Đợi SD khởi động (1-2 phút)

**Bước 3:** Kiểm tra SD đã chạy:
- Mở: http://127.0.0.1:7860
- Nếu thấy giao diện → OK!

**Bước 4:** Mở ChatBot:
- http://127.0.0.1:5000
- Click "🎨 Tạo ảnh"
- Kiểm tra status

---

## 🔧 NẾU SCRIPT TRÊN KHÔNG CHẠY:

### Option A: Chạy thủ công trong PowerShell

```powershell
cd i:\AI-Assistant\stable-diffusion-webui
.\webui.bat --api --xformers --no-half-vae --disable-safe-unpickle
```

### Option B: Dùng python trực tiếp

```powershell
cd i:\AI-Assistant\stable-diffusion-webui
python webui.py --api --xformers --no-half-vae --disable-safe-unpickle
```

### Option C: Cài dependencies thiếu

Nếu báo thiếu module:
```powershell
pip install gradio fastapi uvicorn
pip install transformers accelerate safetensors
```

---

## 📋 CHECKLIST TRƯỚC KHI CHẠY:

- [ ] ChatBot đang chạy: http://127.0.0.1:5000 ✅ (ĐÃ CHẠY)
- [ ] Đã có checkpoint models trong `stable-diffusion-webui/models/Stable-diffusion/`
- [ ] Có GPU NVIDIA với CUDA (hoặc chấp nhận chạy CPU - rất chậm)

---

## 🎯 CHECKPOINT MODELS:

Nếu chưa có models, tải ngay:

1. **Vào CivitAI**: https://civitai.com/
2. **Tìm model**: 
   - Anything V5
   - MeinaMix
   - ChilloutMix
   - Realistic Vision
3. **Download** file `.safetensors`
4. **Đặt vào**: `i:\AI-Assistant\stable-diffusion-webui\models\Stable-diffusion\`

**HOẶC** dùng model mặc định nếu đã có sẵn trong folder.

---

## 📊 KIỂM TRA SAU KHI CHẠY:

### 1. SD WebUI đang chạy?
```
http://127.0.0.1:7860
```
→ Phải thấy giao diện Stable Diffusion

### 2. API enabled?
```
http://127.0.0.1:7860/docs
```
→ Phải thấy API documentation (FastAPI)

### 3. ChatBot detect được SD?
- Mở: http://127.0.0.1:5000
- Click nút "🎨 Tạo ảnh"
- Xem status box → Phải hiện:
  ```
  ✅ Stable Diffusion đang chạy | Model: xxxxx
  ```

---

## 🚀 TEST TẠO ẢNH:

Nếu 3 bước trên OK:

1. Nhập prompt:
   ```
   1girl, beautiful, smile, anime style
   ```

2. Negative prompt:
   ```
   bad quality, ugly
   ```

3. Để mặc định settings

4. Click **🎨 Tạo ảnh**

5. Đợi 10-30 giây

6. Ảnh xuất hiện! 🎉

---

## ❓ NẾU VẪN GẶP VẤN ĐỀ:

**Cho tôi biết:**

1. **Lỗi gì khi chạy `start_sd_simple.bat`?**
   - Copy toàn bộ error message

2. **Có GPU NVIDIA không?**
   - Mở Task Manager → Performance → GPU
   - Có hiện "NVIDIA GeForce..." không?

3. **Đã có checkpoint models chưa?**
   - Check folder: `stable-diffusion-webui\models\Stable-diffusion\`
   - Có file `.safetensors` hoặc `.ckpt` nào không?

4. **SD WebUI từng chạy được trước đây chưa?**
   - Nếu có → Dùng cách cũ + thêm flag `--api`

---

## 📝 TÓM TẮT:

✅ **ChatBot** → Đã chạy OK: http://127.0.0.1:5000
✅ **Tính năng tạo ảnh** → Đã tích hợp xong
⏳ **Stable Diffusion** → Cần khởi động

**Chạy ngay:**
```
Double-click: start_sd_simple.bat
```

**Hoặc báo lỗi cho tôi để fix tiếp!** 😊

---

**Files hỗ trợ:**
- `start_sd_simple.bat` ← Script mới, bypass lỗi
- `FIX_SD_ERROR.md` ← Hướng dẫn chi tiết các options
- `IMAGE_GENERATION_GUIDE.md` ← Hướng dẫn sử dụng đầy đủ
- `QUICK_START_IMAGE_GEN.md` ← Quick reference

**Sẵn sàng giúp bạn tiếp! 🚀**
