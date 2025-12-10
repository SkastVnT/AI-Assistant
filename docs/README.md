# 📚 Documentation Hub

Welcome to AI Assistant documentation center!

## 📖 Core Documentation

### 🚀 Getting Started
- [Getting Started Guide](GETTING_STARTED.md) - Complete setup guide for all services
- [Quick Reference Card](QUICK_REFERENCE.md) - Cheat sheet for common tasks
- [Main README](../README.md) - Project overview
- [Project Structure](../STRUCTURE.md) - **NEW** Enterprise-grade structure guide

### 🏗️ Architecture & API
- [API Documentation](API_DOCUMENTATION.md) - Complete API reference for all services
- [Database Design](DATABASE_CURRENT_STATE.md) - Database schemas & design
- [Project Organization](../PROJECT_ORGANIZATION.md) - File organization & cleanup history

### 🔧 Service-Specific Documentation
- [ChatBot v2.0](../services/chatbot/README.md) - Multi-model chatbot with image generation
- [Text2SQL v2.0](../services/text2sql/README.md) - Natural language to SQL conversion
- [Document Intelligence v1.6](../services/document-intelligence/README.md) - OCR + AI processing
- [Speech2Text v3.6+](../services/speech2text/README.md) - Vietnamese speech transcription
- [Stable Diffusion](../services/stable-diffusion/README.md) - AI image generation
- [LoRA Training](../services/lora-training/README.md) - Fine-tune AI models
- [Image Upscale](../services/image-upscale/README.md) - Image enhancement

## 📁 Documentation Structure

```
docs/
├── README.md                      # This file - Documentation index
├── GETTING_STARTED.md             # Complete setup guide
├── QUICK_REFERENCE.md             # Quick reference card
├── API_DOCUMENTATION.md           # API reference
├── DATABASE_CURRENT_STATE.md      # Database design
├── DOCUMENTATION_GUIDELINES.md    # Documentation standards
├── CHATBOT_MIGRATION_ROADMAP.md   # ChatBot migration guide
├── CHANGELOG_v2.2.md              # Version 2.2 changelog
├── GOOGLE_DRIVE_SETUP.md          # Google Drive integration
├── GOOGLE_DRIVE_UPLOAD_GUIDE.md   # Google Drive upload guide
│
├── archives/                      # Historical documentation
│   ├── 2025-11/                  # November 2025 archive
│   │   ├── 2025-11-06/           # Nov 6 sessions
│   │   ├── 2025-11-07/           # Nov 7 sessions
│   │   ├── 2025-11-09/           # Nov 9 sessions
│   │   ├── 2025-11-10/           # Nov 10 sessions
│   │   └── 2025-11-legacy/       # Legacy docs & commits
│   └── old-summaries/            # Archived summary files (70+ files)
│       └── INDEX.md              # Archive index
│
├── guides/                        # Detailed guides
│   ├── BUILD_GUIDE.md            # Build & deployment guide
│   ├── IMAGE_GENERATION_GUIDE.md # Image generation guide
│   └── QUICK_START_IMAGE_GEN.md  # Quick start for images
│
└── chart_guide/                   # Chart & visualization guides
    ├── FLOWCHART_STANDARDS.md    # Flowchart standards
    └── examples/                 # Chart examples
```
**For Developers:**
- 🆕 New to project? → [Getting Started](GETTING_STARTED.md)
- 📝 Need commands? → [Quick Reference](QUICK_REFERENCE.md)
- 🏗️ Understanding structure? → [Project Structure](../STRUCTURE.md) ⭐ NEW!
- 🔌 Using APIs? → [API Documentation](API_DOCUMENTATION.md)

**For Operations:**
- 🚀 Deploying services? → [Getting Started](GETTING_STARTED.md)
- ⚙️ Configuration? → [Quick Reference](QUICK_REFERENCE.md)
- 🗄️ Database setup? → [Database Design](DATABASE_CURRENT_STATE.md)
- 📊 Testing? → [Testing Guide](../TESTING_QUICKSTART.md) or [Complete Tests](../COMPLETE_TEST_SUMMARY.md)

**For Contributors:**
- 📚 Understanding changes? → [Archives](archives/)
- 📂 Project organization? → [Organization Guide](../PROJECT_ORGANIZATION.md)
- 🔒 Security updates? → [Archives/2025-11-07](archives/2025-11-07/)
**For Contributors:**
| I want to... | Read this |
|--------------|-----------|
| 🚀 Start using the project | [Getting Started](GETTING_STARTED.md) |
| 🏗️ Understand the structure | [Project Structure](../STRUCTURE.md) ⭐ |
| 🔌 Use the APIs | [API Documentation](API_DOCUMENTATION.md) |
| 🗄️ Design databases | [Database Design](DATABASE_CURRENT_STATE.md) |
| ⚡ Quick commands reference | [Quick Reference](QUICK_REFERENCE.md) |
| 🧪 Run tests | [Testing Quickstart](../TESTING_QUICKSTART.md) |
| 📂 Understand organization | [Project Organization](../PROJECT_ORGANIZATION.md) |
| 📜 See historical changes | [Archives](archives/) |ING_STARTED.md) |
| 🏗️ Understand the structure | [Project Structure](PROJECT_STRUCTURE.md) |
| 🔌 Use the APIs | [API Documentation](API_DOCUMENTATION.md) |
## 📦 Recent Updates (Dec 2025)

### ✅ Latest Changes: December 10, 2025

**Major Project Restructure:**
- 🏗️ **Enterprise-grade structure** - All services moved to `services/`
- 📁 **Resource consolidation** - Models, data, templates in `resources/`
- 🏭 **Infrastructure separation** - Docker configs in `infrastructure/`
- 📊 **Complete test suite** - 330+ tests with 85%+ coverage
- 🧹 **Documentation cleanup** - Archived 70+ old summaries, removed duplicates
- ✅ **Professional organization** - Clear separation of concerns

**Key Documents:**
- 📘 [STRUCTURE.md](../STRUCTURE.md) - Complete project structure guide
- 📗 [PROJECT_ORGANIZATION.md](../PROJECT_ORGANIZATION.md) - Organization history
- 📙 [COMPLETE_TEST_SUMMARY.md](../COMPLETE_TEST_SUMMARY.md) - Test suite overview
- 📕 [TESTING_QUICKSTART.md](../TESTING_QUICKSTART.md) - Quick testing guide

### ✅ Previous Updates: November 2025

**Structure Reorganization (Nov 25, 2025):**
- 🗂️ Consolidated all November archives into `archives/2025-11/`
- 🧹 Cleaned up legacy documentation folders
- 📝 Merged `guide docs/` into `docs/guides/`
- ✅ Simplified documentation structure

**Development Archive:**
- 🔒 Security fixes (12 vulnerabilities patched)
- 🔐 MongoDB credential leak remediation
- 🚀 ChatBot v2.0 Phase 2 development
- 📚 Historical documentation archived
- 🔒 Security fixes (12 vulnerabilities patched)
- 🔐 MongoDB credential leak remediation
- 🚀 ChatBot v2.0 Phase 2 development
- 📚 Historical documentation archived

### 🆕 Active Development

- **ChatBot v2.0** - Phase 2: Multimodal AI + Advanced Image Gen (30% complete)
- **Text2SQL v2.0** - AI Learning + Question Generation
- **Document Intelligence v1.6** - Batch Processing + Templates
- **RAG Services v1.0** - Caching + Monitoring (Production Ready)
- **Speech2Text v3.6+** - Web UI Ready

## 💡 Documentation Standards

All documentation follows:
- ✅ Clear structure with sections
- ✅ Code examples with syntax highlighting
- ✅ Visual diagrams where helpful
- ✅ Table of contents for long docs
- ✅ Cross-references to related docs
- ✅ Regular archival of historical documentation

## 🤝 Contributing to Docs

When adding new documentation:
1. Place in appropriate `docs/` or service folder
2. Update this index
3. Add cross-references
4. Follow markdown standards
5. Include examples

---

**Last Updated**: November 25, 2025 | **Version**: 2.1.0
