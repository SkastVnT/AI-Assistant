# ChatBot Docs

Index tài liệu cho ChatBot service (Flask monolith, port 5000).
Tài liệu gốc/authoritative là [../README.md](../README.md). File này chỉ điều hướng.

> Lưu ý: hệ thống tạo ảnh đã chuyển từ Stable Diffusion WebUI đơn lẻ (port 7860,
> AnythingV4) sang **router đa-provider** `core/image_gen`. Một số guide cũ trong
> thư mục này có thể còn nhắc tới setup cũ — ưu tiên các file đã đánh dấu *Updated 2026*.

---

## Image Generation (gen)

| Doc | Nội dung |
|---|---|
| [IMAGE_GENERATION_TOOL_GUIDE.md](IMAGE_GENERATION_TOOL_GUIDE.md) | **Chính** — router đa-provider, quality modes, endpoints, payload |
| [IMG2IMG_ADVANCED_GUIDE.md](IMG2IMG_ADVANCED_GUIDE.md) | Img2img / edit flow nâng cao |
| [LORA_VAE_GUIDE.md](LORA_VAE_GUIDE.md) | LoRA + VAE cho local ComfyUI |
| [LOCAL_MODELS_GUIDE.md](LOCAL_MODELS_GUIDE.md) | Quản lý checkpoint/model local |

Tóm tắt provider (chi tiết ở guide trên):

| Provider | Priority | Env key |
|---|---|---|
| fal.ai | 90 | `FAL_API_KEY` |
| Black Forest Labs | 85 | `BFL_API_KEY` |
| Replicate | 80 | `REPLICATE_API_TOKEN` |
| StepFun | 75 | `STEPFUN_API_KEY` |
| OpenAI | 70 | `OPENAI_API_KEY` |
| Together AI | 60 | `TOGETHER_API_KEY` |
| ComfyUI Fast | 15 | `COMFYUI_URL` / `SD_API_URL` |
| ComfyUI | 10 | `COMFYUI_URL` / `SD_API_URL` |

Surface gen khác: `/api/nano-banana/*` (`NANO_BANANA_ENABLED`),
`/api/anime-pipeline/*` (`IMAGE_PIPELINE_V2`),
`/api/reasoning-image-gen/*` (`REASONING_PIPELINE`), `/api/video/*` (Sora 2).

---

## Tools & Integration

| Doc | Nội dung |
|---|---|
| [TOOLS_INTEGRATION_GUIDE.md](TOOLS_INTEGRATION_GUIDE.md) | Web search, reverse image, SauceNAO |
| [MCP_INTEGRATION.md](MCP_INTEGRATION.md) | MCP server (stdio) integration |
| [last30days_integration.md](last30days_integration.md) | Social research tool (`LAST30DAYS_ENABLED`) |
| [council-streaming-events.md](council-streaming-events.md) | SSE events cho 4-agent council |

## Database

| Doc | Nội dung |
|---|---|
| [MONGODB_SETUP.md](MONGODB_SETUP.md) | Cấu hình MongoDB |
| [MONGODB_INTEGRATION.md](MONGODB_INTEGRATION.md) | Repository pattern + query cache |
| [MONGODB_DATA_PUSH_GUIDE.md](MONGODB_DATA_PUSH_GUIDE.md) | Đẩy dữ liệu vào MongoDB |
| [STORAGE_MANAGEMENT.md](STORAGE_MANAGEMENT.md) | Quản lý storage ảnh/file |

## Vận hành

| Doc | Nội dung |
|---|---|
| [USAGE_GUIDE.md](USAGE_GUIDE.md) | Hướng dẫn sử dụng |
| [TESTING_GUIDE.md](TESTING_GUIDE.md) | Chạy test (venv-core) |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Xử lý sự cố |
| [CHANGELOG.md](CHANGELOG.md) | Lịch sử thay đổi |
| [architecture/](architecture/) | Ghi chú kiến trúc (agentic, xAI native) |

---

## Khởi động nhanh

```powershell
# Browser
python services/chatbot/run.py     # http://127.0.0.1:5000

# Desktop (Electron frameless + tray)
cd app/electron && npm run dev
```

Env loader: `services/shared_env.py` → `load_shared_env(__file__)` (1 lần/process),
đọc `app/config/.env_dev` hoặc `.env`. Xem [../README.md](../README.md) cho danh sách
env key đầy đủ.
