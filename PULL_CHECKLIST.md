# 🔍 KIỂM TRA REQUIREMENTS - CHUẨN BỊ PULL VỀ PC

**Ngày kiểm tra:** 31/10/2025  
**Branch:** Ver_1  
**Python version:** 3.10.6  

---

## ✅ TỔNG QUAN

Tất cả requirements.txt đã được cập nhật và **READY TO USE** khi pull về PC có sẵn branch Img2Img.

---

## 📦 1. ChatBot Service

**File:** `ChatBot/requirements.txt`

### ✅ Đã có sẵn (từ Img2Img):
- flask==3.0.0
- flask-cors==4.0.0
- python-dotenv==1.0.0
- openai
- google-generativeai
- Pillow
- requests
- torch, transformers, accelerate
- numpy

### 🆕 CẦN CÀI THÊM:
```bash
cd ChatBot
.\venv_chatbot\Scripts\activate
pip install werkzeug>=3.0.0 sentencepiece>=0.1.99 protobuf>=3.20.0 tqdm jsonschema pyyaml aiofiles
```

**Thời gian:** ~2-3 phút  
**Kích thước:** ~50MB

---

## 📊 2. Text2SQL Service

**File:** `Text2SQL Services/requirements.txt`

### ✅ Đã có sẵn:
- Flask
- python-dotenv
- google-generativeai
- requests
- pandas, numpy, scikit-learn

### 🆕 CẦN CÀI THÊM:
```bash
cd "Text2SQL Services"
.\venv_text2sql\Scripts\activate
pip install werkzeug>=3.0.0 clickhouse-connect>=0.7.7 sqlparse>=0.4.4 openpyxl>=3.1.0
```

**Thời gian:** ~1-2 phút  
**Kích thước:** ~30MB

---

## 🎤 3. Speech2Text Service

**File:** `Speech2Text Services/requirements.txt`

### ✅ ĐÃ ĐẦY ĐỦ - KHÔNG CẦN CÀI THÊM
- Requirements.txt đã hoàn chỉnh từ trước
- Tất cả dependencies đã được cài đặt

### ℹ️ Lưu ý:
- Nếu chưa có venv: Chạy `.\scripts\fix_dependencies.bat`
- Đảm bảo có PyTorch với CUDA 11.8

---

## 🎨 4. Stable Diffusion WebUI

**File:** `stable-diffusion-webui/requirements.txt`

### ✅ ĐÃ ĐẦY ĐỦ - KHÔNG CẦN CÀI THÊM
- Requirements.txt đã được cập nhật với Python 3.10.6 note
- Tất cả dependencies đã được cài từ branch Img2Img

### ℹ️ Lưu ý:
- PyTorch đã được comment (cài riêng)
- Nếu lỗi thiếu package nào, chỉ cần: `pip install <package-name>`

---

## 🚀 HƯỚNG DẪN PULL VÀ CHẠY

### Bước 1: Pull code
```bash
cd AI-Assistant
git checkout Ver_1
git pull origin Ver_1
```

### Bước 2: Cài thêm dependencies mới

**ChatBot:**
```bash
cd ChatBot
.\venv_chatbot\Scripts\activate
pip install werkzeug sentencepiece protobuf tqdm jsonschema pyyaml aiofiles
cd ..
```

**Text2SQL:**
```bash
cd "Text2SQL Services"
.\venv_text2sql\Scripts\activate
pip install werkzeug clickhouse-connect sqlparse openpyxl
cd ..
```

### Bước 3: Kiểm tra .env files
```bash
# Đảm bảo các file .env vẫn còn và đúng
ChatBot\.env
"Text2SQL Services"\.env
"Speech2Text Services"\app\config\.env
```

### Bước 4: Test chạy từng service

**ChatBot:**
```bash
cd ChatBot
.\venv_chatbot\Scripts\activate
python app.py
# Mở: http://localhost:5000
```

**Text2SQL:**
```bash
cd "Text2SQL Services"
.\venv_text2sql\Scripts\activate
python app.py
# Mở: http://localhost:5001
```

**Speech2Text:**
```bash
cd "Speech2Text Services"
.\app\s2t\Scripts\activate
python app\web_ui.py
# Mở: http://localhost:5002
```

**Stable Diffusion:**
```bash
cd stable-diffusion-webui
.\venv_sd\Scripts\activate
python webui.py --api
# Mở: http://localhost:7860
```

---

## ⚡ QUICK START (Nếu đã cài đủ)

### Chạy ChatBot + SD (Recommended):
```bash
.\scripts\startup\start_chatbot_with_sd.bat
```

### Chạy ChatBot only:
```bash
.\scripts\startup\start_chatbot_only.bat
```

---

## 🔧 XỬ LÝ LỖI THƯỜNG GẶP

### 1. "ModuleNotFoundError: No module named 'werkzeug'"
```bash
pip install werkzeug>=3.0.0
```

### 2. "ModuleNotFoundError: No module named 'sentencepiece'"
```bash
pip install sentencepiece
```

### 3. PyTorch CUDA issues
```bash
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 4. Port đã được sử dụng
```bash
# Tìm process đang dùng port
netstat -ano | findstr :5000

# Kill process
taskkill /PID <PID> /F
```

---

## 📝 TÓM TẮT

### ✅ ĐÃ SẴN SÀNG:
- Speech2Text Service: 100% ready
- Stable Diffusion WebUI: 100% ready
- ChatBot: 95% ready (thiếu vài utilities nhỏ)
- Text2SQL: 90% ready (thiếu database connector)

### 🆕 CẦN CÀI THÊM:
- **ChatBot**: 8 packages nhỏ (~50MB, 2-3 phút)
- **Text2SQL**: 4 packages nhỏ (~30MB, 1-2 phút)
- **Tổng thời gian cài đặt**: ~5 phút
- **Tổng dung lượng download**: ~80MB

### 🎯 KẾT LUẬN:
**PC của bạn sẽ chạy được NGAY sau khi pull và cài thêm vài packages nhỏ!**

Không cần cài lại PyTorch, không cần download models lại, chỉ cần:
1. Pull code
2. Cài ~12 packages nhỏ (5 phút)
3. Chạy!

---

## 📞 HỖ TRỢ

Nếu gặp vấn đề:
1. Check Python version: `python --version` (phải là 3.10.6)
2. Check CUDA: `nvidia-smi` (phải có CUDA 11.8)
3. Check venv activated: dòng lệnh phải có `(venv_*)` ở đầu
4. Xem logs error và search Google hoặc hỏi tôi

---

**Made with ❤️ for smooth deployment**
