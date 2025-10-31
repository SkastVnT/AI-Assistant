# 🚀 HƯỚNG DẪN CHẠY DỰ ÁN

## 🎯 **3 CÁCH CHẠY ĐƠN GIẢN NHẤT:**

### **1. 🌐 Web UI (KHUYÊN DÙNG)** 
```bash
# Chỉ cần chạy 1 lệnh:
RUN.bat
# Chọn 1, mở browser: http://localhost:5000
```
**✅ Ưu điểm**: Drag & drop files, giao diện đẹp, dễ sử dụng

### **2. 🐍 Command Line**
```bash
# Trực tiếp
python src\main.py

# Hoặc model cụ thể
python src\t5_model.py          # T5 AI (offline)  
python src\gemini_model.py      # Gemini AI (cần API key)
```
**✅ Ưu điểm**: Nhanh, trực tiếp, command line

### **3. 📊 Kiểm tra hệ thống**
```bash
python tools\system_check.py
```

---

## 🗂️ **CÁCH VỨT FILE:**

### **🗑️ Tự động cleanup:**
```bash
# Mở Web UI (http://localhost:5000)
# Click nút "🗑️ Dọn dẹp" 
# Xóa files > 1 giờ tuổi
```

### **🛠️ Manual cleanup:**
```bash
python file_manager.py
# Chọn option cleanup
```

### **📂 Thư mục chứa files:**
- **Audio input**: `data/audio/`
- **Results**: `data/results/`  
- **Logs**: `logs/`

---

## 🌐 **FLASK WEB UI FEATURES:**

### **✨ Giao diện đẹp:**
- 🎨 **Modern design** với gradient background
- 📱 **Responsive** - chạy tốt trên mobile
- 🎯 **Drag & drop** files dễ dàng
- 📊 **Real-time progress** tracking

### **🚀 Tính năng:**
- ✅ **Upload** audio files (MP3, WAV, M4A, FLAC, AAC, OGG, WMA)
- ✅ **4 models** lựa chọn: Smart, Fast, T5, Gemini
- ✅ **Real-time progress** với progress bar
- ✅ **Download results** as text file
- ✅ **Copy to clipboard** kết quả
- ✅ **Job history** theo dõi lịch sử
- ✅ **Auto cleanup** files cũ

### **🎯 Workflow:**
1. Mở `http://localhost:5000`
2. Drag & drop file audio 
3. Chọn model (Smart, Fast, T5, Gemini)
4. Click "🚀 Bắt đầu chuyển đổi"
5. Đợi progress bar (2-20 phút)
6. Copy hoặc download kết quả

---

## 📊 **MODELS COMPARISON:**

| Model | Thời gian | Chất lượng | Yêu cầu | Khuyên dùng |
|-------|-----------|------------|---------|-------------|
| **🏆 Smart** | 8-15 phút | ⭐⭐⭐⭐ | Offline | ✅ Mặc định |
| **⚡ Fast** | 2-5 phút | ⭐⭐⭐ | Offline | Nhanh nhất |
| **🤖 T5** | 10-20 phút | ⭐⭐⭐⭐ | Offline | AI fusion |
| **🌟 Gemini** | 8-15 phút | ⭐⭐⭐⭐⭐ | API key | Chất lượng cao nhất |

---

## 🛠️ **TROUBLESHOOTING:**

### **❌ Lỗi thường gặp:**

**"Virtual environment not found":**
```bash
python -m venv s2t
```

**"Flask not found":**
```bash
s2t\Scripts\activate
pip install flask
```

**"API key not configured" (Gemini):**
```bash
# Sửa file .env:
GEMINI_API_KEY=your_key_here
```

**"Permission denied":**
```bash
# Chạy CMD as Administrator
```

### **🔧 File paths issue:**
- Đảm bảo chạy từ thư mục gốc dự án
- Check file `src\main.py` có tồn tại không

---

## 🎉 **QUICK START SUMMARY:**

### **🥇 Cách NHANH NHẤT:**
```bash
1. Double-click: RUN.bat
2. Chọn: 1 (Web UI)  
3. Mở browser: http://localhost:5000
4. Drag & drop file audio
5. Click "Bắt đầu chuyển đổi"
```

### **🎯 File management:**
```bash
# Web UI: Click "🗑️ Dọn dẹp"
# Manual: python file_manager.py
```

**Web UI URL**: `http://localhost:5000` 🌐  
**Features**: Drag & drop, 4 models, progress tracking, download results 📊  
**Support**: MP3, WAV, M4A, FLAC, AAC, OGG, WMA (max 500MB) 📁