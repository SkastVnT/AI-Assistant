# =============================================================================
# AI-Assistant - Restructured Project
# =============================================================================
# ARCHITECTURE OVERVIEW:
#
# This project follows a microservices architecture with:
# - Modular code structure (controllers, services, models, routes)
# - Shared utilities and configurations
# - Docker containerization with database persistence
# - CI/CD pipeline with GitHub Actions
# - Comprehensive testing (unit, integration, e2e)
# - AI self-learning capabilities
#
# DIRECTORY STRUCTURE:
# ai-assistant/
# ├── docker-compose.yml          # Main orchestration
# ├── .env.example                 # Environment template
# ├── pyproject.toml               # Python project config
# ├── services/                    # Microservices
# │   ├── chatbot/                 # Main chatbot (Port 5000)
# │   │   ├── app/
# │   │   │   ├── __init__.py
# │   │   │   ├── main.py          # Flask app factory
# │   │   │   ├── routes/          # API endpoints
# │   │   │   ├── controllers/     # Business logic
# │   │   │   ├── services/        # External integrations
# │   │   │   ├── models/          # Data models
# │   │   │   └── utils/           # Helpers
# │   │   ├── config/              # Configuration
# │   │   ├── tests/               # Service tests
# │   │   └── Dockerfile
# │   ├── hub-gateway/             # API Gateway (Port 3000)
# │   ├── text2sql/                # NL to SQL (Port 5002)
# │   ├── document-intelligence/   # OCR + AI (Port 5003)
# │   ├── speech2text/             # ASR (Port 5001)
# │   ├── stable-diffusion/        # Image Gen (Port 7860)
# │   ├── lora-training/           # Fine-tuning (Port 7862)
# │   ├── image-upscale/           # Upscaling (Port 7863)
# │   └── mcp-server/              # MCP Protocol
# ├── shared/                      # Shared code
# │   ├── database/                # DB connections
# │   ├── cache/                   # Caching utilities
# │   ├── models/                  # Shared data models
# │   └── utils/                   # Common utilities
# ├── tests/                       # Global tests
# │   ├── unit/
# │   ├── integration/
# │   └── e2e/
# ├── docker/                      # Docker configs
# │   └── mongo-init/              # MongoDB initialization
# ├── .github/                     # CI/CD
# │   └── workflows/
# └── docs/                        # Documentation
#
# =============================================================================
