# 🚨 FIX LỖI "ACCESS DENIED" KHI CÀI STABLE DIFFUSION

## ❌ VẤN ĐỀ:

```
ERROR: Could not install packages due to an OSError: [WinError 5] Access is denied
```

**Nguyên nhân:** File Pillow đang được sử dụng bởi ChatBot đang chạy → Không thể gỡ/cài lại.

---

## ✅ GIẢI PHÁP ĐƠN GIẢN NHẤT:

### Option 1: Chạy SD KHÔNG cài đặt lại (KHUYẾN NGHỊ)

**Bước 1:** Đóng TẤT CẢ terminal Python đang chạy
- Stop ChatBot (Ctrl+C trong terminal ChatBot)
- Đóng tất cả cửa sổ Python

**Bước 2:** Chạy script mới:
```
Double-click: start_sd_no_install.bat
```

Script này sẽ:
- Skip bước cài đặt (tránh conflict)
- Chạy trực tiếp với dependencies có sẵn
- Nếu thiếu gì sẽ báo lỗi cụ thể

---

### Option 2: Cài trong PowerShell Administrator

**Bước 1:** Đóng HẾT Python processes:
```powershell
taskkill /F /IM python.exe
```

**Bước 2:** Mở PowerShell **VỚI QUYỀN ADMINISTRATOR**
- Right-click PowerShell → Run as Administrator

**Bước 3:** Chạy:
```powershell
cd i:\AI-Assistant\stable-diffusion-webui
python launch.py --api --xformers --no-half-vae --disable-safe-unpickle
```

---

### Option 3: Dùng webui-user.bat có sẵn

**Bước 1:** Mở file `webui-user.bat` trong notepad:
```
i:\AI-Assistant\stable-diffusion-webui\webui-user.bat
```

**Bước 2:** Thêm dòng này vào (trước @echo off):
```batch
set COMMANDLINE_ARGS=--api --xformers --no-half-vae --disable-safe-unpickle
```

**Bước 3:** Save và double-click `webui-user.bat`

---

### Option 4: Cài dependencies riêng (TỪ TỪ)

Nếu SD cần thêm packages:

```powershell
# Đóng ChatBot trước!
taskkill /F /IM python.exe

# Cài từng cái cần thiết
pip install gradio==3.41.2
pip install fastapi==0.94.0
pip install uvicorn
pip install transformers
```

Sau đó chạy `start_sd_no_install.bat`

---

## 🎯 CÁCH NHANH NHẤT (KHUYẾN NGHỊ):

### Dùng Stable Diffusion với --skip-prepare-environment:

**1. Đóng ChatBot:**
```
Ctrl+C trong terminal ChatBot
```

**2. Chạy ngay:**
```
Double-click: start_sd_no_install.bat
```

**3. Nếu báo thiếu module nào:**
```powershell
# Ví dụ: No module named 'gradio'
pip install gradio==3.41.2
```

Rồi chạy lại `start_sd_no_install.bat`

---

## 🔍 KIỂM TRA CÁC PROCESS ĐANG CHẠY:

### Xem Python processes:
```powershell
tasklist | findstr python
```

### Kill tất cả Python:
```powershell
taskkill /F /IM python.exe
```

### Kill tất cả Python và pip:
```powershell
taskkill /F /IM python.exe
taskkill /F /IM pip.exe
timeout /t 2
```

---

## 📋 CHECKLIST:

- [ ] Đã đóng ChatBot (Ctrl+C)
- [ ] Đã kill tất cả python.exe
- [ ] Chờ 5 giây
- [ ] Chạy `start_sd_no_install.bat`
- [ ] Nếu thiếu module → Cài riêng → Chạy lại

---

## 💡 LƯU Ý:

**Pillow version conflict:**
- ChatBot cần: Pillow 12.0.0 (mới nhất)
- SD cần: Pillow 9.5.0 (cũ hơn)

→ **Giải pháp:** Dùng 2 môi trường riêng HOẶC dùng Pillow mới cho cả 2

**Để dùng Pillow mới:**
```powershell
# Downgrade lại nếu SD báo lỗi
pip install Pillow==12.0.0

# Sau đó chạy SD với --skip-prepare-environment
```

---

## 🚀 THỬ NGAY:

```batch
REM 1. Stop ChatBot
REM Nhan Ctrl+C trong terminal ChatBot

REM 2. Chay SD
start_sd_no_install.bat

REM 3. Neu OK, kiem tra
REM http://127.0.0.1:7860
```

---

## ❓ NẾU VẪN LỖI:

Cho tôi biết:
1. **Lỗi gì khi chạy `start_sd_no_install.bat`?**
2. **Có module nào thiếu không?**
3. **SD WebUI đã từng chạy được trước đây chưa?**

Tôi sẽ hướng dẫn cài từng module cần thiết! 😊

---

**TL;DR:**
1. Ctrl+C ChatBot
2. Run: `start_sd_no_install.bat`  
3. Enjoy! 🎨
