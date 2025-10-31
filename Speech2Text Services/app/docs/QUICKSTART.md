# 📋 QUICK START GUIDE

## 🎯 FILE QUAN TRỌNG NHẤT

### ⭐ TOP 5 FILES BẠN CẦN BIẾT:

1. **run_dual_models.py** 🏆
   - Chất lượng tốt nhất
   - Không bỏ sót thông tin
   - Dùng cho công việc quan trọng

2. **run_whisper_with_gemini.py** ⚡
   - Nhanh nhất (2 phút)
   - Chất lượng tốt
   - Dùng hàng ngày

3. **Phowhisper.py** 🇻🇳
   - Chuyên tiếng Việt
   - Giọng địa phương
   - Backup option

4. **.env** 🔐
   - Chứa API key
   - **QUAN TRỌNG** - Không chia sẻ

5. **check_health.py** 📊
   - Phân tích kết quả
   - So sánh models

---

## 🚀 CHẠY NHANH 3 BƯỚC

```powershell
# Bước 1: Activate
.\s2t\Scripts\activate

# Bước 2: Chỉnh file .env (nếu chưa)
# GEMINI_API_KEY=your_key
# AUDIO_PATH=path/to/audio.mp3

# Bước 3: Chạy
python run_dual_models.py
```

---

## 📂 CẤU TRÚC ĐƠN GIẢN

```
📦 d:\WORK\s2t\
├── 🔥 run_dual_models.py          ← CHẠY CÁI NÀY
├── 🔥 run_whisper_with_gemini.py  ← Hoặc cái này (nhanh)
├── 🔥 Phowhisper.py               ← Hoặc cái này (PhoWhisper)
├── 🔐 .env                         ← Cấu hình API key
├── 📊 check_health.py              ← Kiểm tra kết quả
└── 📂 result/                      ← Kết quả ở đây
    ├── dual/      ← 🏆 Kết quả tốt nhất
    ├── gemini/    ← Cleaned
    └── raw/       ← Raw
```

---

## 💡 TIPS

### ✅ Khi nào dùng gì?

| Tình huống | Dùng script | Lý do |
|------------|-------------|-------|
| Giao dịch, CSKH quan trọng | `run_dual_models.py` | Không bỏ sót info |
| Test nhanh, demo | `run_whisper_with_gemini.py` | Nhanh 2 phút |
| Giọng địa phương mạnh | `Phowhisper.py` | Chuyên Việt |

### 📝 Kết quả nằm ở đâu?

- 🏆 **Tốt nhất**: `result/dual/dual_models_*.txt`
- 📝 **Cleaned**: `result/gemini/*_cleaned_*.txt`
- 📄 **Raw**: `result/raw/*_raw_*.txt`

---

## ⚠️ LƯU Ý QUAN TRỌNG

1. **File .env** - KHÔNG commit lên Git (đã có .gitignore bảo vệ)
2. **Thư mục No use/** - Các file cũ, không dùng nữa
3. **Virtual env s2t/** - Luôn activate trước khi chạy

---

## 🎯 KẾT QUẢ MẪU

### Dual Model đã bắt được:
- ✅ Mã đơn: `G-I-V-B-B-B-B-B-I-6-9-F-F`
- ✅ Tên: Hoàng Đông, Lisa Thạch
- ✅ Địa chỉ: Duyên Hải, Trà Vinh
- ✅ Ngày: Mùng 4

### Whisper (nhanh) đã bắt được:
- ✅ Mã đơn: `G-I-V-B-B-B-B-B-I-6-9-F-F`
- ✅ Nội dung chính xác
- ⚠️ Có thể thiếu vài chi tiết nhỏ

---

## 🆘 CẦN TRỢ GIÚP?

Đọc file **README.md** để biết chi tiết đầy đủ!

---

**Version**: 1.0  
**Updated**: Oct 14, 2025
