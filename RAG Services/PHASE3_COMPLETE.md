# 🤖 Phase 3 Complete - RAG Integration with LLM

## ✅ Features Implemented

### 1. **FREE LLM Integration**
- ✅ Google Gemini API (FREE tier)
- ✅ 15 requests/minute limit
- ✅ 1,500 requests/day limit
- ✅ 1M token context window
- ✅ No cost for personal use

### 2. **RAG Engine**
- ✅ Retrieve relevant chunks (semantic search)
- ✅ Generate answers with LLM
- ✅ Citation tracking
- ✅ Source attribution
- ✅ Confidence scoring

### 3. **Dual Mode Interface**
- ✅ **Search Mode**: Find relevant chunks
- ✅ **RAG Q&A Mode**: AI-generated answers
- ✅ Toggle between modes
- ✅ Visual mode indicators

### 4. **Answer Display**
- ✅ Beautiful AI answer card
- ✅ Markdown formatting support
- ✅ Source documents with relevance scores
- ✅ Expandable search results
- ✅ Copy functionality

### 5. **Smart Features**
- ✅ Language detection (Vietnamese/English)
- ✅ Context-aware responses
- ✅ Top-K retrieval control
- ✅ Error handling
- ✅ Status indicators

---

## 🚀 How to Use RAG Mode

### 1. Get FREE Gemini API Key

Visit: https://makersuite.google.com/app/apikey

1. Sign in with Google account
2. Click "Create API Key"
3. Copy the key

### 2. Configure API Key

**Option A: Environment Variable (Recommended)**
```bash
# Windows
set GEMINI_API_KEY=your_api_key_here

# Linux/Mac
export GEMINI_API_KEY=your_api_key_here
```

**Option B: .env File**
```bash
# Create or edit .env file
echo GEMINI_API_KEY=your_api_key_here >> .env
```

### 3. Start Server
```bash
python app.py
```

### 4. Use RAG Mode

1. Upload your documents
2. Click **"RAG Q&A"** button (purple mode)
3. Ask questions in natural language
4. Get AI-generated answers with sources!

---

## 🎯 RAG vs Search Mode

### Search Mode (Blue)
- **What it does**: Finds relevant text chunks
- **Output**: List of matching passages with scores
- **Use when**: You want to browse relevant content
- **Example**: "machine learning" → Shows 5 chunks mentioning ML

### RAG Q&A Mode (Purple)
- **What it does**: AI generates comprehensive answer
- **Output**: Natural language answer + sources
- **Use when**: You want a direct answer to a question
- **Example**: "What is machine learning?" → Full explanation

---

## 📡 New API Endpoints

### RAG Query
```bash
POST /api/rag/query
Content-Type: application/json

{
  "query": "What is machine learning?",
  "top_k": 5,
  "language": "auto"  // auto, vi, en
}
```

**Response:**
```json
{
  "answer": "Machine learning is a subset of AI...",
  "sources": [
    {
      "name": "ml_intro.pdf",
      "relevance": 0.95,
      "file_type": ".pdf"
    }
  ],
  "retrieved_chunks": 5,
  "model": "gemini-1.5-flash"
}
```

### Check RAG Status
```bash
GET /api/rag/status
```

**Response:**
```json
{
  "available": true,
  "model": "gemini-1.5-flash",
  "message": "RAG ready"
}
```

---

## 🎨 UI Features

### Mode Toggle
- **Blue button**: Search mode
- **Purple button**: RAG Q&A mode
- **Status badge**: Shows current mode info

### RAG Answer Card
- **Gradient background**: Purple/blue
- **Robot icon**: AI indicator
- **Formatted text**: Bold, italic, code blocks
- **Sources section**: Documents used with scores
- **Expandable details**: View source chunks

### Smart Highlighting
- Query terms highlighted in yellow
- Relevance scores color-coded
- Source attribution visible

---

## 💡 Example Queries

### Good RAG Questions:
✅ "What is machine learning?"  
✅ "How does neural network work?"  
✅ "Explain the differences between..."  
✅ "Summarize the main points about..."  
✅ "What are the applications of..."  

### Search Queries:
✅ "machine learning algorithms"  
✅ "neural network architecture"  
✅ "deep learning examples"  

---

## 🔧 Configuration

### LLM Settings (config.py)

```python
# LLM Provider
LLM_PROVIDER = "gemini"  # Options: gemini, ollama, huggingface

# Gemini Model (FREE)
GEMINI_MODEL = "gemini-1.5-flash"  # Fast and free
# GEMINI_MODEL = "gemini-1.5-pro"  # Better quality, same free tier

# Retrieval
TOP_K_RESULTS = 5  # More context = better answers
SIMILARITY_THRESHOLD = 0.7  # Minimum relevance
```

### Rate Limits (FREE Tier)

| Limit | Value |
|:------|:------|
| Requests per minute | 15 |
| Requests per day | 1,500 |
| Context window | 1M tokens |
| Cost | **$0** |

---

## 🛠️ Architecture

### RAG Pipeline

```
User Question
     ↓
[1] Semantic Search
     ↓
Retrieved Chunks (Top-K)
     ↓
[2] Build Context
     ↓
LLM Prompt (Question + Context)
     ↓
[3] Gemini API
     ↓
Generated Answer
     ↓
Display with Sources
```

### Code Structure

```
RAG Services/
├── app/
│   ├── core/
│   │   ├── llm_client.py       # Gemini API wrapper
│   │   ├── rag_engine.py       # RAG pipeline
│   │   ├── vectorstore.py      # Search
│   │   └── config.py           # Settings
│   │
│   ├── static/js/main.js       # Frontend RAG logic
│   └── templates/index.html    # RAG UI
│
└── app.py                       # RAG endpoints
```

---

## 🎯 Prompt Engineering

### Our RAG Prompt Template:

```
You are a helpful AI assistant that answers questions 
based on provided documents.

IMPORTANT INSTRUCTIONS:
1. Answer using ONLY information from documents
2. If documents don't contain info, say so clearly
3. Cite sources by mentioning document names
4. Be concise but comprehensive
5. Detect language and respond in same language
6. Use markdown formatting

DOCUMENTS:
[Retrieved chunks here]

USER QUESTION:
[User query here]

ANSWER:
```

### Why This Works:
- ✅ Clear boundaries (only use documents)
- ✅ Source citation requirement
- ✅ Language flexibility
- ✅ Markdown for better formatting
- ✅ Handles missing information gracefully

---

## 🚀 Advanced Usage

### Python API Example

```python
import requests

# RAG Query
response = requests.post(
    'http://localhost:5003/api/rag/query',
    json={
        'query': 'What is the main topic?',
        'top_k': 5,
        'language': 'vi'  # Force Vietnamese
    }
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")
```

### Integrate with Other Services

```python
# In ChatBot service
import requests

def get_rag_answer(question):
    response = requests.post(
        'http://localhost:5003/api/rag/query',
        json={'query': question}
    )
    return response.json()['answer']

# Use in chat
user_question = "What is AI?"
rag_answer = get_rag_answer(user_question)
```

---

## 🐛 Troubleshooting

### No API Key Error
```
⚠️ LLM not configured. Please set GEMINI_API_KEY
```

**Solution:**
1. Get key from https://makersuite.google.com/app/apikey
2. Set environment variable or .env file
3. Restart server

### Rate Limit Exceeded
```
Error: Resource exhausted (quota)
```

**Solution:**
- Wait 1 minute (15 req/min limit)
- Or wait for daily reset (1500 req/day)
- Consider using Ollama for unlimited local LLM

### Poor Answer Quality
**Solutions:**
- Increase `TOP_K_RESULTS` (more context)
- Lower `SIMILARITY_THRESHOLD` (more relevant chunks)
- Upload more relevant documents
- Use more specific questions

---

## 💰 Cost Comparison

| Service | This RAG | OpenAI GPT-4 | Anthropic Claude |
|:--------|:---------|:-------------|:-----------------|
| **Embedding** | $0 (local) | $0.0001/1K | $0.0001/1K |
| **Vector DB** | $0 (local) | $0.40/GB-month | $0.40/GB-month |
| **LLM** | $0 (Gemini) | $0.03/1K tokens | $0.015/1K tokens |
| **Monthly (1000 queries)** | **$0** | ~$50 | ~$25 |
| **Yearly** | **$0** | ~$600 | ~$300 |

**Total Savings: $300-600/year** 💰

---

## 🎉 Phase 3 Status

**Status**: ✅ **COMPLETE**

**Achievement Unlocked:**
- 🤖 Full RAG pipeline
- 💬 AI-generated answers
- 📚 Source citations
- 🆓 100% FREE models
- 🎨 Beautiful UI integration

**Ready for**: Phase 4 - Advanced Features

---

## 📚 Alternative LLM Options

### If Gemini Quota Exhausted:

**1. Ollama (Local, Unlimited)**
```bash
# Install Ollama
# Then:
ollama pull llama2
ollama pull mistral
```

**2. HuggingFace Inference API (FREE tier)**
```python
# config.py
LLM_PROVIDER = "huggingface"
HF_MODEL = "google/flan-t5-large"
```

**3. Local Models**
```python
# config.py
LLM_PROVIDER = "local"
LOCAL_MODEL = "Qwen2.5-1.5B-Instruct"
```

---

## 🎓 Learning Resources

- [Gemini API Docs](https://ai.google.dev/tutorials/python_quickstart)
- [RAG Explained](https://www.pinecone.io/learn/retrieval-augmented-generation/)
- [Prompt Engineering Guide](https://www.promptingguide.ai/)

---

**Version**: 1.0.0 (Phase 3)  
**Port**: 5003  
**Status**: ✅ RAG Complete  
**Next**: 🚀 Advanced Features (Phase 4)
