# LoRA Training Tool - Quick Start Guide

## 🚀 Installation

### Windows:
```cmd
# 1. Run setup (one-time)
bin\setup.bat

# 2. Start WebUI with Redis
bin\start_webui_with_redis.bat
```

### Linux/Mac:
```bash
# 1. Run setup (one-time)
chmod +x bin/setup.sh
./bin/setup.sh

# 2. Start WebUI with Redis
chmod +x bin/start_webui_with_redis.sh
./bin/start_webui_with_redis.sh
```

## 📋 Setup Steps

### 1. First Time Setup:
```cmd
bin\setup.bat
```

This will:
- ✅ Create virtual environment (./lora/)
- ✅ Install PyTorch (choose CPU/CUDA)
- ✅ Install all dependencies
- ✅ Setup WD14 Tagger
- ✅ Install Redis client

**Choose PyTorch version:**
- **Option 1**: CPU only (no GPU required)
- **Option 2**: CUDA 11.8 (for RTX 20/30 series)
- **Option 3**: CUDA 12.1 (for RTX 40 series)

### 2. Configure API Keys:

Edit `.env` file:
```env
# Gemini API (for AI config recommendations)
GEMINI_API_KEY=your-api-key-here

# Redis (auto-configured)
REDIS_HOST=localhost
REDIS_PORT=6379
```

Get Gemini API key: https://aistudio.google.com/app/apikey

### 3. Start WebUI:
```cmd
bin\start_webui_with_redis.bat
```

This will:
- ✅ Auto-start Redis if not running
- ✅ Install missing dependencies
- ✅ Start WebUI at http://127.0.0.1:7860

## 🎯 Features

### WebUI Tabs:
1. **Dataset** - Select, tag, analyze datasets
2. **🛠️ Tools** - Resize, convert, deduplicate, validate
3. **Model** - Base model, LoRA settings
4. **Training** - LR, epochs, optimizer
5. **Advanced** - LoRA+, Min-SNR, EMA

### Dataset Tools:
- **🖼️ Resize Images** - Giảm resolution (512x512, 768x768)
- **🔄 Convert Format** - PNG → WebP/JPG
- **🗑️ Remove Duplicates** - Xóa ảnh trùng
- **📁 Organize** - Auto-organize by resolution
- **✅ Validate** - Check lỗi dataset

### AI Features:
- **🤖 Auto Config** - Gemini AI recommendations
- **🏷️ WD14 Tagger** - Local NSFW-safe tagging
- **📊 Analysis** - Dataset quality scoring

## 📦 Requirements

- **Python**: 3.10 or higher
- **RAM**: 8GB minimum, 16GB recommended
- **VRAM**: 8GB for training (optional, can use CPU)
- **Disk**: 10GB free space
- **Docker**: For Redis (optional)

## 🔧 Troubleshooting

### Redis not starting?
```cmd
# Manual start
docker run -d -p 6379:6379 --name lora-redis redis:7-alpine

# Or use WebUI without Redis:
bin\start_webui.bat
```

### Python not found?
```cmd
# Install Python 3.10+ from:
https://www.python.org/downloads/
```

### CUDA errors?
```cmd
# Check GPU compatibility:
nvidia-smi

# Reinstall PyTorch with correct CUDA version
```

### WD14 Tagger issues?
```cmd
# Reinstall WD14
bin\setup_wd14.bat
```

## 📚 Documentation

- **[README.md](README.md)** - Project overview
- **[docs/WEBUI_GUIDE.md](docs/WEBUI_GUIDE.md)** - WebUI detailed guide
- **[docs/GEMINI_INTEGRATION.md](docs/GEMINI_INTEGRATION.md)** - AI features
- **[docs/REDIS_INTEGRATION.md](docs/REDIS_INTEGRATION.md)** - Caching setup
- **[docs/NSFW_TRAINING_GUIDE.md](docs/NSFW_TRAINING_GUIDE.md)** - NSFW training
- **[docs/](docs/)** - All documentation

## 🎯 Scripts Reference

All scripts are in `bin/` folder:

| Script | Description |
|--------|-------------|
| `setup.bat/sh` | One-time environment setup |
| `start_webui_with_redis.bat/sh` | Start WebUI + Redis |
| `start_webui.bat/sh` | Start WebUI only |
| `stop_redis.bat/sh` | Stop Redis container |
| `setup_wd14.bat` | Install WD14 Tagger |
| `quick_tag_nsfw.bat` | Quick NSFW tagging |

See [bin/README.md](bin/README.md) for detailed script documentation.
# Manual start
docker run -d -p 6379:6379 --name ai-assistant-redis redis:7-alpine

# Or skip Redis (fallback mode)
python webui.py
```

### Dependencies error?
```cmd
# Reinstall
.\lora\Scripts\activate.bat
pip install -r requirements.txt --force-reinstall
```

### Port 7860 already in use?
```cmd
# Change port
python webui.py --port 7861
```

## 📚 Workflow Example

### Quick Training Workflow:
```
1. Run: start_webui_with_redis.bat
   ↓
2. Open: http://127.0.0.1:7860
   ↓
3. Dataset tab → Select dataset
   ↓
4. Tools tab → Resize to 512x512 (tiết kiệm VRAM)
   ↓
5. Tools tab → Auto-Tag with WD14 (NSFW safe!)
   ↓
6. Dataset tab → Get AI Config (Gemini recommendations)
   ↓
7. Training tab → Start Training!
```

## 🐳 Docker Alternative

### Using Docker Compose:
```bash
# Start all services (Redis + LoRA Training)
docker-compose up redis lora-training

# Access WebUI
http://localhost:7860
```

### Using Docker directly:
```bash
# Build image
docker build -t lora-training ./train_LoRA_tool

# Run container
docker run -d \
  -p 7860:7860 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/output:/app/output \
  --gpus all \
  lora-training
```

## 🎓 Training Tips

### For Beginners:
1. Start with small dataset (50-100 images)
2. Use 512x512 resolution
3. Let AI recommend config
4. Monitor training logs

### For NSFW Content:
1. Use WD14 Tagger (local, no upload)
2. Gemini only gets metadata (safe!)
3. Enable Redis caching (privacy++)

### Best Performance:
1. Enable Redis (70% faster with caching)
2. Use WebP format (50% smaller)
3. Remove duplicates
4. Batch operations

## 📊 Redis Benefits

| Feature | Without Redis | With Redis |
|---------|--------------|------------|
| Dataset Analysis | 10s each time | 10s once, instant after |
| AI Config | Call Gemini every time | Cached 30min |
| Progress Tracking | Lost on restart | Persistent |
| Multi-client | No | Yes |

## 🔗 Useful Links

- **Gemini API**: https://aistudio.google.com/app/apikey
- **Docker**: https://www.docker.com/
- **Documentation**: ./docs/
- **Issues**: Report bugs on GitHub

## 💡 Quick Commands

```cmd
# Setup environment
setup.bat

# Start WebUI
start_webui_with_redis.bat

# Stop Redis
stop_redis.bat

# View logs
type logs\training.log

# Update dependencies
.\lora\Scripts\activate.bat
pip install -r requirements.txt --upgrade
```

## ✅ Checklist

- [ ] Run `setup.bat` successfully
- [ ] Edit `.env` with Gemini API key
- [ ] Redis container running (or auto-start enabled)
- [ ] WebUI accessible at http://127.0.0.1:7860
- [ ] Test with small dataset first
- [ ] Monitor logs for errors

---

**Happy Training!** 🎉

For more details, see:
- `docs/GEMINI_INTEGRATION.md` - AI config guide
- `docs/NSFW_TRAINING_GUIDE.md` - NSFW safe practices
- `docs/REDIS_INTEGRATION.md` - Redis benefits
- `docs/WEBUI_GUIDE.md` - Complete WebUI docs
