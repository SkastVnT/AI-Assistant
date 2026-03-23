# 🐳 Docker Deployment Guide

## 🚀 Quick Start

### Production Environment
```bash
# 1. Configure environment
cp .env.docker .env
# Edit .env with your GEMINI_API_KEY

# 2. Start all services
docker\manage.bat start
# or on Linux: bash docker/manage.sh start

# 3. Access services
# API: http://localhost/docs
# Health Monitor: http://localhost/monitoring/
```

### Development Environment
```bash
# Start dev environment (CPU only, hot reload)
docker\manage.bat start-dev

# Access services
# API: http://localhost:8000/docs
# File Server: http://localhost:8090
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   Nginx (Port 80)               │
│              Load Balancer & Proxy              │
└─────────────────┬───────────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌─────────┐  ┌─────────┐  ┌─────────┐
│   API   │  │ Health  │  │  File   │
│ Service │  │Monitor  │  │ Server  │
│ :8000   │  │ :8080   │  │ :8090   │
└─────────┘  └─────────┘  └─────────┘
    │
    ├── Model Services ──────────────────┐
    │                                    │
    ▼                                    ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
│   T5    │  │PhoWhis  │  │Whisper  │  │ Gemini  │
│ :8001   │  │ :8002   │  │ :8003   │  │ :8004   │
└─────────┘  └─────────┘  └─────────┘  └─────────┘

    ├── Supporting Services ─────────────┐
    │                                    │
    ▼                                    ▼
┌─────────┐                         ┌─────────┐
│  Redis  │                         │Postgres │
│ :6379   │                         │ :5432   │
└─────────┘                         └─────────┘
```

## 📦 Services

### Core Services

| Service | Port | Description | GPU Required |
|---------|------|-------------|--------------|
| **API** | 8000 | Main FastAPI web service | No |
| **T5** | 8001 | T5 AI fusion (offline) | Yes |
| **PhoWhisper** | 8002 | Vietnamese specialized | Yes |
| **Whisper** | 8003 | OpenAI Whisper baseline | Yes |
| **Gemini** | 8004 | Cloud AI proxy | No |

### Supporting Services

| Service | Port | Description | Data |
|---------|------|-------------|------|
| **Nginx** | 80/443 | Load balancer & proxy | - |
| **Redis** | 6379 | Caching & job queue | Memory |
| **PostgreSQL** | 5432 | Results database | Persistent |
| **Health Monitor** | 8080 | System monitoring | - |

## 🔧 Management Commands

### Windows
```cmd
docker\manage.bat COMMAND [OPTIONS]
```

### Linux/Mac
```bash
bash docker/manage.sh COMMAND [OPTIONS]
```

### Available Commands

| Command | Description |
|---------|-------------|
| `start` | Start production environment |
| `start-dev` | Start development environment |
| `stop` | Stop all services |
| `restart` | Restart all services |
| `logs [service]` | View logs |
| `status` | Show service status |
| `health` | Check system health |
| `shell service` | Enter container shell |
| `build` | Build all images |
| `clean` | Remove all data |
| `update` | Update and restart |

## 🌐 API Endpoints

### Main API (Port 8000/80)
- `GET /` - Service information
- `GET /health` - Health check
- `POST /upload` - Upload audio file
- `POST /transcribe` - Start transcription
- `GET /status/{job_id}` - Check job status
- `GET /download/{job_id}` - Download result
- `GET /models` - Available models
- `GET /docs` - API documentation

### Model Services (Ports 8001-8004)
- `GET /health` - Service health
- `POST /transcribe` - Direct transcription
- `GET /` - Service info

### Health Monitor (Port 8080)
- `GET /health` - Full system health
- `GET /metrics` - Performance metrics
- `GET /services` - Service status

## 🔑 Configuration

### Environment Variables (.env.docker)
```env
# Required
GEMINI_API_KEY=your_api_key_here

# Optional
CUDA_VISIBLE_DEVICES=0
POSTGRES_PASSWORD=custom_password
REDIS_URL=redis://redis:6379
```

### GPU Configuration
For NVIDIA GPU support:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

## 💾 Data Persistence

### Volumes
- `model_cache` - Downloaded AI models
- `postgres_data` - Database storage
- `redis_data` - Cache storage

### Host Mounts
- `./audio` → `/app/audio` - Input audio files
- `./result` → `/app/result` - Output transcripts
- `./logs` → `/app/logs` - Application logs

## 🔍 Monitoring

### Health Checks
```bash
# Quick health check
curl http://localhost/health

# Detailed system health
curl http://localhost/monitoring/health

# Individual service health
curl http://localhost/t5/health
curl http://localhost/phowhisper/health
```

### Logs
```bash
# All logs
docker\manage.bat logs

# Specific service
docker\manage.bat logs api
docker\manage.bat logs t5-service
```

### Performance
```bash
# Resource usage
docker\manage.bat status

# System metrics
curl http://localhost/monitoring/metrics
```

## 🛠️ Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check requirements
docker --version
docker-compose --version

# Check logs
docker\manage.bat logs
```

**GPU not detected:**
```bash
# Check NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:11.8-base-ubuntu22.04 nvidia-smi

# Update CUDA_VISIBLE_DEVICES in .env.docker
```

**API connection errors:**
```bash
# Check service health
docker\manage.bat health

# Restart services
docker\manage.bat restart
```

**Out of memory:**
```bash
# Check resources
docker stats

# Clean up
docker\manage.bat clean
```

### Debug Mode

Enter container for debugging:
```bash
# Enter API container
docker\manage.bat shell api

# Enter T5 service
docker\manage.bat shell t5-service

# Check logs inside container
tail -f /app/logs/app.log
```

## 🔄 Updates

### Update Services
```bash
# Pull latest images and restart
docker\manage.bat update
```

### Rebuild from Source
```bash
# Rebuild all images
docker\manage.bat build

# Restart with new images
docker\manage.bat restart
```

## 🚀 Production Deployment

### Security
- Change default passwords in `.env.docker`
- Use SSL certificates in `docker/ssl/`
- Enable firewall rules
- Use external database for production

### Scaling
```bash
# Scale specific services
docker-compose up -d --scale t5-service=2
docker-compose up -d --scale phowhisper-service=3
```

### External Services
```env
# Use external database
DATABASE_URL=postgresql://user:pass@external-db:5432/s2t_db

# Use external Redis
REDIS_URL=redis://external-redis:6379
```

## 📊 Usage Examples

### 1. Upload and Transcribe
```bash
# Upload audio file
curl -X POST -F "file=@audio.mp3" http://localhost/upload

# Start transcription
curl -X POST "http://localhost/transcribe?file_id=YOUR_FILE_ID&model=t5"

# Check status
curl http://localhost/status/YOUR_JOB_ID

# Download result
curl http://localhost/download/YOUR_JOB_ID
```

### 2. Development Workflow
```bash
# Start dev environment
docker\manage.bat start-dev

# Make changes to code
# Code auto-reloads in dev mode

# View logs
docker\manage.bat logs api-dev

# Test API
curl http://localhost:8000/docs
```

### 3. Production Monitoring
```bash
# Start production
docker\manage.bat start

# Monitor health
curl http://localhost/monitoring/health

# Check performance
curl http://localhost/monitoring/metrics

# View service status
docker\manage.bat status
```

---

**Version**: 2.0.0  
**Updated**: October 20, 2025  
**Docker**: Production Ready 🐳