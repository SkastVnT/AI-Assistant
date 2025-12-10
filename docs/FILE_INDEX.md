# 📋 Complete File Index - AI Assistant

Quick reference for locating any file in the project.

## 📄 Root Level Files

### Essential Documentation
- `README.md` - Main project documentation
- `LICENSE` - MIT License
- `SECURITY.md` - Security policies
- `STRUCTURE.md` - **NEW** Enterprise structure guide
- `PROJECT_ORGANIZATION.md` - File organization history
- `COMPLETE_TEST_SUMMARY.md` - Test suite overview (330+ tests)
- `TESTING_QUICKSTART.md` - Quick testing guide
- `SCRIPTS_GUIDE.md` - **NEW** All batch scripts documentation

### Configuration Files
- `.env.example` - Environment variables template
- `.gitignore` - Git ignore patterns
- `.pre-commit-config.yaml` - Pre-commit hooks
- `pyproject.toml` - Project metadata
- `setup.py` - Package setup
- `requirements.txt` - Root dependencies
- `requirements-test.txt` - Test dependencies
- `pytest.ini` - Pytest configuration

### Batch Scripts (15 files)
**Individual Service Launchers:**
- `start-hub-gateway.bat` - Port 3000
- `start-chatbot.bat` - Port 5001
- `start-text2sql.bat` - Port 5002
- `start-document-intelligence.bat` - Port 5003
- `start-speech2text.bat` - Port 7860
- `start-stable-diffusion.bat` - Port 7861
- `start-lora-training.bat` - Port 7862
- `start-image-upscale.bat` - Port 7863

**Batch Operations:**
- `start-all.bat` - Start all services
- `stop-all.bat` - Stop all services
- `check-status.bat` - Check service status

**Utilities:**
- `menu.bat` - Interactive menu
- `setup-all.bat` - Setup all services
- `test-all.bat` - Run all tests
- `clean-logs.bat` - Clean logs

## 📁 Directory Structure

```
AI-Assistant/
├── services/              # All 8 microservices
├── tests/                 # Test suite (330+ tests)
├── docs/                  # Documentation
├── infrastructure/        # Docker & deployment
├── config/                # Configuration files
├── scripts/               # Utility scripts
├── resources/             # Models, data, assets
├── diagram/               # Architecture diagrams
└── local_data/            # Local development data
```

## 🤖 Services Directory

### services/chatbot/
- `app.py` - Main application
- `README.md` - Service documentation
- `requirements.txt`
- `config/` - MongoDB config
- `src/` - Source code
- `templates/` - HTML templates
- `static/` - CSS/JS files
- `docs/` - 27 feature docs
- `tests/` - Unit tests

### services/text2sql/
- `app_simple.py` - Main application
- `README.md`
- `requirements.txt`
- `src/` - Source code
- `docs/` - Documentation

### services/document-intelligence/
- `app.py` - Main application
- `README.md`
- `SETUP_GUIDE.md`
- `requirements.txt`
- `src/ocr/` - OCR modules
- `templates/` - HTML templates

### services/speech2text/
- `app/web_ui.py` - Main application
- `README.md`
- `requirements.txt`
- `app/api/` - API endpoints
- `docs/` - 10 documentation files

### services/stable-diffusion/
- `webui.py` - Main WebUI
- `README.md`
- `modules/` - Core modules
- `extensions/` - Extensions
- `scripts/` - Utility scripts

### services/lora-training/
- `webui.py` - Training WebUI
- `README.md`
- `requirements.txt`
- `scripts/` - Training scripts
- `utils/` - Utilities
- `docs/` - 15 documentation files

### services/image-upscale/
- `src/upscale_tool/app.py` - Main app
- `README.md`
- `requirements.txt`
- `models/` - AI models

### services/hub-gateway/
- `hub.py` - API Gateway
- `handlers/` - Request handlers
- `utils/` - Utilities

## 🧪 Tests Directory

```
tests/
├── conftest.py                    # Pytest configuration
├── pytest.ini                     # Pytest settings
├── README.md                      # Testing documentation
├── run-tests.bat                  # Test runner (Windows)
├── run-tests.sh                   # Test runner (Linux)
│
├── unit/                          # Unit tests (300+ tests)
│   ├── test_hub.py               # Hub Gateway (50 tests)
│   ├── test_chatbot.py           # ChatBot (40 tests)
│   ├── test_text2sql.py          # Text2SQL (35 tests)
│   ├── test_document_intelligence.py  # Doc Intel (80 tests)
│   ├── test_speech2text.py       # Speech2Text (70 tests)
│   ├── test_lora_training.py     # LoRA (40 tests)
│   ├── test_upscale_tool.py      # Upscale (35 tests)
│   └── test_stable_diffusion.py  # SD (40 tests)
│
├── integration/                   # Integration tests
│   └── test_api_integration.py   # API integration (30+ tests)
│
├── mocks/                         # Mock objects (20+)
│   └── __init__.py
│
└── fixtures/                      # Test data
    └── sample_data.py
```

## 📚 Docs Directory

```
docs/
├── README.md                      # Documentation index
├── GETTING_STARTED.md             # Setup guide
├── API_DOCUMENTATION.md           # API reference
├── QUICK_REFERENCE.md             # Command cheatsheet
├── DATABASE_CURRENT_STATE.md      # Database design
├── DOCUMENTATION_GUIDELINES.md    # Doc standards
├── CHATBOT_MIGRATION_ROADMAP.md   # Migration guide
├── CHANGELOG_v2.2.md              # Version history
├── GOOGLE_DRIVE_SETUP.md          # Drive integration
├── GOOGLE_DRIVE_UPLOAD_GUIDE.md   # Upload guide
│
├── guides/                        # How-to guides
│   ├── BUILD_GUIDE.md
│   ├── IMAGE_GENERATION_GUIDE.md
│   └── QUICK_START_IMAGE_GEN.md
│
├── chart_guide/                   # Visualization guides
│   └── FLOWCHART_STANDARDS.md
│
└── archives/                      # Historical docs
    ├── 2025-11/                  # November 2025
    └── old-summaries/            # 70+ archived files
        └── INDEX.md
```

## ⚙️ Config Directory

```
config/
├── __init__.py
├── logging_config.py              # Logging configuration
├── model_config.py                # AI model configs
├── google_oauth_credentials.json  # OAuth credentials
└── token.pickle                   # Auth tokens
```

## 🔧 Scripts Directory

```
scripts/
├── README.md                      # Scripts documentation
├── check_system.py                # System checker
├── utilities/                     # Utility scripts
│   └── upload_docs_to_drive.py
├── archive/                       # Old startup scripts
└── deprecated/                    # Legacy test scripts
```

## 📦 Resources Directory

```
resources/
├── models/                        # AI model files
│   ├── RealESRGAN_x2plus.pth
│   ├── RealESRGAN_x4plus.pth
│   ├── ScuNET_GAN.pth
│   └── SwinIR_realSR_x4.pth
│
├── data/                          # Application data
│   ├── input/
│   └── output/
│
├── database/                      # Database files
│   ├── PHASE3_COMPLETE.md
│   └── scripts/
│
├── logs/                          # Application logs
├── templates/                     # Shared templates
├── examples/                      # Code examples
│   ├── basic_completion.py
│   ├── chain_prompts.py
│   └── google_drive_upload.py
│
└── assets/                        # Static assets
```

## 🏗️ Infrastructure Directory

```
infrastructure/
├── docker/                        # Docker configs
│   ├── docker-compose.yml        # Multi-service compose
│   ├── Dockerfile                # Main Dockerfile
│   └── .dockerignore             # Docker ignore
│
└── deployment/                    # Deployment
    └── Makefile                  # Build automation
```

## 🎨 Diagram Directory

```
diagram/
├── README.md
├── 01_usecase_diagram.md
├── 02_class_diagram.md
├── 03_sequence_diagrams.md
├── 04_database_design.md
├── 05_er_diagram.md
├── 05_er_diagram_all.md
├── 05_er_diagram_mongodb.md
├── 05_er_cardinality_patterns.md
├── 06_component_diagram.md
├── 07_activity_diagram.md
├── 08_state_diagram.md
└── 09_deployment_diagram.md
```

## 🔍 Quick File Finder

| I need... | Look here |
|-----------|-----------|
| **Start a service** | Root: `start-*.bat` files |
| **Service code** | `services/<service-name>/` |
| **Documentation** | `docs/` or `STRUCTURE.md` |
| **Tests** | `tests/unit/` or `tests/integration/` |
| **Configuration** | `config/` or service-specific `config/` |
| **Scripts** | Root `.bat` files or `scripts/` |
| **Models** | `resources/models/` |
| **Logs** | `resources/logs/` or `services/*/logs/` |
| **Examples** | `resources/examples/` |
| **Architecture** | `diagram/` |
| **Docker** | `infrastructure/docker/` |

## 📊 File Statistics

```
Total Services:        8
Batch Scripts:        15
Documentation Files:  40+
Test Files:          13 (330+ tests)
Archived Docs:       70+
Python Services:      8
```

---

**Last Updated:** December 10, 2025  
**Version:** 2.3  
**Status:** ✅ Clean & Organized
