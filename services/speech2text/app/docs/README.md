# 🎙️ Vietnamese Speech-to-Text System

Hệ thống nhận dạng giọng nói tiếng Việt sử dụng Whisper, PhoWhisper và Gemini AI.

## 📊 TỔNG QUAN HỆ THỐNG

### 🎯 Mục tiêu
- Nhận dạng chính xác giọng nói tiếng Việt (tất cả vùng miền)
- Xử lý hội thoại phức tạp (giao dịch, CSKH, cuộc gọi...)
- Không bỏ sót thông tin quan trọng (mã đơn, số điện thoại, địa danh...)
- Tự động làm sạch và chuẩn hóa transcript

### 🏗️ Kiến trúc
```
Audio Input → Audio Preprocessing → AI Models → Gemini Post-Processing → Clean Output
                                    ↓
                        ┌───────────┴───────────┐
                        │                       │
                  Whisper large-v3      PhoWhisper-large
                  (Cấu trúc tốt)        (Chuyên tiếng Việt)
                        │                       │
                        └───────────┬───────────┘
                                    ↓
                              Gemini AI Fusion
                          (Chọn tốt nhất từ cả 2)
```

### ⚡ QUICK START

**Cách 1: Chạy trực tiếp (Windows)**
```bash
.\run.bat
# Hoặc PowerShell
.\run.ps1
```

**Cách 2: Chạy thủ công**
```bash
.\s2t\Scripts\Activate.ps1
python run_dual_models.py
```

### 🛠️ Yêu Cầu Hệ Thống
- **Python**: 3.10+
- **GPU**: NVIDIA GPU với CUDA 12.1+ (khuyến nghị RTX 3060 trở lên)
- **RAM**: Tối thiểu 16GB
- **Disk**: 10GB trống cho models

---

## 📁 CẤU TRÚC PROJECT

```
d:\WORK\s2t\
├── 🔥 SCRIPTS CHÍNH
│   ├── run_dual_models.py          ⭐⭐⭐⭐⭐ [BEST] Dual Model Fusion
│   ├── Phowhisper.py               ⭐⭐⭐⭐ PhoWhisper Optimized
│   ├── run_whisper_with_gemini.py  ⭐⭐⭐⭐ Whisper + Gemini (Fast)
│   └── check_health.py             ⭐⭐⭐ Phân tích kết quả
│
├── 🔐 CẤU HÌNH
│   ├── .env                        API Keys & Config
│   ├── .gitignore                  Git security
│   └── Dockerfile                  Container setup
│
├── 📂 OUTPUTS
│   ├── result/
│   │   ├── dual/                   🏆 Kết quả fusion (tốt nhất)
│   │   ├── gemini/                 📝 Cleaned transcripts
│   │   └── raw/                    📄 Raw transcripts
│   └── audio/                      🎵 Processed audio files
│
├── 🗂️ ARCHIVED
│   └── No use/
│       ├── audio_preprocessing.py  (Đã tích hợp vào scripts chính)
│       ├── PhoWhisper_optimized.py (Duplicate - không dùng)
│       └── run_whisper_vietnamese.py (Demo cũ)
│
└── 🐍 ENVIRONMENT
    └── s2t/                        Python virtual environment
```

---

## 🚀 HƯỚNG DẪN SỬ DỤNG

### 1️⃣ Cài đặt môi trường

```powershell
# Activate virtual environment
.\s2t\Scripts\activate

# Kiểm tra packages (nếu cần cài thêm)
pip install faster-whisper transformers torch google-generativeai
pip install librosa soundfile scipy python-dotenv
```

### 2️⃣ Cấu hình API Key

Chỉnh sửa file `.env`:
```env
GEMINI_API_KEY=your_api_key_here
AUDIO_PATH=path/to/your/audio.mp3
```

### 3️⃣ Chạy transcription

#### 🏆 Option 1: DUAL MODEL (Khuyến nghị - Chất lượng cao nhất)
```powershell
python run_dual_models.py
```
**Đặc điểm:**
- ✅ Kết hợp Whisper large-v3 + PhoWhisper-large
- ✅ Gemini AI fusion thông minh
- ✅ KHÔNG BỎ SÓT thông tin (mã đơn, số...)
- ⏱️ Thời gian: ~17 phút
- 📊 Độ chính xác: **Cao nhất**

**Kết quả mẫu:**
- Mã đơn hàng: `G-I-V-B-B-B-B-B-I-6-9-F-F` ✅
- Tên người: Hoàng Đông, Lisa Thạch ✅
- Địa danh: Duyên Hải, Trà Vinh ✅

#### ⚡ Option 2: WHISPER + GEMINI (Nhanh nhất)
```powershell
python run_whisper_with_gemini.py
```
**Đặc điểm:**
- ✅ Whisper large-v3 + Gemini AI
- ✅ Chất lượng tốt
- ⏱️ Thời gian: ~2 phút
- 📊 Độ chính xác: Tốt

#### 🇻🇳 Option 3: PHOWHISPER (Chuyên tiếng Việt)
```powershell
python Phowhisper.py
```
**Đặc điểm:**
- ✅ PhoWhisper-large (chuyên biệt tiếng Việt)
- ✅ Tốt cho giọng địa phương
- ⏱️ Thời gian: ~3 phút
- 📊 Độ chính xác: Tốt cho accent Việt

---

## 📊 SO SÁNH HIỆU SUẤT

| Model | Thời gian | Mã đơn | Tên/Địa danh | Chất lượng | Use Case |
|-------|-----------|--------|--------------|------------|----------|
| **Dual Model** | 17 phút | ✅ Bắt được | ✅ Chính xác | 🏆 Xuất sắc | Quan trọng, cần chính xác cao |
| **Whisper + Gemini** | 2 phút | ✅ Bắt được | ✅ Tốt | ⭐⭐⭐⭐ | Cần nhanh, chất lượng tốt |
| **PhoWhisper** | 3 phút | ⚠️ Có thể thiếu | ✅ Tốt | ⭐⭐⭐ | Giọng địa phương mạnh |

---

## 📝 OUTPUT FILES

### Dual Model Output:
```
result/dual/
└── dual_models_[filename]_[timestamp].txt
    ├── WHISPER LARGE-V3 RESULT
    ├── PHOWHISPER-LARGE RESULT
    └── 🏆 FUSED RESULT (BEST OF BOTH)

result/gemini/
└── dual_fused_[filename]_[timestamp].txt
    └── Clean version (chỉ kết quả fusion)
```

### Single Model Output:
```
result/raw/
└── [model]_raw_[filename]_[timestamp].txt
    └── Raw transcript from model

result/gemini/
└── [model]_cleaned_[filename]_[timestamp].txt
    └── Cleaned by Gemini AI
```

---

## 🛠️ TROUBLESHOOTING

### ❌ Lỗi: "GEMINI_API_KEY not found"
**Giải pháp:** Kiểm tra file `.env` có chứa API key đúng

### ❌ Lỗi: "CUDA not available"
**Giải pháp:** Script tự động fallback về CPU, không ảnh hưởng chức năng

### ❌ Lỗi: "File not found"
**Giải pháp:** Kiểm tra đường dẫn trong `.env` hoặc file có tồn tại không

### ❌ Kết quả thiếu thông tin
**Giải pháp:** Dùng `run_dual_models.py` để có kết quả đầy đủ nhất

---

## 📈 PHÂN TÍCH KẾT QUẢ

Chạy script phân tích:
```powershell
python check_health.py
```

Kết quả bao gồm:
- 📊 Thống kê từ, ký tự
- ❌ Đếm lỗi "unk" tokens
- ⏱️ Thời gian xử lý
- 🎯 Quality score
- 💡 Khuyến nghị model phù hợp

---

## 🔐 BẢO MẬT

### ⚠️ Files KHÔNG được commit lên Git:
- `.env` - Chứa API keys
- `s2t/` - Virtual environment
- `result/` - Output files
- `audio/` - Processed audio
- `models/` - Downloaded models

### ✅ `.gitignore` đã cấu hình bảo vệ các file này

---

## 🎯 KHUYẾN NGHỊ SỬ DỤNG

### 📌 Cho dự án QUAN TRỌNG (CSKH, Giao dịch):
```powershell
python run_dual_models.py
```
➡️ Đảm bảo **KHÔNG BỎ SÓT** thông tin

### ⚡ Cho xử lý NHANH (Demo, Test):
```powershell
python run_whisper_with_gemini.py
```
➡️ Cân bằng tốc độ & chất lượng

### 🇻🇳 Cho giọng ĐỊA PHƯƠNG mạnh:
```powershell
python Phowhisper.py
```
➡️ Chuyên biệt tiếng Việt

---

## 📞 LIÊN HỆ & HỖ TRỢ

- 📧 Email: your_email@example.com
- 📝 Issues: Tạo issue trên GitHub
- 📚 Docs: Xem file này

---

## 📜 LICENSE

MIT License - Sử dụng tự do

---

## 🎉 CREDITS

- **Whisper**: OpenAI
- **PhoWhisper**: VinAI Research
- **Gemini AI**: Google
- **faster-whisper**: Systran

---

**🚀 Version**: 1.0.0  
**📅 Last Updated**: October 14, 2025  
**✨ Status**: Production Ready
