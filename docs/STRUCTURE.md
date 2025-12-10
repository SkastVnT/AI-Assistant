# 🏗️ AI-Assistant - Reorganized Project Structure

> **Reorganized:** December 10, 2025  
> **Status:** ✅ Clean & Professional Enterprise Structure

---

## 📊 New Structure Overview

```
AI-Assistant/
│
├── 📄 ROOT LEVEL (Essential Files Only)
│   ├── README.md                          # Main documentation
│   ├── COMPLETE_TEST_SUMMARY.md           # Test suite overview
│   ├── TESTING_QUICKSTART.md              # Quick test guide
│   ├── PROJECT_ORGANIZATION.md            # Structure guide
│   ├── SECURITY.md                        # Security policies
│   ├── LICENSE                            # MIT License
│   │
│   ├── .env.example                       # Environment template
│   ├── .gitignore                         # Git ignore rules
│   ├── .pre-commit-config.yaml           # Pre-commit hooks
│   │
│   ├── requirements.txt                   # Python dependencies
│   ├── requirements-test.txt              # Test dependencies
│   ├── pyproject.toml                     # Project metadata
│   ├── setup.py                          # Package setup
│   │
│   ├── pytest.ini                        # Pytest configuration
│   ├── run-tests.bat                     # Windows test runner
│   └── run-tests.sh                      # Linux/Mac test runner
│
├── 🤖 services/                          # All Microservices
│   ├── chatbot/                          # ChatBot Service
│   │   ├── app.py
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   ├── src/
│   │   ├── templates/
│   │   ├── static/
│   │   ├── docs/
│   │   └── tests/
│   │
│   ├── text2sql/                         # Text2SQL Service
│   │   ├── app_simple.py
│   │   ├── README.md
│   │   ├── requirements.txt
│   │   ├── src/
│   │   └── docs/
│   │
│   ├── document-intelligence/            # Document Intelligence
│   │   ├── app.py
│   │   ├── README.md
│   │   ├── SETUP_GUIDE.md
│   │   ├── src/ocr/
│   │   └── templates/
│   │
│   ├── speech2text/                      # Speech2Text Service
│   │   ├── README.md
│   │   ├── app/api/
│   │   ├── requirements.txt
│   │   └── docs/
│   │
│   ├── stable-diffusion/                 # Stable Diffusion WebUI
│   │   ├── webui.py
│   │   ├── README.md
│   │   ├── modules/
│   │   ├── extensions/
│   │   └── scripts/
│   │
│   ├── image-upscale/                    # Image Upscale Tool
│   │   ├── README.md
│   │   ├── src/upscale_tool/
│   │   ├── requirements.txt
│   │   └── docs/
│   │
│   ├── lora-training/                    # LoRA Training Tool
│   │   ├── webui.py
│   │   ├── README.md
│   │   ├── scripts/
│   │   ├── configs/
│   │   └── docs/
│   │
│   └── hub-gateway/                      # API Gateway (Hub)
│       ├── hub.py
│       ├── __init__.py
│       ├── handlers/
│       └── utils/
│
├── 🧪 tests/                             # Testing Infrastructure
│   ├── README.md                         # Testing documentation
│   ├── conftest.py                       # Pytest fixtures
│   ├── pytest.ini                        # Pytest config
│   │
│   ├── unit/                             # Unit tests
│   │   ├── test_hub.py                   # Hub Gateway (50 tests)
│   │   ├── test_chatbot.py               # ChatBot (40 tests)
│   │   ├── test_text2sql.py              # Text2SQL (35 tests)
│   │   ├── test_document_intelligence.py # Doc Intelligence (80 tests)
│   │   ├── test_speech2text.py           # Speech2Text (70 tests)
│   │   ├── test_lora_training.py         # LoRA Training (40 tests)
│   │   ├── test_upscale_tool.py          # Upscale (35 tests)
│   │   └── test_stable_diffusion.py      # SD WebUI (40 tests)
│   │
│   ├── integration/                      # Integration tests
│   │   └── test_api_integration.py       # API integration (30 tests)
│   │
│   ├── mocks/                            # Mock objects
│   │   └── __init__.py                   # 20+ mock classes
│   │
│   └── fixtures/                         # Test fixtures
│       └── sample_data.py                # Sample test data
│
├── 📚 docs/                              # Documentation Hub
│   ├── README.md                         # Docs index
│   ├── GETTING_STARTED.md                # Setup guide
│   ├── API_DOCUMENTATION.md              # API reference
│   ├── PROJECT_STRUCTURE.md              # Architecture
│   ├── QUICK_REFERENCE.md                # Commands
│   ├── DATABASE_CURRENT_STATE.md         # Database info
│   ├── CHANGELOG_v2.2.md                 # Version history
│   │
│   ├── guides/                           # How-to guides
│   ├── chart_guide/                      # Visualization guides
│   │
│   └── archives/                         # Historical docs
│       ├── 2025-11/                      # Monthly archives
│       └── old-summaries/                # Old summary files
│           └── INDEX.md                  # Archive index
│
├── 🏗️ infrastructure/                    # Infrastructure & DevOps
│   ├── docker/                           # Docker configuration
│   │   ├── docker-compose.yml            # Multi-service compose
│   │   ├── Dockerfile                    # Main Dockerfile
│   │   └── .dockerignore                 # Docker ignore
│   │
│   └── deployment/                       # Deployment scripts
│       └── Makefile                      # Build automation
│
├── ⚙️ config/                            # Configuration Files
│   ├── __init__.py
│   ├── logging_config.py                 # Logging setup
│   ├── model_config.py                   # AI model configs
│   ├── google_oauth_credentials.json     # OAuth credentials
│   └── token.pickle                      # Auth tokens
│
├── 🔧 scripts/                           # Utility Scripts
│   ├── setup/                            # Setup scripts
│   ├── startup/                          # Startup scripts
│   ├── utilities/                        # Helper utilities
│   ├── training/                         # Training scripts
│   ├── stable-diffusion/                 # SD utilities
│   │
│   ├── check_system.py                   # System checker
│   ├── test_runner.py                    # Advanced test runner
│   ├── cleanup_and_reupload.py           # Cleanup utility
│   ├── upload_to_drive.py                # Google Drive upload
│   ├── upload_docs_to_drive.py           # Docs uploader
│   ├── test_google_drive.py              # Drive test
│   ├── test_sd_api.py                    # SD API test
│   ├── install_pytorch_cuda.bat          # PyTorch installer
│   ├── run-tests.bat                     # Test runner (Windows)
│   └── run-tests.sh                      # Test runner (Linux)
│
├── 📦 resources/                         # Resources & Assets
│   ├── models/                           # AI model files
│   │   ├── RealESRGAN_x2plus.pth
│   │   ├── RealESRGAN_x4plus.pth
│   │   ├── ScuNET_GAN.pth
│   │   └── SwinIR_realSR_x4.pth
│   │
│   ├── data/                             # Application data
│   │   ├── input/
│   │   └── output/
│   │
│   ├── database/                         # Database files
│   │   ├── PHASE3_COMPLETE.md
│   │   └── scripts/
│   │
│   ├── logs/                             # Application logs
│   │
│   ├── templates/                        # Shared templates
│   │
│   ├── examples/                         # Code examples
│   │   ├── basic_completion.py
│   │   ├── chain_prompts.py
│   │   └── google_drive_upload.py
│   │
│   └── assets/                           # Static assets
│       └── standard_base_project_structure.png
│
├── 🎨 diagram/                           # Architecture Diagrams
│   ├── README.md
│   ├── 01_usecase_diagram.md
│   ├── 02_class_diagram.md
│   ├── 03_sequence_diagrams.md
│   ├── 04_database_design.md
│   ├── 05_er_diagram.md
│   ├── 05_er_diagram_all.md
│   ├── 05_er_diagram_mongodb.md
│   ├── 05_er_cardinality_patterns.md
│   ├── 06_component_diagram.md
│   ├── 07_activity_diagram.md
│   ├── 08_state_diagram.md
│   └── 09_deployment_diagram.md
│
└── 🔐 .github/                           # GitHub Configuration
    └── workflows/                        # CI/CD workflows

```

---

## 🎯 Key Improvements

### ✅ Before vs After

**Before (Messy):**
```
❌ 7 service folders mixed in root
❌ data/, models/, templates/ scattered
❌ docker-compose.yml in root
❌ config files everywhere
❌ Hard to find what you need
```

**After (Clean):**
```
✅ All services in services/
✅ All resources in resources/
✅ All infrastructure in infrastructure/
✅ Clear separation of concerns
✅ Enterprise-grade structure
```

---

## 📁 Directory Purpose

| Directory | Purpose | Contents |
|-----------|---------|----------|
| `services/` | **All Microservices** | 8 independent services |
| `tests/` | **Test Suite** | 330+ unit & integration tests |
| `docs/` | **Documentation** | Guides, API docs, archives |
| `infrastructure/` | **DevOps** | Docker, deployment configs |
| `config/` | **Configuration** | App configs, credentials |
| `scripts/` | **Utilities** | Helper scripts, automation |
| `resources/` | **Assets** | Models, data, templates, logs |
| `diagram/` | **Architecture** | System diagrams (mermaid) |
| `.github/` | **CI/CD** | GitHub workflows |

---

## 🤖 Services Structure

All services follow consistent structure:

```
services/<service-name>/
├── README.md              # Service documentation
├── app.py / webui.py      # Main application
├── requirements.txt       # Dependencies
├── Dockerfile            # Container config (if any)
├── src/                  # Source code
├── templates/            # HTML templates (if web)
├── static/              # Static files (if web)
├── docs/                # Service-specific docs
└── tests/               # Service tests
```

### Service List

1. **chatbot/** - Multi-model AI ChatBot (Port 5001)
2. **text2sql/** - Natural Language to SQL (Port 5002)
3. **document-intelligence/** - OCR & Document Analysis (Port 5003)
4. **speech2text/** - Audio Transcription & Diarization (Port 7860)
5. **stable-diffusion/** - AI Image Generation (Port 7861)
6. **image-upscale/** - Image Enhancement (RealESRGAN)
7. **lora-training/** - LoRA Model Fine-tuning
8. **hub-gateway/** - API Gateway & Orchestrator (Port 3000)

---

## 📦 Resources Organization

### models/
AI model weights (RealESRGAN, SwinIR, ScuNET)

### data/
- `input/` - Input data
- `output/` - Generated output

### database/
Database schemas and scripts

### logs/
Application logs (auto-generated)

### templates/
Shared HTML templates

### examples/
Code usage examples

### assets/
Images, diagrams, static files

---

## 🏗️ Infrastructure

### docker/
- `docker-compose.yml` - Multi-service orchestration
- `Dockerfile` - Container image
- `.dockerignore` - Ignore patterns

### deployment/
- `Makefile` - Build automation

---

## 🔧 Scripts Organization

### setup/
Initial setup and installation scripts

### startup/
Service startup scripts

### utilities/
Helper utilities and tools

### training/
ML model training scripts

### stable-diffusion/
SD-specific utilities

---

## 🧪 Testing Structure

```
tests/
├── unit/              # Isolated component tests
│   └── test_*.py     # 8 test files, 300+ tests
├── integration/       # Service interaction tests
│   └── test_api_integration.py
├── mocks/            # Mock objects (20+)
└── fixtures/         # Test data
```

**Total: 330+ tests with 85%+ coverage**

---

## 📚 Documentation Structure

```
docs/
├── Core Docs          # Getting started, API, structure
├── guides/            # Step-by-step tutorials
├── chart_guide/       # Visualization guides
└── archives/          # Historical documentation
    ├── 2025-11/       # Monthly archives
    └── old-summaries/ # Old summary files (23 files)
```

---

## 🚀 Quick Navigation

| Task | Command / Path |
|------|----------------|
| 🏁 **Start** | `README.md` |
| 🤖 **Run ChatBot** | `cd services/chatbot && python app.py` |
| 📊 **Run Text2SQL** | `cd services/text2sql && python app_simple.py` |
| 🧪 **Run Tests** | `.\run-tests.bat` or `pytest` |
| 📖 **Read Docs** | `docs/GETTING_STARTED.md` |
| 🐳 **Deploy All** | `cd infrastructure/docker && docker-compose up` |
| ⚙️ **Configure** | Edit files in `config/` |
| 📦 **Add Models** | Place in `resources/models/` |
| 🔧 **Run Script** | `python scripts/<script-name>.py` |

---

## 💡 Benefits

### 🎯 Clear Separation
- Services isolated in `services/`
- Infrastructure separate from code
- Resources centralized

### 📦 Scalability
- Easy to add new services
- Modular architecture
- Independent deployment

### 🧹 Maintainability
- Consistent structure across services
- Clear naming conventions
- Easy to locate files

### 🚀 Developer Experience
- Quick navigation
- Intuitive organization
- Professional structure

---

## 🔄 Migration Notes

### Changed Paths

| Old Path | New Path |
|----------|----------|
| `ChatBot/` | `services/chatbot/` |
| `Text2SQL Services/` | `services/text2sql/` |
| `Document Intelligence Service/` | `services/document-intelligence/` |
| `Speech2Text Services/` | `services/speech2text/` |
| `stable-diffusion-webui/` | `services/stable-diffusion/` |
| `train_LoRA_tool/` | `services/lora-training/` |
| `upscale_tool/` | `services/image-upscale/` |
| `src/hub.py` | `services/hub-gateway/hub.py` |
| `docker-compose.yml` | `infrastructure/docker/docker-compose.yml` |
| `models/` | `resources/models/` |
| `data/` | `resources/data/` |
| `templates/` | `resources/templates/` |
| `logs/` | `resources/logs/` |
| `examples/` | `resources/examples/` |

### Update Required

If you have scripts or configs with hardcoded paths, update them:

```python
# Old
from src.hub import app

# New  
from services.hub_gateway.hub import app
```

```yaml
# Old
volumes:
  - ./models:/models

# New
volumes:
  - ./resources/models:/models
```

---

## 📊 Statistics

```
Services:              8 microservices
Tests:                 330+ test cases
Test Coverage:         85%+
Documentation Files:   30+ active docs
Archived Docs:         70+ files
Lines of Code:         50,000+
Supported AI Models:   10+
```

---

## 🎓 Best Practices

1. **Keep root clean** - Only essential files in root
2. **Follow structure** - Maintain consistency across services
3. **Document changes** - Update docs when adding features
4. **Use resources/** - Don't create new top-level data folders
5. **Centralize configs** - Use `config/` for shared configs
6. **Test everything** - Add tests in `tests/unit/`

---

**Reorganized by:** SkastVnT  
**Date:** December 10, 2025  
**Version:** 2.3 (Enterprise Structure)
