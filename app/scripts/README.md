# 🔧 AI-Assistant Scripts

Service management scripts for the AI-Assistant platform.

## 🚀 Quick Start (Linux/Mac)

```bash
# First-time setup
bash scripts/setup-all.sh

# Start all services
bash scripts/start-all.sh

# Check service health
bash scripts/health-check-all.sh

# Expose to public (Cloudflared tunnels)
bash scripts/expose-public.sh

# Interactive menu
bash menu.sh
```

## 🪟 Quick Start (Windows)

```batch
REM Interactive menu
menu.bat

REM Or run individual commands:
scripts\start-all.bat
scripts\health-check-all.bat
```

## 📁 Structure

```
scripts/
├── start-all.sh              # Start all core services
├── stop-all.sh               # Stop all services
├── health-check-all.sh       # Check service status
├── expose-public.sh          # Create public tunnels
├── setup-all.sh              # First-time setup
├── start-*.sh                # Individual service starters
├── deploy-chatbot.sh         # Deploy with backup
├── rollback-chatbot.sh       # Rollback to previous
├── check_system.py           # System requirements checker
├── fix_dependencies.py       # Dependency conflict resolver
├── health_check.py           # Python health checker
└── utilities/                # Utility scripts
```

## 📜 Service Scripts

| Script | Port | Description |
|--------|------|-------------|
| `start-hub-gateway.sh` | 3000 | API Gateway |
| `start-chatbot.sh` | 5000 | Multi-model ChatBot |
| `start-speech2text.sh` | 5001 | Audio transcription |
| `start-text2sql.sh` | 5002 | NL to SQL |
| `start-document-intelligence.sh` | 5003 | OCR + AI |
| `start-stable-diffusion.sh` | 7860 | Image generation |
| `start-edit-image.sh` | 7861 | Image editing |
| `start-lora-training.sh` | 7862 | Model fine-tuning |
| `start-image-upscale.sh` | 7863 | Image enhancement |
| `start-mcp-server.sh` | 8000 | MCP Server |

## 🌐 Public Exposure (Cloudflared)

```bash
bash scripts/expose-public.sh
```

Features:
- No account required (free tier)
- Automatic URL generation
- URLs saved to `logs/` directory
- Temporary URLs (regenerated on restart)

## 📋 check_system.py
System requirements and environment checker.

**Usage:**
```bash
python scripts/check_system.py
```

**Checks:**
- Python version
- CUDA availability
- Required packages
- Disk space
- Memory

### utilities/upload_docs_to_drive.py
Upload documentation to Google Drive.

**Usage:**
```bash
python scripts/utilities/upload_docs_to_drive.py
```

## 📦 Archived Scripts

Old startup and setup scripts have been moved to:
- `archive/` - Old startup scripts
- `deprecated/` - Legacy test scripts

These are kept for reference but are no longer actively used.

## 🚀 New Script System

All service management scripts are now in the **root directory**:

- Individual service launchers: `start-*.bat`
- Batch operations: `start-all.bat`, `stop-all.bat`
- Utilities: `menu.bat`, `setup-all.bat`, `test-all.bat`, `clean-logs.bat`

See [SCRIPTS_GUIDE.md](../SCRIPTS_GUIDE.md) for complete documentation.

---

**Note:** This directory is now minimal and focused. Most operational scripts have been moved to the root for easier access.
