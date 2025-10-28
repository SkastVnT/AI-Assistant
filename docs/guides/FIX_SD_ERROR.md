# 🔧 FIX LỖI STABLE DIFFUSION INSTALLATION

## ❌ LỖI GẶP PHẢI:

```
ERROR: Could not install packages due to an OSError: [WinError 5] Access is denied: 
'C:\\Users\\SkastVnT\\AppData\\Roaming\\Python\\Python310\\site-packages\\google\\~upb\\_message.pyd'
```

**Nguyên nhân:** Conflict giữa protobuf của google-generativeai (5.29.5) và protobuf mà Stable Diffusion cần (3.20.0)

---

## ✅ GIẢI PHÁP:

### Option 1: Bypass protobuf conflict (KHUYẾN NGHỊ)

Stable Diffusion không thực sự cần protobuf chặt chẽ. Ta có thể skip bước cài open_clip.

**Bước 1:** Mở PowerShell **với quyền Administrator**

**Bước 2:** Chạy lệnh sau:
```powershell
cd i:\AI-Assistant\stable-diffusion-webui

# Khởi động với flag --skip-prepare-environment
python launch.py --api --xformers --no-half-vae --disable-safe-unpickle --skip-prepare-environment
```

**Bước 3:** Nếu thiếu dependencies, cài thêm:
```powershell
pip install gradio fastapi uvicorn
pip install transformers accelerate safetensors
```

---

### Option 2: Cài trong virtual environment riêng (TÁCH BIỆT)

Tạo môi trường riêng cho Stable Diffusion để không conflict với ChatBot.

**Bước 1:** Tạo venv cho SD:
```powershell
cd i:\AI-Assistant\stable-diffusion-webui
python -m venv venv_sd
```

**Bước 2:** Activate:
```powershell
.\venv_sd\Scripts\Activate.ps1
```

**Bước 3:** Cài SD:
```powershell
python launch.py --api --xformers --no-half-vae --disable-safe-unpickle
```

---

### Option 3: Fix protobuf manually (PHỨC TẠP HƠN)

**Bước 1:** Đóng TẤT CẢ terminal/Python processes

**Bước 2:** Mở PowerShell Administrator, chạy:
```powershell
# Gỡ protobuf
pip uninstall protobuf -y

# Cài phiên bản trung gian
pip install protobuf==4.25.3

# Test xem ChatBot còn chạy không
cd i:\AI-Assistant\ChatBot
python -c "import google.generativeai; print('OK')"
```

**Bước 3:** Nếu OK, tiếp tục cài SD:
```powershell
cd i:\AI-Assistant\stable-diffusion-webui
python launch.py --api --xformers --no-half-vae --disable-safe-unpickle
```

---

## 🚀 GIẢI PHÁP NHANH NHẤT (Khuyến nghị):

### Dùng Stable Diffusion WebUI có sẵn mà không cài lại:

Nếu bạn đã có SD WebUI chạy được trước đây:

**Bước 1:** Mở PowerShell:
```powershell
cd i:\AI-Assistant\stable-diffusion-webui
```

**Bước 2:** Chạy với các flag cần thiết:
```powershell
# Cách 1: Dùng webui.bat có sẵn + commandline args
.\webui.bat --api --xformers --no-half-vae --disable-safe-unpickle

# Cách 2: Chạy trực tiếp
python webui.py --api --xformers --no-half-vae --disable-safe-unpickle
```

**Bước 3:** Đợi khởi động xong, mở ChatBot:
```
http://127.0.0.1:5000
```

---

## 📝 CẬP NHẬT SCRIPT KHỞI ĐỘNG:

Tôi sẽ tạo script mới bypass lỗi này:

**File: `start_sd_simple.bat`**
```batch
@echo off
echo ============================================
echo   STABLE DIFFUSION - SIMPLE START
echo ============================================
echo.

cd i:\AI-Assistant\stable-diffusion-webui

echo Khoi dong Stable Diffusion voi API...
echo.

REM Dùng webui.bat có sẵn
.\webui.bat --api --xformers --no-half-vae --disable-safe-unpickle

pause
```

---

## 🎯 CÁCH KHÁC: DÙNG AUTOMATIC1111 TỪ GITHUB RELEASE

Nếu vẫn gặp vấn đề, tải bản build sẵn:

1. Tải từ: https://github.com/AUTOMATIC1111/stable-diffusion-webui/releases
2. Extract vào folder mới
3. Chạy `webui-user.bat` và thêm vào:
   ```
   set COMMANDLINE_ARGS=--api --xformers --no-half-vae --disable-safe-unpickle
   ```

---

## ✅ KIỂM TRA STABLE DIFFUSION ĐÃ CHẠY:

Sau khi khởi động, mở trình duyệt:
```
http://127.0.0.1:7860
```

Nếu thấy giao diện Stable Diffusion → Thành công!

Sau đó:
1. Mở ChatBot: http://127.0.0.1:5000
2. Click nút "🎨 Tạo ảnh"
3. Kiểm tra status - phải hiện "✅ Stable Diffusion đang chạy"

---

## 🐛 NẾU VẪN LỖI:

### Lỗi: "ModuleNotFoundError: No module named 'gradio'"
```powershell
pip install gradio fastapi uvicorn
```

### Lỗi: "RuntimeError: Torch not compiled with CUDA"
→ Cần GPU NVIDIA hoặc chạy CPU mode (rất chậm):
```powershell
python webui.py --api --skip-torch-cuda-test --no-half
```

### Lỗi: "AssertionError: Torch version is not compatible"
→ Reinstall torch:
```powershell
pip install torch==2.0.1 torchvision==0.15.2 --index-url https://download.pytorch.org/whl/cu118
```

---

## 📞 HƯỚNG DẪN CHO BẠN:

**Thử theo thứ tự:**

1. ✅ **Chạy webui.bat trực tiếp** (đơn giản nhất)
2. ⚠️ Nếu không được → Dùng `--skip-prepare-environment`
3. ⚠️ Nếu vẫn không → Tạo venv riêng
4. ⚠️ Cuối cùng → Tải bản build sẵn từ GitHub

**Cho tôi biết bạn muốn thử cách nào, hoặc lỗi gì tiếp theo nhé!** 😊
