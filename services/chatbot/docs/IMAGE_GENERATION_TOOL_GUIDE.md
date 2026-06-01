# 🎨 Image Generation Guide

Hệ thống tạo ảnh đa-provider của ChatBot. Router `core/image_gen/router.py`
(`ImageGenerationRouter`) tự chọn provider tốt nhất theo **priority** + `QualityMode`,
và fallback xuống provider thấp hơn khi provider đầu lỗi.

> Tài liệu cũ mô tả Stable Diffusion WebUI đơn lẻ (AnythingV4, port 7860) đã được
> thay thế hoàn toàn bằng router đa-provider này từ bản v2.

---

## Providers

8 provider tại `core/image_gen/providers/`, chỉ đăng ký khi có env key tương ứng:

| Provider | Priority | Env key | Models tiêu biểu |
|---|---|---|---|
| fal.ai | 90 | `FAL_API_KEY` | FLUX.2 (dev/pro/klein), nano-banana(-pro/-2), seedream5, recraft-v4 |
| Black Forest Labs | 85 | `BFL_API_KEY` | FLUX.2 pro/dev/max, FLUX1 pro/dev |
| Replicate | 80 | `REPLICATE_API_TOKEN` | grok-imagine, FLUX.2, flux-kontext-pro, sdxl-lightning |
| StepFun | 75 | `STEPFUN_API_KEY` | step1x turbo/medium/edit/fill |
| OpenAI | 70 | `OPENAI_API_KEY` | gpt-image-1, DALL-E 3 |
| Together AI | 60 | `TOGETHER_API_KEY` | FLUX1 schnell/dev/kontext/canny/depth/redux |
| ComfyUI Fast | 15 | `COMFYUI_URL` / `SD_API_URL` | local single-pass (~10s, SAA-style) |
| ComfyUI | 10 | `COMFYUI_URL` / `SD_API_URL` | local multi-pass workflow (SD1.5/SDXL) |

> `nano-banana*` models được phục vụ qua fal.ai/Replicate. Ngoài ra có surface trực
> tiếp `routes/nano_banana.py` (`/api/nano-banana/*`) dùng Gemini Image, gate bằng
> `NANO_BANANA_ENABLED` (mặc định `true`).

ComfyUI/ComfyUI Fast chỉ đăng ký khi runtime profile **không** bật
`skip_comfyui_provider` (máy yếu sẽ bỏ qua local provider).

---

## Quality modes

`QualityMode` quyết định thứ tự chọn provider:

| Mode | Hành vi |
|---|---|
| `auto` (mặc định) | Gom provider cùng tier (chênh ≤15 điểm priority) → random để phân tải |
| `fast` | Ưu tiên tier FAST/LOCAL (schnell, klein, comfyui_fast) |
| `quality` | Ưu tiên tier ULTRA/HIGH |
| `free` | Chỉ local (ComfyUI) — không tốn phí |
| `cheap` | Sort theo `cost_per_image` tăng dần |

Khi provider đầu lỗi, router thử provider tiếp theo theo priority giảm dần
(fallback chain). Stream endpoint phát event `provider_try` cho mỗi lần thử.

---

## API Endpoints

Blueprint `routes/image_gen.py` (không có url_prefix, route dùng `/api/image-gen/*`):

| Method | Path | Mô tả |
|---|---|---|
| `POST` | `/api/image-gen/generate` | Tạo ảnh (JSON response) |
| `POST` | `/api/image-gen/stream` | Tạo ảnh (SSE, có event `provider_try`) |
| `POST` | `/api/image-gen/edit` | Edit ảnh gần nhất (img2img) |
| `GET` | `/api/image-gen/providers` | List provider đang bật |
| `GET` | `/api/image-gen/styles` | List style preset |
| `GET` | `/api/image-gen/health` | Health check tất cả provider |
| `GET` | `/api/image-gen/stats` | Thống kê usage + chi phí |
| `GET` | `/api/image-gen/gallery` | Ảnh đã tạo gần đây |
| `GET` | `/api/image-gen/images/<id>` | Serve ảnh theo ID |
| `DELETE` | `/api/image-gen/images/<id>` | Xoá ảnh |
| `POST` | `/api/image-gen/save/<id>` | Upload Google Drive + ImgBB + MongoDB |
| `GET` | `/api/image-gen/meta/<id>` | Metadata ảnh |
| `GET` | `/api/image-gen/loras` | List LoRA catalog (filter/pagination) |
| `GET/POST` | `/api/image-gen/loras/suggest` | Preview LoRA auto-inject cho prompt |
| `GET` | `/api/image-gen/loras/stats` | Thống kê LoRA catalog |
| `POST` | `/api/image-gen/loras/reload` | Rebuild LoRA catalog |

### Surface gen khác

| Path | Gate flag | Mô tả |
|---|---|---|
| `/api/nano-banana/*` | `NANO_BANANA_ENABLED` (default `true`) | Gemini Image trực tiếp |
| `/api/anime-pipeline/*` | `IMAGE_PIPELINE_V2` (default `true`) | Anime pipeline 7-agent + ComfyUI |
| `/api/reasoning-image-gen/*` | `REASONING_PIPELINE` (default `false`) | Multi-panel local pipeline |
| `/api/video/*` | — | Sora 2 text/image-to-video |

---

## Request payload (generate / stream)

```json
{
  "prompt": "anime girl, long hair, cherry blossom",
  "provider": null,
  "quality_mode": "auto",
  "width": 1024,
  "height": 1024,
  "num_images": 1,
  "style": null,
  "enhance_prompt": true
}
```

Giới hạn (xem `routes/image_gen.py`): `prompt` ≤ 2000 ký tự, dim 64–3840,
steps ≤ 150, rate limit 10 request / 60s mỗi session.

---

## Tính năng tự động

- **Prompt enhancement** — `core/image_gen/enhancer.py` rewrite prompt bằng LLM
  trước khi gen (tắt được qua `enhance_prompt: false`).
- **Character auto-detection** — `character_detector.py` quét prompt, nếu khớp
  character (local registry + SAA fallback) sẽ auto-inject LoRA và ép provider
  `comfyui_fast`.
- **LoRA auto-resolution** — `lora_resolver.py` phát hiện trigger (style/NSFW/outfit)
  và resolve tối đa 4 LoRA cho local provider.

---

## Troubleshooting

**Không có provider nào khả dụng** → kiểm tra env key. Router log
`[ImageRouter] Initialized providers: [...]` khi khởi động cho biết provider nào
được đăng ký.

**ComfyUI / anime pipeline trả 503** → ComfyUI chưa chạy. Start ComfyUI tại
`COMFYUI_URL` (mặc định `http://127.0.0.1:8188`) trước khi gọi.

**Muốn chỉ dùng local, không tốn phí** → đặt `quality_mode: "free"` hoặc
`provider: "comfyui"`.

---

**Updated:** 2026-06 · multi-provider router (`core/image_gen`)
