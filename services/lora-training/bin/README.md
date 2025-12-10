# LoRA Training Tool - Scripts

Tất cả scripts tiện ích cho setup và chạy LoRA Training Tool.

## 🚀 Main Scripts

### Setup (Chạy lần đầu)
- **`setup.bat`** (Windows) - Setup môi trường, install dependencies
- **`setup.sh`** (Linux/Mac) - Setup cho Unix systems

### Start WebUI
- **`start_webui_with_redis.bat`** (Windows) - ⭐ Recommended! Start với Redis caching
- **`start_webui_with_redis.sh`** (Linux/Mac) - Start với Redis caching
- **`start_webui.bat`** (Windows) - Start đơn giản (không Redis)
- **`start_webui.sh`** (Linux/Mac) - Start đơn giản

### Redis Management
- **`stop_redis.bat`** (Windows) - Stop Redis container
- **`stop_redis.sh`** (Linux/Mac) - Stop Redis container

### Utilities
- **`setup_wd14.bat`** - Setup WD14 Tagger
- **`quick_tag_nsfw.bat`** - Quick tag NSFW dataset với WD14

---

## 📖 Usage

### First Time Setup:
```bash
# Windows
bin\setup.bat

# Linux/Mac
chmod +x bin/setup.sh
bin/setup.sh
```

### Start WebUI:
```bash
# Windows (với Redis - recommended)
bin\start_webui_with_redis.bat

# Linux/Mac
chmod +x bin/start_webui_with_redis.sh
bin/start_webui_with_redis.sh
```

### Quick NSFW Tagging:
```bash
# Windows
bin\quick_tag_nsfw.bat path\to\your\dataset

# Linux/Mac
bin/quick_tag_nsfw.sh path/to/your/dataset
```

---

## 🔧 Script Details

### `setup.bat/sh`
**Chức năng:**
- Tạo virtual environment (./lora/)
- Chọn PyTorch version (CPU/CUDA 11.8/CUDA 12.1)
- Install tất cả dependencies
- Setup WD14 Tagger
- Install Redis client

**Chỉ cần chạy 1 lần!**

---

### `start_webui_with_redis.bat/sh`
**Chức năng:**
- Auto-activate virtual environment
- Check và auto-start Redis nếu cần
- Install/update dependencies
- Set environment variables
- Start WebUI tại http://127.0.0.1:7860

**Features:**
- ✅ Auto-detect Redis status
- ✅ Fallback nếu Redis fail
- ✅ Auto-create .env file
- ✅ Progress indicators
- ✅ Error handling

---

### `start_webui.bat/sh`
**Chức năng:**
- Start WebUI đơn giản (không Redis)
- Dùng khi không cần caching
- Fallback script

---

### `setup_wd14.bat`
**Chức năng:**
- Download WD14 Tagger models
- Setup cho NSFW tagging
- Test installation

---

### `quick_tag_nsfw.bat`
**Chức năng:**
- Quick tag tất cả images trong dataset
- Sử dụng WD14 Tagger
- 100% local, NSFW-safe

**Usage:**
```bash
bin\quick_tag_nsfw.bat C:\datasets\my_nsfw_dataset
```

---

## 💡 Tips

### Lần đầu sử dụng:
```bash
1. bin\setup.bat
2. Edit .env với GEMINI_API_KEY
3. bin\start_webui_with_redis.bat
```

### Lần sau:
```bash
# Chỉ cần:
bin\start_webui_with_redis.bat
```

### Troubleshooting:
```bash
# Nếu Redis fail
bin\stop_redis.bat
bin\start_webui_with_redis.bat

# Nếu dependencies lỗi
.\lora\Scripts\activate.bat
pip install -r requirements.txt --force-reinstall
```

---

## 📁 Folder Structure

```
bin/
├── setup.bat                          # Setup for Windows
├── setup.sh                           # Setup for Linux/Mac
├── start_webui_with_redis.bat         # ⭐ Start with Redis (Windows)
├── start_webui_with_redis.sh          # ⭐ Start with Redis (Unix)
├── start_webui.bat                    # Simple start (Windows)
├── start_webui.sh                     # Simple start (Unix)
├── stop_redis.bat                     # Stop Redis (Windows)
├── stop_redis.sh                      # Stop Redis (Unix)
├── setup_wd14.bat                     # Setup WD14 Tagger
└── quick_tag_nsfw.bat                 # Quick NSFW tagging
```

---

**See also:**
- [QUICK_START.md](../QUICK_START.md) - Overall quick start guide
- [docs/REDIS_INTEGRATION.md](../docs/REDIS_INTEGRATION.md) - Redis details
- [docs/NSFW_TRAINING_GUIDE.md](../docs/NSFW_TRAINING_GUIDE.md) - NSFW guide

**Last Updated**: 2024-12-01
