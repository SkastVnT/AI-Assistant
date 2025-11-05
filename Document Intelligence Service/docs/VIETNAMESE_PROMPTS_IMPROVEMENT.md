# 🇻🇳 CẢI THIỆN PROMPT AI CHO TIẾNG VIỆT

## 📋 TỔNG QUAN

Đã cải thiện toàn bộ prompt AI để phù hợp với:
- ✅ Ngữ cảnh Việt Nam
- ✅ Loại văn bản Việt Nam
- ✅ Cách diễn đạt tiếng Việt tự nhiên
- ✅ Các trường thông tin phổ biến ở VN

---

## 🎯 CÁC CẢI TIẾN CHÍNH

### 1. **PHÂN LOẠI VÀN BẢN** (`classify_document`)

#### ❌ Trước:
```
Classify this Vietnamese document...
Return ONLY the category name...
```

#### ✅ Sau:
```
📋 DANH MỤC:
- CMND/CCCD: Chứng minh nhân dân, Căn cước công dân
- Hộ chiếu: Passport
- Bằng lái xe: Giấy phép lái xe
- Hóa đơn: Hóa đơn VAT, hóa đơn điện tử
- Bảng lương: Phiếu lương, bảng thanh toán
- CV/Hồ sơ: Hồ sơ xin việc
...

🎯 YÊU CẦU:
- Chỉ trả về TÊN DANH MỤC
- Không giải thích
```

**Lợi ích:**
- Thêm nhiều loại văn bản VN (Bằng lái, Bảng lương, CV...)
- Mô tả chi tiết từng loại
- Icons giúp dễ đọc
- Hướng dẫn rõ ràng hơn

---

### 2. **TRÍCH XUẤT THÔNG TIN** (`extract_information`)

#### ❌ Trước:
```
Extract key information...
For ID Card, extract: full_name, id_number...
Return ONLY valid JSON
```

#### ✅ Sau:
```
🎯 HƯỚNG DẪN THEO LOẠI VÀN BẢN:

📇 CMND/CCCD:
- ho_ten: Họ và tên đầy đủ
- so_cmnd_cccd: Số CMND/CCCD
- ngay_sinh: Ngày tháng năm sinh (DD/MM/YYYY)
- gioi_tinh: Nam/Nữ
- noi_sinh: Nơi sinh
- que_quan: Quê quán
- dia_chi_thuong_tru: Địa chỉ thường trú
- ngay_cap: Ngày cấp
- noi_cap: Nơi cấp

🧾 HÓA ĐƠN:
- ten_cong_ty, ma_so_thue, so_hoa_don
- hang_hoa_dich_vu, tong_tien, tong_tien_chu

📄 HỢP ĐỒNG:
- so_hop_dong, loai_hop_dong
- ben_a, ben_b (tên, địa chỉ, người đại diện)
- ngay_ky, hieu_luc

⚠️ LƯU Ý:
- Giá trị là chuỗi tiếng Việt có dấu
- Nếu không tìm thấy: null
```

**Lợi ích:**
- Rõ ràng từng trường thông tin
- Format chuẩn Việt Nam (DD/MM/YYYY)
- Tên field tiếng Việt không dấu
- Hướng dẫn chi tiết cho từng loại văn bản

---

### 3. **TÓM TẮT VÀN BẢN** (`summarize_document`)

#### ❌ Trước:
```
Tóm tắt văn bản này bằng tiếng Việt...
Tập trung vào các thông tin quan trọng nhất.
```

#### ✅ Sau:
```
📝 TÓM TẮT VÀN BẢN TIẾNG VIỆT

🎯 YÊU CẦU:
- Tóm tắt trong tối đa 5 câu
- Tiếng Việt có dấu, chuẩn chính tả
- Tập trung: ai, cái gì, khi nào, ở đâu, tại sao
- Giữ nguyên số liệu, tên riêng
- Viết súc tích, dễ hiểu
- Không thêm ý kiến cá nhân

💡 TÓM TẮT:
```

**Lợi ích:**
- Cấu trúc 5W1H rõ ràng
- Nhấn mạnh giữ nguyên thông tin quan trọng
- Yêu cầu chính tả chuẩn
- Format đẹp, dễ đọc

---

### 4. **TRẢ LỜI CÂU HỎI** (`answer_question`)

#### ❌ Trước:
```
Dựa vào văn bản sau, trả lời câu hỏi...
Trả lời ngắn gọn, chính xác...
```

#### ✅ Sau:
```
❓ TRẢ LỜI CÂU HỎI VỀ VÀN BẢN

📄 NỘI DUNG VÀN BẢN:
[text]

🎯 CÂU HỎI:
[question]

📝 HƯỚNG DẪN:
- Trả lời bằng tiếng Việt có dấu
- Dựa CHÍNH XÁC vào văn bản
- Trích dẫn cụ thể
- Nếu không tìm thấy: "Không tìm thấy..."
- Không suy đoán

💬 TRẢ LỜI:
```

**Lợi ích:**
- Hướng dẫn chi tiết cách trả lời
- Xử lý trường hợp không có thông tin
- Nhấn mạnh độ chính xác
- Template trả lời rõ ràng

---

### 5. **DỊCH VÀN BẢN** (`translate_document`)

#### ❌ Trước:
```
Translate this document to English.
Preserve the original meaning...
```

#### ✅ Sau:
```
🌐 DỊCH VÀN BẢN

🎯 YÊU CẦU:
- Dịch sang: tiếng Anh (English)
- Giữ nguyên ý nghĩa và ngữ cảnh
- Dịch tự nhiên, không máy móc
- Giữ nguyên tên riêng, địa danh
- Giữ format đoạn văn
- Chỉ trả về BẢN DỊCH

✨ BẢN DỊCH:
```

**Lợi ích:**
- Tên ngôn ngữ song ngữ (VN + EN)
- Yêu cầu dịch tự nhiên
- Hướng dẫn xử lý tên riêng
- Format rõ ràng

---

### 6. **SO SÁNH VÀN BẢN** (`compare_documents`)

#### ❌ Trước:
```
So sánh hai văn bản:
1. Điểm giống
2. Điểm khác
3. Thay đổi quan trọng
```

#### ✅ Sau:
```
🔄 SO SÁNH HAI VÀN BẢN

🎯 YÊU CẦU PHÂN TÍCH:

1️⃣ ĐIỂM GIỐNG NHAU:
   - Nội dung tương đồng
   - Thông tin trùng khớp

2️⃣ ĐIỂM KHÁC BIỆT:
   - Thông tin khác nhau
   - Nội dung thêm/bớt
   - Số liệu thay đổi

3️⃣ THAY ĐỔI QUAN TRỌNG:
   - Con số, ngày tháng
   - Tên, địa chỉ
   - Điều khoản, quy định

📊 KẾT QUẢ SO SÁNH:
```

**Lợi ích:**
- Cấu trúc 3 phần rõ ràng
- Chi tiết từng loại thay đổi
- Icons + Emoji dễ phân biệt
- Format output chuẩn

---

### 7. **PHÂN TÍCH CHUYÊN SÂU** (`generate_insights`)

#### ❌ Trước:
```
Analyze and provide:
1. Main purpose
2. Key points
3. Important dates
4. Parties involved
5. Actions required
```

#### ✅ Sau:
```
💡 PHÂN TÍCH CHUYÊN SÂU

🎯 MỤC ĐÍCH CHÍNH:
[Xác định mục đích/đối tượng]

📌 ĐIỂM QUAN TRỌNG (3-5 điểm):
1. [...]
2. [...]

📅 NGÀY THÁNG & SỐ LIỆU:
- [...]

👥 CÁC BÊN LIÊN QUAN:
- [...]

⚡ HÀNH ĐỘNG CẦN THỰC HIỆN:
- [...]

⚠️ LƯU Ý ĐẶC BIỆT:
- [...]

🔍 PHÂN TÍCH:
```

**Lợi ích:**
- Cấu trúc 6 phần chi tiết
- Icons riêng cho từng phần
- Template đầy đủ
- Dễ đọc, dễ hiểu

---

## 🎨 THIẾT KẾ PROMPT MỚI

### **Nguyên tắc:**

1. **Icons & Emoji** 📱
   - Dễ nhận diện
   - Tăng tính thẩm mỹ
   - Phân biệt các phần

2. **Cấu trúc rõ ràng** 📋
   - Tiêu đề lớn
   - Phân mục chi tiết
   - Yêu cầu cụ thể

3. **Tiếng Việt tự nhiên** 🇻🇳
   - Dùng từ ngữ Việt Nam
   - Context địa phương
   - Thuật ngữ phổ biến

4. **Ví dụ cụ thể** 💡
   - Template output
   - Format mong muốn
   - Trường hợp đặc biệt

---

## 📊 SO SÁNH TRƯỚC/SAU

| Tiêu chí | Trước ❌ | Sau ✅ |
|----------|---------|--------|
| Ngôn ngữ | Mixed EN/VN | 100% Vietnamese |
| Cấu trúc | Đơn giản | Chi tiết, rõ ràng |
| Icons | Không | Có emojis |
| Hướng dẫn | Ngắn gọn | Đầy đủ, cụ thể |
| Context VN | Ít | Phù hợp văn hóa VN |
| Loại văn bản | 8 loại | 12+ loại |
| Trường thông tin | Cơ bản | Đầy đủ VN |
| Output format | Mờ nhạt | Template rõ ràng |

---

## 🚀 CÁCH SỬ DỤNG

### **Không cần làm gì!**

Code đã tự động dùng prompt mới:

```python
# Classification
result = gemini.classify_document(text)
# → Dùng prompt tiếng Việt mới ✅

# Extraction  
result = gemini.extract_information(text, "CMND/CCCD")
# → Dùng template VN chi tiết ✅

# Summary
result = gemini.summarize_document(text, max_sentences=5)
# → Dùng cấu trúc 5W1H ✅
```

---

## 🎯 KẾT QUẢ MONG ĐỢI

### **Phân loại chính xác hơn:**
```
Input: [Ảnh CCCD]
Output: "CMND/CCCD" ✅
(Không phải "ID Card" hay "Other")
```

### **Trích xuất đầy đủ hơn:**
```json
{
  "ho_ten": "Nguyễn Văn A",
  "so_cmnd_cccd": "001234567890",
  "ngay_sinh": "01/01/1990",
  "noi_sinh": "Hà Nội",
  "que_quan": "Nam Định",
  "dia_chi_thuong_tru": "123 Láng Hạ, Đống Đa, Hà Nội",
  "ngay_cap": "01/01/2020",
  "noi_cap": "Cục Cảnh sát ĐKQL cư trú và DLQG về dân cư"
}
```

### **Tóm tắt tự nhiên hơn:**
```
Văn bản là hợp đồng lao động giữa Công ty ABC và ông Nguyễn Văn A, 
được ký ngày 01/01/2024 với thời hạn 2 năm. Chức vụ là Kỹ sư phần mềm 
với mức lương 20 triệu đồng/tháng. Hợp đồng có hiệu lực từ 01/02/2024. 
Các điều khoản về bảo mật và không cạnh tranh được quy định chi tiết.
```

---

## 📝 FILES CHANGED

✅ **src/ai/gemini_client.py** - 7 methods:
- `classify_document()` - Thêm nhiều loại văn bản VN
- `extract_information()` - Template chi tiết cho từng loại
- `summarize_document()` - Cấu trúc 5W1H
- `answer_question()` - Hướng dẫn trả lời rõ ràng
- `translate_document()` - Tên ngôn ngữ song ngữ
- `compare_documents()` - Phân tích 3 cấp độ
- Language names update

✅ **src/ai/document_analyzer.py** - 3 methods:
- `validate_document()` - Checklist kiểm tra VN
- `generate_insights()` - Template phân tích 6 phần
- `extract_fields()` - Hướng dẫn JSON rõ ràng

---

## 🧪 TESTING

### **Test nhanh:**

1. **Restart service:**
   ```powershell
   .\restart_service.bat
   ```

2. **Upload văn bản tiếng Việt:**
   - CMND/CCCD
   - Hóa đơn
   - Hợp đồng

3. **Kiểm tra kết quả:**
   - Phân loại đúng loại?
   - Trích xuất đầy đủ?
   - Tóm tắt tự nhiên?

---

## 💡 LỢI ÍCH

### ✅ **Cho AI:**
- Hiểu context Việt Nam tốt hơn
- Nhận diện loại văn bản chính xác hơn
- Trích xuất đúng format VN

### ✅ **Cho User:**
- Kết quả bằng tiếng Việt tự nhiên
- Thông tin đầy đủ, chi tiết
- Dễ đọc, dễ hiểu

### ✅ **Cho Developer:**
- Code dễ maintain
- Prompt tự document
- Dễ mở rộng thêm loại văn bản

---

## 📚 EXAMPLES

### **Example 1: CMND/CCCD**
```
Input: [Ảnh chụp CCCD]

Classification: "CMND/CCCD" ✅

Extraction:
{
  "ho_ten": "Nguyễn Thị B",
  "so_cmnd_cccd": "001987654321",
  "ngay_sinh": "15/03/1995",
  "gioi_tinh": "Nữ",
  "noi_sinh": "TP Hồ Chí Minh",
  "que_quan": "Long An",
  "dia_chi_thuong_tru": "456 Nguyễn Trãi, Quận 5, TP.HCM"
}
```

### **Example 2: Hóa đơn**
```
Input: [Ảnh hóa đơn VAT]

Classification: "Hóa đơn" ✅

Extraction:
{
  "ten_cong_ty": "Công ty TNHH ABC",
  "ma_so_thue": "0123456789",
  "so_hoa_don": "AB/24-00001",
  "ngay_hoa_don": "05/11/2025",
  "tong_tien": "5,000,000",
  "tong_tien_chu": "Năm triệu đồng chẵn"
}
```

---

## 🎓 BEST PRACTICES

1. **Test với văn bản thực tế VN**
2. **Kiểm tra encoding tiếng Việt**
3. **Verify format output**
4. **Monitor AI response quality**
5. **Collect user feedback**

---

**Version:** 1.5.2  
**Date:** 2025-11-05  
**Status:** ✅ READY TO USE

🇻🇳 **PROMPTS ĐÃ ĐƯỢC TỐI ƯU CHO TIẾNG VIỆT!** 🎉
