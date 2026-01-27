# 🎨 Edit Image Feature - Work In Progress (WIP)

> **Mục tiêu**: Xây dựng tool Edit Image với độ tương đồng ~90% so với Grok Edit Image  
> **Ngày bắt đầu**: 06/01/2026  
> **Trạng thái**: 🚧 Đang nghiên cứu & phát triển

---

## 📋 Tổng quan yêu cầu

### Yêu cầu chính
- **Platform**: Web → CLI → Desktop (theo thứ tự ưu tiên - dễ nhất)
- **Tính năng cốt lõi**: 
  - Tạo ảnh dựa trên nét/đặc trưng của ảnh được tải lên (như Img2Img)
  - Chỉnh sửa theo text prompt (thay đổi nhân vật, phong cách, bối cảnh)
  - **Tìm kiếm trên mạng** để lấy chi tiết nhân vật, vật thể, nội dung (giống Grok)
- **Ưu tiên**: Chất lượng > Tính năng > Tốc độ > > UI (UI tương đối là được)
- **Công nghệ**: Stable Diffusion, ControlNet, tự training model, tích hợp API free
- **Chính sách**: Không có content moderation, tự deploy tự sử dụng (bao gồm NSFW/R18/R18L)

### Yêu cầu chi tiết từ Grok
1. **Text-based editing**: Nhập text yêu cầu chỉnh sửa
   - Thay đổi nhân vật
   - Thay đổi phong cách
   - Thay đổi bối cảnh
   - Thêm/bớt đối tượng
2. **Web search integration**: Tìm kiếm trên mạng lấy chi tiết
   - Nhân vật (character reference)
   - Vật thể (object reference)  
   - Nội dung (content reference)
3. **Image-to-Image**: Tạo ảnh dựa trên đặc trưng ảnh gốc
4. **No content filter**: Không có bất kỳ chính sách cấm nào

### Phần cứng sẵn có
| PC | GPU | VRAM | RAM | Vai trò |
|---|---|---|---|---|
| PC1 | RTX 5070 | 12GB | 32GB DDR5 | Primary - Training & Inference |
| PC2 | RTX 3060 Ti | 8GB | 32GB DDR4 | Secondary - Inference |
| Laptop | RTX 3060 Laptop | 6GB | 16GB DDR4 | Mobile - Inference |

### Dataset & Training
- **Nguồn ảnh có thể sử dụng**:
  - Ảnh do AI tạo (Gemini, ChatGPT, SD, Grok, ...)
  - Ảnh thu thập từ internet
  - Ảnh tự tạo
- **Không cần dataset khổng lồ**: Với LoRA chỉ cần ~10-50 ảnh mẫu
- **Tự training model**: Có thể fine-tune với ảnh AI + ảnh thu thập được

---

## 🤖 Các mô hình AI chỉnh sửa ảnh tiên tiến nhất

### 1. InstructPix2Pix
- **Nguồn**: Stable Diffusion fine-tuned
- **Tính năng**: Chỉnh sửa ảnh theo chỉ dẫn văn bản (instruction-based image editing)
- **Ví dụ**: Đưa ảnh + prompt "hãy biến bầu trời thành cầu vồng"
- **Đặc điểm**: Đặt nền móng cho hướng tiếp cận "instruction-to-image"
- **Link**: [HuggingFace InstructPix2Pix](https://huggingface.co/docs/diffusers/en/training/instructpix2pix)

### 2. Qwen-Image-Edit ⭐ (Khuyến nghị)
- **Nguồn**: Alibaba Qwen AI (2025)
- **Tính năng**: 
  - Thêm, bớt hoặc thay đổi đối tượng trong ảnh
  - 20 tỷ tham số
  - Hỗ trợ nhiều ảnh tham chiếu
  - Tích hợp sẵn kỹ thuật LoRA
  - Tính nhất quán nhân vật cao
- **Đặc điểm**: Đánh giá hàng đầu thế giới về hiệu quả chỉnh sửa ảnh
- **Triển khai**: 
  - Giao diện chat Qwen miễn phí (giới hạn)
  - API trên Alibaba Cloud
  - Self-hosted trên GPU
- **Phiên bản**: 2509, 2511 (cải thiện tính nhất quán nhân vật)
- **Link**: [HuggingFace Qwen-Image-Edit](https://huggingface.co/Qwen/Qwen-Image-Edit)

### 3. Step1X-Edit ⭐ (Khuyến nghị)
- **Nguồn**: StepFun AI (2025)
- **Tính năng**:
  - Kiến trúc LLM đa phương thức
  - Text-to-image + Instruction-based edit
  - Chế độ "reasoning" phân tích lệnh phức tạp
- **Yêu cầu**: 
  - ~7GB cho FP16
  - GPU 24GB (hỗ trợ FP8 để chạy nhẹ hơn)
- **Phiên bản**: v1.1, v1.2 (bổ sung reasoning)
- **Link**: [GitHub Step1X-Edit](https://github.com/stepfun-ai/Step1X-Edit)

### 4. Stable Diffusion XL (SDXL)
- **Nguồn**: Stability AI
- **Tính năng**:
  - Độ phân giải 1024×1024
  - 3.5 tỷ tham số
  - Inpainting, outpainting, style transfer
- **Đặc điểm**: Không có chặn kiểm duyệt mặc định khi chạy cục bộ
- **Fine-tune variants**: Realistic Vision, DreamShaper, Photon

### 5. FLUX.1 (Mới nhất)
- **Nguồn**: Black Forest Labs (2024-2025)
- **Tính năng**:
  - Chất lượng vượt trội SDXL
  - Hiểu prompt tốt hơn
  - Chi tiết cao, ít lỗi tay/ngón
- **Phiên bản**:
  - FLUX.1 [dev] - Open source, chạy local
  - FLUX.1 [schnell] - Nhanh, ít step
  - FLUX.1 [pro] - API only
- **VRAM**: ~12GB+ (có thể quantize)
- **Link**: [GitHub FLUX](https://github.com/black-forest-labs/flux)

### 6. Stable Diffusion 3 (SD3)
- **Nguồn**: Stability AI (2024)
- **Tính năng**:
  - Kiến trúc MMDiT (Multimodal Diffusion Transformer)
  - Text rendering tốt hơn
  - Prompt following chính xác
- **Phiên bản**: SD3 Medium (2B params)
- **Link**: [Stability AI SD3](https://stability.ai/stable-diffusion-3)

### 7. Midjourney (Tham khảo)
- **Đặc điểm**: Chất lượng nghệ thuật cao nhưng:
  - Không mã nguồn mở
  - Có content moderation
  - Không chạy local được
- **Kết luận**: Không phù hợp cho mục tiêu dự án

---

## 🎌 Mô hình chuyên biệt cho Anime (重要)

### Base Models cho Anime

#### 1. Waifu Diffusion v1.4
- **Nguồn**: hakurei/waifu-diffusion
- **Tính năng**: Latent Diffusion fine-tuned trên ảnh anime chất lượng cao
- **Giấy phép**: CreativeML OpenRAIL-M (cho phép thương mại)
- **Link**: [HuggingFace Waifu Diffusion](https://huggingface.co/hakurei/waifu-diffusion-v1-4)

#### 2. Anything V3.0 / V4.0 / V5.0 ⭐
- **Đặc điểm**: 
  - Dành cho "otaku"
  - Tạo ảnh anime cực kỳ chi tiết với vài từ khóa
  - Hỗ trợ Danbooru tags
- **Giấy phép**: CreativeML OpenRAIL-M
- **Link**: [HuggingFace Anything V3](https://huggingface.co/admruul/anything-v3.0)

#### 3. Animagine XL 3.1 ⭐ (SDXL-based)
- **Nguồn**: Cagliostro Lab
- **Tính năng**:
  - SDXL mã nguồn mở cho anime
  - Giải phẫu tay tốt hơn
  - Nhận thức ý niệm cao
  - Chi tiết nhân vật anime sắc nét
- **Giấy phép**: CreativeML OpenRAIL++-M
- **Link**: [HuggingFace Animagine XL 3.1](https://huggingface.co/cagliostrolab/animagine-xl-3.1)

#### 4. Stable Diffusion XL Anime V5
- **Nguồn**: bdsqlsz (dựa trên Animagine 3.1)
- **Tính năng**:
  - SFT để tăng chất lượng anime
  - Màu sắc anime tốt hơn
  - Giải phẫu cơ thể cải thiện
  - Ít 3D, nhiều highlight anime
- **Giấy phép**: Fair-IA-Public-1.0-SD
- **Link**: [HuggingFace SDXL Anime V5](https://huggingface.co/bdsqlsz/stable-diffusion-xl-anime-V5)

#### 5. NovelAI Diffusion Anime V2/V3
- **Nguồn**: NovelAI
- **Tính năng**:
  - V2: Dựa trên SD1.5, chất lượng cao
  - V3: Dựa trên SDXL, tag ordering control
- **Giấy phép**: 
  - V2: CreativeML OpenRAIL-M + CC BY-NC-SA (nghiên cứu)
  - V3: Proprietary (chỉ qua dịch vụ NovelAI)
- **Link**: [HuggingFace NovelAI V2](https://huggingface.co/NovelAI/nai-anime-v2)

#### 6. Pony Diffusion
- **Đặc điểm**: 
  - Chuyên biệt cho NSFW anime
  - Nhiều phiên bản (V5, V6, XL)
  - Cộng đồng lớn trên CivitAI
- **Lưu ý**: Phổ biến trong cộng đồng R18

### Fine-tuned Models cho Anime (CivitAI)

| Model | Đặc điểm | Base | NSFW |
|-------|----------|------|------|
| **MeinaMix** | Anime style, soft colors | SD1.5 | ✅ |
| **CounterfeitXL** | Anime 2D style | SDXL | ✅ |
| **AbyssOrangeMix** | Anime/illustration | SD1.5 | ✅ |
| **Pastel Mix** | Soft pastel anime | SD1.5 | ✅ |
| **GhostMix** | Dark/gothic anime | SD1.5 | ✅ |
| **Blue Pencil** | Sketch/line art anime | SDXL | ✅ |
| **Hassaku XL** | Anime XL quality | SDXL | ✅ |

### ControlNet cho Anime

| Model | Tính năng |
|-------|-----------|
| **anime_control/canny** | Đường viền anime style |
| **anime_control/style** | Style transfer anime |
| **anime_lineart** | Line art extraction |
| **anime_face_segment** | Face segmentation anime |

- **Link**: [HuggingFace Anime Control](https://huggingface.co/lint/anime_control)

### Anime-specific Tools

#### DeepDanbooru
- **Tính năng**: CNN model gắn tag anime từ ảnh
- **Output**: Nhiều nhãn (mỹ thuật, nhân vật, tình huống)
- **Ứng dụng**: Auto-tagging cho training dataset

#### WD14 Tagger (MrSmilingWolf)
- **Tính năng**: Gắn tag theo embedding SD 1.4 (train trên Danbooru)
- **Tích hợp**: Extension cho A1111
- **Link**: [GitHub WD14 Tagger](https://github.com/kawalain/stable-diffusion-webui-wd14-tagger)

#### Booru Tags System
- **Danbooru**: ~3 triệu ảnh anime có tag
- **Gelbooru**: NSFW-friendly tags
- **Pixiv Tags**: Japanese tagging system

### Anime Character Database (Tìm kiếm)

| Nguồn | Đặc điểm |
|-------|----------|
| **Danbooru** | Tag-based, detailed |
| **Gelbooru** | NSFW allowed |
| **Safebooru** | SFW only |
| **Pixiv** | Artist-focused |
| **MyAnimeList** | Character info |
| **AniList** | Character database |

### Anime LoRA phổ biến

| Loại | Mô tả |
|------|-------|
| **Character LoRA** | Train trên 1 nhân vật cụ thể |
| **Style LoRA** | Phong cách vẽ (Ghibli, Makoto Shinkai, etc.) |
| **Concept LoRA** | Khái niệm (school uniform, maid, etc.) |
| **Pose LoRA** | Tư thế nhân vật |
| **Detail LoRA** | Cải thiện chi tiết (hands, eyes, hair) |

---

## 🎛️ Điều khiển bố cục và phong cách

### ControlNet
- **Tính năng**: Gắn điều kiện đầu vào dạng hình ảnh cho mô hình diffusion
- **Preprocessors**:
  - Canny Edge (đường viền)
  - OpenPose (khung xương người)
  - Depth Map
  - Semantic Segmentation
- **Ứng dụng**: Khống chế bố cục và đường nét ảnh đầu ra
- **Link**: [Stable Diffusion Art - ControlNet](https://stable-diffusion-art.com/controlnet/)

### IP-Adapter (Image Prompt Adapter)
- **Nguồn**: Tencent ARC
- **Tính năng**: Đưa hình ảnh làm prompt bổ sung cho Stable Diffusion
- **Đặc điểm**: Lightweight, không thay đổi trọng số gốc
- **Link**: [CSDN Blog](https://blog.csdn.net/x1131230123/article/details/139626621)

### LoRA (Low-Rank Adaptation)
- **Tính năng**:
  - Fine-tune nhẹ (~vài MB)
  - Chỉ cần ~10-50 ảnh mẫu
  - Huấn luyện trong vài phút
- **Ứng dụng**: Thêm phong cách/nhân vật mới mà không giảm khả năng gốc
- **Nguồn LoRA có sẵn**: HuggingFace, CivitAI

### Textual Inversion (Embedding)
- **Tính năng**: Học một "từ" mới đại diện cho concept/style/object
- **Ưu điểm**: File rất nhỏ (~KB), dễ chia sẻ
- **Hạn chế**: Kém linh hoạt hơn LoRA
- **Ứng dụng**: Thêm phong cách, nhân vật đơn giản

### T2I-Adapters
- **Nguồn**: Tencent ARC
- **Tính năng**: 
  - Nhẹ hơn ControlNet
  - Hỗ trợ: Sketch, Keypose, Segmentation, Color, Depth
- **Đặc điểm**: Có thể kết hợp nhiều adapter cùng lúc
- **Link**: [GitHub T2I-Adapter](https://github.com/TencentARC/T2I-Adapter)

---

## 👤 Giải pháp bảo toàn nhân dạng (Identity Preservation)

### InstantID
- **Tính năng**: Zero-shot face copying từ một ảnh duy nhất
- **Pipeline**:
  1. InsightFace trích xuất embedding khuôn mặt
  2. Kết hợp với SDXL tạo ảnh mới
- **Đặc điểm**: Face swap chất lượng cao cho SDXL
- **Tích hợp**: Extension A1111, workflow ComfyUI
- **Link**: [Stable Diffusion Art - InstantID](https://stable-diffusion-art.com/instantid/)

### PuLID (Pure and Lightning ID Customization)
- **Nguồn**: ByteDance (NeurIPS 2024)
- **Tính năng**:
  - Lightning T2I branch
  - Loss tương phản + loss danh tính
  - Chèn danh tính không phá hỏng hành vi gốc
- **Đặc điểm**: Vượt trội về điểm số nhận dạng và khả năng tùy biến
- **Link**: [GitHub ToTheBeginning/PuLID](https://github.com/ToTheBeginning/PuLID)

### EcomID
- **Nguồn**: Alibaba (cuối 2024)
- **Tính năng**:
  - Kết hợp InstantID + PuLID
  - IdentityNet huấn luyện trên 2 triệu ảnh
  - Giữ ổn định danh tính khi thay đổi tuổi/tóc/kính
- **Tích hợp**: Plugin ComfyUI cho SDXL
- **Link**: [AIBase EcomID](https://www.aibase.com/news/12917)

### DreamBooth
- **Nguồn**: Google (2022)
- **Tính năng**:
  - Fine-tune với ~5-10 ảnh
  - Prior preservation technique
  - Học token mới đại diện cho đối tượng
- **Lưu ý**: Đang dần được thay thế bởi LoRA/InstantID/PuLID
- **Link**: [HuggingFace DreamBooth](https://huggingface.co/blog/dreambooth)

---

## 🖥️ Công cụ triển khai cục bộ

### Automatic1111 Web UI
- **Tính năng**:
  - Text-to-image, Image-to-image, Inpainting
  - Hệ thống Extensions (ControlNet, LoRA, InstantID)
  - Quản lý prompt/negative prompt
- **Ưu điểm**: Cộng đồng lớn, miễn phí, mã nguồn mở
- **Link**: [GitHub AUTOMATIC1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui)

### ComfyUI ⭐ (Khuyến nghị)
- **Tính năng**:
  - Giao diện node graph (nút-lưu đồ)
  - Workflow tùy chỉnh linh hoạt
  - Plugin: Step1X-Edit, EcomID, LoRA, ControlNet, IP-Adapter
- **Ưu điểm**: Kết hợp nhiều mô hình/điều kiện dễ dàng
- **Workflow mẫu**: Thay mặt, vẽ ảnh nhiều bước
- **Link**: [GitHub ComfyUI](https://github.com/comfyanonymous/ComfyUI)

### Các UI khác
- **Fooocus**: Đơn giản hóa, giống concept Midjourney
- **InvokeAI**: Tính năng đầy đủ, UI đẹp
- **DiffusionBee**: Cho MacOS

---

## 📊 So sánh và lựa chọn

### Mô hình chỉnh sửa ảnh

| Mô hình | Chất lượng | VRAM | Open Source | Instruction-based |
|---------|-----------|------|-------------|------------------|
| Qwen-Image-Edit | ⭐⭐⭐⭐⭐ | Cao | ✅ | ✅ |
| Step1X-Edit | ⭐⭐⭐⭐⭐ | ~7GB | ✅ | ✅ |
| InstructPix2Pix | ⭐⭐⭐ | Thấp | ✅ | ✅ |
| SDXL | ⭐⭐⭐⭐ | ~8GB | ✅ | ❌ (cần ControlNet) |
| FLUX.1 [dev] | ⭐⭐⭐⭐⭐ | ~12GB | ✅ | ❌ |
| SD3 Medium | ⭐⭐⭐⭐ | ~10GB | ✅ | ❌ |

### Identity Preservation

| Công cụ | Zero-shot | Chất lượng | Tích hợp |
|---------|-----------|-----------|----------|
| InstantID | ✅ | ⭐⭐⭐⭐ | A1111, ComfyUI |
| PuLID | ✅ | ⭐⭐⭐⭐⭐ | Diffusers, ComfyUI |
| EcomID | ✅ | ⭐⭐⭐⭐⭐ | ComfyUI |
| DreamBooth | ❌ | ⭐⭐⭐⭐⭐ | Diffusers, A1111 |

---

## 🗺️ Roadmap đề xuất

### Phase 1: Nghiên cứu & Setup môi trường ✅
- [x] Cài đặt ComfyUI
- [x] Download SDXL base model
- [x] Test Step1X-Edit
- [x] Test Qwen-Image-Edit

### Phase 2: Core Features ✅
- [x] Tích hợp ControlNet (Canny, OpenPose, Depth)
- [x] Tích hợp IP-Adapter
- [x] Tích hợp InstantID/PuLID

### Phase 3: Training Pipeline ✅
- [x] Setup LoRA training
- [x] Tạo dataset từ ảnh AI + ảnh thu thập
- [x] Fine-tune custom model

### Phase 4: UI Development ✅
- [x] Web interface (FastAPI + Gradio)
- [ ] CLI tool (v0.4.0)
- [ ] Desktop app (Electron/Tauri) (v0.5.0)

### Phase 5: API Integration ✅
- [x] Tích hợp free API endpoints
- [ ] Load balancing giữa local và cloud (v0.4.0)
- [ ] Caching system (v0.4.0)

### Phase 6: Advanced Features (v0.4.0 - Planned)
- [ ] PuLID Integration
- [ ] EcomID Integration
- [ ] Batch Processing
- [ ] Multi-GPU Support
- [ ] Model Offloading

---

## 📚 Tài liệu tham khảo

### Official Repositories
- [Step1X-Edit](https://github.com/stepfun-ai/Step1X-Edit)
- [Qwen-Image-Edit](https://huggingface.co/Qwen/Qwen-Image-Edit)
- [PuLID](https://github.com/ToTheBeginning/PuLID)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [AUTOMATIC1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui)

### Tutorials & Guides
- [Stable Diffusion Art - ControlNet](https://stable-diffusion-art.com/controlnet/)
- [Stable Diffusion Art - InstantID](https://stable-diffusion-art.com/instantid/)
- [HuggingFace Diffusers](https://huggingface.co/docs/diffusers)

### Model Downloads
- [CivitAI](https://civitai.com/) - LoRA, Checkpoints
- [HuggingFace](https://huggingface.co/) - Official models
- [ModelScope](https://modelscope.cn/) - Chinese models

### Nguồn Trung Quốc (高质量中文资源)
- [CSDN Blog](https://blog.csdn.net/) - Tutorials tiếng Trung
- [Tencent ARC](https://github.com/TencentARC) - IP-Adapter, GFPGAN
- [Alibaba ModelScope](https://modelscope.cn/) - Qwen models
- [DeepSeek](https://deepseek.com/) - DeepSeek models
- [Baidu AI](https://ai.baidu.com/) - ERNIE models

---

## 🔗 Tích hợp với dự án hiện tại

### Kiểm tra tính năng Img2Img có sẵn
Trong repo `./services/chatbot/` đã có tính năng **Img2Img** giúp tạo ảnh dựa theo đặc trưng được mô phỏng dựa theo Img2Img của Stable Diffusion.

**TODO**: 
- [ ] Review code hiện tại tại `./services/chatbot/`
- [ ] So sánh với yêu cầu mới
- [ ] Quyết định: Mở rộng code cũ hay làm tool mới

---

## 🌐 Tính năng Web Search (Giống Grok)

### Mục tiêu
Tìm kiếm trên mạng để lấy thông tin chi tiết về:
- Nhân vật (characters) - tìm reference images
- Vật thể (objects) - tìm sample images
- Nội dung (content) - tìm style references

### Cách triển khai
1. **Image Search API**: Google Images, Bing Images, Yandex
2. **Character Database**: 
   - Danbooru/Gelbooru tags
   - MyAnimeList characters
   - Wikidata entities
3. **Style Reference**:
   - ArtStation
   - DeviantArt
   - Pinterest

---

## 🔧 Nguồn mô hình từ nghiên cứu mở rộng

### Mô hình từ Trung Quốc (高质量模型)

| Tên | Nguồn | Đặc điểm |
|-----|-------|----------|
| Qwen-Image-Edit | Alibaba | Top tier editing |
| IP-Adapter | Tencent ARC | Image prompt |
| GFPGAN | Tencent ARC | Face restoration |
| CodeFormer | 上海AI实验室 | Face enhancement |
| Real-ESRGAN | 腾讯 | Image upscaling |

### Fine-tuned Models (CivitAI)

| Model | Use Case | NSFW |
|-------|----------|------|
| Realistic Vision | Photorealistic | ✅ |
| DreamShaper | Fantasy/Artistic | ✅ |
| Photon | Photography | ✅ |
| MeinaMix | Anime | ✅ |
| ChilloutMix | Asian faces | ✅ |

### Anime Models Comparison

| Model | Base | Chất lượng | VRAM | NSFW | Khuyến nghị |
|-------|------|-----------|------|------|-------------|
| Animagine XL 3.1 | SDXL | ⭐⭐⭐⭐⭐ | ~8GB | ✅ | 🥇 Best overall |
| Anything V5 | SD1.5 | ⭐⭐⭐⭐ | ~4GB | ✅ | Lightweight |
| MeinaMix | SD1.5 | ⭐⭐⭐⭐ | ~4GB | ✅ | Soft style |
| CounterfeitXL | SDXL | ⭐⭐⭐⭐⭐ | ~8GB | ✅ | 2D anime |
| Pony Diffusion XL | SDXL | ⭐⭐⭐⭐ | ~8GB | ✅ | NSFW focus |
| NovelAI V3 | SDXL | ⭐⭐⭐⭐⭐ | - | ✅ | API only |

---

## 🔄 Công cụ xử lý hậu kỳ (Post-processing)

### Upscalers (Tăng độ phân giải)

| Tool | Đặc điểm | Link |
|------|----------|------|
| Real-ESRGAN | Upscale ảnh thật, anime | [GitHub](https://github.com/xinntao/Real-ESRGAN) |
| ESRGAN | Upscale tổng quát | [GitHub](https://github.com/xinntao/ESRGAN) |
| SwinIR | Transformer-based | [GitHub](https://github.com/JingyunLiang/SwinIR) |
| Latent Upscaler | Tích hợp trong SD | Built-in |
| Ultimate SD Upscale | Tile-based upscale | Extension |

### Face Restoration (Khôi phục khuôn mặt)

| Tool | Nguồn | Đặc điểm |
|------|-------|----------|
| GFPGAN | Tencent ARC | Face enhancement, quality |
| CodeFormer | 上海AI实验室 | Face restoration, detail |
| RestoreFormer | Microsoft | Face restoration |
| InsightFace | - | Face detection + embedding |

### Inpainting & Outpainting

| Tính năng | Mô tả |
|-----------|-------|
| Inpainting | Xóa/thay thế vùng được chọn |
| Outpainting | Mở rộng ảnh ra ngoài khung |
| Object Removal | Xóa đối tượng, AI fill background |
| Background Replace | Thay background giữ subject |

---

## 🎬 Mở rộng: Video & Animation (Tương lai)

### Image-to-Video Models

| Model | Nguồn | Đặc điểm |
|-------|-------|----------|
| Stable Video Diffusion | Stability AI | Image → Short video |
| AnimateDiff | Community | SD → Animation |
| Deforum | Community | Animated sequences |
| Kling | Kuaishou | High quality video |
| Sora | OpenAI | Text → Video (closed) |

### Live Portrait / Talking Head

| Tool | Tính năng |
|------|-----------|
| SadTalker | Audio → Talking face |
| LivePortrait | Ảnh tĩnh → Animation |
| Wav2Lip | Lip sync video |

---

## ⚠️ Lưu ý quan trọng

1. **Trách nhiệm pháp lý**: Tự chịu trách nhiệm về việc sử dụng mô hình
2. **Tự deploy, tự sử dụng**: Không có kiểm duyệt nội dung
3. **Bản quyền**: Cẩn thận với việc sử dụng ảnh có bản quyền để training
4. **Privacy**: Tự quản lý và tuân thủ pháp luật địa phương

---

## 📝 Changelog

### 2026-01-06 (Update 3 - v0.3.0) 🎉
- **Hoàn thành**: IP-Adapter Integration (`app/core/ip_adapter.py`)
  - IPAdapterManager class với singleton pattern
  - Hỗ trợ FaceID, FaceID Plus, Plus variants
  - Style transfer và image prompts
- **Hoàn thành**: InstantID Module (`app/core/instantid.py`)
  - Zero-shot face swap với InsightFace + ControlNet
  - Face extraction từ một ảnh duy nhất
  - Tích hợp với SDXL pipeline
- **Hoàn thành**: Inpaint Anything (`app/core/inpaint_anything.py`)
  - SAM (Segment Anything Model) integration
  - LaMa inpainting cho object removal
  - Click-to-remove workflow
- **Hoàn thành**: LLM-Enhanced InstructPix2Pix (`app/core/enhanced_ip2p.py`)
  - InstructionParser phân tích câu lệnh
  - PromptComposer tối ưu hóa prompt
  - PromptEnricher với web search integration
- **Hoàn thành**: Qwen-Image-Edit Pipeline (`app/core/qwen_edit.py`)
  - 20B parameter SOTA model
  - Multi-turn editing support
  - Semantic + appearance editing modes
  - Text rendering capabilities
- **Hoàn thành**: Step1X-Edit Pipeline (`app/core/step1x_edit.py`)
  - LLM multimodal architecture
  - Reasoning mode cho complex instructions
  - FP8 quantization support (~4GB VRAM)
- **Hoàn thành**: LoRA Training Module (`app/core/lora_training.py`)
  - DatasetPreparer cho image preparation
  - TrainingConfig với Pydantic validation
  - LoRATrainer với 8-bit Adam optimizer
  - DreamBooth + LoRA support
- **Hoàn thành**: Anime ControlNet Models (`app/core/anime_controlnet.py`)
  - lineart_anime preprocessor
  - OpenPose integration
  - Multi-controlnet support
  - Photo-to-anime style transfer
- **Hoàn thành**: API Routes cập nhật (+500 lines)
  - IP-Adapter endpoints
  - InstantID endpoints
  - Inpaint Anything endpoints
  - Smart Edit endpoints (Qwen, Step1X)
- **Hoàn thành**: Gradio UI mở rộng (14 tabs)
  - IP-Adapter tab với FaceID toggle
  - InstantID tab với face preview
  - Inpaint Anything tab với click interface
  - Smart Edit tab với model selection
- **Hoàn thành**: Dependencies updated (`requirements.txt`)
  - segment-anything, simple-lama-inpainting
  - peft, datasets, bitsandbytes
  - einops, sentencepiece

### 2026-01-06 (Update 2)
- Bổ sung: **Kỹ thuật chỉnh sửa nâng cao** (P2P, SAM+Inpaint, Paint-by-Example)
- Bổ sung: Chi tiết cấu hình **Waifu Diffusion, Anything, NovelAI**
- Bổ sung: **Licenses Summary** cho tất cả anime models
- Bổ sung: **Workflow tìm kiếm nhân vật tự động**
- Bổ sung: **APIs cho Character Search** (Danbooru, MAL, AniList, Pixiv)
- Bổ sung: **Auto-tagging Pipeline** code example
- Bổ sung: **Nguồn Trung Quốc mở rộng** (ModelScope, Baidu, ByteDance)
- Bổ sung: **Cập nhật Tool Edit Image** - tính năng đã/chưa implement
- Bổ sung: **Architecture Update** cho v0.2.0
- Tool đã được tạo tại: `./services/edit-image/`

### 2026-01-06 (Initial)
- Khởi tạo tài liệu WIP
- Tổng hợp nghiên cứu từ ChatGPT conversation
- Liệt kê các mô hình và công cụ cần thiết
- Bổ sung: Web search integration
- Bổ sung: Nguồn Trung Quốc
- Bổ sung: Dataset & Training requirements
- Bổ sung: Fine-tuned models từ CivitAI
- Bổ sung: Tích hợp với dự án hiện tại (./services/chatbot/)
- Bổ sung: FLUX.1, SD3, Midjourney (tham khảo)
- Bổ sung: Textual Inversion, T2I-Adapters
- Bổ sung: Post-processing tools (Upscalers, Face Restoration)
- Bổ sung: Video & Animation models (tương lai)
- Bổ sung: **Anime-specific models** (Animagine, Anything, Waifu Diffusion, NovelAI)
- Bổ sung: Anime ControlNet, DeepDanbooru, WD14 Tagger
- Bổ sung: Anime LoRA types (Character, Style, Concept)
- Bổ sung: CivitAI anime models (MeinaMix, CounterfeitXL, Pony)

---

## 🎯 Tổng kết Grok Edit Image Clone

### Các thành phần cần có:

```
┌─────────────────────────────────────────────────────────────┐
│                    EDIT IMAGE TOOL                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │   INPUT     │    │   PROCESS    │    │    OUTPUT     │  │
│  ├─────────────┤    ├──────────────┤    ├───────────────┤  │
│  │ - Image     │───▶│ - SDXL       │───▶│ - Edited      │  │
│  │ - Text      │    │ - ControlNet │    │   Image       │  │
│  │ - Web Search│    │ - IP-Adapter │    │ - Multiple    │  │
│  │             │    │ - InstantID  │    │   Variations  │  │
│  └─────────────┘    │ - LoRA       │    └───────────────┘  │
│                     └──────────────┘                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  WEB INTERFACE                       │   │
│  │  - Upload Image                                      │   │
│  │  - Text Input (edit instructions)                    │   │
│  │  - Web Search (character/object/style reference)    │   │
│  │  - Settings (model, strength, steps, etc.)          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  TRAINING PIPELINE                   │   │
│  │  - LoRA Training (10-50 images)                      │   │
│  │  - DreamBooth (5-10 images)                          │   │
│  │  - Dataset: AI-generated + collected images          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Workflow đề xuất:

```
User Upload Image
       │
       ▼
┌──────────────────┐
│ Preprocessors    │
│ - Canny Edge     │
│ - OpenPose       │
│ - Depth Map      │
│ - Face Detection │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     ┌───────────────────┐
│ Text Instruction │────▶│ Web Search        │
│ "Change to..."   │     │ - Character refs  │
│                  │     │ - Style refs      │
└────────┬─────────┘     └─────────┬─────────┘
         │                         │
         ▼                         ▼
┌─────────────────────────────────────────────┐
│              Diffusion Pipeline              │
│  ┌─────────┐ ┌───────────┐ ┌─────────────┐  │
│  │  SDXL   │ │ControlNet │ │ IP-Adapter  │  │
│  └─────────┘ └───────────┘ └─────────────┘  │
│  ┌─────────┐ ┌───────────┐ ┌─────────────┐  │
│  │InstantID│ │   LoRA    │ │  PuLID      │  │
│  └─────────┘ └───────────┘ └─────────────┘  │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │ Upscaler       │
              │ - Real-ESRGAN  │
              │ - GFPGAN       │
              └────────┬───────┘
                       │
                       ▼
              ┌────────────────┐
              │ Output Image   │
              │ (High Quality) │
              └────────────────┘
```

---

## 🔬 Kỹ thuật chỉnh sửa ảnh nâng cao

### Prompt-to-Prompt (P2P)
- **Nguồn**: Google Research
- **Tính năng**: Chỉnh sửa cấu trúc ảnh bằng cách thay đổi attention maps
- **Ứng dụng**: Swap object, thay đổi thuộc tính mà giữ layout
- **Tích hợp**: A1111 extension, ComfyUI nodes

### Segment Anything + Inpainting
- **Pipeline**:
  1. SAM (Segment Anything Model) tách đối tượng
  2. SD Inpaint hoặc ControlNet chỉnh sửa từng phần
- **Ưu điểm**: Chọn lọc chính xác vùng cần edit
- **Tools**: Grounded-SAM, EditAnything

### Paint-by-Example
- **Tính năng**: Dùng ảnh mẫu làm reference cho inpainting
- **Ứng dụng**: Copy style/object từ ảnh khác vào vùng mask
- **Link**: [GitHub Paint-by-Example](https://github.com/Fantasy-Studio/Paint-by-Example)

### Attention Swap / Style Swap
- **Phương pháp**: Swap self-attention giữa ảnh style và content
- **Ưu điểm**: Không cần training, zero-shot style transfer
- **Hạn chế**: Chưa phổ biến trong production

---

## 🎌 Chi tiết các mô hình Anime quan trọng

### Waifu Diffusion v1.4 (Chi tiết)
```yaml
Model:
  Name: hakurei/waifu-diffusion-v1-4
  Base: Stable Diffusion 1.4
  License: CreativeML OpenRAIL-M (thương mại OK)
  Training Data: Danbooru 2018 (~3M images)
  
Capabilities:
  - Text-to-Image anime
  - Image-to-Image transformation
  - Hỗ trợ Danbooru tags
  
Recommended Settings:
  CFG Scale: 7-9
  Steps: 28-50
  Sampler: Euler a, DPM++ 2M Karras
  Resolution: 512x768, 768x512
```

### Anything V3/V4/V5 (Chi tiết)
```yaml
Model:
  V3: admruul/anything-v3.0
  V4: xyn-ai/anything-v4.0
  V5: stablediffusionapi/anything-v5
  Base: SD1.5
  License: CreativeML OpenRAIL-M
  
Features:
  - "Dành cho otaku"
  - Chi tiết cực cao với ít keywords
  - Hỗ trợ đầy đủ Danbooru tags
  - Có thể tạo NSFW
  
Recommended:
  Negative Prompt: "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"
```

### NovelAI Models (Chi tiết)
```yaml
V2 (Public):
  Name: NovelAI/nai-anime-v2
  Base: SD1.5
  License: CreativeML OpenRAIL-M + CC BY-NC-SA
  Status: Nghiên cứu/cá nhân only
  
V3 (Proprietary):
  Base: SDXL
  Features:
    - Tag ordering control
    - Attention manipulation
    - Chất lượng rất cao
  Access: Chỉ qua NovelAI service
  
V4 (Latest):
  Status: Proprietary, chất lượng cao nhất
  Access: NovelAI subscription only
```

### Licenses Summary

| Model | License | Commercial | NSFW | Notes |
|-------|---------|-----------|------|-------|
| Waifu Diffusion | CreativeML OpenRAIL-M | ✅ | ✅ | Tuân thủ luật pháp |
| Anything V3-V5 | CreativeML OpenRAIL-M | ✅ | ✅ | Free to use |
| Animagine XL 3.1 | CreativeML OpenRAIL++-M | ✅ | ✅ | Hạn chế harmful content |
| SDXL Anime V5 | Fair-IA-Public-1.0-SD | ⚠️ | ✅ | Hạn chế thương mại |
| NovelAI V2 | OpenRAIL-M + CC BY-NC-SA | ❌ | ✅ | Nghiên cứu only |
| NovelAI V3/V4 | Proprietary | ❌ | ✅ | Subscription |

---

## 🔍 Tìm kiếm nhân vật & Reference Images

### Workflow tìm kiếm tự động

```
User Input: "Tạo ảnh Miku Hatsune"
        │
        ▼
┌──────────────────────────┐
│ Character Recognition    │
│ - Parse character name   │
│ - Identify source/series │
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│ Multi-source Search      │
│ ┌──────────────────────┐ │
│ │ Danbooru API         │ │
│ │ - Tags: hatsune_miku │ │
│ │ - Get top images     │ │
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │ MyAnimeList API      │ │
│ │ - Character info     │ │
│ │ - Appearance details │ │
│ └──────────────────────┘ │
│ ┌──────────────────────┐ │
│ │ Pixiv/ArtStation     │ │
│ │ - Style references   │ │
│ └──────────────────────┘ │
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│ Reference Processing     │
│ - Extract features       │
│ - Build prompt           │
│ - Apply IP-Adapter       │
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│ Image Generation         │
│ - Animagine XL 3.1       │
│ - With character LoRA    │
│ - ControlNet pose        │
└──────────────────────────┘
```

### APIs cho Character Search

| Source | API | Features | Rate Limit |
|--------|-----|----------|------------|
| Danbooru | REST API | Tags, images, wiki | 10 req/min (free) |
| Gelbooru | REST API | Tags, images | Generous |
| MyAnimeList | Jikan API | Character info | 3 req/s |
| AniList | GraphQL | Character, media | 90 req/min |
| Pixiv | Unofficial | Search, images | Requires auth |

### Auto-tagging Pipeline

```python
# Ví dụ workflow tự động gắn tag

def auto_tag_image(image_path):
    """
    Tự động gắn Danbooru tags cho ảnh anime
    """
    # 1. Load taggers
    deepdanbooru = load_deepdanbooru()
    wd14_tagger = load_wd14_tagger()
    
    # 2. Predict tags
    dd_tags = deepdanbooru.predict(image_path, threshold=0.5)
    wd_tags = wd14_tagger.predict(image_path, threshold=0.35)
    
    # 3. Merge và filter
    merged = merge_tags(dd_tags, wd_tags)
    
    # 4. Format cho SD
    prompt = format_for_sd(merged)
    
    return prompt
```

---

## 🇨🇳 Nguồn tài nguyên Trung Quốc mở rộng

### ModelScope (阿里云模型库)

| Model | Description | Link |
|-------|-------------|------|
| Qwen-Image-Edit | SOTA image editing | [ModelScope](https://modelscope.cn/models/qwen/Qwen-Image-Edit) |
| Qwen2.5-VL | Vision-Language model | [ModelScope](https://modelscope.cn/models/qwen/Qwen2.5-VL) |
| Kolors | Text-to-Image anime | [ModelScope](https://modelscope.cn/models/Kwai-Kolors) |

### Baidu AI (百度)

| Tool | Description |
|------|-------------|
| ERNIE-ViLG | Text-to-Image, supports Chinese |
| Wenxin Yige | 文心一格 - Image generation |

### ByteDance (字节跳动)

| Model | Description |
|-------|-------------|
| PuLID | Identity preservation |
| MagicAnimate | Image-to-Video |
| AnimateAnyone | Character animation |

### Chinese Community Resources

| Platform | Content |
|----------|----------|
| CSDN Blog | Tutorials, implementations |
| Bilibili | Video tutorials |
| 知乎 (Zhihu) | Technical articles |
| GitHub China mirrors | Model weights |
| Hugging Face mirrors | HF-Mirror.com |

---

## 🛠️ Cập nhật Tool Edit Image

### Tính năng đã implement (v0.2.0) ✅

| Feature | Status | Module |
|---------|--------|--------|
| Text-to-Image | ✅ Complete | `app/core/pipeline.py` |
| Image-to-Image | ✅ Complete | `app/core/pipeline.py` |
| InstructPix2Pix Edit | ✅ Complete | `app/core/pipeline.py` |
| Inpainting | ✅ Complete | `app/api/routes.py` |
| ControlNet | ✅ Complete | `app/core/pipeline.py` |
| Anime Tab (UI) | ✅ Complete | `app/ui/gradio_app.py` |
| REST API | ✅ Complete | `app/api/routes.py` |
| Gradio Web UI | ✅ Complete | `app/ui/gradio_app.py` |
| Web Search Integration | ✅ Complete | `app/core/search.py` |
| Character Search | ✅ Complete | `app/core/search.py` |
| Auto-Tagging (WD14/DeepDanbooru) | ✅ Complete | `app/utils/tagger.py` |
| Upscaler (Real-ESRGAN) | ✅ Complete | `app/core/upscaler.py` |
| Face Restoration (GFPGAN) | ✅ Complete | `app/core/upscaler.py` |
| Search Tab (UI) | ✅ Complete | `app/ui/gradio_app.py` |
| Tagger Tab (UI) | ✅ Complete | `app/ui/gradio_app.py` |
| Upscale Tab (UI) | ✅ Complete | `app/ui/gradio_app.py` |
| Search API Routes | ✅ Complete | `app/api/routes.py` |
| Tagging API Routes | ✅ Complete | `app/api/routes.py` |
| Upscale API Routes | ✅ Complete | `app/api/routes.py` |

### Tính năng đã implement (v0.3.0) ✅ **NEW**

| Feature | Status | Module | Description |
|---------|--------|--------|-------------|
| **IP-Adapter Integration** | ✅ **NEW** | `app/core/ip_adapter.py` | Image prompts, FaceID Plus, style transfer |
| **InstantID Module** | ✅ **NEW** | `app/core/instantid.py` | Zero-shot face swap với InsightFace + ControlNet |
| **Inpaint Anything** | ✅ **NEW** | `app/core/inpaint_anything.py` | SAM + LaMa click-to-remove |
| **LLM-Enhanced InstructPix2Pix** | ✅ **NEW** | `app/core/enhanced_ip2p.py` | Instruction parsing, prompt enrichment, web search |
| **Qwen-Image-Edit Pipeline** | ✅ **NEW** | `app/core/qwen_edit.py` | 20B SOTA model, multi-turn editing, semantic + appearance |
| **Step1X-Edit Pipeline** | ✅ **NEW** | `app/core/step1x_edit.py` | LLM multimodal, reasoning mode, FP8 quantization |
| **LoRA Training Module** | ✅ **NEW** | `app/core/lora_training.py` | DreamBooth/LoRA training, dataset preparation, 8-bit Adam |
| **Anime ControlNet Models** | ✅ **NEW** | `app/core/anime_controlnet.py` | lineart_anime, openpose, multi-controlnet |
| **IP-Adapter Tab (UI)** | ✅ **NEW** | `app/ui/gradio_app.py` | Image prompt UI với FaceID toggle |
| **InstantID Tab (UI)** | ✅ **NEW** | `app/ui/gradio_app.py` | Face swap UI |
| **Inpaint Anything Tab (UI)** | ✅ **NEW** | `app/ui/gradio_app.py` | Click-to-remove UI |
| **Smart Edit Tab (UI)** | ✅ **NEW** | `app/ui/gradio_app.py` | LLM-enhanced editing UI |
| **IP-Adapter API Routes** | ✅ **NEW** | `app/api/routes.py` | `/api/v1/ip-adapter/*` |
| **InstantID API Routes** | ✅ **NEW** | `app/api/routes.py` | `/api/v1/instantid/*` |
| **Inpaint Anything API Routes** | ✅ **NEW** | `app/api/routes.py` | `/api/v1/inpaint-anything/*` |
| **Smart Edit API Routes** | ✅ **NEW** | `app/api/routes.py` | `/api/v1/smart-edit/*` |

### Tính năng cần bổ sung (v0.4.0)

| Feature | Priority | Notes |
|---------|----------|-------|
| PuLID Integration | 🟡 Medium | Alternative face preservation |
| EcomID Integration | 🟡 Medium | Alibaba identity preservation |
| Batch Processing | 🟢 Low | Multiple images |
| CLI Interface | 🟢 Low | Command line tool |
| CodeFormer | 🟢 Low | Alternative face restoration |
| Multi-GPU Support | 🟢 Low | Load balancing across GPUs |
| Model Offloading | 🟢 Low | Sequential offload for low VRAM |

### Architecture (v0.3.0 - Updated)

```
services/edit-image/
├── app/
│   ├── core/
│   │   ├── pipeline.py           # ✅ Diffusion pipelines (SDXL, InstructPix2Pix)
│   │   ├── config.py             # ✅ Pydantic configuration
│   │   ├── search.py             # ✅ Web search (Danbooru, Gelbooru, AniList, MAL)
│   │   ├── upscaler.py           # ✅ Post-processing (Real-ESRGAN, GFPGAN)
│   │   ├── ip_adapter.py         # ✅ NEW: IP-Adapter integration (FaceID, style transfer)
│   │   ├── instantid.py          # ✅ NEW: InstantID face swap (InsightFace + ControlNet)
│   │   ├── inpaint_anything.py   # ✅ NEW: SAM + LaMa inpainting
│   │   ├── enhanced_ip2p.py      # ✅ NEW: LLM-enhanced InstructPix2Pix
│   │   ├── qwen_edit.py          # ✅ NEW: Qwen-Image-Edit 20B pipeline
│   │   ├── step1x_edit.py        # ✅ NEW: Step1X-Edit with reasoning mode
│   │   ├── lora_training.py      # ✅ NEW: LoRA/DreamBooth training module
│   │   └── anime_controlnet.py   # ✅ NEW: Anime-specialized ControlNet
│   ├── api/
│   │   └── routes.py             # ✅ All REST endpoints (v0.3.0: +500 lines)
│   ├── ui/
│   │   └── gradio_app.py         # ✅ Web interface (14 tabs)
│   └── utils/
│       ├── image_utils.py        # ✅ Image processing
│       ├── controlnet_utils.py   # ✅ ControlNet preprocessing
│       └── tagger.py             # ✅ Auto-tagging (WD14, DeepDanbooru)
├── config/
│   └── settings.yaml             # ✅ Configuration file
├── Dockerfile                    # ✅ Docker build
├── docker-compose.yml            # ✅ Docker compose
├── requirements.txt              # ✅ Python dependencies (v0.3.0 updated)
├── start.bat / start.sh          # ✅ Startup scripts
└── setup.bat                     # ✅ Setup script
```

### API Endpoints (v0.3.0)

| Endpoint | Method | Description |
|----------|--------|-------------|
| **Core Endpoints** | | |
| `/api/v1/health` | GET | Health check |
| `/api/v1/models` | GET | List available models |
| `/api/v1/generate` | POST | Text-to-Image |
| `/api/v1/edit` | POST | InstructPix2Pix edit |
| `/api/v1/img2img` | POST | Image-to-Image |
| `/api/v1/inpaint` | POST | Inpainting |
| `/api/v1/controlnet` | POST | ControlNet generation |
| **Search & Tagging** | | |
| `/api/v1/search/images` | POST | Search reference images |
| `/api/v1/search/character` | POST | Search character info |
| `/api/v1/tag` | POST | Auto-tag image |
| `/api/v1/image-to-prompt` | POST | Convert image to prompt |
| **Post-processing** | | |
| `/api/v1/upscale` | POST | Upscale image |
| `/api/v1/restore-faces` | POST | Face restoration |
| `/api/v1/enhance` | POST | Full enhancement pipeline |
| **IP-Adapter (NEW)** | | |
| `/api/v1/ip-adapter/generate` | POST | Generate with image prompt |
| `/api/v1/ip-adapter/face-transfer` | POST | FaceID transfer |
| `/api/v1/ip-adapter/style-transfer` | POST | Style transfer |
| **InstantID (NEW)** | | |
| `/api/v1/instantid/swap` | POST | Face swap |
| `/api/v1/instantid/generate` | POST | Generate with face identity |
| **Inpaint Anything (NEW)** | | |
| `/api/v1/inpaint-anything/segment` | POST | SAM segmentation |
| `/api/v1/inpaint-anything/remove` | POST | Click-to-remove object |
| `/api/v1/inpaint-anything/replace` | POST | Replace segmented region |
| **Smart Edit (NEW)** | | |
| `/api/v1/smart-edit/parse` | POST | Parse edit instruction |
| `/api/v1/smart-edit/edit` | POST | LLM-enhanced edit |
| `/api/v1/smart-edit/qwen` | POST | Qwen-Image-Edit |
| `/api/v1/smart-edit/step1x` | POST | Step1X-Edit |
| **System** | | |
| `/api/v1/clear-cache` | POST | Clear pipeline cache |
| `/api/v1/vram` | GET | VRAM usage stats |

### Gradio UI Tabs (v0.3.0)

1. **Text to Image** - Generate from text prompt
2. **Image to Image** - Transform existing images
3. **Edit Image** - InstructPix2Pix editing
4. **Inpaint** - Fill in regions with brush mask
5. **ControlNet** - Guided generation
6. **Anime** - Specialized anime generation
7. **🎨 IP-Adapter** - Image prompt & style transfer (**NEW**)
8. **👤 InstantID** - Zero-shot face swap (**NEW**)
9. **✂️ Inpaint Anything** - Click-to-remove (**NEW**)
10. **🧠 Smart Edit** - LLM-enhanced editing (**NEW**)
11. **🔍 Search** - Character & reference search
12. **🏷️ Tagger** - Auto-tagging from images
13. **⬆️ Upscale** - Image enhancement
14. **⚙️ Settings** - System info & cache

---

> **Note**: Tài liệu này đang được cập nhật liên tục. Theo dõi các thay đổi trong changelog.
> 
> **v0.3.0 Complete! 🎉 All major features from private docs research implemented!**
> 
> ### v0.3.0 Highlights:
> - 🎨 **IP-Adapter** - Image prompts, FaceID Plus, style transfer
> - 👤 **InstantID** - Zero-shot face swap with InsightFace + ControlNet
> - ✂️ **Inpaint Anything** - SAM + LaMa click-to-remove
> - 🧠 **Smart Edit** - LLM-enhanced editing with web search
> - 🚀 **SOTA Models** - Qwen-Image-Edit (20B) + Step1X-Edit (reasoning mode)
> - 🎓 **LoRA Training** - In-app training with dataset preparation
> - 🎌 **Anime ControlNet** - lineart_anime, openpose, multi-controlnet
