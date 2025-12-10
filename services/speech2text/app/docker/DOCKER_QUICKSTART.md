# 🐳 Docker Quick Start - VistralS2T

## ✅ Đã Fix Lỗi Docker Build

### 🔧 Các Thay Đổi:

1. **docker-compose.yml:**
   - ✅ Xóa `version: '3.8'` (obsolete)
   - ✅ Sửa `context: ../../` (từ root project)
   - ✅ Sửa `dockerfile: app/docker/Dockerfile`

2. **Dockerfile:**
   - ✅ Sửa `COPY requirements.txt .` (từ root)
   - ✅ Sửa `COPY app/core /app/core` (đường dẫn từ root)
   - ✅ Thêm copy app/data, app/tests

## 🚀 Sử Dụng Docker

### Bước 1: Build Image

```bash
cd app/docker
docker compose build
```

### Bước 2: Chuẩn Bị Audio

```bash
# Copy file audio vào input/
copy path\to\your\audio.mp3 input\audio.mp3
```

### Bước 3: Chạy Container

```bash
docker compose up -d
```

### Bước 4: Xem Logs

```bash
# Xem logs realtime
docker compose logs -f

# Xem logs của s2t-system
docker logs s2t-qwen-fusion -f
```

### Bước 5: Lấy Kết Quả

Kết quả sẽ xuất hiện trong:
```
app/docker/output/
├── raw/                # Whisper + PhoWhisper outputs
├── vistral/           # Final fused result ⭐
└── dual/              # Processing logs
```

## 🛠️ Các Lệnh Hữu Ích

```bash
# Kiểm tra status
docker compose ps

# Stop container
docker compose down

# Rebuild từ đầu
docker compose build --no-cache

# Vào trong container
docker exec -it s2t-qwen-fusion bash

# Xem resource usage
docker stats s2t-qwen-fusion

# Xóa container và volumes
docker compose down -v
```

## ⚙️ Configuration

### Set HuggingFace Token (Optional)

Tạo file `.env` trong `app/docker/`:

```env
HF_API_TOKEN=hf_your_token_here
```

### Custom Audio Path

Edit `docker-compose.yml`:

```yaml
environment:
  - AUDIO_PATH=/app/input/your_audio.mp3
```

## 🐛 Troubleshooting

### Container Exit ngay sau khi start

```bash
# Xem logs
docker logs s2t-qwen-fusion

# Chạy interactive để debug
docker run -it --rm docker-s2t-system bash
```

### GPU không nhận

```bash
# Kiểm tra nvidia-docker
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Nếu lỗi, cài lại nvidia-docker:
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
```

### Out of Memory

```bash
# Giảm memory usage trong docker-compose.yml
services:
  s2t-system:
    deploy:
      resources:
        limits:
          memory: 8G
```

### Build Lỗi "not found"

```bash
# Đảm bảo chạy từ đúng folder
cd d:\WORK\s2t\app\docker

# Build lại
docker compose build --no-cache
```

## 📊 Resource Requirements

- **Memory:** 8GB+ RAM
- **GPU:** NVIDIA GPU with 6GB+ VRAM
- **Disk:** 20GB (models + cache)
- **NVIDIA Docker Runtime:** Required

## 🔗 Links

- [Docker Compose Docs](https://docs.docker.com/compose/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)
- [Main README](../../README.md)

---

**Status:** ✅ Docker Ready | **Last Updated:** 2025-10-23
