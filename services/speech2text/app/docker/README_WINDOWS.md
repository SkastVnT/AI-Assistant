# Docker Setup for Windows - Speech2Text System

## Yêu cầu (Requirements)

1. **Docker Desktop for Windows** (đã cài đặt và đang chạy)
2. **WSL2** (Windows Subsystem for Linux 2) - để GPU passthrough
3. **NVIDIA GPU** với driver hỗ trợ CUDA 11.8+

## Hướng dẫn nhanh (Quick Start)

### 1. Khởi động Docker Desktop
- Mở Docker Desktop
- Đợi cho đến khi thấy "Docker Desktop is running"

### 2. Sử dụng script tự động

```bash
cd app\docker
docker-manage.bat
```

Chọn:
- **Option 3**: Build và start lần đầu tiên
- **Option 2**: Start containers (nếu đã build)
- **Option 4**: Stop containers
- **Option 5**: Xem logs

### 3. Hoặc chạy thủ công

#### Build image:
```bash
cd app\docker
docker compose -f docker-compose.windows.yml build
```

#### Start containers:
```bash
docker compose -f docker-compose.windows.yml up -d
```

#### Xem logs:
```bash
docker compose -f docker-compose.windows.yml logs -f
```

#### Stop containers:
```bash
docker compose -f docker-compose.windows.yml down
```

## Cấu trúc thư mục (Directory Structure)

```
app/docker/
├── docker-compose.windows.yml   # Docker Compose config for Windows
├── Dockerfile                    # Docker image definition
├── .env                         # Environment variables (API keys)
├── docker-manage.bat            # Management script
├── input/                       # Input audio files
├── output/                      # Transcription results
└── logs/                        # Application logs
```

## Cấu hình (Configuration)

### File .env
Chứa các API keys và tokens:
- `HF_TOKEN` - HuggingFace token để download models
- `HF_API_TOKEN` - HuggingFace API token
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `GEMINI_API_KEY` - Google Gemini API key (optional)

### File docker-compose.windows.yml
- Đã tối ưu cho Windows + WSL2
- Không sử dụng `runtime: nvidia` (gây lỗi trên Windows)
- GPU passthrough thông qua WSL2 deploy config

## Troubleshooting

### Lỗi: "The system cannot find the file specified"
**Nguyên nhân**: Docker Desktop chưa chạy
**Giải pháp**: Mở Docker Desktop và đợi nó khởi động hoàn toàn

### Lỗi: "unable to get image"
**Nguyên nhân**: Image chưa được build
**Giải pháp**: Chạy build trước:
```bash
docker compose -f docker-compose.windows.yml build
```

### Lỗi: "GPU not available"
**Nguyên nhân**: 
1. WSL2 chưa cài đặt
2. NVIDIA driver chưa hỗ trợ WSL2
3. Docker Desktop chưa enable WSL2 integration

**Giải pháp**:
1. Cài đặt WSL2: `wsl --install`
2. Update NVIDIA driver: https://www.nvidia.com/Download/index.aspx
3. Docker Desktop > Settings > Resources > WSL Integration > Enable

### Lỗi: "HF_TOKEN not set"
**Nguyên nhân**: File .env chưa có hoặc thiếu HF_TOKEN
**Giải pháp**: Tạo file `.env` trong thư mục docker với nội dung:
```
HF_TOKEN=your_huggingface_token_here
HF_API_TOKEN=your_huggingface_token_here
```

## Sử dụng (Usage)

### 1. Đặt file audio vào input/
```bash
copy "C:\path\to\your\audio.mp3" "app\docker\input\"
```

### 2. Chạy container
```bash
docker compose -f docker-compose.windows.yml up -d
```

### 3. Xem kết quả trong output/
Kết quả sẽ xuất hiện trong thư mục `app\docker\output\`

### 4. Xem logs realtime
```bash
docker compose -f docker-compose.windows.yml logs -f
```

## Performance Tips

### Giảm memory usage
Trong `docker-compose.windows.yml`, thay đổi:
```yaml
limits:
  memory: 12G  # Giảm xuống 8G nếu RAM hệ thống < 16GB
```

### Cache models
Models sẽ được cache trong Docker volumes:
- `model_cache` - HuggingFace models
- `torch_cache` - PyTorch cache

Để xóa cache:
```bash
docker volume rm docker_model_cache docker_torch_cache
```

## Cleanup

### Xóa containers và networks
```bash
docker compose -f docker-compose.windows.yml down
```

### Xóa image
```bash
docker rmi vistral-s2t:3.5
```

### Xóa volumes (cache)
```bash
docker compose -f docker-compose.windows.yml down -v
```

## Support

Nếu gặp vấn đề, check logs:
```bash
docker compose -f docker-compose.windows.yml logs --tail=100
```

Hoặc vào trong container để debug:
```bash
docker exec -it s2t-optimized-v3.5 bash
```
