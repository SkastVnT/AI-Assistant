# 🔍 RAG Services - Semantic Search & Knowledge Base

> **100% FREE** - No API costs, completely open-source models

## 📋 Overview

**Phase 1: Core RAG Functionality** ✅ (Current)
- Document upload & processing
- Text extraction from multiple formats
- Semantic search with FREE embedding models
- Local vector database (ChromaDB)

**Phase 2: Web UI** 🚧 (Next)
- ChatBot-style interface
- File management
- Search interface
- Results visualization

**Phase 3: RAG Integration** 📅 (Future)
- Q&A with citations
- Multi-document chat
- Context-aware responses

**Phase 4: Advanced Features** 📅 (Future)
- Vietnamese optimization
- Chat history
- Advanced filters

---

## 🎯 Features (Phase 1)

### ✅ Completed
- 📄 **Multi-format support**: PDF, DOCX, PPTX, XLSX, TXT, MD, HTML
- 🔍 **Semantic search**: Find relevant content by meaning, not just keywords
- 💾 **Local vector DB**: ChromaDB - no API calls, unlimited storage
- 🌍 **Vietnamese-optimized**: Using Vietnamese-specific embedding models
- 🆓 **100% FREE**: All models open-source, no paid APIs

### 🛠️ Technical Stack

| Component | Technology | Cost | Why? |
|:----------|:-----------|:-----|:-----|
| **Embedding** | sentence-transformers<br/>`keepitreal/vietnamese-sbert` | FREE | Vietnamese-optimized, 768-dim vectors |
| **Vector DB** | ChromaDB | FREE | Local, persistent, fast similarity search |
| **Document Processing** | pypdf, python-docx, etc. | FREE | Extract text from all formats |
| **Web Framework** | Flask | FREE | Lightweight, easy to extend |
| **LLM (Phase 3)** | Gemini 1.5 Flash | FREE | 15 req/min, 1M context window |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd "RAG Services"

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
copy .env.example .env

# Edit .env (optional - defaults work fine)
notepad .env
```

### 3. Run Server

```bash
python app.py
```

Server starts at: `http://localhost:5003`

---

## 📡 API Endpoints

### Health Check
```bash
GET /api/health
```

Returns system status and statistics.

### Upload Document
```bash
POST /api/upload
Content-Type: multipart/form-data

file: <your-file>
```

Processes document and adds to vector store.

### Semantic Search
```bash
POST /api/search
Content-Type: application/json

{
  "query": "your search query",
  "top_k": 5
}
```

Returns semantically similar chunks.

### List Documents
```bash
GET /api/documents
```

Returns all indexed documents.

### Delete Document
```bash
DELETE /api/documents/<filename>
```

Removes document from vector store.

### Get Statistics
```bash
GET /api/stats
```

Returns vector store statistics.

---

## 💡 Usage Examples

### Upload Document
```bash
curl -X POST http://localhost:5003/api/upload \
  -F "file=@document.pdf"
```

### Search
```bash
curl -X POST http://localhost:5003/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "top_k": 3}'
```

### Python Example
```python
import requests

# Upload
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:5003/api/upload',
        files={'file': f}
    )
print(response.json())

# Search
response = requests.post(
    'http://localhost:5003/api/search',
    json={'query': 'what is AI?', 'top_k': 5}
)
results = response.json()
for result in results['results']:
    print(f"Score: {result['score']:.2f}")
    print(f"Text: {result['text'][:200]}...")
    print(f"Source: {result['metadata']['source']}\n")
```

---

## 🎨 FREE Embedding Models

Choose the best model for your use case:

| Model | Size | Speed | Languages | Best For |
|:------|:-----|:------|:----------|:---------|
| **vietnamese-sbert** | 420MB | Medium | Vietnamese + English | Vietnamese documents (default) |
| **multilingual-MiniLM** | 420MB | Fast | 50+ languages | Fast multilingual search |
| **multilingual-mpnet** | 1.1GB | Medium | 50+ languages | Better quality, slower |
| **LaBSE** | 470MB | Medium | 109 languages | Maximum language support |

To switch models, edit `app/core/config.py`:
```python
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
```

---

## 📊 Architecture

```
RAG Services/
├── app.py                      # Main Flask application
├── app/
│   ├── core/
│   │   ├── config.py          # Settings (FREE models config)
│   │   ├── embeddings.py      # FREE embedding models
│   │   ├── vectorstore.py     # ChromaDB wrapper
│   │   └── document_processor.py  # Extract text from files
│   ├── api/                    # API endpoints (Phase 2)
│   ├── static/                 # CSS, JS (Phase 2)
│   └── templates/              # HTML templates (Phase 2)
├── data/
│   ├── documents/              # Uploaded files
│   └── vectordb/               # ChromaDB persistent storage
└── requirements.txt            # FREE dependencies only
```

---

## 🔧 Configuration

Edit `app/core/config.py` for customization:

```python
# Embedding model
EMBEDDING_MODEL = "keepitreal/vietnamese-sbert"

# Chunking
CHUNK_SIZE = 512       # tokens per chunk
CHUNK_OVERLAP = 50     # overlap between chunks

# Retrieval
TOP_K_RESULTS = 5      # number of results
SIMILARITY_THRESHOLD = 0.7  # minimum similarity

# File limits
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
```

---

## 🎯 Roadmap

### ✅ Phase 1: Core RAG (Current)
- [x] Document processing
- [x] Embedding generation
- [x] Vector storage
- [x] Semantic search API
- [x] FREE models integration

### 🚧 Phase 2: Web UI (Next Week)
- [ ] ChatBot-style interface
- [ ] File upload UI
- [ ] Search interface
- [ ] Results visualization
- [ ] Document management

### 📅 Phase 3: RAG Integration (Week 3)
- [ ] Connect Gemini API (FREE)
- [ ] Q&A with context
- [ ] Citation tracking
- [ ] Multi-turn conversations

### 📅 Phase 4: Advanced (Week 4)
- [ ] Vietnamese sentence segmentation
- [ ] Query expansion
- [ ] Re-ranking
- [ ] Chat history
- [ ] Metadata filters

---

## 💰 Cost Analysis

| Component | Traditional Cost | Our Cost | Savings |
|:----------|:-----------------|:---------|:--------|
| Embedding API | $0.0001/1K tokens | **$0** | 100% |
| Vector Database | $0.40/GB-month | **$0** | 100% |
| LLM API | $0.001/1K tokens | **$0** | 100% |
| Storage | Cloud storage fees | **$0** | 100% |
| **Total** | $50-500/month | **$0** | **100%** |

---

## 🤝 Integration

### With ChatBot Service
```python
# In ChatBot, use RAG for context
import requests

def get_context(query):
    response = requests.post(
        'http://localhost:5003/api/search',
        json={'query': query, 'top_k': 3}
    )
    results = response.json()['results']
    context = '\n\n'.join([r['text'] for r in results])
    return context

# Use in prompt
context = get_context(user_query)
prompt = f"Context:\n{context}\n\nQuestion: {user_query}"
```

---

## 📝 Notes

- **First run**: Models will download (~500MB for Vietnamese SBERT)
- **GPU**: Automatically uses GPU if available (faster)
- **Memory**: ~2GB RAM needed for embedding model
- **Storage**: Depends on your documents (ChromaDB is efficient)

---

## 🐛 Troubleshooting

### Model download fails
```bash
# Set cache directory
export TRANSFORMERS_CACHE=./models
python app.py
```

### Out of memory
```python
# In config.py, switch to smaller model
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
```

### Slow embedding
- Use GPU if available
- Reduce CHUNK_SIZE
- Switch to faster model

---

## 📚 Resources

- [sentence-transformers Docs](https://www.sbert.net/)
- [ChromaDB Docs](https://docs.trychroma.com/)
- [Gemini API](https://ai.google.dev/tutorials/python_quickstart)

---

## 🎉 Next Steps

1. ✅ **Start server**: `python app.py`
2. 📤 **Upload documents**: Use `/api/upload`
3. 🔍 **Try search**: Use `/api/search`
4. 🎨 **Wait for UI**: Phase 2 coming next week!

---

**Version**: 1.0.0 (Phase 1)  
**Port**: 5003  
**Status**: ✅ Core functionality complete  
**Next**: 🎨 Web UI development
