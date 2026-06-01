# 🎨 Hướng dẫn sử dụng Lora và VAE trong ChatBot

## 📋 Tổng quan

Tính năng mới cho phép bạn sử dụng **Lora models** và **VAE models** khi tạo ảnh với Stable Diffusion để:
- **Lora**: Thêm style/character/concept đặc biệt vào ảnh (anime characters, art styles, etc.)
- **VAE**: Cải thiện chất lượng màu sắc và chi tiết của ảnh

## 🚀 Cách sử dụng

### 1. Txt2Img (Tạo ảnh từ text)

1. Mở modal tạo ảnh (nút 🎨)
2. Chọn tab **Text2Img**
3. Kéo xuống phần **🎨 Lora Models**:
   - Click **➕ Thêm Lora** để thêm Lora model
   - Chọn Lora từ dropdown (ví dụ: `Firefly-1024-v1`, `Kafka-v2`, etc.)
   - Điều chỉnh **Weight** (0.0 - 2.0, khuyến nghị: 0.7 - 1.2)
   - Có thể thêm nhiều Lora cùng lúc
4. Chọn **🔧 VAE Model** (hoặc để Automatic)
5. Nhập prompt và các settings khác như bình thường
6. Click **🎨 Tạo ảnh**

### 2. Img2Img (Tạo ảnh từ ảnh gốc)

1. Mở modal tạo ảnh
2. Chọn tab **Img2Img**
3. Upload ảnh gốc và trích xuất features
4. Kéo xuống phần **🎨 Lora Models** (giống Text2Img)
5. Chọn **🔧 VAE Model**
6. Click **🎨 Tạo ảnh từ hình ảnh**

## 💡 Tips và Best Practices

### Lora Weight Guidelines
- **0.5 - 0.7**: Ảnh hưởng nhẹ, giữ style gốc
- **0.8 - 1.0**: Ảnh hưởng vừa phải (khuyến nghị)
- **1.1 - 1.5**: Ảnh hưởng mạnh, style rõ rệt
- **1.6 - 2.0**: Ảnh hưởng rất mạnh (có thể bị overfitting)

### Sử dụng nhiều Lora
- Tổng weight không nên vượt quá 2.0
- Ví dụ: Lora1 (0.8) + Lora2 (0.6) = 1.4 (OK)
- Ví dụ: Lora1 (1.2) + Lora2 (1.0) = 2.2 (Quá cao, có thể bị artifacts)

### VAE Tips
- **Automatic**: Sử dụng VAE mặc định của checkpoint model
- **kl-f8-anime2**: Tốt cho anime/manga style, màu sắc rực rỡ hơn
- Đổi VAE có thể thay đổi đáng kể màu sắc và contrast

## 📂 Thêm Lora/VAE Models

### Thêm Lora Models
1. Tải file `.safetensors` hoặc `.pt` từ [Civitai](https://civitai.com)
2. Copy vào thư mục LoRA của ComfyUI: `ComfyUI/models/loras/`
3. Gọi `POST /api/image-gen/loras/reload` (hoặc restart) để rebuild catalog
4. Reload ChatBot page

### Thêm VAE Models
1. Tải VAE file `.safetensors` từ [HuggingFace](https://huggingface.co) hoặc Civitai
2. Copy vào: `ComfyUI/models/vae/`
3. Restart ComfyUI
4. Reload ChatBot page

## 🎯 Các Lora Models hiện có

Bạn có **50+ Lora models** trong thư mục, bao gồm:

### Anime Characters (Honkai Star Rail)
- **Firefly-1024-v1**: Character Firefly
- **kafka-v2-naivae-final-6ep**: Kafka character
- **JingliuV4-09**: Jing Liu character
- **Seele**: Seele character
- **Clara**: Clara character
- **Bronya Rand**: Bronya character
- **March 7th**: March 7th character
- **TrailblazerHonkaiStarRail4**: Trailblazer
- Và nhiều nhân vật khác...

### Anime Characters (Genshin Impact)
- **Nahida3**: Nahida character
- **furina-lora-nochekaiser**: Furina character
- **Eula-1.0**: Eula character
- **raiden shogun_LoRA**: Raiden Shogun
- **yaemiko1-000008**: Yae Miko

### Other Anime Characters
- **Tatsumaki**: One Punch Man character
- **atri**: Atri character
- **原神可莉**: Klee character
- **派蒙**: Paimon

### Style Loras
- **SIC_outline_v1.01**: Outline style
- **dilationTapeLora-05**: Special effect

## 🔧 Technical Details

### Lora Syntax
Internally, Lora được apply vào prompt theo syntax:
```
<lora:model_name:weight> your prompt here
```

Ví dụ:
```
<lora:Firefly-1024-v1:0.9> 1girl, firefly, beautiful scenery
```

### VAE Override
VAE được set thông qua `override_settings` trong SD API:
```json
{
  "override_settings": {
    "sd_vae": "kl-f8-anime2.vae.safetensors"
  }
}
```

## ⚠️ Lưu ý

1. **Stable Diffusion WebUI phải đang chạy** để sử dụng tính năng
2. Lora và VAE chỉ load khi modal được mở
3. Nếu không thấy Lora/VAE trong dropdown → Check console logs
4. File `.pt` (PyTorch) cũ hơn `.safetensors` (khuyến nghị dùng .safetensors)

## 🐛 Troubleshooting

### Không thấy Lora trong dropdown
- Check xem SD WebUI có đang chạy không
- Mở Console (F12) xem error logs
- Thử reload page

### Lora không có effect
- Tăng weight lên (thử 1.0 - 1.2)
- Check xem Lora có compatible với checkpoint model không
- Một số Lora chỉ work tốt với specific models

### Ảnh bị artifacts khi dùng nhiều Lora
- Giảm weight của các Lora
- Giảm số lượng Lora (max 2-3 cùng lúc)
- Tăng steps (30-50) để stable hơn

## 📚 Resources

### Download Lora Models
- [Civitai](https://civitai.com) - Largest Lora repository
- [HuggingFace](https://huggingface.co/models?pipeline_tag=text-to-image)

### Download VAE Models
- [stabilityai/sd-vae-ft-mse](https://huggingface.co/stabilityai/sd-vae-ft-mse) - Official VAE
- [kl-f8-anime2](https://huggingface.co/hakurei/waifu-diffusion-v1-4) - Anime VAE

---

**Chúc bạn tạo được những bức ảnh đẹp! 🎨✨**
