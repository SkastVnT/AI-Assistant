# 👨‍💻 RAG Services - Development Guide

> **Complete guide for developing and contributing to RAG Services**  
> **Version:** 1.0.0  
> **Difficulty:** Intermediate  
> **Last Updated:** November 6, 2025

---

## 📋 OVERVIEW

This guide covers everything you need to know để develop và contribute vào RAG Services project.

---

## 🚀 GETTING STARTED

### Development Environment Setup

#### 1. System Requirements

```bash
# Minimum
- Python 3.11+
- Git 2.30+
- 8GB RAM
- 10GB free disk space

# Recommended
- Python 3.11+
- Git 2.40+
- 16GB RAM
- 20GB SSD
- VS Code / PyCharm
```

#### 2. Clone Repository

```bash
git clone https://github.com/SkastVnT/AI-Assistant.git
cd "AI-Assistant/RAG Services"
```

#### 3. Create Virtual Environment

```bash
# Windows
python -m venv RAG
RAG\Scripts\activate

# Linux/Mac
python3.11 -m venv RAG
source RAG/bin/activate
```

#### 4. Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies
pip install -r requirements-dev.txt

# Or install all
pip install -e ".[dev]"
```

**`requirements-dev.txt`**:
```txt
# Testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
pytest-asyncio==0.21.1

# Code quality
black==23.12.0
flake8==6.1.0
pylint==3.0.3
mypy==1.7.1
isort==5.13.0

# Documentation
sphinx==7.2.6
sphinx-rtd-theme==2.0.0

# Debugging
ipdb==0.13.13
ipython==8.19.0

# Pre-commit hooks
pre-commit==3.5.0
```

#### 5. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your development keys
nano .env
```

**Development `.env`**:
```properties
# Development mode
FLASK_ENV=development
DEBUG=True
TESTING=False

# Use free/cheap APIs for dev
GEMINI_API_KEY_1=your-free-gemini-key
DEEPSEEK_API_KEY=your-cheapest-key

# Local Redis (optional for dev)
REDIS_HOST=localhost
REDIS_PORT=6379

# Logging
LOG_LEVEL=DEBUG
LOG_FILE=logs/dev.log
```

---

## 📁 PROJECT STRUCTURE

```
RAG Services/
├── app/
│   ├── __init__.py              # App factory
│   ├── core/                    # Core business logic
│   │   ├── __init__.py
│   │   ├── rag_engine.py       # Main RAG pipeline
│   │   ├── llm_client.py       # LLM wrapper
│   │   ├── vietnamese_processor.py
│   │   ├── cache.py
│   │   ├── chat_history.py
│   │   ├── monitoring.py
│   │   ├── analytics.py
│   │   ├── filters.py
│   │   └── reliability.py
│   ├── api/                     # API routes
│   │   ├── __init__.py
│   │   ├── query.py
│   │   ├── documents.py
│   │   └── stats.py
│   ├── models/                  # Data models
│   │   ├── __init__.py
│   │   ├── query.py
│   │   └── document.py
│   ├── utils/                   # Utilities
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   └── helpers.py
│   ├── static/                  # Frontend assets
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   └── templates/               # HTML templates
│       └── index.html
├── tests/                       # Test suites
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── unit/                   # Unit tests
│   │   ├── test_rag_engine.py
│   │   ├── test_llm_client.py
│   │   └── test_vietnamese.py
│   ├── integration/            # Integration tests
│   │   ├── test_api.py
│   │   └── test_pipeline.py
│   └── fixtures/               # Test data
│       └── sample_docs.txt
├── data/                       # Application data
│   ├── documents/              # Knowledge base
│   └── vectordb/               # Vector store
├── docs/                       # Documentation
├── logs/                       # Application logs
├── scripts/                    # Utility scripts
│   ├── setup_dev.sh
│   ├── run_tests.sh
│   └── lint.sh
├── .env.example               # Environment template
├── .gitignore
├── .pre-commit-config.yaml    # Pre-commit hooks
├── pytest.ini                 # Pytest config
├── setup.py                   # Package setup
├── requirements.txt           # Production deps
├── requirements-dev.txt       # Development deps
└── README.md
```

---

## 🏗️ ARCHITECTURE

### Core Components

#### 1. RAG Engine (`app/core/rag_engine.py`)

**Responsibilities**:
- Document ingestion & chunking
- Vector embedding
- Semantic search
- Context assembly
- Response generation

**Key Methods**:
```python
class RAGEngine:
    def __init__(self):
        """Initialize RAG engine with dependencies"""
        
    def ingest_document(self, file_path: str) -> str:
        """Ingest and index a document"""
        
    def query(self, query: str, session_id: str = None) -> dict:
        """Process query and generate response"""
        
    def _retrieve_context(self, query: str, k: int = 5) -> list:
        """Retrieve relevant document chunks"""
        
    def _generate_response(self, query: str, context: list) -> str:
        """Generate response using LLM"""
```

#### 2. LLM Client (`app/core/llm_client.py`)

**Purpose**: Unified interface for multiple LLM providers

**Interface**:
```python
class LLMClient:
    def __init__(self, provider: str = "openai", model: str = "gpt-4"):
        """Initialize LLM client"""
        
    def generate(
        self,
        prompt: str,
        context: str = None,
        **kwargs
    ) -> str:
        """Generate text completion"""
        
    def embed(self, text: str) -> list[float]:
        """Generate text embedding"""
```

#### 3. Vietnamese Processor (`app/core/vietnamese_processor.py`)

**Purpose**: Vietnamese NLP pipeline

**Features**:
```python
class VietnameseProcessor:
    def tokenize(self, text: str) -> list[str]:
        """Word segmentation"""
        
    def pos_tag(self, text: str) -> list[tuple]:
        """Part-of-speech tagging"""
        
    def extract_entities(self, text: str) -> list[dict]:
        """Named Entity Recognition"""
        
    def normalize(self, text: str) -> str:
        """Text normalization"""
```

---

## 🎨 CODING STANDARDS

### Python Style Guide

Follow **PEP 8** with these additions:

```python
# 1. Imports ordering (use isort)
import os  # stdlib
import sys

import chromadb  # third-party
import openai

from app.core.rag_engine import RAGEngine  # local


# 2. Type hints
def process_query(query: str, model: str = "gpt-4") -> dict:
    """Process user query with specified model.
    
    Args:
        query: User's question
        model: LLM model to use
        
    Returns:
        dict with answer and metadata
    """
    pass


# 3. Docstrings (Google style)
class RAGEngine:
    """Main RAG pipeline orchestrator.
    
    This class handles document ingestion, vector search,
    and response generation using LLMs.
    
    Attributes:
        vectorstore: ChromaDB instance
        llm_client: LLM client wrapper
        
    Example:
        >>> engine = RAGEngine()
        >>> result = engine.query("What is AI?")
        >>> print(result["answer"])
    """


# 4. Error handling
try:
    result = llm_client.generate(prompt)
except OpenAIError as e:
    logger.error(f"OpenAI API error: {e}")
    raise APIException("LLM generation failed") from e


# 5. Logging
import logging

logger = logging.getLogger(__name__)

def process():
    logger.info("Starting process")
    logger.debug("Debug info: %s", data)
    logger.warning("Warning message")
    logger.error("Error occurred", exc_info=True)


# 6. Constants
MAX_TOKENS = 4000
DEFAULT_MODEL = "gpt-4"
CACHE_TTL = 3600


# 7. Configuration
from dataclasses import dataclass

@dataclass
class Config:
    """Application configuration"""
    model: str = "gpt-4"
    max_tokens: int = 500
    temperature: float = 0.7
```

### Code Formatting

```bash
# Format code with black
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/
pylint app/ tests/

# Type checking
mypy app/ tests/
```

---

## 🧪 TESTING

### Test Structure

```python
# tests/unit/test_rag_engine.py
import pytest
from app.core.rag_engine import RAGEngine


class TestRAGEngine:
    """Test RAG Engine functionality"""
    
    @pytest.fixture
    def engine(self):
        """Create RAG engine instance"""
        return RAGEngine()
    
    def test_init(self, engine):
        """Test initialization"""
        assert engine.vectorstore is not None
        assert engine.llm_client is not None
    
    def test_query_basic(self, engine):
        """Test basic query"""
        result = engine.query("What is AI?")
        assert "answer" in result
        assert isinstance(result["answer"], str)
        assert len(result["answer"]) > 0
    
    @pytest.mark.parametrize("query,expected", [
        ("Hello", "greeting"),
        ("Xin chào", "vietnamese"),
    ])
    def test_query_types(self, engine, query, expected):
        """Test different query types"""
        result = engine.query(query)
        assert expected in result["metadata"]["type"]
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_rag_engine.py

# Specific test
pytest tests/unit/test_rag_engine.py::TestRAGEngine::test_query_basic

# With coverage
pytest --cov=app --cov-report=html

# With verbose output
pytest -v

# Stop on first failure
pytest -x

# Run only marked tests
pytest -m "unit"
pytest -m "integration"
```

### Test Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=term --cov-report=html

# View HTML report
open htmlcov/index.html  # Mac/Linux
start htmlcov/index.html  # Windows
```

**Coverage targets**:
- Overall: > 80%
- Core modules: > 90%
- Utils: > 70%

---

## 🔍 DEBUGGING

### Using Debugger

```python
# 1. Using pdb
import pdb

def process_query(query):
    pdb.set_trace()  # Breakpoint
    result = engine.query(query)
    return result


# 2. Using ipdb (better)
import ipdb

def process_query(query):
    ipdb.set_trace()
    result = engine.query(query)
    return result


# 3. Using VS Code debugger
# Add breakpoint in editor (F9)
# Run with debugger (F5)
```

### Logging for Debug

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Log variables
logger.debug("Query: %s", query)
logger.debug("Context: %s", context[:100])
logger.debug("Response time: %.2f", duration)
```

---

## 🚀 DEVELOPMENT WORKFLOW

### 1. Create Feature Branch

```bash
# Update master
git checkout master
git pull origin master

# Create feature branch
git checkout -b feature/your-feature-name

# Or bugfix
git checkout -b bugfix/issue-123
```

### 2. Make Changes

```bash
# Edit files
vim app/core/new_feature.py

# Add tests
vim tests/unit/test_new_feature.py

# Run tests
pytest tests/unit/test_new_feature.py

# Check code quality
black app/
flake8 app/
```

### 3. Commit Changes

```bash
# Stage changes
git add app/core/new_feature.py tests/unit/test_new_feature.py

# Commit with conventional commit message
git commit -m "feat: add new feature for X

- Implemented feature Y
- Added tests for Z
- Updated documentation

Closes #123"
```

**Commit Message Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

### 4. Push and Create PR

```bash
# Push to remote
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# - Add description
# - Link related issues
# - Request reviewers
```

### 5. Code Review

- Address review comments
- Make requested changes
- Push updates to same branch
- PR updates automatically

### 6. Merge

After approval:
```bash
# Merge via GitHub UI
# Or locally:
git checkout master
git merge feature/your-feature-name
git push origin master
```

---

## 🛠️ USEFUL SCRIPTS

### Development Scripts

**`scripts/setup_dev.sh`**:
```bash
#!/bin/bash
# Setup development environment

python -m venv RAG
source RAG/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
echo "Development environment ready!"
```

**`scripts/run_tests.sh`**:
```bash
#!/bin/bash
# Run all tests with coverage

pytest --cov=app --cov-report=term --cov-report=html tests/
echo "Coverage report: htmlcov/index.html"
```

**`scripts/lint.sh`**:
```bash
#!/bin/bash
# Run all linters

echo "Running black..."
black app/ tests/

echo "Running isort..."
isort app/ tests/

echo "Running flake8..."
flake8 app/ tests/

echo "Running pylint..."
pylint app/ tests/

echo "Running mypy..."
mypy app/ tests/

echo "All checks complete!"
```

---

## 📚 DOCUMENTATION

### Writing Documentation

- Follow DOCUMENTATION_GUIDELINES.md
- Use clear, concise language
- Include code examples
- Add diagrams when helpful
- Keep docs updated with code

### Building Docs

```bash
# Using Sphinx
cd docs/
make html

# View docs
open _build/html/index.html
```

---

## 🆘 GETTING HELP

### Resources

- 📖 [Project Documentation](./docs/)
- 💬 [Discord Community](https://discord.gg/ai-assistant)
- 🐛 [GitHub Issues](https://github.com/SkastVnT/AI-Assistant/issues)
- 📧 Email: dev@ai-assistant.com

### Asking Questions

When asking for help:
1. Search existing issues first
2. Provide context (what you're trying to do)
3. Include error messages
4. Share relevant code snippets
5. Describe what you've tried

---

<div align="center">

## 🎉 DEVELOPMENT GUIDE COMPLETE

**Happy coding! Build amazing features!**

---

**📅 Created:** November 6, 2025  
**👤 Author:** SkastVnT  
**🔄 Version:** 1.0.0  
**📍 Location:** `RAG Services/docs/DEVELOPMENT_GUIDE.md`

[🏠 Back to Docs](../README.md) | [🧪 Testing Guide](./TESTING_GUIDE.md)

</div>
