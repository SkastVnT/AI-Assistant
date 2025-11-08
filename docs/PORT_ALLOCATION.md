# AI Assistant - Port Allocation Guide

## 🎯 Port Overview

| Service | Port | Status | URL | Purpose |
|---------|------|--------|-----|---------|
| **Hub Gateway** | **3000** | 🟢 Active | http://localhost:3000 | **Giao diện chính - BẮT ĐẦU TỪ ĐÂY** |
| ChatBot | 5000 | 🟢 Active | http://localhost:5000 | Multi-model AI chatbot |
| Text2SQL | 5001 | 🟢 Active | http://localhost:5001 | Natural language to SQL |
| Speech2Text | 5002 | 🟢 Active | http://localhost:5002 | Vietnamese speech-to-text |
| Document Intelligence | 5003 | 🟢 Active | http://localhost:5003 | OCR + AI document analysis |
| RAG Services | 5004 | 🟢 Active | http://localhost:5004 | Retrieval-Augmented Generation |
| Stable Diffusion | 7860 | 🟢 Active | http://localhost:7860 | Text-to-image generation |

## 🚀 Recommended Startup Order

### Method 1: Hub First (Recommended)
```batch
1. Start Hub Gateway (3000)
   cd i:\AI-Assistant\scripts\startup
   start_hub.bat

2. Open Hub in browser
   http://localhost:3000

3. From Hub UI, click "Mở dịch vụ" on any service card
   → Service opens in new tab automatically
```

### Method 2: All Services (Full Experience)
```batch
cd i:\AI-Assistant\scripts\startup
start_all_services.bat

# This starts all 7 services (Hub + 6 services) in separate terminals
# Wait 30-60 seconds, then open http://localhost:3000
```

### Method 3: Individual Services (Development)
```batch
# Terminal 1: Hub
cd i:\AI-Assistant
venv_hub\Scripts\activate.bat
python src\hub.py

# Terminal 2+: Start specific services as needed
cd i:\AI-Assistant\ChatBot
venv_chatbot\Scripts\activate.bat
python app.py
```

## 📊 Port Allocation Strategy

### Design Principles:
1. **Hub = 3000** - Gateway/Homepage (không conflict với React dev server 3001)
2. **Services = 5000-5004** - Consecutive ports cho dễ nhớ
3. **Stable Diffusion = 7860** - Default SD WebUI port
4. **Reserved = 8000-8999** - Future services/databases

### Port Ranges:
```
3000         → Hub Gateway (entry point)
5000-5004    → AI Services (main)
7860         → Image Generation
8000+        → Databases/Infrastructure (if needed)
```

## 🔍 Port Conflict Resolution

### Check if port is in use:
```powershell
# Windows
netstat -ano | findstr ":3000"
netstat -ano | findstr ":5000"

# Get process info
tasklist | findstr "<PID>"
```

### Kill process using port:
```powershell
# Find PID
netstat -ano | findstr ":3000"

# Kill by PID
taskkill /PID <process-id> /F
```

### Change port if needed:
Edit `config/model_config.py`:
```python
PORT = int(os.getenv("HUB_PORT", "3000"))  # Change 3000 to another port
```

## 🌐 Service Communication Flow

```
┌─────────────────────────────────────────┐
│   User Browser                          │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│   Hub Gateway (Port 3000)               │
│   ================================       │
│   - Service directory                   │
│   - Service health checks               │
│   - One-click service launch            │
│   - API endpoints                       │
└─────────────┬───────────────────────────┘
              │
              ├──────────────────────┬──────────────┬──────────────┬────────────┬──────────────┐
              │                      │              │              │            │              │
              ▼                      ▼              ▼              ▼            ▼              ▼
        ┌──────────┐           ┌──────────┐   ┌──────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐
        │ ChatBot  │           │ Text2SQL │   │ Speech2  │  │   Doc   │  │   RAG   │  │    SD    │
        │  (5000)  │           │  (5001)  │   │Text(5002)│  │Int(5003)│  │ (5004)  │  │  (7860)  │
        └──────────┘           └──────────┘   └──────────┘  └─────────┘  └─────────┘  └──────────┘
```

## 🛡️ Security Considerations

### Production Deployment:
1. **Change default ports** for security
2. **Use reverse proxy** (nginx/Apache)
3. **Enable HTTPS** with SSL certificates
4. **Configure CORS** properly (restrict origins)
5. **Add authentication** to Hub
6. **Use environment variables** for sensitive configs

### Example nginx configuration:
```nginx
# Hub Gateway
location / {
    proxy_pass http://localhost:3000;
}

# ChatBot Service
location /chatbot {
    proxy_pass http://localhost:5000;
}

# Other services...
```

## 📱 Mobile/Remote Access

### LAN Access:
```bash
# Find your local IP
ipconfig  # Windows

# Access from other devices on same network
http://<your-local-ip>:3000
```

### Internet Access (NOT RECOMMENDED without security):
```bash
# Port forwarding on router
External Port: 80 → Internal: 3000

# Better: Use ngrok for testing
ngrok http 3000
```

## 🔧 Environment Configuration

### Hub (.env):
```bash
HUB_PORT=3000
HUB_HOST=0.0.0.0
DEBUG=True
CORS_ORIGINS=*
```

### Services (Individual .env files):
```bash
# ChatBot/.env
PORT=5000

# Text2SQL Services/.env
PORT=5001

# etc...
```

## 📈 Monitoring

### Check all services status:
```powershell
# Check all ports at once
netstat -ano | findstr "3000 5000 5001 5002 5003 5004 7860"
```

### Hub API health check:
```bash
curl http://localhost:3000/api/health
curl http://localhost:3000/api/services
```

## 💡 Best Practices

1. ✅ **Always start Hub first** - It's your main entry point
2. ✅ **Use `start_all_services.bat`** for full experience
3. ✅ **Keep ports consistent** - Don't change unless necessary
4. ✅ **Document port changes** - Update this file if you change ports
5. ✅ **Test after changes** - Verify all services work after config changes
6. ✅ **Close cleanly** - Use Ctrl+C to stop services properly

## 🎓 Quick Reference Commands

```batch
# Start Hub
cd i:\AI-Assistant\scripts\startup && start_hub.bat

# Start All
cd i:\AI-Assistant\scripts\startup && start_all_services.bat

# Check Ports
netstat -ano | findstr "3000 5000 5001 5002 5003 5004 7860"

# Kill All Services
taskkill /F /IM python.exe

# Setup Virtual Environments
cd i:\AI-Assistant\scripts\startup && setup_all_venvs.bat
```

## 📚 Related Documentation

- [HUB_QUICKSTART.md](./HUB_QUICKSTART.md) - Hub setup guide
- [VENV_SETUP_GUIDE.md](./VENV_SETUP_GUIDE.md) - Virtual environment setup
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - General reference
- Service-specific READMEs in each service directory

---

**Last Updated:** November 8, 2025  
**Version:** 2.0  
**Maintainer:** SkastVnT
