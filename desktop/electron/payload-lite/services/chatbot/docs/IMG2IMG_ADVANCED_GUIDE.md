# 🖼️ Advanced Img2Img System - User Guide

## Tổng quan
Hệ thống Img2Img nâng cao cho phép tạo ảnh từ hình ảnh gốc với trích xuất đặc trưng tự động và khả năng lọc chi tiết.

## Cách sử dụng

### 1. Mở Tool
Có 2 cách:
- **Cách 1**: Click icon 🎨 "Tạo ảnh" → Chọn tab "🖼️ Tạo ảnh theo hình ảnh"
- **Cách 2**: Click button **"🖼️ Tạo ảnh bằng Upload"** trong sidebar (tự động mở tab Img2Img)

### 2. Upload Hình Ảnh
- Click vào khung upload hoặc kéo thả ảnh vào
- Hỗ trợ: JPG, PNG, WebP
- Preview hiển thị ngay sau khi upload

### 3. Trích Xuất Đặc Trưng
- Click **"🔬 Trích xuất đặc trưng"**
- **Deep Thinking Mode**: Check để trích xuất chi tiết hơn (50 tags thay vì 30)
- Đặc trưng được phân loại theo **8 categories**:
  - 💇 **Tóc**: kiểu tóc, màu tóc, phụ kiện tóc
  - 👁️ **Mắt**: màu mắt, hình dạng, biểu cảm
  - 👄 **Miệng**: nụ cười, biểu cảm miệng
  - 😊 **Khuôn mặt**: sẹo, nốt ruồi, má hồng, makeup
  - 👑 **Phụ kiện**: kính, hoa tai, nón, mặt nạ
  - 👔 **Quần áo**: áo, váy, đồng phục
  - 🧍 **Cơ thể**: tư thế, vị trí
  - 🏞️ **Background**: nền, môi trường
  - 🎨 **Style**: chất lượng, phong cách vẽ

### 4. Lọc Đặc Trưng
Có **2 cách lọc**:
- **Lọc cả category**: Check vào checkbox category để loại bỏ toàn bộ (VD: bỏ hết tóc)
- **Lọc từng tag**: Click vào tag riêng lẻ để loại bỏ (VD: chỉ bỏ "black hair")

**Tip**: 
- Tags bị lọc sẽ có màu xám và gạch ngang
- Click lại để bỏ lọc

### 5. Cấu Hình Generation

#### Prompt & Negative
- **Prompt bổ sung**: Điều chỉnh bổ sung (VD: "pink hair, red eyes")
  - 🎲 Random: Tạo prompt ngẫu nhiên
- **Negative Prompt**: Những gì KHÔNG muốn có
  - 🎲 Random: Tạo negative prompt ngẫu nhiên

#### Kích Thước Ảnh
- **Width/Height**: 512px → 1920px (FHD)
- Mặc định: 768x768
- Khuyến nghị: 768x768 hoặc 1024x1024 cho anime

#### Advanced Settings
- **Denoising Strength** (0.0-1.0): Mức độ thay đổi từ ảnh gốc
  - 0.4-0.6: Giữ lại nhiều đặc điểm gốc
  - 0.7-0.8: Thay đổi nhiều hơn
  - 0.9-1.0: Gần như tạo mới hoàn toàn
  
- **Feature Weight** (0-100%): Tỷ lệ giữa đặc trưng và prompt
  - 80%: Giữ 80% đặc trưng ảnh gốc, 20% prompt người dùng
  - 50%: Cân bằng giữa features và prompt
  - 20%: Ưu tiên prompt người dùng hơn
  - 100%: Chỉ dùng đặc trưng, bỏ qua prompt

- **Steps**: Số bước tạo (30 khuyến nghị cho img2img)
- **CFG Scale**: Độ tuân theo prompt (7-12 khuyến nghị)

### 6. Generate
- Click **"🎨 Tạo ảnh từ hình ảnh"**
- Đợi model xử lý (10-60 giây tùy kích thước)
- Ảnh kết quả hiển thị bên dưới
- Có thể **"💬 Gửi vào Chat"** hoặc **"📥 Tải xuống"**

## Workflow Ví Dụ

### Ví dụ 1: Đổi màu tóc & mắt
1. Upload ảnh anime girl với tóc đen, mắt đen
2. Extract features → Thấy tags: "black hair", "black eyes"
3. **Không lọc gì**, chỉ thêm prompt: "pink hair, red eyes"
4. Feature Weight: 80% (giữ 80% đặc trưng khác, chỉ đổi tóc/mắt)
5. Generate → Kết quả: tóc hồng, mắt đỏ, giữ nguyên pose/outfit

### Ví dụ 2: Loại bỏ phụ kiện trên đầu
1. Upload ảnh có bow, ribbon
2. Extract features
3. **Check vào category "👑 Phụ kiện"** → Loại bỏ hết bow, ribbon, earrings
4. Prompt: "" (để trống hoặc thêm "simple design")
5. Generate → Kết quả: không còn phụ kiện

### Ví dụ 3: Đổi background
1. Upload ảnh với blue background
2. Extract features
3. **Click vào các tags trong category "🏞️ Background"** để loại bỏ
4. Prompt: "outdoor, cherry blossoms, sunset sky"
5. Feature Weight: 50% (để prompt background có tác động mạnh hơn)
6. Generate → Kết quả: background mới, giữ nhân vật

## Tips & Tricks

### Khi nào dùng Deep Thinking?
- ✅ Khi muốn chi tiết tối đa để lọc chính xác
- ✅ Khi ảnh gốc có nhiều chi tiết nhỏ
- ❌ Khi muốn tạo nhanh, không cần quá chi tiết

### Feature Weight nên để bao nhiêu?
- **90-100%**: Chỉ tái tạo lại ảnh gốc với quality cao hơn
- **70-80%**: Thay đổi nhỏ (đổi màu, bỏ vật thể)
- **50-60%**: Thay đổi vừa (đổi style, background)
- **20-40%**: Thay đổi lớn, chỉ giữ composition cơ bản

### Denoising Strength vs Feature Weight
- **Denoising** = Mức độ AI tự do sáng tạo từ noise
- **Feature Weight** = Tỷ lệ giữa extracted tags và user prompt
- Kết hợp: Denoising 0.6 + Feature Weight 80% = Giữ ảnh gốc nhưng có biến đổi nhẹ

## Troubleshooting

### Ảnh sinh ra khác hoàn toàn với gốc?
- ✅ Giảm Denoising Strength xuống 0.4-0.5
- ✅ Tăng Feature Weight lên 90-100%
- ✅ Kiểm tra xem có lọc nhầm category quan trọng không

### Ảnh sinh ra giống hệt ảnh gốc?
- ✅ Tăng Denoising Strength lên 0.7-0.8
- ✅ Giảm Feature Weight xuống 50-60%
- ✅ Thêm prompt mạnh hơn với nhiều chi tiết

### Prompt bổ sung không có tác dụng?
- ✅ Giảm Feature Weight xuống (VD: 50%)
- ✅ Hoặc check lại xem có tags conflict không (VD: vừa có "black hair" trong features, vừa prompt "pink hair" với weight thấp)

### Model không trích xuất đúng?
- ✅ Thử bật Deep Thinking Mode
- ✅ Kiểm tra ảnh upload có rõ nét không
- ✅ DeepDanbooru chuyên anime, không phù hợp với ảnh thật

## Model Trích Xuất

Hiện tại hệ thống sử dụng **DeepDanbooru** - một model chuyên trích xuất tags cho ảnh anime/manga.

### Giới thiệu DeepDanbooru
- **Nguồn**: ResNet-based neural network trained on Danbooru dataset
- **Đặc điểm**: 
  - ✅ Rất tốt cho anime, manga, illustrations
  - ✅ Trích xuất được 10,000+ tags chuẩn Danbooru
  - ✅ Phân loại characters, styles, objects, poses
  - ❌ Không phù hợp cho ảnh realistic/photos
  - ❌ Có thể nhầm lẫn với anime style khác thường

### Có model khác không?

Có! Dưới đây là các alternatives:

#### 1. **CLIP Interrogator** (Tốt cho ảnh thật)
- Model: OpenAI CLIP + BLIP
- Ưu điểm: Tốt cho realistic photos, general images
- Nhược điểm: Prompt format khác, không có tags chi tiết như Danbooru
- **Cách thêm**: Cần extend backend để gọi CLIP interrogate API

#### 2. **WD14 Tagger** (Alternative cho anime)
- Model: Waifu Diffusion 1.4 Tagger
- Ưu điểm: Tương tự DeepDanbooru nhưng mới hơn, accurate hơn
- Nhược điểm: Cần cài thêm extension/model
- **Cách thêm**: Install WD14 Tagger extension trong SD WebUI

#### 3. **ViT-L/14 CLIP** (Hybrid)
- Model: Vision Transformer CLIP
- Ưu điểm: Balanced giữa anime và realistic
- Nhược điểm: Không chi tiết bằng DeepDanbooru cho anime specific

### Recommendation
- **Cho anime/manga illustrations**: Giữ DeepDanbooru (đang dùng) ✅
- **Cho realistic photos**: Nên thêm CLIP Interrogator
- **Cho quality tốt nhất**: Kết hợp cả 2 (DeepDanbooru + CLIP) và để user chọn

### Roadmap (Future Enhancement)
- [ ] Thêm WD14 Tagger option
- [ ] Thêm CLIP Interrogator cho realistic images
- [ ] Auto-detect image type và chọn model phù hợp
- [ ] Ensemble multiple models để tăng accuracy

---

**Version**: 1.0  
**Last Updated**: October 30, 2025  
**Author**: AI ChatBot Assistant
