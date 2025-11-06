# 🤖 RAG Services - Retrieval-Augmented Generation System

> **Advanced Vietnamese-optimized RAG service with multi-LLM support, intelligent caching, and real-time monitoring**  
> **Version:** 1.0.0  
> **Status:** 🚧 In Development  
> **Last Updated:** November 6, 2025

---

## 📋 OVERVIEW

RAG Services là hệ thống Retrieval-Augmented Generation (RAG) tiên tiến, được tối ưu hóa cho tiếng Việt, cung cấp khả năng trả lời câu hỏi dựa trên knowledge base với độ chính xác cao.

### 🎯 Key Features

- ✅ **Multi-LLM Support**: OpenAI GPT-4, DeepSeek, Google Gemini
- ✅ **Vietnamese Optimization**: Tối ưu xử lý tiếng Việt với underthesea
- ✅ **Intelligent Caching**: Redis-based caching để tăng tốc response
- ✅ **Vector Database**: ChromaDB cho semantic search
- ✅ **Real-time Monitoring**: Analytics và performance tracking
- ✅ **Chat History**: Lưu trữ và quản lý conversation context
- ✅ **Content Filtering**: Lọc nội dung không phù hợp
- ✅ **Reliability**: Error handling và fallback mechanisms
- ✅ **Web UI**: Modern interface với real-time updates

---

## 🏗️ ARCHITECTURE

### System Components

```
RAG Services/
├── app/                          # Application core
│   ├── core/                     # Core modules
│   │   ├── rag_engine.py        # RAG orchestration engine
│   │   ├── llm_client.py        # Multi-LLM client wrapper
│   │   ├── vietnamese_processor.py  # Vietnamese NLP
│   │   ├── cache.py             # Redis caching layer
│   │   ├── chat_history.py      # Conversation management
│   │   ├── monitoring.py        # System monitoring
│   │   ├── analytics.py         # Analytics & metrics
│   │   ├── filters.py           # Content filtering
│   │   └── reliability.py       # Error handling
│   ├── api/                     # REST API endpoints
│   ├── static/                  # Frontend assets
│   │   ├── css/                 # Stylesheets
│   │   └── js/
│   │       └── main.js          # Frontend logic
│   └── templates/
│       └── index.html           # Web UI
├── data/                        # Data storage
│   ├── documents/               # Knowledge base documents
│   └── vectordb/                # ChromaDB vector store
├── docs/                        # Documentation
├── RAG/                         # Virtual environment
├── .env                         # Environment configuration
└── README.md                    # This file
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM Providers** | OpenAI, DeepSeek, Gemini | Text generation |
| **Vector DB** | ChromaDB | Semantic search |
| **Cache** | Redis (planned) | Response caching |
| **NLP** | underthesea | Vietnamese processing |
| **Embeddings** | sentence-transformers | Text vectorization |
| **Web Framework** | Flask | API & Web UI |
| **Frontend** | HTML/CSS/JavaScript | User interface |

---

## 🚀 QUICK START

### Prerequisites

- Python 3.11+
- 8GB+ RAM
- Internet connection (for LLM APIs)

### Installation

```bash
# 1. Navigate to RAG Services directory
cd "RAG Services"

# 2. Create virtual environment
python -m venv RAG

# 3. Activate virtual environment
# Windows:
RAG\Scripts\activate
# Linux/Mac:
source RAG/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Configuration

Edit `.env` file:

```properties
# LLM API Keys
OPENAI_API_KEY=sk-proj-your-key-here
DEEPSEEK_API_KEY=sk-your-key-here
GEMINI_API_KEY_1=your-key-here

# Service Configuration
RAG_PORT=5003
FLASK_ENV=development

# Optional: Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Run Service

```bash
# Development mode
python app.py

# Production mode
gunicorn -w 4 -b 0.0.0.0:5003 app:app
```

Service will be available at: `http://localhost:5003`

---

## 📖 CORE MODULES

### 1. RAG Engine (`rag_engine.py`)

**Purpose**: Core orchestration của RAG pipeline

**Key Functions**:
- Document ingestion và indexing
- Query processing và retrieval
- Context assembly
- Response generation

**Usage**:
```python
from app.core.rag_engine import RAGEngine

engine = RAGEngine()
response = engine.query("Câu hỏi của bạn?")
```

### 2. LLM Client (`llm_client.py`)

**Purpose**: Unified interface cho multiple LLM providers

**Supported Models**:
- OpenAI: GPT-4, GPT-4-turbo, GPT-3.5
- DeepSeek: DeepSeek-Chat
- Google: Gemini-2.0-Flash (FREE tier)

**Usage**:
```python
from app.core.llm_client import LLMClient

client = LLMClient(provider="openai", model="gpt-4")
response = client.generate(prompt, context)
```

### 3. Vietnamese Processor (`vietnamese_processor.py`)

**Purpose**: Xử lý và tối ưu văn bản tiếng Việt

**Features**:
- Word segmentation (tách từ)
- POS tagging
- Named Entity Recognition
- Text normalization
- Sentiment analysis

**Usage**:
```python
from app.core.vietnamese_processor import VietnameseProcessor

processor = VietnameseProcessor()
tokens = processor.tokenize("Xin chào Việt Nam")
entities = processor.extract_entities(text)
```

### 4. Cache System (`cache.py`)

**Purpose**: Caching để tăng tốc response time

**Strategy**:
- Query caching: Cache responses cho similar queries
- Embedding caching: Cache computed embeddings
- TTL-based expiration

**Usage**:
```python
from app.core.cache import CacheManager

cache = CacheManager()
cached_response = cache.get(query_hash)
cache.set(query_hash, response, ttl=3600)
```

### 5. Chat History (`chat_history.py`)

**Purpose**: Quản lý conversation context

**Features**:
- Session management
- Context window management
- History persistence
- Context summarization

**Usage**:
```python
from app.core.chat_history import ChatHistory

history = ChatHistory(session_id)
history.add_message("user", message)
context = history.get_context(limit=5)
```

### 6. Monitoring (`monitoring.py`)

**Purpose**: Real-time system monitoring

**Metrics**:
- Request count & rate
- Response time (avg, p95, p99)
- Cache hit rate
- Error rate
- LLM token usage

**Usage**:
```python
from app.core.monitoring import Monitor

monitor = Monitor()
monitor.log_request(duration, tokens, cache_hit)
stats = monitor.get_stats()
```

### 7. Analytics (`analytics.py`)

**Purpose**: Advanced analytics và insights

**Features**:
- Query pattern analysis
- User behavior tracking
- Performance trends
- Cost tracking (LLM API costs)

### 8. Content Filters (`filters.py`)

**Purpose**: Lọc nội dung không phù hợp

**Filter Types**:
- Profanity filter
- PII detection
- Harmful content detection
- Relevance scoring

### 9. Reliability (`reliability.py`)

**Purpose**: Error handling và resilience

**Features**:
- Automatic retry with exponential backoff
- Fallback LLM selection
- Circuit breaker pattern
- Health checks

---

## 🎨 WEB INTERFACE

### Features

- 💬 Real-time chat interface
- 📊 Live performance metrics
- 📜 Conversation history
- ⚙️ Settings panel
- 🎨 Modern, responsive design

### API Endpoints

```
POST   /api/query              # Submit query
GET    /api/history            # Get chat history
GET    /api/stats              # Get system stats
POST   /api/document/upload    # Upload document
DELETE /api/history/clear      # Clear history
GET    /health                 # Health check
```

---

## 📊 PERFORMANCE

### Benchmarks (Target)

| Metric | Target | Current |
|--------|--------|---------|
| Average Response Time | < 2s | TBD |
| Cache Hit Rate | > 70% | TBD |
| Throughput | 100 req/min | TBD |
| Accuracy | > 90% | TBD |
| Uptime | 99.9% | TBD |

### Cost Optimization

**LLM Pricing (per 1M tokens)**:

| Provider | Input | Output | Notes |
|----------|-------|--------|-------|
| OpenAI GPT-4o-mini | $0.15 | $0.60 | Recommended |
| DeepSeek | $0.14 | $0.28 | Most affordable |
| Gemini 2.0 Flash | FREE | FREE | 15 RPM limit |

**Cost Savings**:
- Cache hit → $0 cost
- Smart context trimming → 30-50% token reduction
- Multi-tier LLM strategy → Use cheaper models when possible

---

## 🧪 TESTING

### Run Tests

```bash
# All tests
python -m pytest

# Specific test files
python test_phase6.py
python test_vietnamese.py

# With coverage
pytest --cov=app tests/
```

### Test Categories

- **Unit Tests**: Individual module testing
- **Integration Tests**: End-to-end pipeline
- **Vietnamese NLP Tests**: Language-specific validation
- **Performance Tests**: Load testing, benchmarks

---

## 📚 DOCUMENTATION

### Available Docs

- [Phase 4 Complete](./docs/PHASE4_COMPLETE.md) - Phase 4 completion report
- [Phase 4 Summary](./docs/PHASE4_SUMMARY.md) - Quick summary
- [Phase 4 Frontend](./docs/PHASE4_FRONTEND_COMPLETE.md) - Frontend details
- [Phase 4 Quick Reference](./docs/PHASE4_QUICKREF.md) - Quick ref guide
- [API Documentation](./docs/API_DOCUMENTATION.md) - API reference
- [Deployment Guide](./docs/DEPLOYMENT_GUIDE.md) - Deploy instructions

---

## 🔒 SECURITY

### API Key Management

- ✅ Store keys in `.env` (never commit!)
- ✅ Use environment variables
- ✅ Rotate keys regularly
- ✅ Monitor API usage

### Data Privacy

- No user data logging (except anonymous analytics)
- Document storage is local
- No data sent to 3rd parties (except LLM APIs)
- GDPR-compliant (optional)

---

## 🐛 TROUBLESHOOTING

### Common Issues

#### 1. "LLM API Error"

**Symptom**: API calls failing

**Solution**:
```bash
# Check API keys
cat .env | grep API_KEY

# Verify internet connection
ping api.openai.com

# Check API quotas
# Visit provider dashboards
```

#### 2. "ChromaDB Error"

**Symptom**: Vector database issues

**Solution**:
```bash
# Clear ChromaDB
rm -rf data/vectordb/*

# Reinitialize
python -c "from app.core.rag_engine import RAGEngine; RAGEngine().init_db()"
```

#### 3. "Slow Response Times"

**Symptom**: Queries taking too long

**Solution**:
- Enable caching (Redis)
- Reduce context window size
- Use faster LLM (Gemini free tier)
- Optimize document chunking

#### 4. "Vietnamese Text Issues"

**Symptom**: Poor Vietnamese processing

**Solution**:
```bash
# Reinstall underthesea
pip uninstall underthesea
pip install underthesea==6.7.0

# Verify installation
python -c "from underthesea import word_tokenize; print(word_tokenize('Xin chào'))"
```

---

## 🚧 DEVELOPMENT STATUS

### Completed Phases

- ✅ **Phase 1**: Project setup & structure
- ✅ **Phase 2**: Core RAG engine (Basic)
- ✅ **Phase 3**: LLM integration
- ✅ **Phase 4**: Frontend & Web UI
- ✅ **Phase 5**: Vietnamese optimization
- ✅ **Phase 6**: Advanced features (caching, monitoring)

### Current Phase: Production Readiness

- [ ] Performance optimization
- [ ] Load testing
- [ ] Documentation completion
- [ ] Deployment automation
- [ ] CI/CD pipeline

### Roadmap

**Q1 2026**:
- Redis caching implementation
- Multi-user support
- Advanced analytics dashboard
- Mobile app

**Q2 2026**:
- Fine-tuned Vietnamese LLM
- Custom embedding model
- Enterprise features
- API rate limiting

---

## 🤝 CONTRIBUTING

### Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/SkastVnT/AI-Assistant.git
cd "AI-Assistant/RAG Services"

# 2. Create feature branch
git checkout -b feature/your-feature

# 3. Install dev dependencies
pip install -r requirements-dev.txt

# 4. Make changes and test
python -m pytest

# 5. Commit and push
git commit -m "feat: your feature description"
git push origin feature/your-feature

# 6. Create Pull Request
```

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings (Google style)
- Add unit tests for new features
- Update documentation

---

## 📝 CHANGELOG

### Version 1.0.0 (2025-11-06)

**Added**:
- Initial release
- Multi-LLM support (OpenAI, DeepSeek, Gemini)
- Vietnamese processing with underthesea
- Web UI with real-time updates
- Monitoring and analytics
- Chat history management
- Content filtering
- Reliability features

**Known Issues**:
- Cache system not fully implemented (Redis integration pending)
- Performance optimization needed for large documents
- Mobile UI needs improvement

---

## 📄 LICENSE

This project is part of the AI-Assistant ecosystem.

See [LICENSE](../LICENSE) file for details.

---

## 📞 SUPPORT

### Need Help?

- 📧 Email: support@ai-assistant.com
- 💬 Discord: [Join our community](https://discord.gg/ai-assistant)
- 📖 Docs: [Full Documentation](./docs/)
- 🐛 Issues: [GitHub Issues](https://github.com/SkastVnT/AI-Assistant/issues)

### Team

- **Project Lead**: SkastVnT
- **Contributors**: AI-Assistant Team

---

<div align="center">

## 🎉 RAG SERVICES - READY TO USE

**Build powerful Q&A systems with advanced RAG technology!**

---

**📅 Created:** November 6, 2025  
**👤 Maintainer:** SkastVnT  
**🔄 Version:** 1.0.0  
**📍 Location:** `RAG Services/README.md`  
**🏷️ Tags:** #rag #llm #vietnamese #ai #vectordb #chromadb

[📖 View Documentation](./docs/) | [🚀 Quick Start](#-quick-start) | [🐛 Report Issue](https://github.com/SkastVnT/AI-Assistant/issues)

</div>
