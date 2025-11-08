# 🚀 AI Assistant - Quick Reference Card

## 📡 Port Configuration

| Service | Port | URL | Status |
|---------|------|-----|--------|
| **Hub Gateway** | `3000` | http://localhost:3000 | ✅ Safe (no conflicts) |
| **ChatBot** | `5000` | http://localhost:5000 | ✅ Available |
| **Text2SQL** | `5001` | http://localhost:5001 | ✅ Available |
| **Speech2Text** | `5002` | http://localhost:5002 | ✅ Available |
| **Document Intelligence** | `5003` | http://localhost:5003 | ✅ Available |
| **RAG Services** | `5004` | http://localhost:5004 | ✅ Available |
| **Stable Diffusion** | `7860` | http://localhost:7860 | ✅ Available |
| ~~Kafka UI~~ | ~~8080~~ | - | ⚠️ Reserved for Kafka |

> **Note**: Port 3000 được chọn để tránh conflict với Kafka UI (8080)

---

## 🔑 API Keys Location

### Master .env File
```bash
d:\WORK\AI assistant\.env
```

Contains all API keys for:
- ✅ OpenAI API
- ✅ DeepSeek API  
- ✅ Google Gemini API (2 keys)
- ✅ HuggingFace Token
- ✅ ClickHouse credentials

### Service-specific .env
- `ChatBot/.env` - ChatBot only keys
- `Speech2Text Services/.env` - Speech2Text only keys
- `Text2SQL Services/.env` - Text2SQL only keys

---

## ⚡ Quick Start Commands

### Start Hub Gateway
```bash
cd "d:\WORK\AI assistant"
python hub.py
# → http://localhost:3000
```

### Start All Services (Windows)
```bash
cd "d:\WORK\AI assistant"
start_all.bat
```

### Start All Services (Linux/Mac)
```bash
cd "d:\WORK\AI assistant"
./start_all.sh
```

### Individual Services
```bash
# ChatBot
cd "d:\WORK\AI assistant\ChatBot"
python app.py

# Speech2Text
cd "d:\WORK\AI assistant\Speech2Text Services\app"
python web_ui.py

# Text2SQL
cd "d:\WORK\AI assistant\Text2SQL Services"
python app.py
```

---

## 🔍 Check Port Usage

### Windows
```powershell
netstat -ano | findstr "3000 5000 5001 5002"
```

### Linux/Mac
```bash
lsof -i :3000,5000,5001,5002
```

---

## 🧪 Test Endpoints

### Hub Gateway Health Check
```bash
curl http://localhost:3000/api/health
```

### Get All Services
```bash
curl http://localhost:3000/api/services
```

### Get Hub Statistics
```bash
curl http://localhost:3000/api/stats
```

---

## 📁 Project Structure Quick Ref

```
AI-Assistant/
├── .env                    # ✅ Master environment file
├── hub.py                  # Entry point (port 3000)
├── config/                 # Hub configuration
│   └── model_config.py     # PORT = 3000
├── src/                    # Hub source code
├── examples/               # Usage examples
└── [Services]/             # Individual services
```

---

## 🛠️ Common Tasks

### Update API Keys
1. Edit `.env` file in root
2. Keys auto-loaded on restart
3. No need to restart if using python-dotenv

### Change Hub Port
1. Edit `config/model_config.py`:
   ```python
   PORT = int(os.getenv("HUB_PORT", "3000"))
   ```
2. Or set environment variable:
   ```bash
   export HUB_PORT=4000  # Linux/Mac
   $env:HUB_PORT=4000    # PowerShell
   ```

### Check Service Status
```bash
# Visit Hub Dashboard
http://localhost:3000

# Or check individual service
curl http://localhost:5000/health
curl http://localhost:5001/health  
curl http://localhost:5002/health
```

---

## 🔥 Troubleshooting

### Port Already in Use
```bash
# Find process using port
netstat -ano | findstr :3000

# Kill process (Windows)
taskkill /PID <PID> /F

# Kill process (Linux/Mac)
kill -9 <PID>
```

### API Keys Not Working
1. Check `.env` file exists
2. Verify no spaces around `=`
3. Check keys not expired
4. Try using `.env.example` as template

### Service Not Starting
1. Check Python version (3.8+)
2. Install requirements: `pip install -r requirements.txt`
3. Check logs in `logs/` directory
4. Verify port not in use

---

## 📚 Documentation Links

| Document | Description |
|----------|-------------|
| [README.md](README.md) | Main overview |
| [QUICKSTART.md](QUICKSTART.md) | Quick setup guide |
| [Hub Gateway Guide](docs/HUB_README.md) | Hub Gateway details |
| [Project Structure](docs/PROJECT_STRUCTURE.md) | Complete structure |
| [All Docs](docs/README.md) | Documentation hub |

---

## 🎯 Development Workflow

### 1. Start Development
```bash
# Start Hub
python hub.py

# Start services you need
cd ChatBot && python app.py
```

### 2. Make Changes
- Edit code in `src/` or service directories
- Flask auto-reloads in debug mode

### 3. Test Changes
```bash
# Run examples
cd examples
python basic_completion.py
```

### 4. Commit Changes
```bash
git add .
git commit -m "feat: your changes"
git push origin master
```

---

## 💡 Pro Tips

1. **Use .env file**: Never hardcode API keys
2. **Check ports first**: Avoid conflicts
3. **Read logs**: `logs/hub.log` has all info
4. **Use Hub Dashboard**: Easy service navigation
5. **Start Hub first**: Then individual services

---

## 🔐 Security Reminders

- ✅ `.env` is in `.gitignore`
- ✅ Never commit API keys
- ✅ Rotate keys regularly
- ✅ Use different keys for production
- ✅ Set strong `FLASK_SECRET_KEY`

---

## 📊 Service Dependencies

```
Hub Gateway (3000)
├── Flask
├── Flask-CORS
└── python-dotenv

ChatBot (5000)
├── Flask
├── openai
└── google-generativeai

Speech2Text (5001)
├── Flask
├── whisper
└── pyannote.audio

Text2SQL (5002)
├── Flask
└── google-generativeai
```

---

## 🚀 Production Deployment

### Using Docker
```bash
# Build image
docker build -t ai-assistant-hub .

# Run container
docker run -p 3000:3000 --env-file .env ai-assistant-hub
```

### Using setup.py
```bash
# Install as package
pip install -e .

# Run hub
hub
```

---

<div align="center">

**Last Updated**: October 28, 2025 | **Version**: 2.0.0

[GitHub Repository](https://github.com/SkastVnT/AI-Assistant)

</div>
