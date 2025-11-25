# 📚 Documentation Hub

Welcome to AI Assistant documentation center!

## 📖 Core Documentation

### 🚀 Getting Started
- [Getting Started Guide](GETTING_STARTED.md) - Complete setup guide for all services
- [Quick Reference Card](QUICK_REFERENCE.md) - Cheat sheet for common tasks
- [Main README](../README.md) - Project overview

### 🏗️ Architecture & API
- [API Documentation](API_DOCUMENTATION.md) - Complete API reference for all services
- [Project Structure](PROJECT_STRUCTURE.md) - Detailed architecture & structure
- [Database Design](DATABASE_CURRENT_STATE.md) - Database schemas & design

### 🔧 Service-Specific Documentation
- [ChatBot v2.0](../ChatBot/README.md) - Multi-model chatbot with auto-file analysis
- [Text2SQL v2.0](../Text2SQL%20Services/README.md) - Natural language to SQL conversion
- [Document Intelligence v1.6](../Document%20Intelligence%20Service/README.md) - OCR + AI processing
- [RAG Services v1.0](../RAG%20Services/README.md) - Retrieval-Augmented Generation
- [Speech2Text v3.6+](../Speech2Text%20Services/README.md) - Vietnamese speech transcription
- [Stable Diffusion](../stable-diffusion-webui/README.md) - Image generation

## 📁 Documentation Structure

```
docs/
├── README.md                      # This file - Documentation index
├── GETTING_STARTED.md             # Complete setup guide
├── QUICK_REFERENCE.md             # Quick reference card
├── API_DOCUMENTATION.md           # API reference
├── PROJECT_STRUCTURE.md           # Architecture & structure
├── DATABASE_CURRENT_STATE.md      # Database design
├── DOCUMENTATION_GUIDELINES.md    # Documentation standards
│
├── archives/                      # Historical documentation
│   └── 2025-11/                  # November 2025 archive
│       ├── 2025-11-06/           # Nov 6 sessions
│       ├── 2025-11-07/           # Nov 7 sessions
│       ├── 2025-11-09/           # Nov 9 sessions
│       ├── 2025-11-10/           # Nov 10 sessions
│       ├── 2025-11-legacy/       # Legacy docs & commits
│       └── *.md                  # Monthly updates
│
├── guides/                        # Detailed guides
│   ├── BUILD_GUIDE.md            # Build & deployment guide
│   ├── IMAGE_GENERATION_GUIDE.md # Image generation guide
│   ├── QUICK_START_IMAGE_GEN.md  # Quick start for images
│   └── GOOGLE_DRIVE_UPLOAD_GUIDE.md # Upload files to Google Drive
│
└── chart_guide/                   # Chart & visualization guides
    ├── FLOWCHART_STANDARDS.md    # Flowchart standards
    └── examples/                 # Chart examples
```

## 🎯 Quick Navigation

**For Developers:**
- 🆕 New to project? → [Getting Started](GETTING_STARTED.md)
- 📝 Need commands? → [Quick Reference](QUICK_REFERENCE.md)
- 🏗️ Understanding structure? → [Project Structure](PROJECT_STRUCTURE.md)
- 🔌 Using APIs? → [API Documentation](API_DOCUMENTATION.md)

**For Operations:**
- 🚀 Deploying services? → [Getting Started](GETTING_STARTED.md)
- ⚙️ Configuration? → [Quick Reference](QUICK_REFERENCE.md)
- 🗄️ Database setup? → [Database Design](DATABASE_CURRENT_STATE.md)

**For Contributors:**
- 📚 Understanding changes? → [Archives](archives/)
- 🔒 Security updates? → [Archives/2025-11-07](archives/2025-11-07/)

## 🔍 Finding Information

| I want to... | Read this |
|--------------|-----------|
| 🚀 Start using the project | [Getting Started](GETTING_STARTED.md) |
| 🏗️ Understand the structure | [Project Structure](PROJECT_STRUCTURE.md) |
| 🔌 Use the APIs | [API Documentation](API_DOCUMENTATION.md) |
| 🗄️ Design databases | [Database Design](DATABASE_CURRENT_STATE.md) |
| ⚡ Quick commands reference | [Quick Reference](QUICK_REFERENCE.md) |
| 📜 See historical changes | [Archives](archives/) |

## 📦 Recent Updates (Nov 2025)

### ✅ Latest Changes: November 2025

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
