# AI-Assistant

Nền tảng microservices tích hợp nhiều dịch vụ AI: chatbot, speech-to-text, OCR, text-to-sql, image upscale, lora training, mcp server.

## Tổng quan

- Kiến trúc: Python + Flask theo mô hình nhiều service.
- Chạy cục bộ bằng script hoặc Docker Compose.
- Dùng cấu hình môi trường chung qua file `.env` trong `app/config`.

## Cổng dịch vụ

| Service | Port |
| --- | --- |
| ChatBot | 5000 |
| Hub Gateway | 3000 |
| Speech2Text | 5001 |
| Text2SQL | 5002 |
| Document Intelligence | 5003 |
| ComfyUI | 8188 |

## Chạy nhanh

### 1) Clone và chạy menu

```bash
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant

# Windows
menu.bat

# Linux/Mac
./menu.sh
```

### 2) Chạy bằng Docker

```bash
# Full stack
docker-compose -f app/config/docker-compose.yml up -d

# Lightweight mode
docker-compose -f app/config/docker-compose.light.yml up -d

# Health check chatbot
curl http://localhost:5000/health
```

### 3) Chạy từng service (Windows)

```bat
app\scripts\start-chatbot.bat
app\scripts\start-hub-gateway.bat
app\scripts\start-speech2text.bat
app\scripts\start-document-intelligence.bat
app\scripts\start-text2sql.bat
```

## Cấu hình môi trường

Tạo file môi trường từ mẫu:

```bash
app/config/.env.example -> app/config/.env
```

Biến tối thiểu nên có:

```env
# Chọn ít nhất 1 nhà cung cấp LLM
GROK_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
DEEPSEEK_API_KEY=

# Database
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=chatbot

# Shared env profile
env=dev
```

## Cấu trúc thư mục chính

```text
services/            # Các service chính
app/config/          # Cấu hình và docker compose
app/scripts/         # Script vận hành
app/requirements/    # Bộ requirements theo nhóm
tests/               # Test suite
private/             # Dữ liệu/submodule nội bộ
```

## Tài liệu liên quan

- [app/scripts/README.md](app/scripts/README.md)
- [app/requirements/README.md](app/requirements/README.md)
- [tests/README.md](tests/README.md)
- [SECURITY.md](SECURITY.md)

## Contributing

1. Tạo nhánh mới từ `master`.
2. Commit theo phạm vi thay đổi.
3. Mở Pull Request.

## Author & Collaborator

- [SkastVnT](https://github.com/SkastVnT)
- [sug1omyo](https://github.com/sug1omyo)

## License

MIT. Xem chi tiết tại [LICENSE](LICENSE).
