# 🎨 Hướng dẫn nhanh: Sử dụng Lora và VAE trong ChatBot WebUI

## 📌 TÓM TẮT NHANH

### Lora là gì?
- **Lora** = Style/Character/Concept nhỏ gọn
- Thêm style đặc biệt, nhân vật cụ thể vào ảnh
- Có thể dùng **nhiều Lora cùng lúc**

### VAE là gì?
- **VAE** = Bộ lọc màu sắc và chi tiết
- Cải thiện màu sắc, độ sắc nét, giảm artifacts
- Chỉ chọn **1 VAE** mỗi lần (hoặc Automatic)

---

## 🚀 CÁCH SỬ DỤNG TRONG CHATBOT

### 1️⃣ Mở Modal Tạo Ảnh
- Click nút **🎨 Tạo ảnh** trong ChatBot
- Chọn tab **Text2Img** hoặc **Img2Img**

### 2️⃣ Chọn VAE (Tùy chọn)
```
Dropdown: 🔧 VAE Model
├── Automatic (Mặc định)
├── kl-f8-anime2.safetensors ⭐ (Best cho Anime)
├── Blessed2.vae.safetensors
└── ClearVAE_V2.3.safetensors
```
**Khuyến nghị:** Chọn `kl-f8-anime2` cho anime

### 3️⃣ Thêm Lora Models
Click **➕ Thêm Lora** (có thể thêm nhiều lần)

**Mỗi Lora có 2 thông số:**
```
┌─────────────────────────────────┐
│ [Chọn Lora ▼] [Weight: 1.0]  ❌│
└─────────────────────────────────┘
```

- **Chọn Lora:** Dropdown chọn model
- **Weight:** Độ mạnh (0.0 - 2.0)
- **❌:** Xóa Lora này

### 4️⃣ Nhập Prompt và Generate
- Nhập prompt bình thường
- Click **🎨 Tạo ảnh**
- Lora và VAE tự động được áp dụng!

---

## 📊 LOẠI LORA VÀ CÁCH DÙNG

### 🎭 Loại 1: POSITIVE LORAS (Thêm vào ảnh)

#### Quality/Detail Enhancers
```yaml
DetailTweaker:        0.5 - 0.8  # Tăng chi tiết
AddMoreDetails:       0.5 - 0.7  # Thêm texture
BetterHands:          0.8 - 1.0  # Fix tay
BeautifulEyes:        0.6 - 0.9  # Mắt đẹp hơn
HairDetailer:         0.5 - 0.7  # Tóc rõ nét
```

#### Art Style Loras
```yaml
GhibliBackground:     0.4 - 0.7  # Phong cảnh Ghibli
MakotoShinkai:        0.5 - 0.8  # Style Makoto Shinkai
AnimeLineart:         0.6 - 1.0  # Nét vẽ anime
WatercolorStyle:      0.5 - 0.8  # Màu nước
```

#### Character Loras
```yaml
Kafka-v2:             0.8 - 1.1  # Nhân vật Kafka
Firefly-1024:         0.8 - 1.1  # Nhân vật Firefly
Seele:                0.9 - 1.2  # Nhân vật Seele
```

**Cách dùng:**
1. Chọn Lora từ dropdown
2. Set weight phù hợp
3. Prompt bình thường (không cần thêm gì)

---

### 🚫 Loại 2: NEGATIVE EMBEDDINGS (Loại bỏ lỗi)

```yaml
EasyNegative:          1.0  # Fix anatomy, quality
BadDream:              1.0  # Loại bỏ artifacts
UnrealisticDream:      1.0  # Tăng realism
bad-hands-5:           1.0  # Fix tay (embedding)
verybadimagenegative:  1.0  # Universal fix
```

**Cách dùng:**
- **KHÔNG thêm vào ChatBot UI**
- Thêm trực tiếp vào **Negative Prompt:**

```
Negative Prompt:
EasyNegative, BadDream, UnrealisticDream, bad-hands-5,
bad anatomy, bad hands, extra fingers, worst quality
```

**Lưu ý:** Embeddings `.pt` dùng tên file (không có `<lora:>`!)

---

## 💡 VÍ DỤ THỰC TÊ

### Example 1: Anime Girl Portrait (Basic)
```yaml
VAE: kl-f8-anime2
Lora 1: DetailTweaker (0.7)
Lora 2: BeautifulEyes (0.8)

Prompt:
masterpiece, best quality, 1girl, blue hair, beautiful eyes, 
detailed face, smile, outdoors, sunlight

Negative:
EasyNegative, bad anatomy, worst quality, low quality
```

---

### Example 2: Character với Style
```yaml
VAE: kl-f8-anime2
Lora 1: Kafka-v2 (1.0)
Lora 2: MakotoShinkai (0.6)
Lora 3: DetailTweaker (0.5)

Prompt:
kafka, 1girl, purple hair, red eyes, sitting, city background,
sunset, cinematic lighting

Negative:
EasyNegative, BadDream, bad hands, blurry
```

---

### Example 3: Fix Hands Problem
```yaml
VAE: kl-f8-anime2
Lora 1: BetterHands (1.0)
Lora 2: DetailTweaker (0.7)

Prompt:
1girl, showing hands, open palms, five fingers, 
perfect hands, beautiful hands

Negative:
bad-hands-5, EasyNegative, extra fingers, fused fingers,
mutated hands, malformed hands
```

---

### Example 4: Style Mix (Ghibli + Details)
```yaml
VAE: kl-f8-anime2
Lora 1: GhibliBackground (0.6)
Lora 2: DetailTweaker (0.6)
Lora 3: HairDetailer (0.5)

Prompt:
1girl, long hair, in forest, trees, flowers, studio ghibli style,
detailed scenery, soft lighting

Negative:
EasyNegative, worst quality, blurry
```

---

## ⚖️ WEIGHT GUIDE (Độ mạnh Lora)

```
0.0 - 0.3  →  Rất nhẹ (gần như không ảnh hưởng)
0.4 - 0.6  →  Nhẹ (subtle effect)
0.7 - 0.9  →  Vừa phải ⭐ (KHUYẾN NGHỊ)
1.0 - 1.2  →  Mạnh (strong effect)
1.3 - 1.5  →  Rất mạnh (có thể overpowering)
1.6 - 2.0  →  Quá mạnh (risk of artifacts/overfitting)
```

### Công thức tổng weight:
```
✅ GOOD: Lora1(0.8) + Lora2(0.7) + Lora3(0.5) = 2.0 total
⚠️  RISKY: Lora1(1.2) + Lora2(1.0) + Lora3(0.8) = 3.0 total
❌ BAD: Lora1(1.5) + Lora2(1.5) + Lora3(1.0) = 4.0 total
```

**Rule:** Tổng weight tất cả Loras ≤ 2.5 là an toàn

---

## 🎯 COMBO KHUYẾN NGHỊ

### 🏆 Universal Quality Combo
```yaml
VAE: kl-f8-anime2
Lora 1: DetailTweaker (0.7)
Lora 2: BeautifulEyes (0.8)

→ Work tốt với mọi anime checkpoint
```

---

### 🖐️ Hand Fix Combo
```yaml
VAE: kl-f8-anime2
Lora 1: BetterHands (0.9)
Lora 2: DetailTweaker (0.6)

Negative: bad-hands-5, extra fingers, mutated hands
```

---

### 🎨 Style Master Combo
```yaml
VAE: kl-f8-anime2
Lora 1: [Style Lora] (0.7)  # Ghibli/Makoto/etc
Lora 2: DetailTweaker (0.5)
Lora 3: HairDetailer (0.4)

→ Style + Quality balanced
```

---

### 👤 Character + Style Combo
```yaml
VAE: kl-f8-anime2
Lora 1: [Character Lora] (1.0)  # Kafka/Firefly/etc
Lora 2: [Style Lora] (0.6)      # Optional
Lora 3: DetailTweaker (0.5)

→ Character với style đặc biệt
```

---

## ⚠️ LƯU Ý QUAN TRỌNG

### ✅ DO (Nên làm):
- Dùng VAE `kl-f8-anime2` cho anime
- Weight Lora từ 0.7-1.0 là tốt nhất
- Test với 1-2 Loras trước khi thêm nhiều
- Dùng negative embeddings (EasyNegative, etc.)
- Restart SD WebUI sau khi thêm Lora/VAE mới

### ❌ DON'T (Không nên):
- Dùng quá nhiều Loras (>4 cùng lúc)
- Weight quá cao (>1.5 dễ bị artifacts)
- Tổng weight >3.0 (sẽ bị overfitting)
- Quên set VAE (màu sẽ bị xám xịt)
- Dùng negative Lora trong positive prompt

---

## 🔧 TROUBLESHOOTING

### ❓ Lora không có effect?
```
→ Tăng weight lên (1.0 - 1.2)
→ Check xem Lora có compatible với checkpoint không
→ Restart SD WebUI
```

### ❓ Ảnh bị artifacts / distorted?
```
→ Giảm weight của Loras
→ Giảm số lượng Loras (max 2-3)
→ Tăng steps (35-50)
→ Giảm CFG scale (7-8)
```

### ❓ Màu sắc xấu / xám xịt?
```
→ Chọn VAE: kl-f8-anime2 (IMPORTANT!)
→ Không để VAE = None
→ Restart SD WebUI sau khi add VAE
```

### ❓ Hands vẫn bị lỗi?
```
→ Add Lora: BetterHands (1.0)
→ Negative: bad-hands-5, extra fingers
→ Tăng steps lên 40-50
→ Enable Hires Fix
→ Dùng simple hand poses
```

### ❓ Không thấy Lora trong dropdown?
```
→ Check file trong: stable-diffusion-webui/models/Lora/
→ Restart SD WebUI
→ Reload ChatBot page (F5)
→ Check browser console (F12) xem có lỗi không
```

---

## 📂 QUẢN LÝ LORA/VAE

### Thêm Lora/VAE mới:
```bash
# Lora location
C:\Users\Asus\Downloads\Compressed\AI-Assistant\
  └── stable-diffusion-webui\
      └── models\
          └── Lora\          # ← Copy .safetensors/.pt here

# VAE location
C:\Users\Asus\Downloads\Compressed\AI-Assistant\
  └── stable-diffusion-webui\
      └── models\
          └── VAE\           # ← Copy .safetensors here
```

### Sau khi thêm file:
1. ✅ Restart Stable Diffusion WebUI
2. ✅ Reload ChatBot page (F5)
3. ✅ Mở modal tạo ảnh → Check dropdown

---

## 🌟 BEST LORA/VAE ĐỂ TẢI

### 📥 MUST-HAVE (Download ngay):

**VAE:**
```
✅ kl-f8-anime2.safetensors
   → https://civitai.com/api/download/models/23906
```

**Negative Embeddings:**
```
✅ EasyNegative.pt
   → https://civitai.com/api/download/models/9208

✅ BadDream.pt
   → https://civitai.com/api/download/models/77169

✅ bad-hands-5.pt
   → https://civitai.com/api/download/models/116230
```

**Quality Loras:**
```
✅ DetailTweaker.safetensors
   → https://civitai.com/api/download/models/62833

✅ BetterHands.safetensors
   → https://civitai.com/api/download/models/116765
```

---

## 📚 TÀI LIỆU THÊM

- Chi tiết hơn: `LORA_VAE_GUIDE.md`
- Download script: `download_loras_vaes.py`
- Links đầy đủ: Xem file guide chính

---

## 💬 SUPPORT

Có vấn đề? Check:
1. SD WebUI có đang chạy không? (`http://127.0.0.1:7860`)
2. Files Lora/VAE đã copy đúng folder chưa?
3. Đã restart SD WebUI sau khi add files chưa?
4. Browser console (F12) có error không?

---

**🎨 Chúc bạn tạo được những bức ảnh tuyệt đẹp! ✨**
